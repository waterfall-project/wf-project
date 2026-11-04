# Registre des risques

## Ce que montre l’écran

La grille de l’écran de [gestion des risques](FBS-4.6.md) : une ligne par risque que le filtre par état retient, tels que la révision lue les tient. Le serveur la trie, la cherche et la filtre comme l’adresse le demande ; le pied porte le total général des provisions des risques retenus. Le registre se lit : un risque se déclare, se modifie et se réexamine par les commandes de l’écran et de son détail.

Le libellé d’un risque est un lien vers son détail, qui s’ouvre à côté du registre. L’état d’un risque survenu est un lien vers le devis filtré sur les lignes qui en sont issues, pour qui lit le devis, ou vers le planning filtré sur les tâches et les lignes qui en sont issues, pour qui lit le planning sans lire le devis.

## Ses commandes

- **Rechercher un libellé** retient les risques dont le libellé contient le texte saisi.
- **Filtres des colonnes** déplie, sous les cartes, la barre des filtres qui suivent ; elle est repliée par défaut, et s’ouvre d’elle-même quand un de ces filtres est actif.
- **Filtrer par zone** retient les risques dont la case de la matrice est dans les zones choisies.
- **Bornes de la probabilité** et **Bornes des montants** retiennent, pour chaque colonne de nombres — probabilité, gravité, provision, coût à la survenance, réestimé des survenus —, les risques dont la valeur est entre un minimum et un maximum, inclus ; la probabilité s’y écrit de 0 à 1. Un risque identifié ou écarté, sans coût à la survenance ni réestimé, n’est retenu par aucune borne de ces deux colonnes.
- **Période du dernier réexamen** retient les risques dont le dernier réexamen tombe entre deux jours, fin incluse.
- **Non réexaminés depuis le dernier marquage** fixe la fin de cette période au jour du dernier marquage du projet : la revue périodique présente les risques dont la probabilité n’a pas été réexaminée depuis. Le serveur filtre, et les totaux suivent.
- **Colonnes** choisit les colonnes montrées.
- Un en-tête trie le registre par sa colonne ; le réestimé des survenus et la case de la matrice ne se trient pas.

## Ses colonnes et ses valeurs calculées

La gravité, la provision et le coût à la survenance sont calculés, colonnes entières, et portent Σ en en-tête : une cellule pressée nomme les règles dont sa valeur dépend, telles que le risque les dit. La case de la matrice se lit par son signal et sa zone, jamais par la seule couleur. Un risque survenu ou écarté ne porte plus de ligne de provision : sa provision est celle qu’il portait dans la révision de référence, nulle s’il n’y était pas identifié. Seul un risque survenu porte un coût à la survenance : le total de son devis propre quand il a été déclaré survenu. Le réestimé des survenus, en regard, est la somme des montants réestimés courants des lignes qui en sont issues : il montre la dérive du risque, sans entrer dans l’écart de couverture.

## Les gestes au clavier

- Le registre est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur le libellé d’un risque ouvre son détail ; sur une cellule calculée, l’explication de sa valeur, que `Échap` ferme.
- Sur un en-tête, `Entrée` ou `Espace` trie ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [La gestion des risques](FBS-4.6.md) et [les provisions des risques retenus](FBS-4.6.2.md) ;
- la notion : [la provision et la réserve](notions/provision-et-reserve.md).
