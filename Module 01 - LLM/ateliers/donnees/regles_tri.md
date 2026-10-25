# Fictiva SA — Règles de tri des demandes clients

Fictiva SA est une entreprise **fictive** de distribution B2B de matériel informatique et de fournitures de bureau (Suisse romande). Le service client reçoit chaque jour plusieurs centaines d'emails. Chaque demande doit recevoir **une catégorie** et **un niveau d'urgence**.

## Catégories

| Catégorie | Définition |
|---|---|
| `reclamation` | Le client signale un problème (produit défectueux ou endommagé, colis abîmé, erreur ou retard de livraison, intervention non effectuée), qu'il demande ou non une correction : remplacement, échange, intervention, livraison du manquant. |
| `remboursement` | Le client demande explicitement un remboursement, un avoir ou un retour de marchandise contre remboursement. |
| `litige_facturation` | Le client conteste une facture ou une relance : montant, prix, remise, TVA, doublon, conditions de paiement, adresse de facturation, blocage de compte lié à une facture. |
| `question_produit` | Demande d'information avant ou après achat : caractéristiques, compatibilité, disponibilité, prix, délai, documentation, offre commerciale demandée par le client. |
| `autre` | Tout le reste : changement de coordonnées, gestion des accès, ouverture de compte, candidature, prospection reçue, remerciement, message de test ou sans objet. Un problème signalé, même sans demande d'action, relève de `reclamation`. |

**Demande à plusieurs intentions.** Retenir la catégorie qui engage le plus Fictiva, dans cet ordre de priorité : `remboursement` > `litige_facturation` > `reclamation` > `question_produit` > `autre`.

## Niveaux d'urgence

| Urgence | Critères |
|---|---|
| `haute` | Au moins un des cas suivants : l'activité du client est bloquée ou à l'arrêt ; menace explicite de résiliation, de procédure ou de recours à un avocat ; montant en jeu supérieur à 5 000 CHF ; risque pour la sécurité des personnes. |
| `normale` | Sans critère d'urgence haute, une action de Fictiva est attendue : traiter une réclamation, un remboursement ou un litige ; répondre à une question assortie d'un délai (« aujourd'hui », « cette semaine », « demain ») ; ouvrir un compte ; créer ou désactiver un accès. |
| `basse` | Aucune action rapide n'est attendue : demande d'information sans délai, prospection ou sollicitation reçue (étude, partenariat), candidature, remerciement, changement de coordonnées, simple signalement sans demande. |

Dans le doute entre `normale` et `basse`, retenir `normale`.
