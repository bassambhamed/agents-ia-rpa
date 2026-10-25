"""Réglages du service, lus dans les variables d'environnement (fichier backend/.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Reglages:
    reranking: bool = True  # recherche hybride sur 20 candidats, puis cross-encoder
    k: int = 4  # extraits transmis au modèle
    origines_cors: tuple[str, ...] = ("http://localhost:3000",)  # frontend Next.js

    @classmethod
    def depuis_environnement(cls) -> "Reglages":
        origines = os.getenv("ORIGINES_CORS", "http://localhost:3000")
        return cls(
            reranking=os.getenv("RERANKING", "true").lower() == "true",
            k=int(os.getenv("NOMBRE_EXTRAITS", "4")),
            origines_cors=tuple(o.strip() for o in origines.split(",") if o.strip()),
        )
