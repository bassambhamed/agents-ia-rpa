"""Schémas des entrées et sorties de l'API (validés par Pydantic, décrits dans /docs)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000, examples=["Livrez-vous en France ?"])


class Recherche(Question):
    k: int = Field(default=4, ge=1, le=10, description="Nombre d'extraits à renvoyer")


class Extrait(BaseModel):
    numero: int = Field(description="Numéro de l'extrait dans le prompt, repris dans les citations [n]")
    fichier: str
    document: str
    section: str
    texte: str
    score: float | None
    cite: bool = Field(default=False, description="Extrait cité dans la réponse")


class Reponse(BaseModel):
    question: str
    reponse: str
    trouve: bool = Field(description="Faux si l'assistant n'a pas trouvé la réponse dans la documentation")
    extraits: list[Extrait]
    sources: list[str] = Field(description="Fichiers cités")
    modele: str
    latence_s: float
    cout_usd: float | None = Field(description="Coût estimé au tarif public payant (palier gratuit : non facturé)")


class ResultatRecherche(BaseModel):
    question: str
    extraits: list[Extrait]


class Document(BaseModel):
    fichier: str
    titre: str
    extraits: int


class Sante(BaseModel):
    statut: str
    modele: str
    documents: int
    extraits_indexes: int
    reranking: bool
    langsmith: bool
