# Sauvegarde et restauration

## Ce que montre l’écran

Les sauvegardes de la plateforme, hors de tout projet. Une sauvegarde porte la plateforme entière ; restaurer, c’est remplacer la plateforme par elle.

De haut en bas :

- **Planification** : l’état de la sauvegarde planifiée — active ou suspendue —, sa fréquence, son jour pour une sauvegarde hebdomadaire, son heure en temps universel (UTC), sa rétention — combien de sauvegardes la plateforme conserve — et sa copie externe : l’emplacement, le dossier et le nombre de copies gardées, ou « Aucune ».
- La liste des sauvegardes, chacune avec sa date, sa taille, sa vérification, son déclenchement et sa conservation, que le serveur trie — la plus récente d’abord —, filtre et pagine ; son pied dit combien il en retient.
- Pour qui peut restaurer la plateforme, **Restaurer une sauvegarde d’une autre installation**.

## Ses commandes

- **Modifier la planification**, pour qui peut modifier les sauvegardes, ouvre son formulaire, qui l’enregistre entière : état, fréquence, jour, heure (UTC) — l’heure de ce poste qu’elle représente aujourd’hui est dite à côté —, sauvegardes conservées, et la copie externe vers l’un des emplacements que l’installation déclare, dans un dossier relatif, avec au moins autant de copies gardées que de sauvegardes conservées, et l’état de la copie, active ou suspendue ; **Aucune copie** la retire. **Tester l’emplacement** fait écrire puis effacer un fichier témoin à l’emplacement choisi, et dit le résultat.
- **Sauvegarder maintenant**, pour qui peut modifier les sauvegardes, lance une sauvegarde ; son avancement se suit dans le panneau des tâches.

Sur chaque sauvegarde, les commandes qu’elle liste, chacune dans sa colonne, présente quand une sauvegarde de la page l’offre ; une commande indisponible dit la condition qui lui manque :

- **Conserver** marque la sauvegarde à conserver : la rotation ne la supprime pas ; **Ne plus conserver** lève la marque.
- **Télécharger** l’archive de la sauvegarde ; indisponible tant qu’elle n’est pas vérifiée (« sauvegarde vérifiée »).
- **Restaurer** ouvre la restauration de la plateforme depuis la sauvegarde. Indisponible pour une sauvegarde non vérifiée, pendant une sauvegarde (« aucune sauvegarde en cours ») ou une autre restauration (« aucune restauration en cours »). Le dialogue dit ce qui sera perdu — tout ce qui a été saisi depuis —, que les utilisateurs seront déconnectés et que la restauration sera inscrite au journal d’audit ; il ne restaure qu’une fois saisi l’identifiant de la sauvegarde. La restauration lancée, l’écran fait place à celui de la maintenance, qui la suit jusqu’à son terme et propose alors de se reconnecter.

Pendant une restauration, seul le téléchargement reste disponible. Aucune commande ne supprime une sauvegarde : la rotation s’en charge, selon la rétention.

**Restaurer une sauvegarde d’une autre installation** : **Déposer** envoie, morceau par morceau, l’**Archive de la sauvegarde** téléchargée sur une installation de même version ou plus ancienne ; déposée, **Restaurer cette sauvegarde** ouvre le même dialogue de restauration.

Au-dessus de la liste :

- **Période des sauvegardes**, **Filtrer par déclenchement**, **Filtrer par vérification**, **Conservation** et, entre deux bornes, la taille en octets.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page**, **Page précédente** et **Page suivante** parcourent la liste.

## Ses colonnes et ses valeurs calculées

Toute valeur est celle du serveur. La taille s’écrit dans l’unité qui lui convient ; le filtre sur la taille, lui, se borne en octets. La date est à l’heure de ce poste ; l’heure de la planification est en temps universel.

## Les gestes au clavier

- La liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur une commande de la liste la presse ; pressée indisponible, elle dit la condition qui lui manque.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Dans un dialogue, `Échap` le ferme sans rien faire — sauf pendant l’envoi d’une restauration, qui attend la réponse du serveur.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [La surveillance de l’état du système](FBS-1.3.md), qui date la dernière sauvegarde, sa copie externe et le dernier test de restauration, et signale leurs échecs ;
- [le journal d’audit](FBS-1.5.md), qui inscrit les sauvegardes et les restaurations.
