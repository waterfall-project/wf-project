# Registre des risques

## Ce que montre l’écran

La grille de l’écran de [gestion des risques](FBS-4.6.md) : une ligne par risque que le filtre par état retient, tels que la révision lue les tient. Le serveur la trie, la cherche et la filtre comme l’adresse le demande ; le pied porte le total général des provisions des risques retenus. Le registre se lit : un risque se déclare, se modifie et se réexamine par les commandes de l’écran et de son détail.

Le libellé d’un risque est un lien vers son détail, qui s’ouvre à côté du registre.

## Ses commandes

- **Rechercher un libellé** retient les risques dont le libellé contient le texte saisi.
- **Colonnes** choisit les colonnes montrées.
- Un en-tête trie le registre par sa colonne ; le coût à la survenance et la case de la matrice ne se trient pas.

## Ses colonnes et ses valeurs calculées

La gravité, la provision et le coût à la survenance sont calculés, colonnes entières, et portent Σ en en-tête : une cellule pressée nomme les règles dont sa valeur dépend, telles que le risque les dit. La case de la matrice se lit par son signal et sa zone, jamais par la seule couleur. Un risque survenu ou écarté ne porte plus de ligne de provision : sa provision est celle qu’il portait dans la révision de référence, nulle s’il n’y était pas identifié. Seul un risque survenu porte un coût à la survenance : le total de son devis propre quand il a été déclaré survenu.

## Les gestes au clavier

- Le registre est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur le libellé d’un risque ouvre son détail ; sur une cellule calculée, l’explication de sa valeur, que `Échap` ferme.
- Sur un en-tête, `Entrée` ou `Espace` trie ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [La gestion des risques](FBS-4.6.md) et [les provisions des risques retenus](FBS-4.6.2.md) ;
- la notion : [la provision et la réserve](notions/provision-et-reserve.md).
