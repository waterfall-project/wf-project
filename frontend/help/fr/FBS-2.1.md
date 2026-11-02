# Portefeuille de projets

## Ce que montre l’écran

La valeur du portefeuille et la liste de ses projets, sur le périmètre que vous choisissez. Les vues du portefeuille consolident : rien ne s’y saisit. Elles agrègent tous les projets du périmètre, que vous en soyez contributeur ou non, et n’ouvrent que ceux que vous pouvez consulter ; un autre compte dans les totaux et figure dans la liste, sans lien.

Sous le titre, le périmètre que le serveur a retenu — les états, le nombre de projets, la période, le nœud d’organisation — et la date de calcul, que portent tous les chiffres de l’écran. Calculé au jour courant, chaque projet contribue par sa révision courante ; à une date passée, par sa dernière révision marquée avant cette date, et selon l’état qu’il avait alors.

De haut en bas :

- **Valeur du portefeuille** : le **Carnet**, somme des budgets de référence des projets en cours ; le **Pipeline brut** et le **Pipeline pondéré**, somme des devis courants des projets en chiffrage, brute puis pondérée par leurs probabilités de gain ; le **Réalisé**, somme des coûts réels des projets terminés sur la période ; et le **Taux de transformation**, part des offres sorties du chiffrage sur la période qui sont passées en cours.
- La liste des projets, que le serveur trie, cherche, filtre et pagine ; son pied dit combien de projets il retient.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés, chacun pressé ou non. Le dernier état retenu ne se relâche pas : un périmètre en garde au moins un.
- **Du** et **Au**, la période, et **Calculé au**, la date de calcul, puis **Appliquer**. Une période qui finit avant de commencer est refusée à son champ, la vue non lue.
- **Nœud d’organisation et ses descendants** ne restreint que les lignes de main-d’œuvre dont le rôle relève du nœud ; les autres totaux n’en changent pas.

Au-dessus de la liste :

- **Filtre par zone des indices** retient les projets dont l’indice de coût ou l’indice de délai est dans l’une des zones choisies ; **Toutes les zones** lève le filtre. Un projet sans indice n’est dans aucune zone.
- Le champ de recherche retient les projets dont le libellé contient le texte saisi.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page**, **Projets précédents** et **Projets suivants** parcourent la liste.

Le libellé d’un projet que vous pouvez consulter est un lien qui l’ouvre.

## Ses colonnes et ses valeurs calculées

Tout chiffre est celui du serveur : une grandeur du portefeuille est la somme de celles des projets, un indice ou un pourcentage le rapport de ces sommes, jamais une moyenne. Un projet en chiffrage compte pour son montant pondéré par sa probabilité de gain, sauf dans le pipeline brut. Une valeur que le serveur ne peut pas calculer le dit, avec sa raison, et ne vaut jamais zéro. La zone d’un indice se lit par son signal, jamais par la seule couleur.

## Les gestes au clavier

- La liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur le libellé d’un projet l’ouvre.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- Les autres vues du portefeuille : [le plan de charge agrégé](FBS-2.2.md), [la performance](FBS-2.3.md), [la structure des coûts](FBS-2.4.md), [les risques](FBS-2.5.md), [la courbe en S](FBS-2.6.md), [la santé du pilotage](FBS-2.7.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [les indices](notions/indices.md), [les révisions](notions/revisions.md).
