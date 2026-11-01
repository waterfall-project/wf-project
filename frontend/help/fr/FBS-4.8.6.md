# Suivi des jalons

## Ce que montre l’écran

Le **Diagramme temps/temps**, sous les cartes des [indicateurs projets](FBS-4.8.md) : comment les dates prévues des jalons ont glissé d’une revue à l’autre. Chaque révision marquée est un point sur l’axe horizontal, à sa date de marquage ; la date qu’elle prévoyait pour chaque jalon, un point sur l’axe vertical. Le dernier point est celui du jour courant.

- Un jalon dont la date ne bouge pas trace une horizontale ; un jalon qui glisse monte, et la pente de sa courbe est la vitesse de son glissement.
- Terminé, sa courbe s’arrête par un point à sa date de terminaison, sur la diagonale des **Dates égales**, et aucune révision marquée ensuite n’y ajoute de point.
- Les révisions marquées avant l’état En cours ne donnent aucun point.

Seuls les jalons inscrits au suivi temps/temps y figurent : un jalon s’y inscrit depuis la [grille de planning](FBS-4.3.2.md), par **Suivi temps/temps** dans le menu de sa cellule. Sans jalon inscrit, l’écran dit « Aucun jalon n’est inscrit au suivi. »

Le suivi porte sur le projet entier, quel que soit son état : un sous-projet n’a pas de jalons. Quand le bandeau filtre un sous-projet, la section le dit.

## Ses commandes

- **Exporter en PNG** enregistre le diagramme en image, avec le projet, la révision et la date de calcul.
- **Valeurs du graphique** déplie ses points en table.

## Ses colonnes et ses valeurs calculées

Toutes les dates sont celles du serveur. La table des valeurs donne, pour chaque point, le **Jalon**, la **Révision du** — sa date de marquage —, la **Date prévue** et la date où le jalon a été **Terminé le**, ou **Non terminé**.

## Les gestes au clavier

- `Tab` atteint **Exporter en PNG** et **Valeurs du graphique** ; la table, plus large que la fenêtre, défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md), [l’indicateur de délais](FBS-4.8.5.md) ;
- [la grille de planning](FBS-4.3.2.md), où les jalons s’inscrivent au suivi, et [la santé du pilotage](FBS-2.7.md), qui signale un jalon contractuel dépassé ;
- la notion : [les révisions](notions/revisions.md).
