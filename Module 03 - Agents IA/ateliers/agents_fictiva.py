"""
agents_fictiva.py : briques communes des ateliers 3.B à 3.D.

- modele_chat : modèle de chat LangChain branché sur les fournisseurs d'outils_llm ;
- outils_crm_mcp : outils du CRM, chargés depuis le serveur MCP ;
- calculer_remboursement, creer_ticket : outils locaux (calcul, écriture validée par un humain) ;
- construire_agent : graphe LangGraph « agent ↔ outils » avec mémoire ;
- TraceurLocal : journal des appels de modèles et d'outils, sans service externe ;
- afficher_trajectoire : lecture pas à pas d'une conversation d'agent.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt

import crm
import outils_llm as llm

DOSSIER = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------------

def modele_chat(modele: str | None = None, **options) -> ChatOpenAI:
    """Modèle de chat LangChain pour « fournisseur:modèle » (voir outils_llm)."""
    modele = modele or llm.choisir_modele()
    fournisseur, nom = llm.decouper(modele)
    url, variable = llm.FOURNISSEURS[fournisseur]
    return ChatOpenAI(model=nom, base_url=url, api_key=os.getenv(variable), max_retries=6, **options)


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

async def outils_crm_mcp() -> list:
    """Lance le serveur MCP du CRM (transport stdio) et renvoie ses outils au format LangChain."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient({
        "crm": {"command": sys.executable, "args": [str(DOSSIER / "serveur_crm_mcp.py")],
                "transport": "stdio", "cwd": str(DOSSIER)},
    })
    return await client.get_tools()


@tool
def calculer_remboursement(numero_commande: str, references: list[str], defectueux: bool,
                           consommables_ouverts: bool = False) -> dict:
    """Calcule le montant remboursable pour des articles retournés, selon la politique de retours
    de Fictiva (délais, garantie, frais de traitement, exclusions, validation au-delà de 5 000 CHF).
    references : références des articles retournés (par ex. ["KB-80"]).
    defectueux : true si le client signale un défaut, false pour un retour sans défaut.
    consommables_ouverts : true si des consommables (toners, cartouches, papier) ont été ouverts."""
    return crm.calculer_remboursement(numero_commande, references, defectueux, consommables_ouverts)


@tool
def creer_ticket(numero_client: str, categorie: str, resume: str, montant_chf: float | None = None) -> dict:
    """Crée le ticket de traitement de la demande dans le CRM : catégorie (remboursement,
    reclamation, litige_facturation, question_produit, autre), résumé de la demande et de la
    décision, montant éventuel. Action en écriture : un opérateur humain doit la valider."""
    decision = interrupt({"action": "creer_ticket", "numero_client": numero_client, "categorie": categorie,
                          "resume": resume, "montant_chf": montant_chf})
    if str(decision).strip().lower() not in ("oui", "o", "ok", "valider"):
        return {"statut": "refusé par l'opérateur", "commentaire": str(decision)}
    return crm.creer_ticket(numero_client, categorie, resume, montant_chf)


PROMPT_SAV = """Tu es l'agent du service après-vente de Fictiva SA, distributeur B2B de matériel informatique.
Tu traites une demande de client reçue par email. Nous sommes le 23 octobre 2026.

Méthode :
1. Identifie le client et la commande avec les outils du CRM. Ne suppose jamais une information que tu peux vérifier. Si l'email ne donne pas le numéro de commande, cherche le client puis ses commandes.
2. Pour un retour ou un remboursement, calcule le montant uniquement avec l'outil calculer_remboursement, jamais de tête. Déduis de l'email si l'article est défectueux et, pour des consommables, s'ils ont été ouverts.
3. Crée un ticket qui résume la demande, la décision et le montant éventuel.
4. Termine par un brouillon de réponse au client : 5 à 8 lignes, vouvoiement, sans rien promettre au-delà de la politique. Si une validation par un responsable est requise, dis que la demande est en cours de validation.

Si une information reste introuvable, dis-le dans le brouillon au lieu de l'inventer."""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

def construire_agent(outils: list, prompt: str = PROMPT_SAV, modele: str | None = None,
                     erreurs_outils: bool | str = True, memoire: bool = True):
    """Graphe LangGraph : le modèle choisit des outils, le nœud « outils » les exécute,
    et ainsi de suite jusqu'à une réponse sans appel d'outil.

    erreurs_outils : True renvoie l'erreur d'un outil au modèle au lieu d'interrompre le graphe.
    memoire : conserve l'état entre les appels (par thread_id) ; indispensable pour la validation humaine.
    """
    llm_outille = modele_chat(modele).bind_tools(outils)

    async def agent(etat: MessagesState):
        for _ in range(3):  # garde-fou : un modèle renvoie parfois une réponse vide ; on relance
            reponse = await llm_outille.ainvoke([SystemMessage(prompt), *etat["messages"]])
            if reponse.content or reponse.tool_calls:
                break
        return {"messages": [reponse]}

    graphe = StateGraph(MessagesState)
    graphe.add_node("agent", agent)
    graphe.add_node("outils", ToolNode(outils, handle_tool_errors=erreurs_outils))
    graphe.add_edge(START, "agent")
    graphe.add_conditional_edges("agent", tools_condition, {"tools": "outils", END: END})
    graphe.add_edge("outils", "agent")
    return graphe.compile(checkpointer=InMemorySaver() if memoire else None)


def config(thread: str, *rappels, limite: int = 25) -> dict:
    """Configuration d'exécution : fil de conversation, rappels (traceurs), limite d'étapes."""
    return {"configurable": {"thread_id": thread}, "callbacks": list(rappels), "recursion_limit": limite}


def charger_demandes() -> list[dict]:
    return json.loads((DOSSIER / "donnees" / "demandes_sav.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Observabilité
# ---------------------------------------------------------------------------

def texte_outil(contenu) -> str:
    """Texte d'un résultat d'outil (les outils MCP renvoient une liste de blocs de texte)."""
    if isinstance(contenu, list):
        return " ".join(bloc.get("text", "") if isinstance(bloc, dict) else str(bloc) for bloc in contenu)
    return str(contenu)


class TraceurLocal(BaseCallbackHandler):
    """Enregistre chaque appel de modèle et d'outil : nom, entrée, sortie, tokens, durée, erreur."""

    def __init__(self):
        self.evenements: list[dict] = []
        self._debuts: dict = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        self._debuts[run_id] = (time.perf_counter(), len(messages[0]) if messages else 0)

    def on_llm_end(self, response, *, run_id, **kwargs):
        debut, nb_messages = self._debuts.pop(run_id, (time.perf_counter(), 0))
        message = response.generations[0][0].message
        usage = getattr(message, "usage_metadata", None) or {}
        appels = [appel["name"] for appel in getattr(message, "tool_calls", [])]
        self.evenements.append({
            "type": "modèle", "nom": "LLM", "entree": f"{nb_messages} messages",
            "sortie": ("→ " + ", ".join(appels)) if appels else str(message.content)[:120],
            "tokens_entree": usage.get("input_tokens"), "tokens_sortie": usage.get("output_tokens"),
            "duree_s": round(time.perf_counter() - debut, 2), "erreur": None,
        })

    def on_llm_error(self, error, *, run_id, **kwargs):
        debut, _ = self._debuts.pop(run_id, (time.perf_counter(), 0))
        self.evenements.append({"type": "modèle", "nom": "LLM", "entree": "", "sortie": "",
                                "tokens_entree": None, "tokens_sortie": None,
                                "duree_s": round(time.perf_counter() - debut, 2), "erreur": repr(error)[:200]})

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self._debuts[run_id] = (time.perf_counter(), (serialized or {}).get("name", "outil"), input_str)

    def on_tool_end(self, output, *, run_id, **kwargs):
        debut, nom, entree = self._debuts.pop(run_id, (time.perf_counter(), "outil", ""))
        contenu = texte_outil(getattr(output, "content", output))
        self.evenements.append({"type": "outil", "nom": nom, "entree": str(entree)[:120], "sortie": contenu[:120],
                                "tokens_entree": None, "tokens_sortie": None,
                                "duree_s": round(time.perf_counter() - debut, 2), "erreur": None})

    def on_tool_error(self, error, *, run_id, **kwargs):
        debut, nom, entree = self._debuts.pop(run_id, (time.perf_counter(), "outil", ""))
        interruption = type(error).__name__ == "GraphInterrupt"  # validation humaine, pas une erreur
        self.evenements.append({"type": "outil", "nom": nom, "entree": str(entree)[:120],
                                "sortie": "en attente de validation humaine" if interruption else "",
                                "tokens_entree": None, "tokens_sortie": None,
                                "duree_s": round(time.perf_counter() - debut, 2),
                                "erreur": None if interruption else repr(error)[:200]})

    def tableau(self) -> pd.DataFrame:
        return pd.DataFrame(self.evenements)

    def bilan(self) -> dict:
        t = self.tableau()
        if t.empty:
            return {}
        modeles = t[t.type == "modèle"]
        return {"appels_modele": len(modeles), "appels_outils": int((t.type == "outil").sum()),
                "erreurs": int(t.erreur.notna().sum()),
                "tokens_entree": int(modeles.tokens_entree.fillna(0).sum()),
                "tokens_sortie": int(modeles.tokens_sortie.fillna(0).sum()),
                "duree_totale_s": round(float(t.duree_s.sum()), 1)}


def langfuse_actif() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def traceur_langfuse():
    """Rappel Langfuse si les clés sont dans .env (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL)."""
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def afficher_trajectoire(messages: list) -> None:
    """Affiche la conversation d'un agent : demande, appels d'outils, résultats, réponse."""
    for m in messages:
        if isinstance(m, HumanMessage):
            print(f"👤 DEMANDE\n{m.content}\n")
        elif isinstance(m, AIMessage):
            for appel in m.tool_calls:
                print(f"🤖 APPEL  {appel['name']}({json.dumps(appel['args'], ensure_ascii=False)})")
            if m.content:
                print(f"🤖 RÉPONSE\n{m.content}\n")
        elif isinstance(m, ToolMessage):
            print(f"🔧 RÉSULTAT {m.name} : {texte_outil(m.content)[:300]}\n")
