# Paramètres de coûts

## Ce que montre l’écran

Les paramètres de coûts de l’installation, hors de tout projet, que chaque projet emploie. Sous le titre, la devise unique de l’installation, dans laquelle s’expriment tous les montants : elle se choisit à l’installation, ne se modifie pas, et Waterfall ne convertit aucun montant. Puis le nom de l’entreprise, que portent les fichiers exportés.

De haut en bas, chaque partie sous son titre :

- [les natures et les catégories de coûts](FBS-3.1.1.md) : deux tables, les **Natures de coût** puis les **Catégories de coût** ;
- les [taux horaires](FBS-3.1.2.md) : une ligne par catégorie de main-d’œuvre, une colonne par année.

Chaque table est triée, cherchée, filtrée et paginée par le serveur, et tient sa propre hauteur. Les listes ne montrent que les objets actifs, à moins de demander aussi les désactivés : rien ne se supprime dans le référentiel, un objet se désactive et peut être réactivé. Un objet désactivé n’est plus proposé à la saisie, et reste lisible partout où il est employé.

## Ses commandes

En tête de l’écran :

- **Afficher aussi les désactivés** ajoute aux trois tables les objets désactivés, et leur ajoute un filtre d’état ; **Masquer les désactivés** y revient. Offerte à qui peut lire les paramètres de coûts.
- **Correspondance des coûts réels** mène à la [correspondance de l’extraction des coûts réels](FBS-3.1.3.md).
- **Modifier le nom de l’entreprise** ouvre son formulaire : le nom est obligatoire, de 200 caractères au plus.

Les commandes qui écrivent — le nom de l’entreprise, la création, la modification, la désactivation et la réactivation d’une nature ou d’une catégorie, la saisie d’un taux, l’ajout d’une année — ne sont offertes qu’à qui peut modifier les paramètres de coûts ; aux autres, l’écran se lit. Leur détail est dans l’aide de chaque partie.

Une modification du référentiel ne touche aucune révision marquée, qui garde les valeurs employées à son marquage.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule ici : chaque table montre les objets tels que le serveur les tient, et son pied dit combien elle en retient. Les définitions des colonnes des trois tables suivent.

## Les gestes au clavier

- Chaque table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur une commande d’une cellule — **Modifier**, **Désactiver**, **Réactiver** — la presse ; `Entrée` ou `F2` saisit un taux, `Échap` abandonne la saisie.
- Sur un en-tête, `Entrée` ou `Espace` trie la table par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Les natures et les catégories de coûts](FBS-3.1.1.md), [les taux horaires](FBS-3.1.2.md), [la correspondance de l’extraction des coûts réels](FBS-3.1.3.md) ;
- [les paramètres de ressources](FBS-3.2.md), où chaque rôle de ressource se rattache à une catégorie de main-d’œuvre ;
- [la structure des coûts du portefeuille](FBS-2.4.md), qui ventile les montants par nature de coût.
