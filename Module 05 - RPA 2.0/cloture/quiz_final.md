# Quiz final — Autonomous AI Agents & RPA 2.0

Vingt questions, quatre par jour. Comparé au questionnaire de positionnement, il mesure la progression. Les éléments de réponse sont donnés à la fin.

## Jour 1 — LLM

1. Pourquoi un LLM peut-il donner deux réponses différentes à la même question ?
2. Qu'apporte une sortie structurée validée par un schéma, par rapport à du texte libre ?
3. Citez deux critères, autres que la qualité, pour choisir un modèle.
4. Pourquoi mesure-t-on un prompt sur un jeu de test annoté ?

## Jour 2 — RAG

5. Que mesure la context precision@k ?
6. Pourquoi combiner recherche dense et recherche lexicale ?
7. Comment empêcher un assistant RAG de divulguer un document interne ?
8. Que signifie une fidélité (faithfulness) de 1,0 accompagnée d'une exactitude faible ?

## Jour 3 — Agents IA

9. Qu'est-ce qui distingue un agent d'un workflow déterministe ?
10. Pourquoi un montant de remboursement doit-il être calculé par un outil plutôt que par le modèle ?
11. Quel est le rôle d'un serveur MCP ?
12. Que doit contenir la trace d'un agent pour être utile au débogage ?

## Jour 4 — Agents RAG

13. Que fait le Corrective RAG quand aucun extrait retrouvé n'est pertinent ?
14. Pourquoi l'identité du client ne doit-elle pas être un paramètre visible d'un outil ?
15. Que mesure le kappa de Cohen lors de la calibration d'un juge ?
16. Comment une injection indirecte atteint-elle un agent ?

## Jour 5 — RPA 2.0

17. Citez trois règles qui doivent envoyer un dossier en validation humaine.
18. À quoi sert l'idempotence dans un workflow déclenché par email ?
19. Pourquoi un business case ne peut-il pas se limiter au coût des tokens ?
20. Depuis quand l'obligation de maîtrise de l'IA (AI Act, art. 4) s'applique-t-elle, et à qui ?

## Éléments de réponse

1. La génération est un échantillonnage probabiliste (température, top-p) ; les fournisseurs n'offrent pas de déterminisme garanti.
2. Un format vérifiable automatiquement, des valeurs contrôlées et des erreurs détectées avant d'atteindre le système suivant.
3. Coût, latence, confidentialité (hébergement, rétention), souveraineté, licence.
4. Pour comparer objectivement des versions et éviter les régressions.
5. La part d'extraits pertinents parmi les k premiers, pondérée par leur rang : les bons extraits sont-ils en tête ?
6. Le dense capte le sens et les reformulations ; le lexical capte les références exactes (codes produits, numéros).
7. En filtrant les documents selon les droits de l'utilisateur avant la recherche, jamais par une consigne dans le prompt.
8. La réponse s'appuie bien sur les extraits, mais ceux-ci ne contiennent pas la bonne information : le problème est dans la recherche (ou la référence est à revoir).
9. L'agent choisit dynamiquement ses actions et leur ordre ; le workflow suit un chemin fixé à l'avance.
10. Un calcul déterministe est exact, testable et auditable ; le modèle peut se tromper ou être manipulé.
11. Exposer des outils et des données selon un protocole standard, utilisable par n'importe quel client MCP.
12. Les appels au modèle et aux outils, leurs entrées et sorties, les durées, les tokens et les erreurs.
13. Il reformule la requête, interroge une source alternative, et refuse ou escalade si rien ne convient.
14. Le modèle pourrait l'inventer ou être manipulé pour la changer ; l'identité vient de la session authentifiée.
15. L'accord entre le juge et les annotateurs humains, corrigé de l'accord dû au hasard.
16. Par un contenu retrouvé (document, page web, email) qui contient des instructions malveillantes.
17. Montant au-dessus d'un seuil, décision défavorable au client, urgence haute, litige, contenu suspect, réponse non sourcée.
18. À ne pas traiter deux fois le même message (nouvelles tentatives du serveur de messagerie ou du workflow).
19. Les coûts principaux sont la supervision humaine, l'évaluation continue, la maintenance, l'exploitation et les erreurs résiduelles.
20. Depuis le 2 février 2025, à tous les fournisseurs et déployeurs de systèmes d'IA, pour le personnel qui les utilise.
