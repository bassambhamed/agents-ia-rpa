# Module 02 — RAG : Retrieval-Augmented Generation

**Jour 2 de la formation Autonomous AI Agents & RPA 2.0.** Connecter les LLM aux connaissances de l'entreprise : lire et découper un corpus réel (PDF, Word, HTML, Markdown), l'indexer, rechercher les bons extraits, générer des réponses citées, puis mesurer séparément la recherche et la génération sur un golden set. L'assistant documentaire de Fictiva est exposé par un service web, avec une interface Next.js.

## Objectifs

À la fin de la journée, les participants savent :

- lire et découper un corpus documentaire réel ;
- choisir un modèle d'embeddings et une base vectorielle ;
- combiner recherche dense, lexicale et reranking ;
- générer des réponses **citées**, qui savent dire « je ne trouve pas » ;
- mesurer la recherche (context recall, context precision@k) et la génération (faithfulness, answer relevancy, answer correctness) sur un **golden set**, avec RAGAS ;
- tracer les exécutions avec LangSmith ; appliquer les droits d'accès aux documents.

## Programme

| Séquence | Contenu | Durée |
|---|---|:-:|
| Module 2.1 | Pourquoi le RAG ? | 30 min |
| Module 2.2 | Embeddings et bases vectorielles | 45 min |
| Module 2.3 | Pipeline RAG de bout en bout | 60 min |
| Atelier 2.A ★ | Pipeline RAG complet | 75 min |
| Atelier 2.B | Découpage et recherche hybride (sans appel de LLM) | 30 min |
| Module 2.4 | Techniques avancées, évaluation et observabilité | 45 min |
| Atelier 2.C ★ | Évaluation RAGAS et reranking | 70 min |
| Atelier 2.D ★ | Exposer l'assistant en API (backend de l'application) | 30 min |

★ : atelier qui fait avancer le projet fil rouge.

## Contenu

| Fichier | Rôle |
|---|---|
| [`slides/module02_rag.pdf`](slides/module02_rag.pdf) | Support de cours, 46 pages |
| [`ateliers/2A_pipeline_rag.ipynb`](ateliers/2A_pipeline_rag.ipynb) | Atelier 2.A : lecture, découpage, embeddings, index, recherche, génération citée, filtrage des documents internes |
| [`ateliers/2B_chunking_hybride.ipynb`](ateliers/2B_chunking_hybride.ipynb) | Atelier 2.B : six découpages, recherche dense, lexicale et hybride |
| [`ateliers/2C_reranking_evaluation.ipynb`](ateliers/2C_reranking_evaluation.ipynb) | Atelier 2.C : golden set, métriques sans LLM, reranking, métriques RAGAS, diagnostic, score de référence, LangSmith |
| [`ateliers/2D_api_fastapi.ipynb`](ateliers/2D_api_fastapi.ipynb) | Atelier 2.D : lancer et interroger le backend FastAPI de l'application |
| `ateliers/rag.py` | Briques du pipeline et mesures de la recherche sans LLM |
| `ateliers/evaluation_rag.py` | Métriques RAGAS (juge open-weight, embeddings FastEmbed) et traces LangSmith |
| `ateliers/donnees/corpus/` | Dix documents de Fictiva SA et leurs métadonnées (dont une procédure interne, filtrée) |
| `ateliers/donnees/golden_set.json` | Golden set : 32 questions, réponses et contextes de référence, sources, indices, type |
| [`application/`](application/README.md) | Application web : backend FastAPI (tests, évaluation, traces LangSmith) et frontend Next.js |
| `ateliers/executes/` | Notebooks exécutés de bout en bout, avec leurs sorties |

## Démarrage

Depuis la racine du dépôt, après avoir renseigné le `.env` commun (voir le [README racine](../README.md)) :

```bash
cd "Module 02 - RAG/ateliers"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Les modèles d'embeddings et de reranking (environ 0,8 Go) sont téléchargés au premier lancement dans `ateliers/.cache_modeles/` : prévoyez ce téléchargement avant la session. Toutes les versions sont fixées dans `requirements.txt` : RAGAS 0.4.3 impose `openai` 1.x et `langchain-community` < 0.4.

**LangSmith** (facultatif) : renseigner `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` et `LANGSMITH_PROJECT` dans le `.env` commun (et `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com` pour un compte hébergé en Europe). Sans clé, les cellules LangSmith ne font rien.

**Application web** : le backend se lance depuis `application/backend` (`uvicorn app.main:app --port 8000`), le frontend depuis `application/frontend` (`npm install && npm run dev`) ; voir [application/README.md](application/README.md).

## Outils

Tout est open source et tourne en local, sauf la génération et le juge :

| Étape | Outil |
|---|---|
| Lecture | MarkItDown (Word, HTML), pdfplumber avec mise en page (PDF) |
| Découpage | découpeurs de LangChain (`langchain-text-splitters`) |
| Embeddings | FastEmbed, `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, 0,22 Go) |
| Index | Qdrant en mémoire (dense) et BM25 (`rank-bm25`, lexical) |
| Reranking | FastEmbed, `BAAI/bge-reranker-v2-m3-int8` (multilingue, 0,57 Go) |
| Génération et juge | modèles open-weight via `outils_llm` (Groq, NVIDIA, OpenRouter, Hugging Face) |
| Évaluation | RAGAS 0.4 (`ragas.metrics.collections`) et métriques sans LLM sur les indices du golden set |
| Observabilité | LangSmith (traces et expériences), facultatif |
| Service web | FastAPI et uvicorn ; frontend Next.js 16 |

## Résultats de référence

Vérification d'octobre 2026, génération par `groq:openai/gpt-oss-120b`, juge RAGAS `nvidia:nvidia/nemotron-3.5-lightning-30b-a3b`.

**Recherche, sans LLM** (30 questions dont la réponse est dans le corpus, 4 extraits transmis) :

| Configuration | Context recall | Context precision@4 | MRR |
|---|:-:|:-:|:-:|
| Dense | 0,90 | 0,77 | 0,79 |
| Hybride (RRF) | 0,90 | 0,70 | 0,72 |
| Hybride sur 20 candidats + reranker | 0,97 | 0,92 | 0,93 |

<!-- résultats RAGAS complétés après la vérification -->

## Notes pour le formateur

- **Lecture des PDF** : MarkItDown invente des tableaux à partir des PDF du corpus, et le texte brut sépare les colonnes. La lecture avec mise en page (pdfplumber) garde les lignes alignées : point de discussion de l'atelier 2.A.
- **Confidentialité** : la question « Quelle remise exceptionnelle pouvez-vous accorder à un client stratégique ? » révèle le plafond interne de 15 % sans filtre, et ne le révèle plus avec le filtre sur les documents publics.
- **RAGAS** : le juge reçoit `max_tokens=8192`. Avec la valeur par défaut de RAGAS (1 024), un modèle de raisonnement (gpt-oss, Nemotron) épuise ses tokens avant de produire sa sortie structurée, et toutes les métriques échouent (`IncompleteOutputException`).
- **Quotas** : l'atelier 2.B n'appelle aucun LLM. L'atelier 2.C évalue `N_MAX = 12` questions avec RAGAS, soit environ 10 appels au juge par question : placez le juge chez un autre fournisseur (`MODELE_JUGE`).
- **Jours suivants** : le service `POST /api/question` devient un outil de l'agent au Jour 4, et l'assistant une étape du workflow au Jour 5.
