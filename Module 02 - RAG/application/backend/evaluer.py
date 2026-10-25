"""
evaluer.py : évaluation de l'assistant sur le golden set (tests de non-régression).

Depuis le dossier backend :
    python evaluer.py                 # recherche seule, sans LLM : context recall et context precision@k
    python evaluer.py --generation    # avec les réponses du modèle : refus hors corpus, citations, confidentialité
    python evaluer.py --langsmith     # avec les réponses, enregistrée comme expérience LangSmith
    python evaluer.py --seuil 0.85    # code de sortie 1 si le context recall moyen passe sous le seuil (CI)

Les métriques RAGAS calculées par un LLM juge (fidélité, pertinence, exactitude)
sont présentées dans l'atelier 2.C.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from app import observabilite, rag
from app.config import Reglages
from app.main import construire_assistant

PLAFOND_INTERNE = "15 %"  # information de la procédure interne, qui ne doit jamais être divulguée
NOM_DATASET = "fictiva-golden-set"


def mesurer(entree: dict, extraits: list[rag.Extrait], r: rag.ReponseRAG | None) -> dict:
    ligne = {"id": entree["id"], "type": entree["type"]}
    if entree["indices"]:
        ligne["context_recall"] = rag.couverture(extraits, entree["indices"])
        ligne["context_precision"] = rag.precision_moyenne(extraits, entree["indices"])
    if r is not None:
        if entree["type"] == "hors_corpus":
            ligne["refus_correct"] = float(not r.trouve)
        else:
            ligne["repondue"] = float(r.trouve)
            ligne["citee"] = float(bool(r.citees))
        if entree["type"] == "interne":
            ligne["sans_fuite"] = float(PLAFOND_INTERNE not in r.texte.replace("15%", "15 %"))
    return ligne


def evaluer_localement(assistant: rag.Assistant, golden: list[dict], generation: bool) -> pd.DataFrame:
    lignes = []
    for entree in golden:
        if generation:
            r = assistant.repondre(entree["question"])
            lignes.append(mesurer(entree, r.extraits, r))
        else:
            lignes.append(mesurer(entree, assistant.retrouver(entree["question"]), None))
        print(f"\r{len(lignes)}/{len(golden)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    return pd.DataFrame(lignes).set_index("id")


def evaluer_dans_langsmith(assistant: rag.Assistant, golden: list[dict]) -> None:
    """Le golden set devient un dataset LangSmith, l'évaluation une expérience comparable aux autres."""
    from langsmith import Client, evaluate

    client = Client()
    if not client.has_dataset(dataset_name=NOM_DATASET):
        client.create_dataset(NOM_DATASET, description="Golden set de l'assistant documentaire Fictiva")
        client.create_examples(dataset_name=NOM_DATASET, examples=[
            {"inputs": {"question": g["question"]},
             "outputs": {"reponse_reference": g["reponse_reference"], "indices": g["indices"], "type": g["type"]},
             "metadata": {"id": g["id"]}}
            for g in golden])

    def cible(entrees: dict) -> dict:
        r = assistant.repondre(entrees["question"])
        return {"reponse": r.texte, "trouve": r.trouve, "contextes": [e.texte for e in r.extraits]}

    def rappel_contexte(outputs: dict, reference_outputs: dict) -> dict:
        if not reference_outputs["indices"]:
            return {"key": "context_recall_indices", "score": None}
        return {"key": "context_recall_indices",
                "score": rag.couverture_textes(outputs["contextes"], reference_outputs["indices"])}

    def refus_correct(outputs: dict, reference_outputs: dict) -> dict:
        if reference_outputs["type"] != "hors_corpus":
            return {"key": "refus_correct", "score": None}
        return {"key": "refus_correct", "score": float(not outputs["trouve"])}

    evaluate(cible, data=NOM_DATASET, evaluators=[rappel_contexte, refus_correct],
             experiment_prefix=assistant.modele.replace(":", "-").replace("/", "-"),
             metadata={"modele": assistant.modele, "reranking": assistant.reranker is not None, "k": assistant.k},
             max_concurrency=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Évalue l'assistant documentaire sur le golden set.")
    parser.add_argument("--generation", action="store_true", help="interroger aussi le modèle")
    parser.add_argument("--langsmith", action="store_true", help="enregistrer une expérience LangSmith")
    parser.add_argument("--seuil", type=float, help="context recall moyen minimal (code de sortie 1 en dessous)")
    args = parser.parse_args()

    assistant = construire_assistant(Reglages.depuis_environnement())
    golden = rag.charger_golden_set()

    if args.langsmith:
        if not observabilite.activer_langsmith():
            print("LangSmith non configuré : renseignez LANGSMITH_TRACING, LANGSMITH_API_KEY et LANGSMITH_PROJECT dans .env.")
            return 2
        evaluer_dans_langsmith(assistant, golden)
        return 0

    resultats = evaluer_localement(assistant, golden, args.generation)
    print(f"Modèle : {assistant.modele} | reranking : {assistant.reranker is not None} | k = {assistant.k}\n")
    print(resultats.groupby("type").mean().dropna(how="all").round(2).to_string(), "\n")
    print("Moyennes :", resultats.mean(numeric_only=True).round(3).to_dict())

    rappel = resultats["context_recall"].mean()
    if args.seuil is not None and rappel < args.seuil:
        print(f"Échec : context recall {rappel:.3f} < seuil {args.seuil}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
