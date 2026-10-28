# Performance du portefeuille

## Ce que montre l’écran

La performance des projets en cours du périmètre, en valeur acquise. Sous le titre, le périmètre retenu et la date de calcul. De haut en bas :

- **Indices agrégés** : l’indice de coût et l’indice de délai du portefeuille, chacun avec sa zone, les écarts de coût et de délai cumulés, et le budget de référence agrégé.
- **Projections à terminaison** : pour chaque hypothèse — **Au budget**, **Du chef de projet**, **Au rythme constaté** —, le montant projeté et son écart au budget. Les deux premières sont les sommes des projections des projets ; la troisième est le budget de référence agrégé divisé par l’indice de coût agrégé, et ne se calcule pas tant que celui-ci ne l’est pas.
- **Répartition des projets par zone** : pour chaque indice et chaque zone, le nombre de projets.
- **Évolution trimestrielle des indices** : les courbes des deux indices agrégés, un point par trimestre, calculés aux dates passées.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas. La performance ne porte que sur les projets en cours.
- **Du** et **Au**, la période, et **Calculé au**, la date de calcul, puis **Appliquer**. Une période qui finit avant de commencer est refusée à son champ, la vue non lue.
- **Nœud d’organisation et ses descendants**.

Le graphique :

- **Exporter en PNG** enregistre l’évolution des indices en image, avec le périmètre et la date de calcul ;
- **Valeurs du graphique** déplie les deux indices de chaque trimestre, en table.

## Ses colonnes et ses valeurs calculées

Un indice du portefeuille est un rapport de sommes — la valeur acquise de tous les projets rapportée à leur coût réel, ou à leur valeur planifiée —, jamais la moyenne des indices des projets. Une valeur que le serveur ne peut pas calculer le dit, avec sa raison, et ne vaut jamais zéro ; dans le graphique, elle laisse un trou dans sa courbe. Les zones se lisent par leur signal, jamais par la seule couleur.

## Les gestes au clavier

- `Tab` parcourt les filtres, les tables et les commandes du graphique.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), qui donne les indices de chaque projet, et [la courbe en S](FBS-2.6.md) ;
- [les indicateurs d’un projet](FBS-4.8.md) ;
- les notions : [les indices](notions/indices.md), [la valeur acquise](notions/valeur-acquise.md), [la valeur planifiée](notions/valeur-planifiee.md), [le budget de référence](notions/budget-de-reference.md).
