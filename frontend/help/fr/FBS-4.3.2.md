# Grille de planning

## Ce que montre l’écran

La grille de l’écran de [planification](FBS-4.3.md) : une ligne par tâche de la structure lue, dans l’ordre du plan, chaque récapitulative au-dessus de ses subordonnées, la poignée et le numéro de ligne en tête, le Gantt en dernière colonne. Les totaux de la réponse sont en pied. Le planning ne montre aucune ligne de devis : elles se lisent au devis.

Une tâche se saisit au clavier, cellule par cellule, là où la structure lue liste « Modifier le planning » disponible : son libellé, sa description, son mode de planification, sa durée, ses dates quand elles ne sont pas calculées, ses prédécesseurs, son rattachement au lotissement. Une saisie refusée est dite au-dessus de la grille, et sa cellule est marquée.

## Ses commandes

Les gestes de structure, dans le menu d’une cellule et à leurs touches :

- **Insérer au-dessous** (`Inser`) crée une tâche au même niveau, sous la ligne active ; **Insérer une sous-tâche** (`Alt+Inser`) la crée sous la tâche de la ligne. Un jalon n’a pas de sous-tâche. La tâche se nomme dans un dialogue : elle est créée feuille, en mode automatique, d’un jour, sans prédécesseur.
- **Indenter** (`Alt+Maj+→`), **Désindenter** (`Alt+Maj+←`), **Monter** (`Alt+Maj+↑`) et **Descendre** (`Alt+Maj+↓`) déplacent la ligne active, ou la sélection quand la ligne en fait partie ; une récapitulative emporte ses subordonnées. Un déplacement n’est offert que si les lignes déplacées sont des sœurs qui se suivent et que la voisine sur laquelle il repose est montrée : une recherche ou un filtre peuvent le retirer. On n’indente pas sous un jalon.
- **Supprimer** (`Ctrl+Suppr`) supprime la ligne active ; une récapitulative, après confirmation, avec ses subordonnées, leurs lignes et leurs liaisons.
- **Chronologies** coche les chronologies auxquelles la tâche est inscrite ; **Suivi temps/temps** inscrit un jalon au suivi des jalons contractuels. **Créer une chronologie…** en crée une, quand le projet n’en a pas.

Les gestes et la saisie ne sont offerts que là où la structure lue liste « Modifier le planning » disponible. Une écriture en cours retient les gestes suivants jusqu’à la relecture de la grille, qui se dit occupée.

## Ses colonnes et ses valeurs calculées

La durée se tape avec son unité : « 2 j », « 1 sem », « 1 m » pour un mois, « 30 min », « 4 h » ; un nombre seul est un nombre de jours. Une date se tape dans sa forme courte, ou sous la forme 2026-05-31 ; le serveur complète les heures selon le calendrier.

Les prédécesseurs se saisissent comme dans MS Project, séparés par des points-virgules : le numéro de ligne, le type de la liaison — FD (fin à début, que l’on peut omettre), DD, FF, DF —, puis le décalage, positif ou négatif, avec son unité ou en pourcentage : « 3FD+2 j ; 5DD ». Un numéro que la grille ne connaît pas laisse la saisie ouverte ; une boucle de liaisons est refusée, avec les tâches qu’elle traverse.

Le mode et l’avancement se lisent par une icône nommée ; une tâche du [chemin critique](notions/chemin-critique.md) porte l’icône « Chemin critique », et sa marge est en gras. L’avancement physique d’une récapitulative est calculé, ou dit non calculable avec son motif.

## Les gestes au clavier

- La cellule du numéro est la poignée de la ligne : `Espace` la sélectionne, `Maj+↑` et `Maj+↓` étendent la sélection, `Échap` la lève. À la souris, un clic sélectionne une ligne, `Maj` et un clic étendent la sélection, et la poignée glisse la sélection avant, après ou sous une autre ligne.
- `Alt+Maj` et une flèche déplacent la sélection, comme le glisser de la poignée.
- `Maj+F10` ou la touche Menu ouvre le menu de la cellule.
- Les déplacements dans la grille et la saisie sont décrits dans l’aide de la [planification](FBS-4.3.md).

## Voir aussi

- [La planification](FBS-4.3.md), l’écran entier, et [le Gantt](FBS-4.3.3.md) ;
- [la grille de devis](FBS-4.4.2.md), le même arbre avec ses lignes ;
- les notions : [le chemin critique et la marge](notions/chemin-critique.md), [le lotissement](notions/lotissement.md).
