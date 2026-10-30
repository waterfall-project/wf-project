# Gestion des utilisateurs

## Ce que montre l’écran

Les comptes de l’installation, hors de tout projet : chaque compte avec son origine, le nœud d’organisation auquel il est rattaché, ses rôles d’habilitation et son état. Un compte désactivé reste listé et peut être réactivé ; aucun écran ne supprime un compte. Les rôles donnent les permissions, et la permission ne dit que ce qu’un compte peut faire : c’est la liste des contributeurs d’un projet qui dit sur quels projets.

En tête, le compte rendu de la dernière lecture des comptes du fournisseur d’identité qui a abouti, ou l’indication qu’aucune n’a encore abouti : les comptes créés — sans rôle —, mis à jour, désactivés, les identités de comptes locaux rétablies dans le fournisseur, les comptes locaux qui en ont été retirés, et ce qui a été laissé tel quel, avec son motif, sous **Détails de la dernière lecture**.

Sous ce compte rendu, la **Périodicité de la lecture** : la plateforme lit d’elle-même les comptes du fournisseur d’identité, chaque jour par défaut, à l’heure et, pour une lecture hebdomadaire, au jour réglés ; l’écran dit si la lecture planifiée est active ou suspendue, sa fréquence, son jour et son heure en temps universel (UTC).

Puis la table des comptes, que le serveur trie, cherche, filtre et pagine ; son pied dit combien de comptes il retient.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les comptes ; aux autres, l’écran se lit.

- **Lire les comptes** demande une nouvelle lecture des comptes du fournisseur d’identité. Elle se fait en tâche de fond : le panneau des tâches la suit et propose, à sa fin, de relire l’écran, où paraît son compte rendu.
- **Créer un compte local** ouvre le formulaire : nom, prénom et adresse électronique, tous trois requis. Le compte naît sans rôle ni moyen de se connecter : son titulaire reçoit par courriel le lien qui lui fait fixer son mot de passe. Quand aucune invitation n’a pu partir, le formulaire le dit et offre **Remettre le lien**.
- **Modifier la périodicité** ouvre le formulaire de la périodicité de la lecture : actif ou suspendu, quotidienne ou hebdomadaire, le jour pour une lecture hebdomadaire seulement, et l’heure en temps universel (UTC), avec l’heure locale de ce poste qu’elle représente. La périodicité s’enregistre entière ; une lecture en cours n’est pas interrompue, le réglage vaut dès la suivante.
- Dans la table, le nom et le prénom d’un compte créé dans Waterfall se saisissent dans leur cellule ; ceux d’un compte de l’annuaire ou du fournisseur d’identité sont les leurs, et ne se saisissent pas.
- **État** : l’interrupteur active ou désactive le compte. La désactivation est indisponible pour le dernier compte actif qui porte les permissions d’administration (« un autre compte actif portant les permissions d’administration »), et la réactivation d’un compte anonymisé l’est toujours.
- **Rôles d’habilitation** : la liste des rôles de l’installation, à cocher ou décocher, aucun, un ou plusieurs. Le serveur refuse les rôles qui retireraient au dernier administrateur ses permissions.
- **Lien** donne le lien de fixation du mot de passe d’un compte créé dans Waterfall, à remettre par un autre canal : il ne sert qu’une fois, ne sera plus montré, et en demander un autre rend le précédent caduc. Indisponible pour un compte désactivé (« compte actif »).
- **Courriel** fait renvoyer par le fournisseur d’identité, à l’adresse d’un compte créé dans Waterfall, le courriel qui porte le lien de fixation du mot de passe : pour un titulaire qui ne l’a pas reçu, l’a perdu ou l’a laissé expirer. Un lien précédent cesse de valoir, et le renvoi est inscrit au journal d’audit. Indisponible pour un compte désactivé (« compte actif »). Quand le fournisseur ne peut pas l’envoyer — installation sans messagerie, serveur de courriel en échec —, l’écran dit le refus, jamais un courriel parti : **Lien** donne alors le lien à remettre par un autre canal.
- **Anonymiser**, après confirmation, efface le nom, le prénom et l’adresse d’un compte désactivé, de la table comme du journal d’audit ; l’opération est définitive, et le compte ne se réactive plus. Offerte au seul compte désactivé, indisponible une fois le compte anonymisé.

Tant qu’une écriture d’une ligne est en cours, les commandes de cette ligne attendent sa réponse.

Au-dessus de la table, pour tous :

- **Filtrer par origine**, le nœud de rattachement, **Filtrer par rôle** — un compte qui porte l’un des rôles choisis — et **État du compte** ; pour la création et la dernière modification, une période et un auteur. Un auteur se choisit parmi ceux de la page ; **Chercher** en trouve d’autres parmi les comptes.
- Le champ de recherche retient les comptes dont le nom, le prénom ou l’adresse contient le texte saisi.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page**, **Page précédente** et **Page suivante** parcourent la liste.

La recherche et les filtres sont gardés avec les réglages de la grille : revenir à l’écran sans rien demander les retrouve.

## Ses colonnes et ses valeurs calculées

Aucune valeur ne s’y calcule : chaque colonne montre le compte tel que le serveur le tient. Un compte anonymisé n’a plus ni nom ni adresse, et se montre sous un libellé neutre. Dans les colonnes de création et de modification, un auteur désactivé depuis garde son nom, et un traitement automatique est nommé comme tel.

## Les gestes au clavier

- La table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` ou `F2` saisit un nom, `Échap` abandonne la saisie ; `Entrée` sur l’interrupteur, les rôles, le lien, le courriel ou l’anonymisation presse la commande.
- Sur un en-tête, `Entrée` ou `Espace` trie la table par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des rôles d’habilitation](FBS-1.2.md), où se composent les permissions des rôles ;
- [le journal d’audit](FBS-1.5.md), qui inscrit chaque création, modification, désactivation et anonymisation d’un compte ;
- [la surveillance de l’état du système](FBS-1.3.md), qui date la dernière lecture des comptes du fournisseur d’identité.
