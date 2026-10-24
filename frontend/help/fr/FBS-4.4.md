# Chiffrage et devis

## Ce que montre l’écran

Le devis d’une révision : les tâches de la structure lue et les lignes de devis qu’elles portent, chacune rattachée à une catégorie de coût. C’est la vue de la structure de coûts du côté de l’argent ; le planning en est la vue du côté du temps, sur le même arbre.

Au-dessus de la grille, les [indicateurs du devis](FBS-4.4.1.md) — son total, ses provisions, ses écarts, ses ventilations —, avec leur date de calcul ; et, quand il en manque, les taux horaires dont le calcul a besoin. Le bandeau dit le contexte de lecture et la structure lue — la structure principale, un différentiel d’avenant ou le devis propre d’un risque —, et offre d’en changer.

Le devis se saisit tant que le projet est en chiffrage : sur la structure principale d’un projet En cours, il se lit seulement, et la dépense restante se réestime au [reste à engager](FBS-4.5.md). Le différentiel d’un avenant et le devis propre d’un risque se saisissent encore. Une ligne chiffre à l’année de référence de la révision ; le serveur la projette sur son année de consommation, que le planning donne, au taux d’inflation du projet.

## Ses commandes

En tête de l’écran :

- **Plan de charge** mène à la répartition mensuelle des charges de la révision, par rôle ;
- **Imports et exports** mène à l’écran où un devis s’importe d’un fichier, quand le projet offre cet import.

Au-dessus de la grille :

- **Lot ou poste** filtre la grille sur un lot ou un poste du lotissement ; les indicateurs restent ceux du projet, ou du sous-projet filtré.
- **Rechercher un libellé**, **Colonnes**, **Arbre** ;
- **Annuler** (`Ctrl+Z`) et **Rétablir** (`Ctrl+Maj+Z`), là où la structure se saisit. Elles restent indisponibles tant que le serveur ne conserve pas l’historique des saisies.
- **Renseigner les taux horaires**, dans l’avis des taux manquants, mène au référentiel des coûts pour qui peut le modifier ; **Voir les taux horaires** pour qui le lit.

Dans le menu d’une cellule (clic droit, `Maj+F10` ou la touche Menu) : les gestes de structure — dont **Insérer une ligne** (`Ctrl+Inser`) —, le pliage, **Annuler** et **Rétablir**, et le sous-menu **Sous-projet**, qui porte la ligne, ou la sélection, à un sous-projet. Leur détail est dans l’aide de la [grille de devis](FBS-4.4.2.md).

La grille ne se saisit, et ne prend un collage, que là où la structure lue liste « Modifier le devis » disponible pour vous. Créer, déplacer ou supprimer une tâche écrit aussi le planning : ces gestes demandent en outre « Modifier le planning ».

## Ses colonnes et ses valeurs calculées

Les montants sont calculés par le serveur, jamais saisis : une ligne de main-d’œuvre vaut sa quantité, sa charge et le taux horaire de sa catégorie pour l’année de référence ; une ligne hors main-d’œuvre, sa quantité et son débours unitaire ; une tâche, ses lignes et ses subordonnées. Une cellule calculée, grisée et marquée Σ, dit de quoi sa valeur dépend quand on tente de la saisir. Le sous-projet d’une ligne de provision vient de son risque : il est calculé.

L’en-tête du montant corrigé de l’inflation nomme, dans son infobulle, l’année de référence de la révision et le taux d’inflation du projet. La colonne « Sous-projet » est masquée tant que vous ne l’affichez pas par **Colonnes**.

## Les gestes au clavier

- La grille est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` ou `F2` saisit une cellule, un caractère tapé commence la saisie, `Échap` l’abandonne ; `Tab` valide et passe à la cellule suivante, `Entrée` à la ligne du dessous.
- Sur un en-tête, `Entrée` ou `Espace` trie les lignes sous chaque tâche par la colonne, les tâches gardant l’ordre du plan ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- `Ctrl+V` colle un bloc copié d’un tableur sur la cellule active, après un aperçu.
- `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs du devis](FBS-4.4.1.md), [la grille de devis](FBS-4.4.2.md), [le montant à l’année de référence](FBS-4.4.3.md) ;
- [le plan de charge](FBS-4.4.4.md), [la planification](FBS-4.3.md), [le reste à engager](FBS-4.5.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [les révisions](notions/revisions.md), [la provision et la réserve](notions/provision-et-reserve.md), [le reste à engager et le devis actualisé](notions/reste-a-engager.md).
