# Surveillance de l’état du système

## Ce que montre l’écran

L’état de la plateforme, hors de tout projet, tel que le serveur le donne au moment où l’écran se lit ; sous le titre, la version installée. De haut en bas :

- **Alertes en cours** : chaque alerte avec son niveau, ce qu’elle signale et depuis quand — un composant indisponible, la file des traitements bloquée, l’échec d’une sauvegarde planifiée ou de sa copie externe, l’échec de la lecture des comptes du fournisseur d’identité, un stockage presque plein, un taux d’erreur anormal. L’alerte nomme ce qu’elle concerne : le composant, l’espace employé et libre, l’emplacement externe et la raison de l’échec. Sans alerte, l’écran dit « Aucune alerte en cours. »
- **Composants** : chaque composant de la plateforme, disponible ou indisponible, la date de sa dernière vérification et sa version.
- **Espace de stockage** : l’espace utilisé et l’espace disponible.
- **Paramètres d’exploitation** : les valeurs en vigueur de ce que l’exploitant fixe au déploiement — la durée de validité du cache des indicateurs, la rétention du résultat d’une tâche de fond, la taille maximale d’un avatar, l’attente d’une tâche en file et les taux d’occupation du stockage et d’erreur qui déclenchent une alerte, avec la fenêtre où le taux d’erreur se mesure. Aucun écran ne les modifie.
- **Dernières opérations** : la dernière lecture des comptes du fournisseur d’identité, la dernière sauvegarde, la dernière copie externe d’une sauvegarde et le dernier test de restauration, chacune datée avec son résultat et le motif d’un échec — ou « Jamais effectuée ».

## Ses commandes

L’écran se lit : il n’a pas de commande. Il montre l’état au moment de sa lecture ; le relire, par le navigateur, en donne un plus récent. Les sauvegardes se lancent et se planifient depuis l’écran des [sauvegardes](FBS-1.4.md), et la lecture des comptes depuis celui des [utilisateurs](FBS-1.1.md).

## Ses colonnes et ses valeurs calculées

Les tables de l’écran ne se trient ni ne se filtrent. Toute valeur est celle du serveur, rien ne se calcule ici. Le niveau d’une alerte se lit par son signal et son libellé, jamais par la seule couleur. Les dates sont à l’heure de ce poste.

## Les gestes au clavier

- `Tab` parcourt l’écran ; une table plus large que la fenêtre défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [La sauvegarde et la restauration](FBS-1.4.md), [la gestion des utilisateurs](FBS-1.1.md) ;
- [le journal d’audit](FBS-1.5.md).
