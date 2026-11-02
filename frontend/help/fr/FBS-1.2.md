# Gestion des rôles d’habilitation

## Ce que montre l’écran

Les rôles d’habilitation de l’installation, hors de tout projet, et les permissions que chacun donne. Un rôle est prédéfini — livré avec l’installation — ou composé par un administrateur ; un compte porte aucun, un ou plusieurs rôles, et tient ses permissions de leur réunion. Une permission dit ce qu’un compte peut faire, jamais sur quel projet.

De haut en bas : la table des rôles, chacun avec sa nature et le nombre de comptes qui le portent, que le serveur trie, cherche et filtre ; puis la matrice **Permissions par fonction** : une ligne par permission du catalogue, rangée sous le nom de la fonction qu’elle couvre, et une colonne par rôle que la table retient, dans son ordre, chaque case disant si le rôle porte la permission. Aucun écran ne crée une permission : le catalogue est celui de l’installation.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les rôles ; aux autres, l’écran se lit.

- **Nouveau rôle** et **Créer un rôle**, en tête de la table, créent un rôle composé de son seul libellé, sans permission : ses permissions se cochent ensuite dans la matrice. Un libellé laissé vide est refusé à son champ.
- Le libellé d’un rôle se saisit dans sa cellule, qui le renomme.
- **Supprimer**, après confirmation, supprime le rôle ; rien ne le restaure, et un rôle recréé sous le même libellé n’est jamais prédéfini. Indisponible tant qu’un compte porte le rôle : la commande dit combien.
- Dans la matrice, chaque case est une case à cocher : cochée ou décochée, elle enregistre aussitôt les permissions du rôle. Les autres cases du rôle attendent la réponse du serveur ; un refus est dit au-dessus de la matrice, et la case reprend l’état d’avant.

Au-dessus de la table, pour tous :

- **Nature** retient les rôles prédéfinis ou les rôles composés ; **Comptes porteurs**, entre deux bornes, les rôles selon le nombre de leurs porteurs ; pour la création et la dernière modification, une période et un auteur.
- Le champ de recherche retient les rôles dont le libellé contient le texte saisi.
- **Colonnes** choisit les colonnes montrées.

La matrice suit la table : un filtre ou une recherche qui écarte un rôle retire aussi sa colonne.

## Ses colonnes et ses valeurs calculées

Le nombre de comptes porteurs est celui que le serveur compte ; rien ne se calcule ici. Le pied de la table dit combien de rôles elle tient.

## Les gestes au clavier

- La table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` ou `F2` saisit un libellé, `Échap` abandonne la saisie ; `Entrée` sur **Supprimer** presse la commande.
- Sur un en-tête, `Entrée` ou `Espace` trie la table par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Dans la matrice, `Tab` passe d’une case à l’autre, `Espace` coche ou décoche.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des utilisateurs](FBS-1.1.md), où les rôles s’attribuent aux comptes ;
- [le journal d’audit](FBS-1.5.md), qui inscrit chaque création, modification et suppression d’un rôle.
