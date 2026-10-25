# Application — Assistant documentaire Fictiva

Application web complète de l'assistant du Module 02 : un **backend FastAPI** qui exécute le pipeline RAG des ateliers, et un **frontend Next.js** pour poser des questions et lire les réponses citées. L'atelier 2.D lance ce backend et l'interroge ; le frontend est le bonus de l'atelier.

```
Navigateur ──> Next.js (frontend, port 3000) ──/api/*──> FastAPI (backend, port 8000) ──> rag.Assistant ──> LLM open-weight
                                                              │                           (Qdrant, BM25, reranker)
                                                              └──> LangSmith (traces, si configuré)
```

Toutes les données sont synthétiques : Fictiva SA est une entreprise fictive.

## Contenu

| Dossier / fichier | Rôle |
|---|---|
| `donnees/` | Copie de `ateliers/donnees` : corpus de dix documents et `golden_set.json` |
| `backend/app/main.py` | API FastAPI : routes, CORS, construction de l'index au démarrage |
| `backend/app/rag.py` | Pipeline RAG (copie de `ateliers/rag.py`, étapes tracées avec `langsmith.traceable`) |
| `backend/app/outils_llm.py` | Accès aux LLM (copie identique à celle des ateliers) |
| `backend/app/observabilite.py` | Traces LangSmith des appels de modèles (`wrap_openai`) |
| `backend/app/schemas.py`, `config.py` | Schémas Pydantic des requêtes et réponses ; réglages lus dans le `.env` commun |
| `backend/evaluer.py` | Évaluation sur le golden set (non-régression, expérience LangSmith) |
| `backend/tests/` | Tests de l'API avec un encodeur et un LLM factices (sans téléchargement ni clé) |
| `frontend/app/page.tsx` | Page de questions-réponses : citations cliquables, extraits, mode « extraits seulement » |
| `frontend/components/`, `frontend/lib/api.ts` | Composants d'affichage et client typé de l'API |
| `frontend/next.config.ts` | Relais des appels `/api/*` vers le backend (`BACKEND_URL`) |

## Prérequis

- Python 3.11 à 3.13 ;
- Node.js 20.9 ou plus récent (testé avec Node 24) ;
- au moins une clé de fournisseur gratuit (Groq ou NVIDIA conseillés).

## Lancer le backend

```bash
cd "Module 02 - RAG/application/backend"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# les clés et réglages sont lus dans le .env commun, à la racine du dépôt (voir ../../../.env.example) ;
# un backend/.env l'emporte s'il existe (modèle : backend/.env.example)
uvicorn app.main:app --reload --port 8000
```

Au démarrage, le service lit le corpus, construit l'index et charge le reranker (quelques secondes ; au premier lancement, téléchargement des modèles d'embeddings et de reranking, environ 0,8 Go, dans `backend/.cache_modeles/`). Documentation interactive : http://localhost:8000/docs.

| Route | Rôle |
|---|---|
| `GET /api/sante` | État du service : modèle, nombre de documents et d'extraits, reranking, LangSmith |
| `GET /api/documents` | Documents publics interrogés (les documents internes ne sont pas listés) |
| `GET /api/exemples` | Une question du golden set par type |
| `POST /api/recherche` | Extraits retrouvés pour une question, **sans appel au modèle** |
| `POST /api/question` | Réponse citée, extraits transmis au modèle, sources, latence et coût estimé |

```bash
curl -s localhost:8000/api/question -H "Content-Type: application/json" \
     -d '{"question": "Quel est le délai d'\''intervention du contrat de maintenance Argent ?"}'
```

## Lancer le frontend

Dans un second terminal :

```bash
cd "Module 02 - RAG/application/frontend"
npm install
cp .env.local.example .env.local  # facultatif : BACKEND_URL, par défaut http://localhost:8000
npm run dev
```

Ouvrir http://localhost:3000. Le navigateur n'appelle que le serveur Next.js, qui relaie `/api/*` vers le backend : pas de CORS à gérer, et l'URL du backend reste côté serveur. Pour la production : `npm run build` puis `npm run start` (la variable `BACKEND_URL` est lue au moment du build).

## Observabilité avec LangSmith

1. Créer un compte sur https://smith.langchain.com (offre Developer gratuite, avec un quota mensuel de traces) et une clé d'API.
2. Dans le `.env` commun (ou `backend/.env`) : `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`, `LANGSMITH_PROJECT=assistant-fictiva` ; pour un compte hébergé en Europe, `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`.
3. Redémarrer le backend : `GET /api/sante` indique `"langsmith": true`.

Chaque question devient une trace :

```
assistant_documentaire (chain)
├── recherche (retriever) : extraits retrouvés, sources et scores
└── ChatOpenAI (llm) : prompt, réponse, tokens, durée
```

Les traces contiennent les questions des utilisateurs : en dehors de la formation (données synthétiques), appliquez la nLPD et le RGPD (région UE, masquage, durée de conservation).

## Tests et évaluation

```bash
cd "Module 02 - RAG/application/backend"
pytest                              # 9 tests, sans modèle à télécharger ni clé
python evaluer.py                   # recherche seule, sans LLM : context recall et context precision@k par type
python evaluer.py --generation      # avec les réponses du modèle : refus hors corpus, citations, absence de fuite
python evaluer.py --seuil 0.85      # code de sortie 1 si le context recall moyen passe sous 0,85 (CI)
python evaluer.py --langsmith       # expérience LangSmith sur le dataset « fictiva-golden-set »
```

Les métriques RAGAS calculées par un LLM juge (faithfulness, answer relevancy, answer correctness…) sont présentées dans l'atelier 2.C ; `evaluer.py` se limite aux mesures rapides et reproductibles, adaptées à une intégration continue.

## Versions

Backend : versions fixées dans `backend/requirements.txt` (FastAPI 0.162, LangSmith 0.14, openai 3.37…). Le backend n'utilise pas RAGAS : il n'a donc pas la contrainte `openai` 1.x des ateliers. Frontend : Next.js 16.4, React 19.3, TypeScript 5.9 (`frontend/package.json` ; `package-lock.json` fige l'arbre complet). Vérifié en octobre 2026.

## Maintenance

- `donnees/` est une **copie** de `ateliers/donnees` : après une modification du corpus ou du golden set, recopier le dossier (`rsync -a --delete ../ateliers/donnees/ donnees/`).
- `backend/app/outils_llm.py` est identique à `ateliers/outils_llm.py` ; `backend/app/rag.py` n'en diffère que par les chemins et les décorateurs `traceable`. Reporter toute modification dans les deux versions.
