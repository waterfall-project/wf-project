# Grille de devis

## Ce que montre l’écran

La grille de l’écran du [devis](FBS-4.4.md) : les tâches de la structure lue, dans l’ordre du plan, et sous chacune les lignes de devis qu’elle porte, avant ses sous-tâches. Une ligne de main-d’œuvre porte un rôle de ressource, qui fixe sa catégorie, et une charge en heures ; une autre ligne porte une quantité et un débours unitaire. Une ligne de provision, que le serveur tient d’un risque, ne se saisit pas. Les totaux de la réponse sont en pied.

Sur le différentiel d’un avenant, la colonne « Écart » marque chaque ligne : **+** ajoutée, **-** retirée, **M** modifiée ; la couleur double la marque, et une ligne retirée se lit sans se toucher.

## Ses commandes

Les gestes de structure, dans le menu d’une cellule et à leurs touches, comme au planning : **Insérer au-dessous** (`Inser`), **Insérer une sous-tâche** (`Alt+Inser`), **Indenter** (`Alt+Maj+→`), **Désindenter** (`Alt+Maj+←`), **Monter** (`Alt+Maj+↑`), **Descendre** (`Alt+Maj+↓`), **Supprimer** (`Ctrl+Suppr`) ; et en propre :

- **Insérer une ligne** (`Ctrl+Inser`) crée une ligne de devis sur la tâche active, ou sous la ligne active. Un dialogue demande sa catégorie et sa quantité, et son libellé, facultatif : laissé vide, le serveur le compose du libellé de la tâche et, s’il y en a un, de celui du rôle ; le reste se saisit dans la grille. Elle n’est pas offerte depuis une récapitulative ni depuis un jalon, et une tâche terminée n’en reçoit plus (« tâche non terminée »).
- **Sous-projet** porte la ligne, ou la sélection, à un sous-projet du projet, ou à aucun. Il n’est pas offert sur une ligne de provision, ni sur la ligne d’une tâche démarrée dont le sous-projet a reçu des coûts réels.
- **Le collage** d’un bloc copié d’un tableur (`Ctrl+V`) se fait sur la cellule active. Un aperçu dit combien de lignes seront écrites et lesquelles sont refusées, avec leur motif ; **Appliquer le collage** écrit les lignes valides, **Abandonner** n’écrit rien. Un bloc qui s’étendrait sous une colonne masquée, sur des lignes pliées ou que le tri, la recherche ou un filtre ont déplacées, est refusé d’emblée, la cause dite.

La saisie, le collage et les gestes de ligne demandent « Modifier le devis » ; les gestes de tâche demandent aussi « Modifier le planning ».

## Ses colonnes et ses valeurs calculées

La catégorie d’une ligne de main-d’œuvre est celle de son rôle : elle ne se saisit pas. Une ligne qui emploie une catégorie ou un rôle désactivé le dit dans la colonne « Objet désactivé ». Les montants, calculés, se lisent dans l’aide du [montant à l’année de référence](FBS-4.4.3.md).

## Les gestes au clavier

- La poignée de la ligne, dans la colonne du numéro : `Espace` la sélectionne, `Maj+↑` et `Maj+↓` étendent la sélection, `Échap` la lève ; `Alt+Maj` et une flèche la déplacent, comme le glisser de la poignée à la souris.
- `Maj+F10` ou la touche Menu ouvre le menu de la cellule.
- Les déplacements dans la grille, la saisie et le tri sont décrits dans l’aide du [devis](FBS-4.4.md).
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [Le devis](FBS-4.4.md), l’écran entier, et [ses indicateurs](FBS-4.4.1.md) ;
- [la grille de planning](FBS-4.3.2.md), le même arbre sans les lignes ;
- les notions : [l’avenant et le différentiel](notions/avenant-et-differentiel.md), [la provision et la réserve](notions/provision-et-reserve.md).
