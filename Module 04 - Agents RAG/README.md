# Module 04 — Agents RAG : la fusion des deux mondes

**Jour 4 de la formation Autonomous AI Agents & RPA 2.0.** L'assistant documentaire du Jour 2 connaît la documentation mais ne fait qu'une recherche ; l'agent du Jour 3 consulte le CRM mais ignore la documentation. L'**agent RAG** les réunit : il répond au client connecté au portail de Fictiva à partir de trois sources (documentation, base de connaissances du support, compte du client), cite des références vérifiables, contrôle ses recherches (CRAG, Self-RAG), et il est évalué puis attaqué (red teaming).

## Objectifs

À la fin de la journée, les participants savent :

- faire de la recherche un **outil** de l'agent, sur plusieurs sources ;
- choisir un pattern : Agentic, Adaptive, Corrective ou Self-RAG ;
- rendre les citations **vérifiables** et l'accès aux données conforme aux droits du client ;
- évaluer réponses et **trajectoires** sur un golden set, avec un LLM juge calibré ;
- attaquer leur agent (**red teaming**) et le défendre en profondeur.

## Programme

| Séquence | Contenu | Durée |
|---|---|:-:|
| Module 4.1 | Pourquoi un agent RAG ? | 25 min |
| Module 4.2 | Patterns d'architecture : Agentic, Adaptive, Corrective et Self-RAG, multi-index | 55 min |
| Module 4.3 | Conception : sources, outils, planification, mémoire, citations, identité du client | 50 min |
| Atelier 4.A ★ | Agent RAG multi-sources, exposé par l'API (`POST /agent`) | 90 min |
| Atelier 4.B ★ | Self-RAG et Corrective RAG | 45 min |
| Module 4.4 | Évaluation, fiabilité et sécurité (OWASP Top 10 for LLM Applications) | 50 min |
| Atelier 4.C ★ | Suite d'évaluation et red teaming | 65 min |

★ : atelier qui fait avancer le projet fil rouge.

## Contenu

| Fichier | Rôle |
|---|---|
| [`slides/module04_agents_rag.pdf`](slides/module04_agents_rag.pdf) | Support de cours, 40 pages |
| [`ateliers/4A_agent_rag_multi_sources.ipynb`](ateliers/4A_agent_rag_multi_sources.ipynb) | Atelier 4.A : sources, outils, agent LangGraph, citations, conversation sur plusieurs tours, routeur Adaptive RAG, API |
| [`ateliers/4B_self_rag_crag.ipynb`](ateliers/4B_self_rag_crag.ipynb) | Atelier 4.B : graphe CRAG + Self-RAG, comparé au RAG du Jour 2 |
| [`ateliers/4C_evaluation_red_teaming.ipynb`](ateliers/4C_evaluation_red_teaming.ipynb) | Atelier 4.C : golden set, trajectoires, LLM juge calibré, avant et après 4.B, red teaming |
| `ateliers/agent_rag.py` | Sources, outils (identité du client dans la configuration), agent, citations, routeur, recherche corrective, garde-fous |
| `ateliers/evaluation_agent.py` | Métriques sans LLM, juges d'exactitude et de fidélité, kappa de Cohen, détection des attaques réussies |
| `ateliers/api_assistant.py` | Service web : `GET /sante`, `POST /question` (assistant du Jour 2), `POST /agent` (Jour 4), port 8002 |
| `ateliers/donnees/base_support/articles.json` | Base de connaissances du support : 20 articles publics et une note interne (`KB-900`, filtrée) |
| `ateliers/donnees/golden_set_agent.json` | Golden set : 32 questions (documentation, support, CRM, plusieurs sources, hors périmètre, confidentialité) |
| `ateliers/donnees/jugements_humains.json` | 16 réponses annotées à la main, pour calibrer le juge |
| `ateliers/donnees/red_teaming/` | Huit attaques rattachées à l'OWASP Top 10 for LLM Applications, et deux articles piégés |
| `ateliers/rag.py`, `crm.py`, `donnees/corpus/`, `donnees/crm.json` | Briques des Jours 2 et 3 (copies) |
| `ateliers/executes/` | Notebooks exécutés de bout en bout, avec leurs sorties |

## Démarrage

Depuis la racine du dépôt, après avoir renseigné le `.env` commun (voir le [README racine](../README.md)) :

```bash
cd "Module 04 - Agents RAG/ateliers"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Le service se lance aussi hors du notebook : `uvicorn api_assistant:app --port 8002`, puis http://localhost:8002/docs. Les modèles d'embeddings et de reranking (environ 0,8 Go) sont téléchargés au premier lancement.

## Outils

| Rôle | Outil |
|---|---|
| Agent et graphes CRAG / Self-RAG | LangGraph : graphe d'état, `ToolNode`, mémoire de conversation |
| Modèle | `langchain-openai`, branché sur les fournisseurs d'`outils_llm` |
| Recherche | pipeline du Jour 2 : FastEmbed (embeddings et reranker, en local), Qdrant en mémoire, BM25 |
| Juges (évaluateur d'extraits, vérification, exactitude, fidélité, attaques) | modèles open-weight via `outils_llm`, sorties structurées Pydantic |
| Service web | FastAPI et uvicorn |

Le modèle de l'agent doit savoir appeler des outils : `gpt-oss` (Groq), `nemotron-3.5-lightning` (NVIDIA), `qwen3.8` (Groq). Placez le juge de 4.C chez un autre fournisseur (`MODELE_JUGE`).

## Résultats de référence

Vérification d'octobre 2026, agent `nvidia:nvidia/nemotron-3.5-lightning-30b-a3b`, juge `groq:qwen/qwen3.8-27b`.

- **4.A** : les cinq trajectoires choisissent les bonnes sources ; la question sur le code E-21 interroge le CRM et le support et répond juste (imprimante livrée le 19 octobre, garantie de 24 mois, procédure de l'article `KB-104`) ; aucune citation inventée. La conversation sur trois tours retrouve la commande, calcule 216 CHF avec l'outil, puis cite la FAQ sur les frais de retour. Le **routeur** Adaptive RAG classe la question E-21 en « documentation » : réponse partielle, exactement le risque annoncé (une erreur de routage est définitive).

<!-- résultats de 4.B et 4.C complétés après la vérification -->

## Notes pour le formateur

- **Identité du client** : les outils du CRM lisent le numéro du client dans la configuration de l'exécution (`RunnableConfig`), que le modèle ne voit pas. C'est ce qui fait échouer les attaques sur les données d'un autre client, quel que soit le prompt.
- **Références citables** : `[DOC-n]`, `[KB-nnn]`, `[CMD-AAAA-NNNN]`, `[CL-nnnnn]`. Les modèles écrivent parfois ces références avec un tiret insécable (`KB‑104`) : `ar.normaliser_tirets` les rétablit avant la vérification.
- **Pannes observées pendant la mise au point**, reprises dans les slides :
  - l'outil `mes_commandes` ne renvoyait que la date de commande : l'agent l'a prise pour la date de livraison et a calculé une garantie absurde ;
  - le paramètre `requete` des outils de recherche était écrit `requête` par le modèle : erreurs de validation en boucle ; il s'appelle désormais `question` ;
  - l'évaluateur d'extraits (4.B) recopiait toute la ligne de l'extrait au lieu de sa référence : tous les extraits semblaient non pertinents et CRAG faisait moins bien que le RAG simple ; la référence est maintenant extraite du texte renvoyé.
- **Quotas** : un tour d'agent coûte 2 à 6 appels au modèle, avec un contexte de 3 000 à 9 000 tokens. L'atelier 4.C évalue `N_MAX = 12` questions par campagne (deux campagnes, plus les juges et les attaques : environ 250 appels).
- **Jour 5** : le workflow du Jour 5 réutilise l'agent RAG pour rédiger les réponses aux emails.
