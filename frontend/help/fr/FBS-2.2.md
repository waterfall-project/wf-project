# Plan de charge agrégé

## Ce que montre l’écran

La charge des projets du périmètre, par rôle de ressource et par mois, face à la capacité de chaque rôle. La charge d’un projet en cours est celle de son reste à engager ; celle d’un projet en chiffrage, quand il est retenu, celle de son devis pondéré par sa probabilité de gain. Sous le titre, le périmètre retenu et la date de calcul.

De haut en bas :

- **Charge empilée par rôle et par mois** : une barre par mois, divisée par rôle, en heures, le total du mois à son sommet, et la capacité du périmètre — la somme des capacités des rôles retenus — en pointillés.
- **Charge par rôle et par mois** : pour chaque rôle, sa capacité mensuelle, puis, mois par mois, sa charge en heures et son taux de charge, rapport de la charge à la capacité, avec le signal de sa zone.

Sans charge sur le périmètre et l’horizon choisis, l’écran le dit.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas.
- **Calculé au**, la date de calcul, puis **Appliquer**. Cette vue ne prend pas de période.
- **Nœud d’organisation et ses descendants** restreint la charge et la capacité aux rôles qui relèvent du nœud.
- **Horizon** : 6, 12 ou 24 mois, ou **Par défaut**, celui du serveur.
- **Seuil de sous-charge** : 30 %, 50 % ou 70 %, ou **Par défaut**, celui que le serveur retient. Un mois dont le taux de charge est sous le seuil est signalé, comme un mois où il dépasse 100 %.

Le graphique :

- **Exporter en PNG** enregistre le graphique en image, avec le périmètre, l’horizon, le nœud et la date de calcul ;
- **Valeurs du graphique** déplie le total de chaque mois, en table.

L’horizon et le seuil vivent dans l’adresse de la vue : ils ne sont pas gardés d’une consultation à l’autre.

## Ses colonnes et ses valeurs calculées

Toute valeur est celle du serveur : la charge d’un rôle est la somme des charges des projets du périmètre, le total d’un mois celle des rôles, la capacité du périmètre celle des rôles retenus. Un taux que le serveur ne peut pas calculer le dit, avec sa raison, et ne vaut jamais zéro. Les zones — surcharge, sous-charge — se lisent par leur signal, jamais par la seule couleur.

## Les gestes au clavier

- `Tab` parcourt les filtres, les commandes du graphique et ses tables ; une table plus large que la fenêtre défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), [la structure des coûts](FBS-2.4.md), qui ventile la main-d’œuvre par nœud ;
- [le plan de charge d’un projet](FBS-4.4.4.md) ;
- la notion : [le reste à engager et le devis actualisé](notions/reste-a-engager.md).
