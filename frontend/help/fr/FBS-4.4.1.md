# Indicateurs du devis

## Ce que montre l’écran

Les cartes au-dessus de la grille de [devis](FBS-4.4.md), telles que le serveur les calcule pour la révision lue, et pour le sous-projet quand le bandeau en filtre un ; un filtre par lot ou par poste ne restreint que la grille. Chaque carte porte sa date de calcul. Le front n’y calcule rien : un montant qu’il ne peut pas lire n’est pas montré.

- **Total du devis** : son total général, lignes de provision comprises.
- **Provisions identifiées** : ce que portent les lignes de provision des risques identifiés.
- **Écart avec la référence** : l’écart entre le total du devis de la révision lue et celui de la [révision de référence](notions/revisions.md), lignes de provision comprises de part et d’autre, quand le projet en a une.
- **Écart avec la révision marquée précédente**, quand il y en a une.
- **Par nature de coût**, en montant et en part du total ; **Par sous-projet** ; **Par lot** : le total du sous-arbre de la tâche qui porte chaque lot du lotissement, un lot sans tâche rattachée étant présenté sans total. Une part qui ne peut pas être calculée le dit, avec son motif.

Quand des catégories de coût de main-d’œuvre n’ont pas de taux horaire pour l’année de référence de la révision, l’avis « Taux horaires manquants » les nomme avec l’année : le devis ne peut pas être calculé avant qu’elles en aient un, et ses indicateurs sont dits indisponibles.

## Ses commandes

- **Renseigner les taux horaires** mène au référentiel des coûts, pour qui peut le modifier ; **Voir les taux horaires**, pour qui ne peut que le lire.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs des cartes sont calculées par le serveur, inflation comprise, à l’année de consommation des lignes.

## Les gestes au clavier

Les cartes se lisent dans l’ordre de la page ; `Tab` atteint les liens de l’avis des taux manquants.

## Voir aussi

- [Le devis](FBS-4.4.md) et [la grille de devis](FBS-4.4.2.md) ;
- [les indicateurs du reste à engager](FBS-4.5.1.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [la provision et la réserve](notions/provision-et-reserve.md).
