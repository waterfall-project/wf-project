# Rôles de ressources

## Ce que montre l’écran

La deuxième table des [paramètres de ressources](FBS-3.2.md) : les rôles de ressources, chacun un poste ou une fonction de l’entreprise, que les lignes de devis de main-d’œuvre emploient. Chacun avec son libellé, son code, unique, son nœud d’organisation, sa catégorie de coût de main-d’œuvre, dont le taux horaire chiffre ses heures, son calendrier, qui donne ses jours travaillés aux tâches qui l’emploient, et sa capacité : les heures disponibles par mois et l’effectif auquel elles correspondent. La capacité ne varie pas dans le temps, et seules les heures se comparent au plan de charge.

Les trois rattachements sont obligatoires et désignent, quand ils se font, des objets actifs ; la table les nomme tels que le serveur les résout, actifs ou non. Le nœud d’un rôle ne change plus après sa création : un rôle qui change de service se désactive, et se recrée sous le nouveau nœud.

## Ses commandes

Ces commandes ne sont offertes qu’à qui peut modifier les paramètres de ressources :

- **Nouveau rôle** ouvre le formulaire : code, unique, libellé, nœud, catégorie de main-d’œuvre, calendrier, heures par mois et effectif, tous requis.
- **Modifier**, sur une ligne, ouvre le même formulaire, sans le nœud, que le formulaire nomme.
- **Désactiver** et **Réactiver**, dans la colonne **État**, sans confirmation. La réactivation d’un rôle dont le nœud est désactivé est indisponible (« nœud d’organisation actif ») : la commande reste présentée et dit la condition qui lui manque.

Un code ou un libellé déjà porté est refusé à son champ, qui nomme le rôle qui le porte ; une valeur hors de ses bornes, avec la borne franchie.

Au-dessus de la table, pour tous :

- **Code du rôle** ; **Nœud d’organisation**, qui retient les rôles du nœud et de ses descendants ; **Catégorie de coût** ; **Calendrier** — chacun avec son choix « Tous » — ; un filtre d’état quand les désactivés sont affichés ;
- **Bornes de « Rôles de ressources »** : les heures par mois et l’effectif entre deux bornes. Une borne supérieure sous la borne inférieure est refusée à son champ, et la table n’est pas lue ;
- le champ de recherche retient les rôles dont le code ou le libellé contient le texte saisi ;
- **Colonnes**, **Lignes par page**, **Page précédente** et **Page suivante**.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque rôle est celui que tient le serveur. Le pied dit combien de rôles la table retient.

## Les gestes au clavier

- La table est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur **Modifier**, **Désactiver** ou **Réactiver** presse la commande ; un formulaire fermé rend le focus à la cellule d’où il a été ouvert.
- Sur un en-tête, `Entrée` ou `Espace` trie la table ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [L’arbre d’organisation](FBS-3.2.1.md), [les calendriers](FBS-3.2.3.md), [les taux horaires](FBS-3.1.2.md) ;
- [le plan de charge agrégé](FBS-2.2.md), qui compare la charge de chaque rôle à sa capacité ;
- [le devis](FBS-4.4.md), dont chaque ligne de main-d’œuvre porte un rôle.
