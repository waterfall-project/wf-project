# Natures et catégories de coûts

## Ce que montre l’écran

Deux tables des [paramètres de coûts](FBS-3.1.md), l’une sous l’autre :

- les **Natures de coût** : chacune avec son code, unique, son libellé et son type — main-d’œuvre, hors main-d’œuvre ou provision pour risques ;
- les **Catégories de coût** : chacune avec son code, son libellé, sa nature et son code comptable, unique et documentaire.

Une catégorie se rattache à une nature, dont elle prend le type : seules les catégories de main-d’œuvre portent des [taux horaires](FBS-3.1.2.md) et se rattachent aux rôles de ressources ; une ligne de provision d’un risque porte une catégorie d’une nature de provision pour risques. Désactiver une nature désactive ses catégories.

Une liste vide le dit ; une recherche ou un filtre qui ne retient rien garde la table, pour être changé.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les paramètres de coûts :

- **Nouvelle nature** ouvre le formulaire de la nature : code, unique, libellé et type, tous requis.
- **Nouvelle catégorie** ouvre celui de la catégorie : code et code comptable, uniques l’un et l’autre, libellé et nature, tous requis.
- **Modifier**, sur une ligne, ouvre le même formulaire sur l’objet. Le type d’une nature ne se modifie plus dès qu’une de ses catégories est employée par une ligne de devis ou de reste à engager, porte un taux horaire ou est rattachée à un rôle de ressource ; le formulaire dit laquelle de ces conditions manque. Une catégorie ne se rattache alors qu’à une nature du même type.
- **Désactiver** et **Réactiver**, dans la colonne **État**, changent l’état de l’objet, sans confirmation. La réactivation d’une catégorie dont la nature est désactivée est indisponible (« nature de coût active ») : la commande reste présentée et dit la condition qui lui manque.

Un code ou un libellé déjà porté est refusé à son champ, qui nomme l’objet qui le porte. Ce que fait une écriture est dit au-dessus de la table ; un refus qui nomme un objet à réactiver d’abord le dit aussi.

Au-dessus de chaque table, pour tous :

- **Types de nature** retient les natures des types choisis ; **Nature** retient les catégories d’une nature ;
- un filtre d’état — **Tous les états**, **Actifs**, **Désactivés** — quand les désactivés sont affichés ;
- le champ de recherche retient les objets dont le code ou le libellé contient le texte saisi, et, pour les catégories, le code comptable ;
- **Colonnes**, **Lignes par page**, **Page précédente** et **Page suivante**.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque objet est celui que tient le serveur, la nature d’une catégorie nommée comme il la résout, active ou non. Le pied de chaque table dit combien d’objets elle retient.

## Les gestes au clavier

- Chaque table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur **Modifier**, **Désactiver** ou **Réactiver** presse la commande ; un formulaire fermé rend le focus à la cellule d’où il a été ouvert.
- Sur un en-tête, `Entrée` ou `Espace` trie la table ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [Les paramètres de coûts](FBS-3.1.md) et [les taux horaires](FBS-3.1.2.md) ;
- [les rôles de ressources](FBS-3.2.2.md), rattachés à une catégorie de main-d’œuvre ;
- la notion : [la provision et la réserve](notions/provision-et-reserve.md).
