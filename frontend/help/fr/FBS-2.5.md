# Risques du portefeuille

## Ce que montre l’écran

Les risques des projets du périmètre et leur couverture. Sous le titre, le périmètre retenu et la date de calcul. De haut en bas :

- **Provisions des risques** : le total des provisions des risques identifiés, puis, sur la période, les provisions des risques survenus et celles des risques écartés.
- **Couverture des risques** : la réserve de référence, face aux provisions restantes et au coût des risques survenus, et l’écart de couverture. Elle ne porte que sur les projets en cours et terminés : un projet en chiffrage n’a pas de référence.
- **Risques les plus lourds** : les risques identifiés, tous projets confondus, classés par montant de provision, chacun avec son projet.
- **Matrice des risques** : un nuage de bulles, la probabilité en abscisse et la gravité, en part du budget de référence, en ordonnée, chaque bulle aussi grande que la gravité en montant ; sous elle, le décompte des risques par case.

Un projet en chiffrage, quand il est retenu, apporte ses risques identifiés et leurs provisions telles qu’elles sont, sans pondération.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas.
- **Du** et **Au**, la période des survenances et des abandons, et **Calculé au**, la date de calcul, puis **Appliquer**. Une période qui finit avant de commencer est refusée à son champ, la vue non lue.

Dans la vue :

- le nom d’un projet, dans les risques les plus lourds, l’ouvre quand vous pouvez le consulter ; une bulle de la matrice ouvre de même le projet de son risque ;
- **Exporter en PNG** enregistre la matrice en image, avec le périmètre et la date de calcul ; **Valeurs du graphique** déplie ses valeurs, en table.

## Ses colonnes et ses valeurs calculées

Toutes les sommes sont calculées par le serveur et marquées Σ. La provision d’un risque est sa gravité pondérée par sa probabilité. Une valeur que le serveur ne peut pas calculer le dit, avec sa raison, et ne vaut jamais zéro. Un risque dont la gravité ne peut pas être rapportée au budget n’est pas tracé dans la matrice, et la matrice dit combien et pourquoi. La zone d’une case se lit par son signal, jamais par la seule couleur.

## Les gestes au clavier

- `Tab` parcourt les filtres, les tables, les liens et les commandes de la matrice ; `Entrée` sur le nom d’un projet l’ouvre.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), [la santé du pilotage](FBS-2.7.md), qui signale les risques non réexaminés ;
- [la gestion des risques d’un projet](FBS-4.6.md) ;
- la notion : [la provision et la réserve](notions/provision-et-reserve.md).
