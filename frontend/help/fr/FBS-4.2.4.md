# Contributeurs

## Ce que montre l’écran

Une liste des [paramètres du projet](FBS-4.2.md) : qui participe à cette affaire, chacun avec sa qualité — **Chef de projet** ou **Contributeur** — et l’état de son compte. Une affaire multi-métiers ne relève d’aucun service : le chef de projet la structure, les managers des métiers en chiffrent la charge. La liste change à chaque affaire, contrairement à l’arbre d’organisation.

Elle ne remplace pas les habilitations : un rôle d’habilitation dit ce qu’un utilisateur a le droit de faire, la liste dit sur quels projets il le fait. La consultation et la saisie d’un projet sont réservées à ses contributeurs, chacune sous sa permission, et son paramétrage à ses chefs de projet ; la permission de consulter tous les projets ouvre les autres à la lecture. Le créateur d’un projet en est le premier chef de projet, et un projet non terminal en garde toujours au moins un.

## Ses commandes

- **Modifier les contributeurs**, offerte aux chefs de projet tant que le projet n’est pas terminal, ouvre la liste dans un dialogue. On y change la qualité d’un contributeur, on le retire (**Retirer**), et l’on inscrit, un par un (**Inscrire**), les **Contributeurs proposés** : les comptes des services dont les rôles de ressources sont employés par les lignes du devis, chacun avec son nœud d’organisation et les rôles qui le proposent. Rien de proposé n’est appliqué sans vous ; rien n’est écrit avant **Enregistrer**, qui écrit la liste entière. Sous la commande, une phrase nomme les comptes proposés qui attendent votre confirmation.
- Une liste sans chef de projet est refusée avant tout envoi. Un compte que l’installation n’a pas, ou désactivé, est refusé à sa ligne, nommé ; si la liste a changé depuis sa lecture, le refus offre de relire la page.

Au-dessus de la liste, pour tous : **Filtrer par qualité** et **État du compte** — **Comptes actifs** ou **Comptes désactivés** — retiennent des contributeurs, **Toutes les qualités** et **Tous les comptes** lèvent les filtres ; le champ de recherche retient les contributeurs dont le nom contient le texte saisi ; **Colonnes**.

Pendant qu’un enregistrement est en route, **Modifier les contributeurs** attend sa réponse, pour rouvrir la liste sur la version qu’elle apporte.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque colonne se trie par le serveur. Un chef de projet est marqué d’une icône à côté de sa qualité ; un compte anonymisé garde le nom que le serveur lui donne.

## Les gestes au clavier

- La liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Dans le dialogue, `Tab` parcourt les qualités, les retraits, les propositions et les commandes ; `Échap` le ferme sans rien enregistrer.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres du projet](FBS-4.2.md) ;
- [la gestion des utilisateurs](FBS-1.1.md) et [les rôles d’habilitation](FBS-1.2.md) ;
- [les rôles de ressources](FBS-3.2.2.md), dont l’emploi au devis fonde les propositions.
