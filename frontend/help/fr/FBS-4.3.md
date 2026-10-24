# Planification

## Ce que montre l’écran

Le planning d’une révision : l’arbre des tâches de la structure lue, avec leurs durées, leurs dates et leurs liaisons, et le Gantt dans la dernière colonne de la grille, ligne pour ligne. C’est la vue de la structure de coûts du côté du temps ; le devis en est la vue du côté de l’argent, sur le même arbre.

Le bandeau du haut dit le contexte de lecture : le projet, la révision lue, la structure lue — la structure principale par défaut, un différentiel d’avenant ou le devis propre d’un risque — et les filtres actifs. Il offre de changer de structure. Sur une révision marquée, il dit que rien ne se saisit : une [révision marquée](notions/revisions.md) est figée.

Les dates des tâches en mode automatique sont calculées par le serveur, d’après leur durée, leurs liaisons et leur calendrier : l’écran les montre telles qu’il les rend, et ne date rien lui-même. Le planning est la source des années de consommation du devis et de la [valeur planifiée](notions/valeur-planifiee.md) quand la révision devient la référence.

## Ses commandes

En tête de l’écran :

- **Chronologies**, **Imports et exports**, **Arborescence de tâches** mènent aux écrans voisins du planning, dans le même contexte.
- **Contractualiser l’avenant**, sur le différentiel d’un avenant seulement : lit le compte rendu de la fusion — tâches, lignes et liaisons ajoutées, modifiées, retirées, tâches démarrées qui seront terminées, motifs qui la refusent —, demande le nom de version de la révision produite, puis confie la fusion au traitement de fond. Indisponible tant que la révision n’a aucun avenant à fusionner (« un avenant non fusionné ») ; refusée par les motifs que le compte rendu nomme.

Au-dessus de la grille :

- **Lot ou poste** filtre la grille sur la tâche qui porte un lot ou un poste du lotissement, avec ses subordonnées et ses ancêtres. Le bandeau montre le filtre et permet de le lever.
- **Rechercher un libellé** retient les tâches dont le libellé contient le texte saisi.
- **Colonnes** choisit les colonnes montrées ; **Arbre** plie tout, déplie tout, ou plie jusqu’à un niveau.
- **Annuler** (`Ctrl+Z`) et **Rétablir** (`Ctrl+Maj+Z`), là où la structure se saisit. Elles restent indisponibles tant que le serveur ne conserve pas l’historique des saisies.
- **Insérer une tâche**, dans une grille vide, crée sa première tâche.
- **Engendrer le planning**, dans la grille vide de la structure principale : engendre le squelette depuis le lotissement — une récapitulative par lot et par poste, une tâche par livrable et leurs jalons de fin. Indisponible dès que la structure comporte une tâche.

Dans le menu d’une cellule (clic droit, `Maj+F10` ou la touche Menu) : **Insérer au-dessous**, **Insérer une sous-tâche**, **Indenter**, **Désindenter**, **Monter**, **Descendre**, **Supprimer**, le pliage de la ligne, **Annuler** et **Rétablir**, et deux sous-menus : **Chronologies**, pour inscrire la tâche — ou la sélection — à une chronologie, et **Suivi temps/temps** pour un jalon. Le détail de ces gestes et de leurs touches est dans l’aide de la [grille de planning](FBS-4.3.2.md) ; le zoom et l’export du Gantt dans celle du [Gantt](FBS-4.3.3.md).

La grille ne se saisit, et n’offre ses gestes, que là où la structure lue liste « Modifier le planning » disponible pour vous : une révision marquée, un projet clos ou un traitement de fond en cours la laissent en lecture seule. Une cellule calculée ne se saisit jamais : elle dit de quoi sa valeur dépend.

## Ses colonnes et ses valeurs calculées

Une colonne dont l’en-tête porte Σ est calculée par le serveur ; une cellule calculée est grisée et marquée Σ. Les dates d’une tâche en mode automatique, la durée et l’avancement d’une récapitulative, la marge totale sont calculés. La colonne « Chronologies » est masquée tant que vous ne l’affichez pas par **Colonnes**.

## Les gestes au clavier

- La grille est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` ou `F2` saisit une cellule ; un caractère tapé commence la saisie ; `Échap` l’abandonne. Validée, la saisie passe à la cellule suivante : `Tab` le long de la ligne, `Entrée` à la ligne du dessous.
- Le planning garde l’ordre du plan : aucune colonne ne se trie. Sur un en-tête, `Maj` et les flèches élargissent ou rétrécissent la colonne.
- `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- `F1` ouvre cette aide.

## Voir aussi

- [La grille de planning](FBS-4.3.2.md) et [le Gantt](FBS-4.3.3.md), les deux parties de l’écran ;
- [les chronologies](FBS-4.3.1.md), [les imports et exports](FBS-4.3.4.md), [l’arborescence de tâches](FBS-4.3.5.md) ;
- [le devis](FBS-4.4.md), la même structure du côté de l’argent ;
- les notions : [les révisions](notions/revisions.md), [le chemin critique et la marge](notions/chemin-critique.md), [le lotissement](notions/lotissement.md), [l’avenant et le différentiel](notions/avenant-et-differentiel.md).
