"""
evaluation_rag.py : évaluation de l'assistant documentaire (atelier 2.C) et observabilité LangSmith.

- metriques_recherche : context recall et context precision@k sans LLM, à partir
  des indices du golden set ;
- evaluer_ragas : les métriques de la bibliothèque RAGAS (fidélité, pertinence de la
  réponse, précision et rappel du contexte, exactitude), calculées par un LLM juge
  open-weight et les embeddings FastEmbed locaux ;
- activer_langsmith : traces des appels de modèles dans LangSmith, si ses clés sont
  dans .env (LANGSMITH_TRACING=true, LANGSMITH_API_KEY, LANGSMITH_PROJECT).
"""

from __future__ import annotations

import asyncio
import functools
import os

import pandas as pd

import outils_llm as llm
import rag

METRIQUES_RAGAS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]


# ---------------------------------------------------------------------------
# Métriques de recherche sans LLM
# ---------------------------------------------------------------------------

def metriques_recherche(extraits: list[rag.Extrait], entree: dict) -> dict:
    """Rappel et précision du contexte pour une entrée du golden set (indices de référence)."""
    if not entree["indices"]:
        return {}
    rang = rag.rang_premier_pertinent(extraits, entree["indices"])
    return {
        "context_recall": rag.couverture(extraits, entree["indices"]),
        "precision_a_k": rag.precision_a_k(extraits, entree["indices"]),
        "context_precision": rag.precision_moyenne(extraits, entree["indices"]),
        "reciprocal_rank": 1 / rang if rang else 0.0,
    }


# ---------------------------------------------------------------------------
# RAGAS : LLM juge et embeddings
# ---------------------------------------------------------------------------

def llm_ragas(modele: str | None = None):
    """LLM juge de RAGAS, branché sur un fournisseur d'outils_llm (format OpenAI)."""
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    fournisseur, nom = llm.decouper(modele or llm.choisir_modele())
    url, variable = llm.FOURNISSEURS[fournisseur]
    client = AsyncOpenAI(base_url=url, api_key=os.getenv(variable), max_retries=10)
    # max_tokens : les modèles de raisonnement (gpt-oss, Nemotron) consomment des tokens avant de répondre ;
    # avec la valeur par défaut de RAGAS (1 024), la sortie structurée du juge est tronquée.
    return llm_factory(nom, client=client, max_tokens=8192)


@functools.cache
def _classe_embeddings():
    from ragas.embeddings import BaseRagasEmbedding

    class EmbeddingsFastEmbed(BaseRagasEmbedding):
        """Embeddings locaux (FastEmbed) au format attendu par RAGAS."""

        def __init__(self, encodeur: rag.Encodeur):
            self.encodeur = encodeur

        def embed_text(self, text: str, **kwargs) -> list[float]:
            return self.encodeur.encoder([text])[0].tolist()

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return self.embed_text(text)

    return EmbeddingsFastEmbed


def embeddings_ragas(encodeur: rag.Encodeur):
    return _classe_embeddings()(encodeur)


async def evaluer_ragas(echantillons: list[dict], juge, embeddings, paralleles: int = 3) -> pd.DataFrame:
    """Calcule les métriques RAGAS de chaque échantillon.

    Un échantillon contient : id, question, reponse, contextes (textes des extraits
    retrouvés) et reference (réponse de référence du golden set).
    """
    from ragas.metrics.collections import (AnswerCorrectness, AnswerRelevancy, ContextPrecision,
                                           ContextRecall, Faithfulness)

    metriques = {
        "faithfulness": (Faithfulness(llm=juge),
                         lambda e: dict(user_input=e["question"], response=e["reponse"], retrieved_contexts=e["contextes"])),
        "answer_relevancy": (AnswerRelevancy(llm=juge, embeddings=embeddings),
                             lambda e: dict(user_input=e["question"], response=e["reponse"])),
        "context_precision": (ContextPrecision(llm=juge),
                              lambda e: dict(user_input=e["question"], reference=e["reference"], retrieved_contexts=e["contextes"])),
        "context_recall": (ContextRecall(llm=juge),
                           lambda e: dict(user_input=e["question"], retrieved_contexts=e["contextes"], reference=e["reference"])),
        "answer_correctness": (AnswerCorrectness(llm=juge, embeddings=embeddings),
                               lambda e: dict(user_input=e["question"], response=e["reponse"], reference=e["reference"])),
    }
    limite = asyncio.Semaphore(paralleles)

    async def noter(echantillon, nom):
        metrique, arguments = metriques[nom]
        async with limite:
            try:
                return (await metrique.ascore(**arguments(echantillon))).value
            except Exception as erreur:  # noqa: BLE001 - une métrique en échec ne bloque pas les autres
                print(f"{echantillon['id']} {nom} : échec ({type(erreur).__name__})")
                return None

    lignes = []
    for echantillon in echantillons:
        notes = await asyncio.gather(*(noter(echantillon, nom) for nom in METRIQUES_RAGAS))
        lignes.append({"id": echantillon["id"], **dict(zip(METRIQUES_RAGAS, notes))})
        print(f"\r{len(lignes)}/{len(echantillons)} échantillons évalués", end="", flush=True)
    print()
    return pd.DataFrame(lignes).set_index("id").astype(float)


# ---------------------------------------------------------------------------
# Observabilité LangSmith
# ---------------------------------------------------------------------------

def langsmith_actif() -> bool:
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true" and bool(os.getenv("LANGSMITH_API_KEY"))


def activer_langsmith() -> bool:
    """Trace dans LangSmith chaque appel de modèle fait par outils_llm (si les clés sont présentes)."""
    if not langsmith_actif():
        return False
    from langsmith.wrappers import wrap_openai

    if not getattr(llm.client, "trace_langsmith", False):
        client_original = llm.client

        @functools.cache
        def client_trace(fournisseur):
            return wrap_openai(client_original(fournisseur))

        client_trace.trace_langsmith = True
        llm.client = client_trace
    return True
