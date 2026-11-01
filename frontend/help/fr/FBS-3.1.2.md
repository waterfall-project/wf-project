# Taux horaires

## Ce que montre l’écran

La grille des taux horaires des [paramètres de coûts](FBS-3.1.md) : une ligne par catégorie de coût de main-d’œuvre, avec son code, son libellé et son état, et une colonne par année, chaque cellule le taux horaire de la catégorie pour cette année, dans la devise de l’installation. Une année sans taux est une cellule vide. Les catégories des autres natures ne portent pas de taux.

Le pied de la grille dit combien de catégories elle retient et la devise des taux, jamais une somme. La grille est triée, cherchée et paginée par le serveur ; les années sont celles de toute la grille, sur chaque page.

Un taux sert au chiffrage des lignes de main-d’œuvre des projets. Sa modification ne touche aucune révision marquée : une révision en cours la reprend par **Appliquer la mise à jour des taux**, sur l’écran des [révisions](FBS-4.1.md).

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les paramètres de coûts :

- Une cellule se saisit : la saisie enregistre le taux de cette catégorie pour cette année, seul. Un taux ne se vide pas.
- **Ajouter une année à la grille** : l’**Année**, puis **Ajouter la colonne**. Aucune colonne ne se crée d’elle-même : la colonne ajoutée est vide, les taux des autres années inchangés, et elle n’entre dans la grille du serveur qu’avec son premier taux saisi. Une année que la grille a déjà, ou hors de 2000 à 2100, est refusée.
- **Retirer la colonne**, pour une année ajoutée dont aucun taux n’est encore saisi.

Au-dessus de la grille, pour tous :

- un filtre d’état des catégories, quand les désactivées sont affichées ; elles se réactivent dans la liste des [catégories](FBS-3.1.1.md) ;
- **Bornes de « Grille des taux horaires »** : l’**Année du taux**, la dernière par défaut, et les bornes du **Taux horaire** de cette année. Une borne supérieure sous la borne inférieure est refusée à son champ, et la grille n’est pas lue ;
- le champ de recherche retient les catégories dont le code ou le libellé contient le texte saisi ;
- **Colonnes**, **Lignes par page**, **Page précédente** et **Page suivante**.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque taux est celui que le serveur tient, et le taux qu’il répond à une saisie prend la place de la cellule. Chaque colonne se trie, celle d’une année par son taux ; une catégorie sans taux pour l’année garde l’ordre du code.

## Les gestes au clavier

- La grille est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` ou `F2` saisit un taux, un caractère tapé commence la saisie, `Échap` l’abandonne ; `Tab` valide et passe à la cellule suivante, `Entrée` à la ligne du dessous.
- Sur un en-tête, `Entrée` ou `Espace` trie la grille ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [Les paramètres de coûts](FBS-3.1.md) et [les natures et les catégories de coûts](FBS-3.1.1.md) ;
- [les rôles de ressources](FBS-3.2.2.md), dont la catégorie donne le taux de leurs heures ;
- [la gestion des révisions](FBS-4.1.md), où une révision en cours applique la mise à jour des taux.
