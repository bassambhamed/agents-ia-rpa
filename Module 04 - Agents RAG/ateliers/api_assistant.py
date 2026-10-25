"""
api_assistant.py : service web de l'assistant de Fictiva.

Il reprend l'assistant documentaire du Jour 2 (même pipeline que le backend de
l'application du Module 02) et ajoute l'agent RAG multi-sources du Jour 4 :

    GET  /sante      état du service
    POST /question   assistant documentaire du Jour 2 : une source, une recherche, une réponse citée
    POST /agent      agent RAG : documentation, base de support et compte du client, avec mémoire
                     de conversation et garde-fous (atelier 4.C)

Lancement, depuis le dossier ateliers :
    uvicorn api_assistant:app --port 8002

Documentation interactive : http://localhost:8002/docs
Le workflow du Jour 5 appellera POST /agent.
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

import agent_rag as ar
import rag

etat: dict = {}


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    # Les index, le reranker et l'agent sont construits une seule fois, au démarrage du service.
    sources = ar.construire_sources()
    etat["sources"] = sources
    etat["assistant"] = rag.Assistant(sources.documentation, sources.reranker)
    etat["agent"] = ar.construire_agent(ar.creer_outils(sources, garde_fous=True), prompt=ar.PROMPT_AGENT_DURCI)
    yield


app = FastAPI(
    title="Assistant de Fictiva",
    description="Assistant documentaire (Jour 2) et agent RAG multi-sources (Jour 4) du portail client de Fictiva SA. "
                "Données synthétiques.",
    version="2.0",
    lifespan=cycle_de_vie,
)


# --- Jour 2 : assistant documentaire --------------------------------------

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000, examples=["Livrez-vous en France ?"])


class Source(BaseModel):
    numero: int
    document: str
    fichier: str
    extrait: str


class Reponse(BaseModel):
    reponse: str
    trouve: bool
    sources: list[Source]
    modele: str
    latence_s: float


@app.get("/sante")
def sante() -> dict:
    sources = etat["sources"]
    return {
        "statut": "ok",
        "extraits_indexes": len(sources.documentation.extraits),
        "articles_support": len(sources.support.extraits),
        "modele": etat["assistant"].modele,
    }


@app.post("/question", response_model=Reponse)
def poser_question(entree: Question) -> Reponse:
    r = etat["assistant"].repondre(entree.question)
    sources = [
        Source(numero=n, document=r.extraits[n - 1].titre, fichier=r.extraits[n - 1].source,
               extrait=r.extraits[n - 1].texte[:300])
        for n in r.citees
    ]
    return Reponse(reponse=r.texte, trouve=r.trouve, sources=sources, modele=r.modele,
                   latence_s=round(r.latence_s, 2))


# --- Jour 4 : agent RAG multi-sources ---------------------------------------

class DemandeAgent(BaseModel):
    # En production, le numéro de client vient du jeton d'authentification du portail,
    # jamais du texte saisi : c'est lui qui limite l'agent au compte du client.
    numero_client: str = Field(pattern=r"^CL-\d{5}$", examples=["CL-10234"])
    message: str = Field(min_length=3, max_length=2000,
                         examples=["Une de nos imprimantes LX-500 affiche le code E-21. Est-elle sous garantie ?"])
    conversation: str | None = Field(default=None, description="Identifiant renvoyé par la réponse précédente, pour poursuivre une conversation")


class Citation(BaseModel):
    reference: str
    source: str


class ReponseAgent(BaseModel):
    reponse: str
    conversation: str
    citations: list[Citation]
    citations_invalides: list[str] = Field(description="Références citées mais jamais renvoyées par un outil")
    outils: list[str]
    alertes: list[str] = Field(description="Interventions des garde-fous sur la réponse")
    appels_modele: int
    latence_s: float


@app.post("/agent", response_model=ReponseAgent)
async def interroger_agent(demande: DemandeAgent) -> ReponseAgent:
    conversation = demande.conversation or uuid.uuid4().hex[:12]
    r = await ar.demander(etat["agent"], demande.numero_client, demande.message, conversation, controle_sortie=True)
    sources = etat["sources"]
    return ReponseAgent(
        reponse=r.reponse, conversation=conversation,
        citations=[Citation(reference=ref, source=sources.libelle(ref)) for ref in r.citees if ref not in r.invalides],
        citations_invalides=r.invalides, outils=[o["nom"] for o in r.outils], alertes=r.alertes,
        appels_modele=r.appels_modele, latence_s=r.latence_s,
    )
