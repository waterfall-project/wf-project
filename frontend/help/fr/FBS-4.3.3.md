# Gantt

## Ce que montre l’écran

La dernière colonne de la [grille de planning](FBS-4.3.2.md), épinglée à droite : chaque ligne y dessine sa tâche sur l’échelle du temps, alignée sur la grille. Une tâche est une barre — pleine sur le chemin critique, creuse ailleurs —, une récapitulative un crochet, un jalon un losange ; les liaisons joignent les tâches comme leur type le dit. Rien ne s’y lit à la seule couleur : chaque barre est nommée par ses dates, et « critique » quand elle l’est. Les jours chômés du calendrier de la tâche sont hachurés.

Le Gantt se lit, il ne se saisit pas : les dates changent par la grille. Une ligne pliée dans la grille l’est aussi dans le Gantt ; le bouton qui précède le crochet d’une récapitulative la plie ou la déplie.

## Ses commandes

Dans le coin de l’en-tête du Gantt :

- **Zoom avant** (`Ctrl++`) resserre l’échelle, jusqu’aux heures travaillées d’une journée ; indisponible quand le zoom est à son plus fort.
- **Zoom arrière** (`Ctrl+-`) élargit l’échelle ; indisponible quand le zoom est à son plus faible.
- **Ajuster au projet** règle l’échelle pour montrer le projet entier ; indisponible quand elle le montre déjà.
- **Exporter en PNG** enregistre le Gantt en image, sur toute son étendue au niveau de zoom choisi, une ligne par tâche montrée, avec le projet, la révision et la date de calcul. Indisponible quand l’image serait trop grande pour le navigateur : dézoomez, ou pliez des récapitulatives.

Le zoom et l’export se trouvent aussi au menu d’une cellule du Gantt. Sur un Mac, `⌘` tient lieu de `Ctrl`.

## Ses colonnes et ses valeurs calculées

Les dates que le Gantt dessine sont celles que la grille montre, calculées par le serveur pour une tâche en mode automatique.

## Les gestes au clavier

- La poignée sur le bord gauche de la colonne règle sa largeur : à la souris, ou depuis l’en-tête, `Maj` et les flèches, la flèche gauche l’élargissant. La largeur se garde comme celle des autres colonnes.
- `Ctrl++` et `Ctrl+-` zooment depuis la grille.

## Voir aussi

- [La planification](FBS-4.3.md) et [la grille de planning](FBS-4.3.2.md) ;
- [les chronologies](FBS-4.3.1.md), une vue en frise des tâches choisies ;
- la notion : [le chemin critique et la marge](notions/chemin-critique.md).
