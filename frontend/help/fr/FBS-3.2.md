# Paramètres de ressources

## Ce que montre l’écran

Les paramètres de ressources de l’installation, hors de tout projet. Trois paramétrages qui se complètent, puis les unités de durée, de haut en bas :

- l’[arbre d’organisation](FBS-3.2.1.md) : les services de l’entreprise, en arbre sans limite de profondeur ;
- les [rôles de ressources](FBS-3.2.2.md) : chacun rattaché à un nœud, à une catégorie de main-d’œuvre et à un calendrier, avec sa capacité ;
- les [calendriers](FBS-3.2.3.md) : les heures travaillées de chaque jour de la semaine, dont un par défaut ;
- les **Unités de durée** : les heures par jour, les heures par semaine et les jours par mois, par lesquels une durée saisie en jours, en semaines ou en mois se convertit en heures.

Chaque table est cherchée et filtrée par le serveur, et tient sa propre hauteur ; les rôles et les calendriers sont aussi triés et paginés par lui. Les listes ne montrent que les objets actifs, à moins de demander aussi les désactivés : rien ne se supprime dans le référentiel, un objet se désactive et peut être réactivé. Chaque objet nomme ceux auxquels il est rattaché, actifs ou non.

## Ses commandes

En tête de l’écran, **Afficher aussi les désactivés** ajoute aux trois tables les objets désactivés, et leur ajoute un filtre d’état ; **Masquer les désactivés** y revient. Offerte à qui peut lire les paramètres de ressources.

Les commandes qui écrivent ne sont offertes qu’à qui peut modifier les paramètres de ressources ; aux autres, l’écran se lit :

- la création, la modification, la désactivation et la réactivation d’un nœud, d’un rôle ou d’un calendrier, et la désignation du calendrier par défaut, détaillées dans l’aide de chaque table ;
- **Modifier les unités de durée** ouvre leur formulaire : chacune strictement positive. Le changement vaut pour tous les projets : les plannings des révisions en cours sont recalculés, une révision marquée garde les heures qu’elle a calculées.

Une modification du référentiel ne touche aucune révision marquée, qui garde les valeurs employées à son marquage.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule ici : chaque table montre les objets tels que le serveur les tient, et son pied dit combien elle en retient. Les définitions des colonnes des trois tables suivent.

## Les gestes au clavier

- Chaque table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur une commande d’une cellule — **Modifier**, **Désactiver**, **Réactiver**, **Désigner** — la presse.
- Sur un en-tête, `Entrée` ou `Espace` trie la table par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Dans l’arbre d’organisation, `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [L’arbre d’organisation](FBS-3.2.1.md), [les rôles de ressources](FBS-3.2.2.md), [les calendriers](FBS-3.2.3.md) ;
- [les paramètres de coûts](FBS-3.1.md), où se tiennent les catégories de main-d’œuvre et leurs taux ;
- [le plan de charge agrégé](FBS-2.2.md), qui compare la charge à la capacité des rôles.
