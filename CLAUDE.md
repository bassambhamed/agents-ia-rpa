# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du projet

Formation **« Autonomous AI Agents & RPA 2.0 »** (5 jours, en français) : un dossier par jour (`Module 0N - <Thème>/`) avec slides Beamer, notebooks d'atelier, données synthétiques, et une application web au Module 02. Le plan détaillé est `plan.md`, source de vérité (export Word si demandé : `pandoc plan.md -o Plan_Formation_Agents_IA_RPA_2.0.docx`).

Le dépôt n'est pas encore sous git ; `.gitignore` prépare la publication sur GitHub. Ne sont **pas publiés** : `plan.md`, `style/`, les cinq sources `.tex` des slides (seuls les PDF le sont), `.env`. Les README ne doivent donc pas renvoyer vers ces fichiers. Le README racine sert de vitrine GitHub (bannière `ai_agents.webp`).

## Commandes

```bash
# Ateliers d'un module (chaque dossier ateliers/ a son requirements.txt aux versions fixées)
cd "Module 04 - Agents RAG/ateliers" && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && jupyter lab

# Application du Module 02
cd "Module 02 - RAG/application/backend"
pytest                                   # 9 tests, LLM et encodeur factices, sans clé
pytest tests/test_api.py::test_sante     # un seul test
python evaluer.py --seuil 0.85           # golden set sans LLM ; --generation, --langsmith
uvicorn app.main:app --reload --port 8000
cd ../frontend && npm install && npm run dev      # aussi : npm run build, npm run typecheck

# Services des ateliers (lancés aussi par les notebooks)
uvicorn api_assistant:app --port 8002    # Module 04 : /question, /agent
uvicorn api_rpa:app --port 8005          # Module 05 : /dossiers, /validations, /console, /tableau-de-bord

# Slides (dans slides/) : ne garder ensuite que le .tex et le .pdf
latexmk -pdf <fichier>.tex && latexmk -c && rm -f *.nav *.snm *.vrb
```

Ports : 8000 backend de l'application, 3000 frontend, 8002 service du Module 04, 8005 service du Module 05, 5678 n8n.

## Architecture : une chaîne de briques réutilisées

Le projet fil rouge (assistant de traitement des demandes clients de Fictiva SA) se construit jour après jour ; chaque module **copie** les briques des jours précédents pour rester autonome :

- **`outils_llm.py`** (tous les modules, et `application/backend/app/`) : accès unique aux LLM sous la forme `fournisseur:modèle` (Groq, NVIDIA, OpenRouter, Hugging Face, tous au format OpenAI). `demander()` impose un schéma Pydantic et bascule sur « JSON demandé dans le prompt » si le fournisseur refuse ; `choisir_modele()` retient le premier modèle de `MODELE_PAR_DEFAUT` puis `MODELES_DE_REPLI` dont la clé est renseignée ; `en_lot()` parallélise (2 par défaut). Il charge le `.env` le plus proche, puis celui de la racine. **Les six copies doivent rester identiques.**
- **J1** : prompt de tri (`prompts/tri_reference.md`, règles de `regles_tri.md`), repris par le tri des emails du J5.
- **J2** : `rag.py` (lecture PDF/DOCX/HTML, découpage par sections, FastEmbed, Qdrant en mémoire + BM25 fusionnés par RRF, reranker, filtre `public_seulement` qui écarte les documents internes). Copié aux J4 et J5 ; la copie de l'application ne diffère que par les chemins et les décorateurs LangSmith `traceable`.
- **J3** : `crm.py` (CRM simulé, date du scénario fixée au 23 octobre 2026, calcul déterministe des remboursements selon la politique de retours), serveur MCP, agent LangGraph du service après-vente.
- **J4** : `agent_rag.py` (sources documentation + base de support + CRM, outils, agent, citations vérifiables, routeur Adaptive RAG, recherche corrective, garde-fous) et `evaluation_agent.py` (juges, kappa, red teaming). L'identité du client passe par la configuration LangGraph (`RunnableConfig`), jamais par un paramètre visible du modèle. Références citables : `[DOC-n]`, `[KB-nnn]`, `[CMD-AAAA-NNNN]`, `[CL-nnnnn]` ; `normaliser_tirets` rétablit les tirets insécables écrits par les modèles. Copié à l'identique au J5.
- **J5** : `rpa_fictiva.py` (`ServiceRPA` : un email devient un dossier ; tri par LLM avec modèle de secours et disjoncteur ; montants calculés par `crm.py` ; réponses rédigées par l'agent du J4 ; **règles de routage codées** qui décident de la validation humaine ; idempotence par `message_id` ; indicateurs). `api_rpa.py` l'expose ; `orchestrateur.py` (Python) et `workflow_n8n.json` (n8n) enchaînent les mêmes appels. La validation humaine suspend le workflow (nœud n8n *Wait*) : l'API enregistre `$execution.resumeUrl` et l'appelle quand le validateur décide.

## Cohérence interne à préserver

- **Numérotation** : chaque jour N compte 4 modules (`N.1` à `N.4`) et des ateliers lettrés (`N.A`…). Un atelier ajouté ou renuméroté impose de mettre à jour la colonne « Évalué par » (§1.1 du plan) et les renvois entre ateliers.
- **Budget horaire** : `plan.md` n'indique ni volume horaire total, ni horaires de journée, ni répartition théorie/ateliers ; ne pas les réintroduire. Seules figurent des durées par module (`· 30 min`) et par atelier (`(50 min)`). Une journée tient en 420 min environ : 30 min d'accueil le J1 ou 15 min de rappel ensuite, 15 min de synthèse ; le J5 ajoute 60 min de restitution et 25 min de clôture.
- **Fil rouge** : les ateliers ★ restent alignés avec le tableau des incréments (§2) ; l'API de 2.D est réutilisée en 4.A et 5.A ; les processus du questionnaire de positionnement (§4) alimentent 5.B.
- **Outillage** : tout outil utilisé en atelier figure dans le tableau du §5, et inversement.
- **Version** : incrémenter la version et la date du pied de page de `plan.md` à chaque révision de fond.
- **Données** : synthétiques uniquement (Fictiva SA). Les faits restent cohérents entre modules (politique de retours, CGV, références et prix, montants). Une modification du corpus se répercute dans le golden set du J2 (`donnees/golden_set.json`), puis dans les copies (`application/donnees/`, corpus des Modules 04 et 05). Les montants de référence (golden sets, emails du J5) se vérifient avec `crm.py`.

## Conventions

- Français ; objectifs formulés avec des verbes d'action mesurables, rattachés à un jour et à un mode d'évaluation ; cadre réglementaire suisse et européen (nLPD, RGPD, AI Act).
- **Notebooks** : une seule version, complète et commentée (pas d'énoncé ni de corrigé). Ils sont modifiés directement (par exemple avec `nbformat`) ; aucun générateur n'est versionné. L'atelier 1.B est un fichier Markdown.
- **Modèles** : uniquement open-weight, via les paliers gratuits de Groq, NVIDIA, OpenRouter et Hugging Face. Pas d'exécution locale : Ollama a été retiré de tout le contenu à la demande de l'auteur, ne pas le réintroduire. Catalogues, quotas et fins de vie changent souvent : tester un modèle avec les clés avant de l'ajouter (appel simple, outils, sortie structurée). Les choix courants sont dans `.env.example`.
- **Slides** : Beamer 16:9, thème `style/beamerthememlops.sty` chargé par `\def\input@path{{../../style/}}`, libellés `\mlfooterlabel` et `\mltitlekicker`. Avec babel-french, mettre entre accolades le corps d'un `\foreach` TikZ ; une frame avec du code est `[fragile]`. Relire le PDF rendu (planches d'images) : les débordements ne sont pas tous signalés dans le journal.
- **Versions** : chaque `requirements.txt` fixe ses versions (`==`). Le Module 02 est contraint par RAGAS 0.4.3 (`openai` 1.x, `langchain-community` < 0.4) ; les autres modules et le backend utilisent `openai` 3.x.

## Vérifier avant de livrer

- Exécuter chaque notebook de bout en bout avec les clés du `.env` commun, sur une copie du **module entier** (2.D lance `../application/backend`), puis lire les sorties : compter les « Error code: 429 » et les « échec », pas seulement le statut de la cellule.
- **Quotas Groq** (8 000 tokens par minute par modèle) : ne pas faire tourner en parallèle des notebooks qui partagent un modèle Groq ; NVIDIA (`nemotron-3.5-lightning`) supporte mieux les agents et les juges.
- **Juge RAGAS** : `llm_factory(..., max_tokens=8192)` ; avec la valeur par défaut (1 024), un modèle de raisonnement tronque sa sortie (`IncompleteOutputException`).
- Publier les notebooks exécutés dans `ateliers/executes/` seulement après avoir retiré les clés, les identifiants d'organisation Groq (`org_…`) et les chemins locaux des sorties.
- Application : `pytest`, `npm run build`, puis un essai avec les deux serveurs lancés.
- **n8n** : l'installer hors du projet et toujours définir `N8N_USER_FOLDER` (sinon il écrit dans `~/.n8n`) ; `n8n import:workflow`, puis `n8n publish:workflow` avant `n8n start`.
