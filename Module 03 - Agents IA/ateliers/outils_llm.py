"""
outils_llm.py : couche commune d'accès aux LLM pour les ateliers de la formation.

Les ateliers utilisent des modèles open-weight, via les paliers gratuits de
fournisseurs qui exposent tous le format OpenAI Chat Completions :

    groq         https://api.groq.com/openai/v1        clé GROQ_API_KEY
    nvidia       https://integrate.api.nvidia.com/v1   clé NVIDIA_API_KEY
    openrouter   https://openrouter.ai/api/v1          clé OPENROUTER_API_KEY
    huggingface  https://router.huggingface.co/v1      clé HF_TOKEN

Un modèle est désigné par « fournisseur:modèle », par exemple
groq:openai/gpt-oss-20b ou nvidia:nvidia/nemotron-3.5-lightning-30b-a3b.
Les clés sont lues dans le fichier .env commun, à la racine de la formation
(voir .env.example) ; un .env placé dans le dossier ateliers l'emporte.
"""

from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Callable, Iterable

import openai
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

DOSSIER = Path(__file__).resolve().parent
DOSSIER_DONNEES = DOSSIER / "donnees"
DOSSIER_PROMPTS = DOSSIER / "prompts"

# Le .env le plus proche l'emporte (load_dotenv n'écrase pas une variable déjà définie) :
# celui du dossier ateliers s'il existe, puis le .env commun à la racine de la formation.
for _dossier in [DOSSIER, *DOSSIER.parents][:5]:
    load_dotenv(_dossier / ".env")

# Fournisseur -> (URL du point d'accès compatible OpenAI, variable de la clé)
FOURNISSEURS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "huggingface": ("https://router.huggingface.co/v1", "HF_TOKEN"),
}

# Ordre d'essai quand le modèle par défaut n'est pas accessible (paliers gratuits
# vérifiés en octobre 2026 ; Hugging Face exige des crédits, épuisés sur un compte gratuit)
MODELES_DE_REPLI = [
    "groq:openai/gpt-oss-20b",
    "nvidia:nvidia/nemotron-3.5-lightning-30b-a3b",
    "openrouter:google/gemma-4-26b-a4b-it:free",
    "huggingface:openai/gpt-oss-20b",
]

# Tarifs publics indicatifs en USD par million de tokens : (entrée, sortie),
# relevés en octobre 2026 (Groq et catalogue OpenRouter). Les paliers gratuits
# ne sont pas facturés : ces prix servent à estimer le coût d'un passage en
# production. Le prix d'un même modèle varie selon le fournisseur.
TARIFS = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "llama-3.3-70b-versatile": (0.10, 0.32),
    "google/gemma-4-31b-it": (0.20, 0.40),
    "nvidia/nemotron-3-super-120b-a12b": (0.30, 2.40),
    "qwen/qwen3-32b": (0.08, 0.28),
}


@dataclass
class Reponse:
    """Résultat d'un appel, avec les mesures utiles pour comparer les modèles."""

    texte: str
    modele: str
    tokens_entree: int
    tokens_sortie: int
    latence_s: float
    cout_usd: float | None  # coût estimé au tarif public payant
    fin: str | None = None  # raison d'arrêt : stop, length, content_filter…
    objet: Any = None  # instance Pydantic quand un schéma est demandé
    structure: str | None = None  # « schéma imposé » ou « JSON demandé dans le prompt »

    def __repr__(self) -> str:
        cout = "n/d" if self.cout_usd is None else f"{self.cout_usd:.6f} $"
        apercu = self.texte if len(self.texte) < 300 else self.texte[:300] + "…"
        return (
            f"[{self.modele}] {self.tokens_entree} tokens en entrée, "
            f"{self.tokens_sortie} en sortie, {self.latence_s:.1f} s, "
            f"coût estimé {cout}, fin={self.fin}\n{apercu}"
        )


# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

def decouper(modele: str) -> tuple[str, str]:
    """« groq:openai/gpt-oss-20b » -> (« groq », « openai/gpt-oss-20b »)."""
    fournisseur, sep, nom = modele.partition(":")
    if not sep or fournisseur not in FOURNISSEURS:
        raise ValueError(
            f"Modèle « {modele} » : utilisez la forme fournisseur:modèle, "
            f"avec un fournisseur parmi {', '.join(FOURNISSEURS)}."
        )
    return fournisseur, nom


def fournisseurs_disponibles() -> dict[str, bool]:
    """Fournisseurs dont la clé est renseignée dans le .env."""
    return {nom: bool(os.getenv(variable)) for nom, (_, variable) in FOURNISSEURS.items()}


def modele_par_defaut() -> str:
    return os.getenv("MODELE_PAR_DEFAUT", "groq:openai/gpt-oss-20b")


def choisir_modele() -> str:
    """Premier modèle accessible : le modèle par défaut, puis les modèles de repli."""
    disponibles = fournisseurs_disponibles()
    for modele in (modele_par_defaut(), *MODELES_DE_REPLI):
        if disponibles[decouper(modele)[0]]:
            return modele
    raise RuntimeError(
        "Aucun fournisseur disponible : renseignez au moins une clé dans le .env commun (voir .env.example)."
    )


@cache
def client(fournisseur: str) -> openai.OpenAI:
    """Client du SDK openai pointé vers le fournisseur.

    Les paliers gratuits limitent le débit (Groq : 8 000 tokens par minute) : en
    cas d'erreur 429, le SDK attend le délai indiqué par le serveur et réessaie
    (jusqu'à 10 fois). Un appel qui dépasse 3 minutes (fournisseur saturé) est
    abandonné, puis réessayé.
    """
    url, variable = FOURNISSEURS[fournisseur]
    return openai.OpenAI(base_url=url, api_key=os.getenv(variable), max_retries=10, timeout=180)


def cout_usd(modele: str, tokens_entree: int, tokens_sortie: int) -> float | None:
    _, nom = decouper(modele)
    tarif = TARIFS.get(nom.lower().removesuffix(":free"))
    if tarif is None:
        return None
    return (tokens_entree * tarif[0] + tokens_sortie * tarif[1]) / 1_000_000


# ---------------------------------------------------------------------------
# Appel unifié
# ---------------------------------------------------------------------------

def demander(
    prompt: str | list[dict],
    *,
    systeme: str | None = None,
    modele: str | None = None,
    schema: type[BaseModel] | None = None,
    max_tokens: int = 8000,
    temperature: float | None = None,
) -> Reponse:
    """Envoie un prompt (ou une liste de messages) et renvoie une Reponse.

    schema : classe Pydantic. La réponse validée est dans `Reponse.objet`.
    Si le fournisseur n'impose pas les schémas pour ce modèle, le schéma est
    décrit dans le prompt et la réponse JSON est validée par Pydantic.
    """
    modele = modele or modele_par_defaut()
    fournisseur, nom = decouper(modele)
    messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else list(prompt)
    if systeme:
        messages = [{"role": "system", "content": systeme}, *messages]
    params: dict[str, Any] = {"model": nom, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        params["temperature"] = temperature

    debut = time.perf_counter()
    objet, structure = None, None
    if schema is None:
        r = client(fournisseur).chat.completions.create(**params)
    else:
        r, objet, structure = _appel_structure(fournisseur, params, schema)
    latence = time.perf_counter() - debut

    choix = r.choices[0]
    t_in = r.usage.prompt_tokens if r.usage else 0
    t_out = r.usage.completion_tokens if r.usage else 0
    return Reponse(
        texte=choix.message.content or "",
        modele=modele,
        tokens_entree=t_in,
        tokens_sortie=t_out,
        latence_s=latence,
        cout_usd=cout_usd(modele, t_in, t_out),
        fin=choix.finish_reason,
        objet=objet,
        structure=structure,
    )


def _appel_structure(fournisseur, params, schema):
    """Schéma imposé par l'API si possible, sinon JSON demandé dans le prompt."""
    try:
        r = client(fournisseur).chat.completions.parse(response_format=schema, **params)
        objet = r.choices[0].message.parsed
        if objet is not None:
            return r, objet, "schéma imposé"
    except (openai.BadRequestError, openai.UnprocessableEntityError,
            openai.LengthFinishReasonError, ValidationError):
        pass  # schéma non pris en charge par ce modèle ou ce fournisseur

    consigne = (
        "Réponds uniquement par un objet JSON valide, sans texte autour, "
        "conforme à ce schéma JSON :\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )
    messages = list(params["messages"])
    if messages[0]["role"] == "system":
        messages[0] = {"role": "system", "content": messages[0]["content"] + "\n\n" + consigne}
    else:
        messages.insert(0, {"role": "system", "content": consigne})
    r = client(fournisseur).chat.completions.create(**{**params, "messages": messages})
    try:
        objet = schema.model_validate_json(extraire_json(r.choices[0].message.content or ""))
    except ValidationError:
        # réponse vide ou mal formée (palier gratuit saturé, par exemple) : une seconde tentative
        r = client(fournisseur).chat.completions.create(**{**params, "messages": messages})
        objet = schema.model_validate_json(extraire_json(r.choices[0].message.content or ""))
    return r, objet, "JSON demandé dans le prompt"


def extraire_json(texte: str) -> str:
    """Isole l'objet JSON d'une réponse (blocs ```json, texte autour)."""
    bloc = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texte, re.S)
    if bloc:
        return bloc.group(1)
    debut, fin = texte.find("{"), texte.rfind("}")
    return texte[debut : fin + 1] if debut != -1 and fin > debut else texte


# ---------------------------------------------------------------------------
# Traitement par lots et mesures
# ---------------------------------------------------------------------------

def en_lot(fonction: Callable[[Any], Any], elements: Iterable[Any], paralleles: int = 2) -> list:
    """Applique `fonction` à chaque élément, en parallèle, en conservant l'ordre.

    Une erreur sur un élément n'interrompt pas le lot : l'exception est
    renvoyée à la place du résultat.
    """
    elements = list(elements)
    resultats: list[Any] = [None] * len(elements)
    termines = 0

    def executer(i):
        try:
            return i, fonction(elements[i])
        except Exception as erreur:  # noqa: BLE001 - on veut tout capturer ici
            return i, erreur

    with ThreadPoolExecutor(max_workers=paralleles) as pool:
        for i, resultat in pool.map(executer, range(len(elements))):
            resultats[i] = resultat
            termines += 1
            print(f"\r{termines}/{len(elements)} appels terminés", end="", flush=True)
    erreurs = [r for r in resultats if isinstance(r, Exception)]
    print(f"\r{len(elements)} appels terminés, {len(erreurs)} erreur(s).")
    if erreurs:
        print("Première erreur :", repr(erreurs[0])[:300])
    return resultats


def bilan(reponses: list[Reponse]) -> dict[str, float | None]:
    """Latence, tokens et coût estimé moyens d'une série d'appels réussis."""
    ok = [r for r in reponses if isinstance(r, Reponse)]
    if not ok:
        return {}
    couts = [r.cout_usd for r in ok]
    cout_moyen = None if None in couts else sum(couts) / len(ok)
    return {
        "appels": len(ok),
        "latence_moyenne_s": round(sum(r.latence_s for r in ok) / len(ok), 2),
        "tokens_entree_moyens": round(sum(r.tokens_entree for r in ok) / len(ok)),
        "tokens_sortie_moyens": round(sum(r.tokens_sortie for r in ok) / len(ok)),
        "cout_pour_1000_usd": None if cout_moyen is None else round(cout_moyen * 1000, 3),
    }


# ---------------------------------------------------------------------------
# Données du projet fil rouge
# ---------------------------------------------------------------------------

def charger_demandes(jeu: str | None = None) -> pd.DataFrame:
    """Demandes clients annotées ; jeu = « exemples », « test » ou None (toutes)."""
    df = pd.read_csv(DOSSIER_DONNEES / "demandes_clients.csv")
    return df if jeu is None else df[df["jeu"] == jeu].reset_index(drop=True)


def lire(nom: str) -> str:
    """Contenu texte d'un fichier du dossier donnees (ex. « regles_tri.md »)."""
    return (DOSSIER_DONNEES / nom).read_text(encoding="utf-8")


def charger_json(nom: str):
    return json.loads(lire(nom))


def sauver_prompt(nom: str, texte: str, **metadonnees) -> Path:
    """Enregistre un prompt dans prompts/<nom>.md avec une ligne de métadonnées."""
    DOSSIER_PROMPTS.mkdir(exist_ok=True)
    entete = " | ".join(f"{cle}: {valeur}" for cle, valeur in metadonnees.items())
    chemin = DOSSIER_PROMPTS / f"{nom}.md"
    chemin.write_text(f"<!-- {entete} -->\n{texte}\n", encoding="utf-8")
    return chemin


def charger_prompt(nom: str) -> str:
    """Relit un prompt enregistré par sauver_prompt (sans la ligne de métadonnées)."""
    texte = (DOSSIER_PROMPTS / f"{nom}.md").read_text(encoding="utf-8")
    if texte.startswith("<!--"):
        texte = texte.split("-->\n", 1)[1]
    return texte.rstrip("\n")


def formater_demande(ligne) -> str:
    """Présente une demande comme un email, entre balises."""
    return (
        "<demande>\n"
        f"De : {ligne['expediteur']} ({ligne['entreprise']})\n"
        f"Objet : {ligne['objet']}\n\n"
        f"{ligne['corps']}\n"
        "</demande>"
    )


def exactitude(verite: Iterable, predictions: Iterable) -> float:
    verite, predictions = list(verite), list(predictions)
    return sum(v == p for v, p in zip(verite, predictions)) / len(verite)


def matrice_confusion(verite: Iterable, predictions: Iterable) -> pd.DataFrame:
    return pd.crosstab(
        pd.Series(list(verite), name="vérité"),
        pd.Series(list(predictions), name="prédiction"),
    )
