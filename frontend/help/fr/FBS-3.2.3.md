# Calendriers

## Ce que montre l’écran

La troisième table des [paramètres de ressources](FBS-3.2.md) : les calendriers, chacun avec son libellé, unique, et les heures travaillées de chacun des sept jours, du lundi au dimanche. Un calendrier convertit une durée en dates pour les tâches du rôle qui l’emploie ; il ne gère ni les jours fériés ni les temps partiels.

Un et un seul calendrier actif est désigné **Par défaut**, marqué dans sa colonne : il s’applique aux tâches auxquelles aucun rôle n’est affecté.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les paramètres de ressources :

- **Nouveau calendrier** ouvre le formulaire : le libellé et les heures de chacun des sept jours, tous requis.
- **Modifier**, sur une ligne, ouvre le même formulaire sur le calendrier.
- **Désigner**, dans la colonne **Par défaut**, fait du calendrier celui par défaut, à la place du précédent. Indisponible pour un calendrier désactivé (« calendrier actif »).
- **Désactiver** et **Réactiver**, dans la colonne **État**, sans confirmation. Le calendrier par défaut ne se désactive qu’après qu’un autre a été désigné (« calendrier autre que celui par défaut »).

Une commande indisponible reste présentée et dit la condition qui lui manque. Un libellé déjà porté est refusé à son champ, qui nomme le calendrier qui le porte.

Au-dessus de la table, pour tous : un filtre d’état quand les désactivés sont affichés ; le champ de recherche, sur le libellé ; **Colonnes**, **Lignes par page**, **Page précédente** et **Page suivante**. Les heures d’un jour ne se filtrent pas.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque calendrier est celui que tient le serveur. Chaque colonne se trie, les heures de chaque jour comprises. Le pied dit combien de calendriers la table retient.

## Les gestes au clavier

- La table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur **Modifier**, **Désigner**, **Désactiver** ou **Réactiver** presse la commande.
- Sur un en-tête, `Entrée` ou `Espace` trie la table ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [Les paramètres de ressources](FBS-3.2.md) et [les rôles de ressources](FBS-3.2.2.md), qui emploient chacun un calendrier ;
- [la planification](FBS-4.3.md), dont le Gantt hachure les jours chômés du calendrier d’une tâche.
