# Module 03 — Agents IA autonomes

**Jour 3 de la formation Autonomous AI Agents & RPA 2.0.** Le tri (Jour 1) et l'assistant documentaire (Jour 2) savent répondre ; l'agent sait **agir**. Les participants écrivent une boucle d'agent à la main, puis construisent avec LangGraph l'agent du service après-vente de Fictiva : il consulte le CRM par un serveur MCP, calcule un remboursement avec un outil déterministe, crée un ticket après validation humaine, et chaque étape est tracée.

## Objectifs

À la fin de la journée, les participants savent :

- choisir entre un workflow déterministe et un agent ;
- écrire la boucle d'un agent et décrire ses outils (function calling) ;
- exposer des outils métier par un serveur **MCP** ;
- construire un agent avec **LangGraph** : état, mémoire, validation humaine (`interrupt`) ;
- orchestrer plusieurs agents spécialisés, et en mesurer le coût ;
- tracer un agent et diagnostiquer ses pannes.

## Programme

| Séquence | Contenu | Durée |
|---|---|:-:|
| Module 3.1 | Du LLM à l'agent autonome : définition, typologie, autonomie graduée, workflow ou agent | 35 min |
| Module 3.2 | Architecture d'un agent : ReAct, planification, mémoire, garde-fous | 50 min |
| Atelier 3.A | Agent ReAct sans framework : calculatrice, taux de change, Wikipédia, météo | 45 min |
| Module 3.3 | Outils, function calling et MCP ; sécurité des outils | 50 min |
| Atelier 3.B ★ | L'agent du service après-vente : CRM via MCP, calcul, validation humaine, mémoire | 75 min |
| Module 3.4 | Multi-agents, frameworks, observabilité | 45 min |
| Atelier 3.C | Une équipe d'agents : analyste, rédacteur, relecteur | 40 min |
| Atelier 3.D ★ | Observabilité et débogage : trois pannes à diagnostiquer | 40 min |

★ : atelier qui fait avancer le projet fil rouge.

## Contenu

| Fichier | Rôle |
|---|---|
| [`slides/module03_agents.pdf`](slides/module03_agents.pdf) | Support de cours, 38 pages |
| [`ateliers/3A_agent_react.ipynb`](ateliers/3A_agent_react.ipynb) | Atelier 3.A : boucle d'agent écrite à la main, function calling, API publiques |
| [`ateliers/3B_agent_sav.ipynb`](ateliers/3B_agent_sav.ipynb) | Atelier 3.B : agent LangGraph du service après-vente |
| [`ateliers/3C_multi_agents.ipynb`](ateliers/3C_multi_agents.ipynb) | Atelier 3.C : équipe de trois agents, comparée à un agent unique |
| [`ateliers/3D_observabilite.ipynb`](ateliers/3D_observabilite.ipynb) | Atelier 3.D : traceur local (Langfuse en option) et diagnostic de pannes |
| `ateliers/crm.py` | CRM simulé (clients, commandes, tickets) et calcul des remboursements selon la politique de retours |
| `ateliers/serveur_crm_mcp.py` | Serveur MCP qui expose le CRM en lecture seule |
| `ateliers/agents_fictiva.py` | Modèle de chat, outils, graphe LangGraph, traceur local, affichage des trajectoires |
| `ateliers/donnees/crm.json`, `demandes_sav.json` | Données du CRM (date du scénario : 23 octobre 2026) et six demandes avec le montant attendu |
| `ateliers/executes/` | Notebooks exécutés de bout en bout, avec leurs sorties |

## Démarrage

Depuis la racine du dépôt, après avoir renseigné le `.env` commun (voir le [README racine](../README.md)) :

```bash
cd "Module 03 - Agents IA/ateliers"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Le modèle doit savoir appeler des outils : `gpt-oss` (par défaut, chez Groq), `nemotron-3.5-lightning` (NVIDIA), `qwen3.8` (Groq). Pour explorer le serveur MCP avec l'inspecteur officiel : `mcp dev serveur_crm_mcp.py`. Langfuse est facultatif : sans ses clés, l'atelier 3.D utilise un traceur local.

## Outils

| Rôle | Outil |
|---|---|
| Agent sans framework | SDK `openai`, function calling |
| Agent et multi-agents | LangGraph : graphe d'état, `ToolNode`, mémoire, `interrupt` |
| Modèle | `langchain-openai`, branché sur les fournisseurs d'`outils_llm` |
| Outils métier | serveur MCP (`mcp`, FastMCP), chargé par `langchain-mcp-adapters` |
| API publiques (3.A) | Frankfurter (taux de la BCE), Wikipédia, Open-Meteo : gratuites, sans clé |
| Observabilité | traceur local (rappels LangChain) ; Langfuse si ses clés sont dans `.env` |

## Résultats de référence

Vérification d'octobre 2026 avec `nvidia:nvidia/nemotron-3.5-lightning-30b-a3b` :

- **3.A** : l'agent enchaîne les outils sans erreur (TVA puis conversion en euros au taux de la BCE, recherche Wikipédia puis calcul) ; la limite d'itérations arrête proprement la boucle.
- **3.B** : sur les demandes de remboursement, l'agent obtient chaque montant attendu (216, 360, 6 250, 0 et 600 CHF) ; au-delà de 5 000 CHF, la validation est requise ; la création du ticket attend la décision de l'opérateur.
- **3.C** : pour la même décision, l'équipe de trois agents prend environ 7 fois plus de temps (129 s contre 18 s) et produit 10 fois plus de tokens en sortie que l'agent unique.
- **3.D** : un numéro de commande inexistant arrête l'agent (`KeyError`) ; des outils mal décrits font passer de 4 à 10 appels au modèle et de 11 à 45 secondes ; l'outil « rappelez-moi » fait boucler l'agent, et une réponse explicite de l'outil y met fin.

## Notes pour le formateur

- **Démonstrations à exploiter** : pour la commande jamais livrée (SAV-6), l'agent propose un remboursement que la politique ne prévoit pas : l'opérateur le refuse (3.B). Sans accès à la documentation, l'agent peut affirmer des règles fausses, comme « pas d'avoir possible » : c'est la transition vers le Jour 4.
- **Taux de change** : avec un outil qui ne renvoie que le taux, un modèle a divisé au lieu de multiplier ; l'outil renvoie maintenant la règle de calcul (3.A).
- **Wikipédia** exige un User-Agent avec un contact, sinon l'API répond 403 ; l'outil de 3.A en déclare un.
- **Quotas** : un agent fait 3 à 6 appels par demande, avec un contexte qui grossit (2 000 à 6 000 tokens). Sur Groq, la limite de 8 000 tokens par minute impose des pauses : NVIDIA est plus confortable pour ce module.
- **Bonus du plan** (agent d'analyse de données avec interpréteur de code en bac à sable) : non développé ; un vrai bac à sable demande un conteneur isolé.
- **Jour 4** : l'agent du service après-vente et le CRM sont réutilisés, avec l'assistant documentaire du Jour 2 comme outil supplémentaire.
