"""
Tests de l'API, sans téléchargement de modèle ni appel de LLM :
- le corpus est réellement lu, découpé et indexé (Qdrant en mémoire et BM25) ;
- un encodeur factice (sac de mots haché) remplace FastEmbed ;
- un LLM factice remplace outils_llm.demander.

Lancement, depuis le dossier backend : pytest
"""

import os
import zlib

os.environ["LANGSMITH_TRACING"] = "false"  # avant l'import du paquet : aucun envoi vers LangSmith

import httpx
import numpy as np
import openai
import pytest
from fastapi.testclient import TestClient

from app import outils_llm as llm
from app import rag
from app.config import Reglages
from app.main import creer_application


class EncodeurFactice:
    """Sac de mots haché sur 512 dimensions : assez pour retrouver des extraits par leurs mots."""

    nom, dimension = "factice", 512

    def encoder(self, textes):
        vecteurs = np.zeros((len(textes), self.dimension), dtype=np.float32)
        for i, texte in enumerate(textes):
            for mot in rag.tokeniser(texte):
                vecteurs[i, zlib.crc32(mot.encode()) % self.dimension] += 1
        return vecteurs / np.maximum(np.linalg.norm(vecteurs, axis=1, keepdims=True), 1e-9)


def llm_factice(prompt, *, systeme=None, modele=None, **_):
    """Répond « non trouvé » si la question porte sur un sujet absent, sinon cite l'extrait 1."""
    texte = rag.NON_TROUVE if "télétravail" in prompt else "Selon la documentation, oui [1]."
    return llm.Reponse(texte=texte, modele=modele, tokens_entree=100, tokens_sortie=10,
                       latence_s=0.01, cout_usd=0.0)


@pytest.fixture(scope="module")
def assistant():
    extraits = rag.decouper(rag.charger_corpus(), "sections", 800, 100, entete=True)
    return rag.Assistant(rag.Index(extraits, EncodeurFactice()), reranker=None, modele="groq:modele-factice", k=4)


@pytest.fixture
def client(assistant, monkeypatch):
    monkeypatch.setattr(rag.llm, "demander", llm_factice)
    app = creer_application(fabrique=lambda reglages: assistant, reglages=Reglages(reranking=False))
    with TestClient(app) as c:  # le bloc with exécute le cycle de vie (construction de l'assistant)
        yield c


def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "ok" and corps["extraits_indexes"] > 20
    assert corps["langsmith"] is False


def test_documents_publics_seulement(client):
    fichiers = [d["fichier"] for d in client.get("/api/documents").json()]
    assert "cgv_fictiva.pdf" in fichiers
    assert "procedure_sav_interne.md" not in fichiers


def test_exemples(client):
    exemples = client.get("/api/exemples").json()
    assert 3 <= len(exemples) <= 6


def test_question_avec_citation(client):
    r = client.post("/api/question", json={"question": "Livrez-vous en France ?"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["trouve"] is True
    assert len(corps["extraits"]) == 4
    assert [e["numero"] for e in corps["extraits"] if e["cite"]] == [1]
    assert corps["sources"] == [corps["extraits"][0]["fichier"]]


def test_question_hors_corpus(client):
    corps = client.post("/api/question", json={"question": "Quelle est la politique de télétravail ?"}).json()
    assert corps["trouve"] is False
    assert corps["sources"] == []


def test_question_trop_courte(client):
    assert client.post("/api/question", json={"question": "?"}).status_code == 422


def test_recherche_sans_document_interne(client):
    r = client.post("/api/recherche", json={"question": "Quelle remise maximale accorder à un client ?", "k": 6})
    assert r.status_code == 200
    extraits = r.json()["extraits"]
    assert len(extraits) == 6
    assert all(e["fichier"] != "procedure_sav_interne.md" for e in extraits)


def test_erreur_du_modele(client, monkeypatch):
    def en_panne(*args, **kwargs):
        raise openai.APIConnectionError(request=httpx.Request("POST", "http://localhost"))

    monkeypatch.setattr(rag.llm, "demander", en_panne)
    r = client.post("/api/question", json={"question": "Livrez-vous en France ?"})
    assert r.status_code == 502


def test_metriques_de_recherche():
    extraits = [rag.Extrait(id=i, texte=t, source="s", titre="t", confidentialite="public")
                for i, t in enumerate(["sans rapport", "délai de 30 jours", "autre", "frais de 15 %"])]
    indices = ["30 jours", "15 %"]
    assert rag.couverture(extraits, indices) == 1.0
    assert rag.precision_a_k(extraits, indices) == 0.5
    assert rag.precision_moyenne(extraits, indices) == pytest.approx((1 / 2 + 2 / 4) / 2)
    assert rag.rang_premier_pertinent(extraits, indices) == 2
