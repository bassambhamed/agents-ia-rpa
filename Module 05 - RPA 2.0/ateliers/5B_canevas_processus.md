# Atelier 5.B — Canevas : transposer la RPA 2.0 à un processus de votre organisation

Ce canevas reprend les rubriques du notebook `5B_transposition.ipynb`, pour un travail sur papier ou en binôme mixte (profil métier et profil technique). **Décrivez le processus de façon anonymisée** : ni nom de client ou de collaborateur, ni donnée personnelle, ni chiffre confidentiel.

## 1. Identification

| Rubrique | Votre réponse |
|---|---|
| Nom du processus | |
| Domaine (finance, RH, service client, achats…) | |
| Propriétaire métier (rôle) | |
| Déclencheur (email, formulaire, échéance, fichier…) | |
| Volume (cas par mois) | |
| Temps de traitement manuel par cas (minutes) | |

## 2. Description métier (5 à 10 lignes)

> Qui fait quoi, avec quels outils, à partir de quelles informations ; quelles décisions ; quelles exceptions.

## 3. Cartographie

| N° | Acteur (rôle) | Action | Système | Automatisable ? (oui / partiellement / non, pourquoi) |
|:-:|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Points de décision et règles appliquées :**

**Exceptions fréquentes :**

**Données personnelles traitées :**

## 4. Éligibilité

Notez chaque critère de 1 (défavorable) à 5 (favorable).

| Critère | Poids | Repères | Note |
|---|:-:|---|:-:|
| Volume | 20 % | 1 : moins de 50 cas par mois ; 5 : plus de 5 000 | |
| Répétitivité | 15 % | 1 : chaque cas est unique ; 5 : quelques variantes connues | |
| Structuration des données | 15 % | 1 : textes libres, scans ; 5 : formulaires, bases de données | |
| Règles de décision | 15 % | 1 : jugement d'expert ; 5 : règles écrites et stables | |
| Valeur attendue | 20 % | temps, délai, qualité, conformité, satisfaction | |
| Risque en cas d'erreur | 15 % | 1 : atteinte aux personnes ou aux droits ; 5 : faible et réversible | |
| **Score pondéré** | | au-dessus de 3,5 : bon candidat | |

**Effort d'automatisation (1 à 5) :** intégrations, qualité des données, conduite du changement.

**Quadrant :** gain rapide · projet stratégique · à reconsidérer · à écarter.

## 5. Ébauche de business case (annuel)

| Poste | Hypothèse | Montant (CHF) |
|---|---|---:|
| Temps manuel actuel | cas × minutes × coût horaire | |
| Temps restant après automatisation | validations, exceptions, contrôle qualité | |
| **Gain annuel** | | |
| Coût des modèles (tokens) | cas × tokens × prix | |
| Exploitation (hébergement, supervision technique) | | |
| Évaluation et maintenance (golden set, prompts, modèles) | | |
| Erreurs résiduelles | taux × coût d'une erreur | |
| **Coûts récurrents** | | |
| Construction (une fois) | conception, intégration, tests, conduite du changement | |
| **Bénéfice net annuel, délai de retour** | | |

**Seuil de rentabilité :** à partir de combien de cas par mois le projet devient-il rentable ?

## 6. Risques et gouvernance

| Question | Réponse |
|---|---|
| Pratique interdite par l'AI Act ? (manipulation, notation sociale…) | |
| Domaine à haut risque (emploi, crédit, éducation, services essentiels…) ? | |
| Les personnes interagissent-elles avec l'IA, ou reçoivent-elles du contenu généré ? | |
| Données personnelles : base légale, information des personnes, analyse d'impact (nLPD, RGPD) ? | |
| Où l'humain valide-t-il ? Selon quelles règles ? | |
| Que se passe-t-il si le service d'IA est indisponible ? | |

## 7. Les trois premières actions

1.
2.
3.
