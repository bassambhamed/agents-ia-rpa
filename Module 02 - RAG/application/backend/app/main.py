"""
main.py : API de l'assistant documentaire Fictiva.

Lancement, depuis le dossier backend :
    uvicorn app.main:app --reload --port 8000

Documentation interactive : http://localhost:8000/docs
Le frontend Next.js (dossier ../frontend) appelle les routes /api/*.
"""

from __future__ import annotations

from collections import Counter
from contextlib import asynccontextmanager
from typing import Callable, Collection

import openai
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import observabilite, rag
from .config import Reglages
from .schemas import Document, Extrait, Question, Recherche, Reponse, ResultatRecherche, Sante


def construire_assistant(reglages: Reglages) -> rag.Assistant:
    """Lit le corpus, découpe, indexe et charge le reranker : quelques secondes au démarrage."""
    return rag.Assistant.construire(reranking=reglages.reranking, k=reglages.k)


def vers_schema(extraits: list[rag.Extrait], citees: Collection[int] = ()) -> list[Extrait]:
    return [
        Extrait(numero=n, fichier=e.source, document=e.titre, section=e.section, texte=e.texte,
                score=None if e.score is None else round(e.score, 4), cite=n in citees)
        for n, e in enumerate(extraits, start=1)
    ]


def creer_application(fabrique: Callable[[Reglages], rag.Assistant] = construire_assistant,
                      reglages: Reglages | None = None) -> FastAPI:
    """Crée l'application. Les tests passent une fabrique qui construit un assistant léger."""
    reglages = reglages or Reglages.depuis_environnement()

    @asynccontextmanager
    async def cycle_de_vie(app: FastAPI):
        observabilite.activer_langsmith()
        app.state.assistant = fabrique(reglages)  # l'index est construit une seule fois
        yield

    app = FastAPI(
        title="Assistant documentaire Fictiva",
        description="Répond aux questions des clients à partir de la documentation publique de Fictiva SA, "
                    "avec citations. Données synthétiques.",
        version="1.0",
        lifespan=cycle_de_vie,
    )
    app.add_middleware(CORSMiddleware, allow_origins=list(reglages.origines_cors),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    def assistant(request: Request) -> rag.Assistant:
        return request.app.state.assistant

    @app.get("/api/sante", response_model=Sante)
    def sante(request: Request) -> Sante:
        a = assistant(request)
        return Sante(statut="ok", modele=a.modele, documents=len({e.source for e in a.index.extraits}),
                     extraits_indexes=len(a.index.extraits), reranking=a.reranker is not None,
                     langsmith=observabilite.langsmith_actif())

    @app.get("/api/documents", response_model=list[Document])
    def documents(request: Request) -> list[Document]:
        """Documents publics interrogés par l'assistant (les documents internes ne sont pas listés)."""
        publics = [e for e in assistant(request).index.extraits if e.confidentialite == "public"]
        titres = {e.source: e.titre for e in publics}
        nombres = Counter(e.source for e in publics)
        return [Document(fichier=f, titre=titres[f], extraits=nombres[f]) for f in sorted(titres)]

    @app.get("/api/exemples", response_model=list[str])
    def exemples() -> list[str]:
        """Une question du golden set par type (hors questions internes), pour l'interface."""
        par_type: dict[str, str] = {}
        for entree in rag.charger_golden_set():
            if entree["type"] != "interne":
                par_type.setdefault(entree["type"], entree["question"])
        return list(par_type.values())

    @app.post("/api/recherche", response_model=ResultatRecherche)
    def rechercher(entree: Recherche, request: Request) -> ResultatRecherche:
        """Extraits retrouvés pour une question, sans appel au modèle (pour comprendre la recherche)."""
        a = assistant(request)
        if a.reranker is None:
            extraits = a.index.rechercher(entree.question, entree.k, a.mode, a.public_seulement)
        else:
            candidats = a.index.rechercher(entree.question, a.candidats, a.mode, a.public_seulement)
            extraits = a.reranker.reordonner(entree.question, candidats, entree.k)
        return ResultatRecherche(question=entree.question, extraits=vers_schema(extraits))

    @app.post("/api/question", response_model=Reponse)
    def poser_question(entree: Question, request: Request) -> Reponse:
        try:
            r = assistant(request).repondre(entree.question)
        except openai.APIError as erreur:
            raise HTTPException(502, f"Le modèle n'a pas répondu ({type(erreur).__name__}). "
                                     "Vérifiez la clé, le quota ou le nom du modèle.") from erreur
        return Reponse(question=r.question, reponse=r.texte, trouve=r.trouve,
                       extraits=vers_schema(r.extraits, r.citees), sources=r.sources(), modele=r.modele,
                       latence_s=round(r.latence_s, 2), cout_usd=r.cout_usd)

    return app


app = creer_application()
