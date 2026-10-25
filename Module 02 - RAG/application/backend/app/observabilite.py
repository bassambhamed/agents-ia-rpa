"""
observabilite.py : traces LangSmith de l'assistant.

Quand LANGSMITH_TRACING=true et LANGSMITH_API_KEY sont définis, chaque question
devient une trace dans le projet LANGSMITH_PROJECT :

    assistant_documentaire (chain)
    ├── recherche (retriever) : extraits retrouvés, sources et scores
    └── ChatOpenAI (llm) : prompt, réponse, tokens, durée

Les étapes « assistant_documentaire » et « recherche » sont déclarées dans rag.py
avec langsmith.traceable ; les appels de modèles sont tracés ici, en enveloppant
le client openai d'outils_llm avec wrap_openai.
"""

from __future__ import annotations

import functools
import os

from . import outils_llm as llm


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
