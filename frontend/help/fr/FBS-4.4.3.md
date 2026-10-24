# Montant à l’année de référence

## Ce que montre l’écran

La colonne « Montant (année de réf.) » de la [grille de devis](FBS-4.4.2.md) : le montant de chaque ligne, de chaque tâche — récapitulative comprise — et du total, chiffré aux taux horaires de l’année de référence de la révision, sans inflation. À côté d’elle, « Montant corrigé de l’inflation » projette ce même montant sur l’année de consommation de la ligne, que le planning donne, au taux d’inflation du projet.

L’année de référence est celle dont les taux horaires chiffrent la révision : retenue à sa création, elle ne change plus. Les années suivantes sont projetées par le taux d’inflation du projet, réglé dans ses paramètres.

Le devis ne montre ni le montant budgété ni le montant réestimé : le premier se lit au [reste à engager](FBS-4.5.md) et fonde le [budget de référence](notions/budget-de-reference.md) ; le second est la réestimation des revues.

## Ses commandes

La colonne ne se saisit pas, et n’a pas de commande propre. Un en-tête trie les lignes sous chaque tâche par leur montant.

## Ses colonnes et ses valeurs calculées

Le montant d’une ligne de main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour l’année de référence ; celui d’une ligne hors main-d’œuvre, le produit de sa quantité et de son débours unitaire ; celui d’une tâche, la somme des lignes qu’elle porte et de ses subordonnées. Une catégorie sans taux horaire pour l’année de référence empêche le calcul : l’écran du devis le dit au-dessus de la grille.

## Les gestes au clavier

- Sur la cellule, `Entrée` ou `F2` ouvre l’explication : de quoi la valeur dépend, et les lignes dont elle vient ; `Échap` la ferme.
- Sur l’en-tête, le survol ou le focus ouvre l’infobulle qui définit la colonne.

## Voir aussi

- [La grille de devis](FBS-4.4.2.md) et [les indicateurs du devis](FBS-4.4.1.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [les révisions](notions/revisions.md).
