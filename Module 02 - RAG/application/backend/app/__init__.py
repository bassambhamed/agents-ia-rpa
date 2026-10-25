"""Backend de l'assistant documentaire Fictiva (FastAPI)."""

from pathlib import Path

from dotenv import load_dotenv

# Les clés (fournisseurs de LLM, LangSmith) et les réglages sont lus dans
# backend/.env avant tout autre import du paquet.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
