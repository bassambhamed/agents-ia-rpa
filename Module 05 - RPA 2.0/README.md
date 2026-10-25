# Module 05 — RPA 2.0 : industrialisation et gouvernance

**Jour 5 de la formation Autonomous AI Agents & RPA 2.0.** Les briques des quatre premiers jours deviennent un processus : chaque email reçu par le service client de Fictiva devient un dossier, trié, instruit, validé par un humain quand il le faut, clôturé et mesuré. Le module couvre aussi l'identification et le chiffrage des processus à automatiser, puis la gouvernance (AI Act, nLPD, RGPD) et la conduite du changement.

## Objectifs

À la fin de la journée, les participants savent :

- distinguer RPA classique et RPA 2.0, et choisir entre API, robot RPA et agent « computer use » ;
- évaluer, prioriser et chiffrer un processus, coûts cachés et seuil de rentabilité compris ;
- intégrer un agent dans un workflow supervisé : déclencheur, validation humaine, reprise, indicateurs ;
- rendre ce workflow résilient : idempotence, nouvelles tentatives, modèle de secours, disjoncteur ;
- traduire l'AI Act, la nLPD et le RGPD en règles, en journaux et en registre.

## Programme

| Séquence | Contenu | Durée |
|---|---|:-:|
| Module 5.1 | De la RPA classique à la RPA 2.0 : IPA, hyperautomation, agents « computer use », plateformes | 45 min |
| Module 5.2 | Identifier, prioriser et chiffrer : éligibilité, matrice, process mining, business case | 45 min |
| Module 5.3 | Concevoir et opérer : architecture, humain dans la boucle, résilience, mise en production | 50 min |
| Atelier 5.A ★ | Workflow RPA 2.0 de bout en bout | 80 min |
| Module 5.4 | Gouvernance, conformité et conduite du changement | 40 min |
| Atelier 5.B | Transposition à votre organisation | 40 min |
| Restitution | Présentation des projets fil rouge (8 min + 4 min d'échanges par binôme) | 60 min |
| Clôture | Quiz final, plan d'action à 90 jours, satisfaction | 25 min |

★ : atelier qui fait avancer le projet fil rouge.

## Contenu

| Fichier | Rôle |
|---|---|
| [`slides/module05_rpa.pdf`](slides/module05_rpa.pdf) | Support de cours, 42 pages |
| [`ateliers/5A_workflow_rpa.ipynb`](ateliers/5A_workflow_rpa.ipynb) | Atelier 5.A : service, règles de routage, boîte de réception, validation humaine, tableau de bord, résilience, n8n |
| [`ateliers/5B_transposition.ipynb`](ateliers/5B_transposition.ipynb) | Atelier 5.B : grille d'éligibilité, matrice, spécification par LLM, business case, pré-diagnostic AI Act |
| [`ateliers/5B_canevas_processus.md`](ateliers/5B_canevas_processus.md) | Canevas papier de l'atelier 5.B, pour les binômes mixtes |
| `ateliers/rpa_fictiva.py` | Services métier : dossiers, tri et extraction, identification, proposition, règles de routage, résilience, indicateurs |
| `ateliers/api_rpa.py` | Service web du workflow (port 8005), console de validation (`/console`), tableau de bord (`/tableau-de-bord`) |
| `ateliers/orchestrateur.py` | Le workflow écrit en Python, équivalent de `workflow_n8n.json` |
| `ateliers/workflow_n8n.json` | Workflow importable dans n8n : webhook, appels HTTP avec nouvelles tentatives, aiguillages, attente de la décision humaine |
| `ateliers/business_case.py` | Éligibilité, priorisation, business case, sensibilité, pré-diagnostic AI Act |
| `ateliers/donnees/emails_entrants.json` | 13 emails de test, avec le résultat attendu (dont un doublon et une tentative de manipulation) |
| `ateliers/donnees/processus_exemples.json` | Sept processus d'exemple pour la matrice de priorisation |
| `ateliers/agent_rag.py`, `rag.py`, `crm.py`, `donnees/corpus/`, `donnees/base_support/` | Briques des Jours 2 à 4 (copies) |
| [`restitution/grille_restitution.md`](restitution/grille_restitution.md) | Consignes et grille d'évaluation de la restitution |
| [`cloture/quiz_final.md`](cloture/quiz_final.md) | Quiz final de la formation (20 questions, éléments de réponse) |
| [`cloture/plan_action_90_jours.md`](cloture/plan_action_90_jours.md) | Plan d'action personnel et feuille de route à 90 jours |
| `ateliers/executes/` | Notebooks exécutés de bout en bout, avec leurs sorties |

## Architecture du workflow

```
Email reçu ──▶ POST /dossiers ──▶ doublon ? ──▶ ignoré
  (webhook n8n                │
   ou orchestrateur)          └──▶ validation humaine ?
                                     ├─ non ──▶ POST /dossiers/{id}/cloturer  (ticket CRM, réponse, KPI)
                                     └─ oui ──▶ POST /dossiers/{id}/attente ──▶ décision (console)
                                                ──▶ reprise du workflow ──▶ POST /dossiers/{id}/cloturer
```

Le modèle comprend et rédige ; il ne décide pas seul. Les montants viennent du calcul déterministe du CRM (politique de retours), et des règles codées envoient en validation humaine : montant au-dessus du seuil (`SEUIL_VALIDATION_CHF`, 1 000 CHF), validation exigée par la politique (plus de 5 000 CHF), décision défavorable au client, urgence haute, litige de facturation, contenu suspect, réponse sans source vérifiable, service d'IA indisponible.

## Démarrage

Depuis la racine du dépôt, après avoir renseigné le `.env` commun (voir le [README racine](../README.md)) :

```bash
cd "Module 05 - RPA 2.0/ateliers"
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Le service se lance aussi hors du notebook : `uvicorn api_rpa:app --port 8005`, puis http://localhost:8005/docs, `/console` et `/tableau-de-bord`.

### Avec n8n (facultatif)

1. Lancer n8n : `npx n8n` (Node.js 24 ou plus récent) ou `docker run -it --rm -p 5678:5678 docker.n8n.io/n8nio/n8n`.
2. Dans http://localhost:5678, importer `ateliers/workflow_n8n.json` (*Import from file*), puis publier le workflow. Si n8n tourne dans Docker, remplacer `127.0.0.1` par `host.docker.internal` dans les nœuds HTTP.
3. Exécuter la section 8 du notebook 5.A : elle envoie des emails au webhook `/webhook/fictiva-email` et valide les dossiers en attente, ce qui relance le workflow.

En production, le webhook se remplace par le nœud *Email Trigger (IMAP)*, et la console par une approbation dans Teams ou Slack.

## Résultats de référence

Vérification d'octobre 2026, avec les clés gratuites : tri par `groq:openai/gpt-oss-120b`, modèle de secours `nvidia:nvidia/nemotron-3.5-lightning-30b-a3b`, n8n 2.44.

- **Boîte de réception** : 12 dossiers sur 12 conformes au résultat attendu (action, montant, passage ou non par la validation humaine) ; le doublon est ignoré ; la tentative de manipulation est signalée et part en validation, sans montant.
- **Indicateurs** : la moitié des dossiers est clôturée sans intervention humaine ; 1,3 appel au modèle et environ 3 300 tokens par dossier ; les remboursements calculés (216, 360, 600 et 6 250 CHF) sont exacts.
- **Résilience** : avec un modèle principal inexistant, le tri bascule sur le modèle de secours ; avec deux modèles en panne, le disjoncteur s'ouvre au troisième échec.
- **n8n** : le workflow importé traite les emails reçus par webhook ; la décision humaine envoyée au service relance l'exécution suspendue (nœud *Wait*), qui clôture le dossier.

## Notes pour le formateur

- **Variabilité du tri** : selon le modèle et le passage, l'urgence d'un email (écran défectueux) peut être classée « haute » et envoyer le dossier en validation sans nécessité. C'est un bon sujet de discussion : une erreur prudente coûte du temps, une erreur dans l'autre sens coûte de l'argent.
- **Quotas** : l'analyse d'un email coûte un appel au modèle, plus deux à cinq pour une réponse rédigée par l'agent. La boîte de réception complète tient dans le palier gratuit de Groq.
- **Business case** (atelier 5.B) : à 6 000 emails par mois, retour sur investissement en 3 mois ; à 300 emails par mois, le même projet perd de l'argent. Les tokens coûtent environ 60 CHF par an ; la supervision, l'évaluation et les erreurs résiduelles, plusieurs dizaines de milliers.
- **AI Act** : calendrier à jour du règlement (UE) 2026/1744 (« omnibus numérique ») : systèmes à haut risque de l'annexe III au 2 décembre 2027, annexe I au 2 août 2028 ; interdictions et maîtrise de l'IA (art. 4) depuis le 2 février 2025.
- **Restitution** : prévoir un poste avec le service lancé et la console ouverte ; chaque binôme rejoue deux ou trois emails.
