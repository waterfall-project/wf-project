# Arbre d’organisation

## Ce que montre l’écran

La première table des [paramètres de ressources](FBS-3.2.md) : les nœuds d’organisation — un service, un département —, en arbre sans limite de profondeur, chacun avec son libellé, en retrait sous son parent, son code, unique, et son niveau, 1 pour une racine. L’arbre se lit entier, dans son ordre, jamais par pages, et ne se trie pas.

Les rôles de ressources se rattachent aux nœuds, et le plan de charge agrégé se filtre par nœud, ses descendants compris. Désactiver un nœud désactive ses descendants et les rôles qui y sont rattachés.

Une recherche ou un filtre retient des nœuds, et l’arbre les montre avec leurs ancêtres.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les paramètres de ressources :

- **Nouveau nœud** ouvre le formulaire : code, unique, libellé, et **Parent** — **Aucun — racine** pour une racine. Un nœud ne prend place que sous un nœud actif.
- **Modifier**, sur une ligne, ouvre le même formulaire sur le nœud. Déplacé sous un autre parent, il emmène ses descendants et ses rôles ; jamais sous lui-même ni sous l’un de ses descendants. Son parent désactivé se garde.
- **Désactiver** et **Réactiver**, dans la colonne **État**, sans confirmation. La réactivation d’un nœud dont le parent est désactivé est indisponible (« nœud parent actif ») : la commande reste présentée et dit la condition qui lui manque.

Au-dessus de l’arbre, pour tous :

- **Code du nœud** retient les nœuds dont le code contient le texte saisi ; **Niveau** retient un niveau ; **Bornes de « Arbre d’organisation »**, un niveau minimal et maximal ;
- un filtre d’état quand les désactivés sont affichés ;
- le champ de recherche retient les nœuds dont le code ou le libellé contient le texte saisi ;
- **Colonnes** ; **Arbre** plie tout, déplie tout, ou plie jusqu’à un niveau ; le bouton d’un libellé plie ou déplie sa ligne.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule. Le pied dit combien de nœuds l’arbre montre, ancêtres des nœuds retenus compris.

## Les gestes au clavier

- L’arbre est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- `Entrée` sur **Modifier**, **Désactiver** ou **Réactiver** presse la commande.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`. Les touches de pliage y vont moins loin : `⌥` et `-`, `⌥` et `+` ne répondent que dans un navigateur qui donne la disposition du clavier, et `⌥` et `*` jamais ; **Arbre** plie et déplie alors.

## Voir aussi

- [Les paramètres de ressources](FBS-3.2.md) et [les rôles de ressources](FBS-3.2.2.md) ;
- [la gestion des utilisateurs](FBS-1.1.md), où chaque compte se rattache à un nœud ;
- [le plan de charge agrégé](FBS-2.2.md), filtré par nœud d’organisation.
