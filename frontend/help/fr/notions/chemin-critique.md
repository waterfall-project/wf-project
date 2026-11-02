# Le chemin critique et la marge totale

## Ce que dit le glossaire

> **Chemin critique** — Désigne l’ensemble des tâches en mode automatique dont la marge totale est nulle ou négative : tout retard sur l’une d’elles retarde la fin du projet, ou une date imposée par une tâche en mode manuel.

> **Marge totale** — Désigne, pour une tâche en mode automatique, l’écart entre sa date au plus tard et sa date au plus tôt : le retard qu’elle peut prendre sans retarder la fin du projet ni une date imposée par une tâche en mode manuel. Elle est négative lorsque la tâche ne peut pas satisfaire une liaison qui la relie à une tâche manuelle.

> **Liaison** — Désigne la relation entre une tâche prédécesseur et une tâche successeur. Elle porte un type — fin à début, début à début, fin à fin, début à fin — et un décalage.

> **Prédécesseur** — Désigne la tâche dont l’exécution conditionne le début ou la fin d’une autre tâche, appelée successeur, au travers d’une liaison.

## Dans Waterfall

Le serveur calcule, pour chaque tâche en mode automatique, ses dates au plus tôt et au plus tard, et la marge qui les sépare ; le front ne calcule rien. Une tâche en mode manuel est une date imposée : elle borne les marges de ses prédécesseurs et de ses successeurs, et n’en porte pas. Un prédécesseur qui ne peut pas satisfaire sa liaison avec une tâche manuelle porte une marge négative, et le conflit est signalé.

Une récapitulative porte la plus petite marge de celles de ses subordonnées qui en portent une, et appartient au chemin critique dès que l’une d’elles y est.

Dans la [grille de planning](../FBS-4.3.2.md), la colonne « Marge » donne la marge totale, en gras sur le chemin critique, et une tâche critique porte l’icône « Chemin critique ». Dans le [Gantt](../FBS-4.3.3.md), sa barre est pleine, creuse ailleurs, et son nom dit « critique » : rien ne se lit à la seule couleur.

## Voir aussi

- [La planification](../FBS-4.3.md), [la grille de planning](../FBS-4.3.2.md), [le Gantt](../FBS-4.3.3.md) ;
- [le lotissement](lotissement.md), dont le squelette pose les premières liaisons.
