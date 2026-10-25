# Module 01 — Fondamentaux des LLM

**Jour 1 de la formation Autonomous AI Agents & RPA 2.0.** Comprendre les grands modèles de langage (architecture, capacités, limites), écrire des prompts robustes et les exploiter par API pour produire des sorties structurées et vérifiables. Le projet fil rouge démarre : trier les demandes clients de Fictiva SA et en extraire les informations clés.

## Objectifs

À la fin de la journée, les participants savent :

- expliquer le fonctionnement, les capacités et les limites des LLM ;
- choisir un modèle selon la qualité, le coût, la latence et la confidentialité ;
- concevoir des prompts robustes et les **mesurer** sur un jeu de test annoté ;
- appeler un LLM par API et obtenir des **sorties structurées** validées par un schéma.

## Programme

| Séquence | Contenu | Durée |
|---|---|:-:|
| Module 1.1 | Introduction à l'IA générative et aux LLM ; panorama du marché | 30 min |
| Module 1.2 | Architecture : Transformer, tokens, contexte, entraînement, raisonnement, paramètres | 50 min |
| Atelier 1.A | Prise en main : premier appel, fournisseurs, tokens, coût, streaming | 20 min |
| Module 1.3 | Prompt engineering appliqué | 40 min |
| Atelier 1.B | Laboratoire de prompting | 50 min |
| Module 1.4 | Utilisation des LLM par API : sorties structurées, erreurs, coûts, sécurité | 40 min |
| Atelier 1.C ★ | Tri des demandes clients (catégorie, urgence) | 50 min |
| Atelier 1.D ★ | Extraction structurée (emails, factures, contrats) | 50 min |
| Atelier 1.E | Comparaison de modèles : qualité, coût, latence, confidentialité | 40 min |

★ : atelier qui fait avancer le projet fil rouge.

## Contenu

| Fichier | Rôle |
|---|---|
| [`slides/module01_llm.pdf`](slides/module01_llm.pdf) | Support de cours, 57 pages |
| [`ateliers/1A_prise_en_main.ipynb`](ateliers/1A_prise_en_main.ipynb) | Atelier 1.A : premier appel, même modèle chez plusieurs fournisseurs, tokens, coût, streaming |
| [`ateliers/1B_laboratoire_prompting.md`](ateliers/1B_laboratoire_prompting.md) | Atelier 1.B : laboratoire de prompting, à mener dans un notebook vierge |
| [`ateliers/1C_tri_demandes.ipynb`](ateliers/1C_tri_demandes.ipynb) | Atelier 1.C : tri des demandes, deux versions de prompt mesurées |
| [`ateliers/1D_extraction_structuree.ipynb`](ateliers/1D_extraction_structuree.ipynb) | Atelier 1.D : extraction structurée validée par Pydantic |
| [`ateliers/1E_comparaison_modeles.ipynb`](ateliers/1E_comparaison_modeles.ipynb) | Atelier 1.E : trois modèles open-weight comparés sur la tâche 1.C |
| `ateliers/outils_llm.py` | Couche commune d'accès aux LLM : fournisseurs, appel unifié, sorties structurées, traitement par lots, mesures |
| `ateliers/donnees/` | 48 demandes annotées, règles de tri, politique de retours, factures, contrats, vérité terrain d'extraction |
| `ateliers/prompts/` | Prompts versionnés ; `tri_reference.md` sert de repli à l'atelier 1.E |
| `ateliers/executes/` | Notebooks exécutés de bout en bout, avec leurs sorties |

## Démarrage

Depuis la racine du dépôt, après avoir renseigné le `.env` commun (voir le [README racine](../README.md)) :

```bash
cd "Module 01 - LLM/ateliers"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Une seule clé gratuite suffit (Groq ou NVIDIA conseillés) ; les autres fournisseurs sont facultatifs.

## Modèles et fournisseurs

Les ateliers n'utilisent que des **modèles open-weight**, via des paliers gratuits compatibles avec le format OpenAI : un seul SDK (`openai`) suffit, et un modèle se désigne par `fournisseur:modèle`.

| Fournisseur | Palier gratuit constaté (octobre 2026) | Modèles utilisés |
|---|---|---|
| Groq | 1 000 requêtes par jour ; 8 000 tokens par minute et 200 000 par jour, par modèle | `openai/gpt-oss-20b` (par défaut), `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` |
| NVIDIA | prototypage, débit limité ; `gpt-oss-20b` souvent saturé | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| OpenRouter | modèles `:free`, environ 50 requêtes par jour sans crédit, souvent saturés | `google/gemma-4-26b-a4b-it:free` |
| Hugging Face | Inference Providers : crédits requis | `openai/gpt-oss-20b` |

## Résultats de référence

<!-- résultats complétés après la vérification -->

## Notes pour le formateur

- **Quotas** : les paliers gratuits limitent les requêtes et les tokens par minute et par jour. Les notebooks mesurent sur `N_MAX = 20` demandes et traitent deux demandes en parallèle ; en cas d'erreur 429, le SDK attend le délai indiqué par le serveur et réessaie (jusqu'à 10 fois). Un prompt de tri fait environ 2 000 tokens : sur Groq, comptez 3 à 4 demandes par minute et par modèle.
- **Conditions** : les paliers gratuits sont réservés au prototypage, et les données envoyées peuvent être conservées. Les ateliers n'utilisent que des données fictives.
- **Sorties structurées** : quand un modèle ne permet pas d'imposer un schéma (Qwen chez Groq, par exemple), `outils_llm` décrit le schéma dans le prompt et valide la réponse avec Pydantic. L'attribut `Reponse.structure` indique la méthode utilisée.
- **Catalogues** : les modèles gratuits changent vite (en octobre 2026, `llama-3.3-70b-versatile` a quitté Groq et plusieurs modèles NVIDIA ont atteint leur fin de vie). Vérifiez la liste des candidats de l'atelier 1.E avant chaque session.
- **Tarifs** : `outils_llm.TARIFS` contient des tarifs publics payants indicatifs, utilisés pour estimer le coût d'un passage en production.
- **Données** : 48 demandes annotées (8 réservées aux exemples, 40 au test), 5 factures, 3 contrats, 10 cas de remboursement et 8 questions pour le laboratoire ; toutes sont fictives.
