# Journal d’audit

## Ce que montre l’écran

Le journal d’audit de la plateforme, hors de tout projet : une inscription par action qui engage — le marquage d’une révision, la désignation de la référence, la contractualisation d’un avenant, la survenance d’un risque, la sortie du cycle de vie, l’exclusion ou la réintégration d’une ligne de coût, l’application d’un import, la vie des comptes et des rôles d’habilitation, les sauvegardes et les restaurations. Chacune dit sa date, son auteur, son action et, sous elle, ce qu’elle a fait — les champs modifiés, les rôles ou permissions donnés et retirés, l’ancien libellé —, la nature et le nom de son objet, son projet et la corrélation de la requête qui l’a produite.

Chaque nom est celui du moment de l’action : un compte désactivé depuis garde le sien, un compte anonymisé paraît sous un libellé neutre. Le journal se lit seulement : rien ne modifie ni ne supprime une inscription. Celui d’un projet clos depuis longtemps se lit comme celui d’un projet en cours, par le filtre du projet.

Le serveur trie le journal — par défaut, le plus récent d’abord —, le cherche, le filtre et le pagine ; sous le titre, le nombre d’inscriptions qu’il retient.

## Ses commandes

Le journal n’a pas de commande d’écriture. Pour le lire :

- **Période**, **Depuis le** et **Avant le**, à la minute et à l’heure de ce poste, puis **Appliquer** : le début est compris, la fin exclue. Une fin qui précède le début est refusée à son champ.
- **Filtrer par nature d’auteur** — un compte ou la plateforme — et **Auteur**, un compte précis.
- Les actions, à cocher dans leur menu, une ou plusieurs.
- **Projet** et **Nature de l’objet**.
- **Corrélation** : l’identifiant d’une requête, lettres, chiffres, « . », « _ » et « - », 64 caractères au plus.
- Le champ de recherche retient les inscriptions dont le nom de l’objet contient le texte saisi.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page**, **Page précédente** et **Page suivante** parcourent le journal.

Les auteurs et les projets proposés sont ceux que le journal entier cite, même pour qui ne peut pas lire les comptes. Dans la table :

- L’objet et le projet sont des liens quand vous pouvez les consulter : le projet ; une révision ; un risque, dans les risques de sa révision, son détail ouvert ; un import, dans les imports et exports de sa révision, son compte rendu montré ; le différentiel d’un avenant, dans les structures de coûts de sa révision. Un compte, un rôle, une sauvegarde ou une ligne de coût n’ont pas d’écran à eux : leur nom se lit seul.
- **Histoire de l’objet** filtre le journal sur ce seul objet ; **Lever** ôte ce filtre.
- La corrélation mène aux seules inscriptions de sa requête.

## Ses colonnes et ses valeurs calculées

Rien ne s’y calcule : chaque inscription garde ce qu’elle a inscrit. Ce qu’a fait une action est écrit dans la langue de l’interface à partir de ce que l’inscription garde. Le journal est toujours trié par l’une de ses colonnes : un en-tête passe d’un sens à l’autre sans lever le tri, et celui de la date remet le journal dans son ordre par défaut. L’action et la nature se trient dans l’ordre de leur liste, non dans l’ordre alphabétique de leurs mots.

## Les gestes au clavier

- La table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur un lien — l’objet, le projet, l’histoire, la corrélation — le suit.
- Sur un en-tête, `Entrée` ou `Espace` trie la table par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des utilisateurs](FBS-1.1.md) et [des rôles d’habilitation](FBS-1.2.md), dont le journal inscrit chaque changement ;
- [la sauvegarde et la restauration](FBS-1.4.md) ;
- [la gestion des révisions](FBS-4.1.md), où se marquent les révisions et se désigne la référence ;
- la notion : [les révisions](notions/revisions.md).
