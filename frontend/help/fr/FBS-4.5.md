# Estimation du reste à engager

## Ce que montre l’écran

Le reste à engager de la révision : ce qu’il reste à dépenser pour terminer le projet, réestimé à chaque revue périodique, ligne par ligne. En réalisation, c’est ici que se tient le devis : le devis de la structure principale se lit seulement dès que le projet est En cours, et la dépense restante se réestime sur cet écran.

Au-dessus de la grille, les [indicateurs du reste à engager](FBS-4.5.1.md) : son total, la marge sur le budget de référence, l’écart à la revue précédente, les ventilations et la couverture des risques. Puis la [grille du reste à engager](FBS-4.5.2.md), sur la structure principale : par défaut les lignes des seules tâches démarrées, que la revue réestime.

Le bandeau ne montre que le sous-projet, seul filtre que ses lectures prennent, et dit qu’il ne restreint que la grille : les indicateurs sont ceux du projet entier.

## Ses commandes

En tête de l’écran :

- **Montrer aussi les tâches non démarrées** ajoute à la grille les tâches qui n’ont pas démarré ; **Ne montrer que les tâches démarrées** revient à la lecture par défaut.
- **Kanban — démarrage des tâches** mène au Kanban, où les tâches se démarrent et se terminent.
- **Plan de charge**, une icône seule, mène à la répartition mensuelle des charges, par rôle.
- **Imports et exports**, quand le projet offre l’import d’un reste à engager.

Au-dessus de la grille : **Lot ou poste**, **Rechercher un libellé**, **Colonnes**, **Arbre**, et **Annuler** (`Ctrl+Z`) et **Rétablir** (`Ctrl+Maj+Z`), indisponibles tant que le serveur ne conserve pas l’historique des saisies.

Dans le menu d’une cellule (clic droit, `Maj+F10` ou la touche Menu) : les gestes de structure, dont **Insérer une ligne** (`Ctrl+Inser`) pour une dépense qui n’avait pas été chiffrée, le pliage, **Annuler** et **Rétablir**, et le sous-menu **Sous-projet**.

La grille ne se saisit que là où la structure principale liste « Réestimer le reste à engager » disponible pour vous : elle manque tant que le projet n’est pas En cours (« projet en cours »), et une ligne d’une tâche terminée ne se réestime plus (« tâche non terminée »).

## Ses colonnes et ses valeurs calculées

Le montant budgété, le réestimé à la revue précédente et le montant réestimé sont calculés par le serveur ; les grandeurs à la revue précédente sont conservées, jamais saisies. Seules la quantité, la charge et le débours unitaire courants se saisissent, une ligne à la fois. La fin d’une tâche se lit sans se saisir, et une fin dépassée porte sa marque propre. La colonne « Sous-projet » est masquée tant que vous ne l’affichez pas par **Colonnes**.

## Les gestes au clavier

- La grille est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` ou `F2` saisit une cellule, un caractère tapé commence la saisie, `Échap` l’abandonne ; `Tab` valide et passe à la cellule suivante, `Entrée` à la ligne du dessous.
- Sur un en-tête, `Entrée` ou `Espace` trie les lignes sous chaque tâche, les tâches gardant l’ordre du plan ; l’avancement et la fin ne trient pas. `Maj` et les flèches élargissent ou rétrécissent la colonne.
- `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs du reste à engager](FBS-4.5.1.md) et [sa grille](FBS-4.5.2.md) ;
- [le Kanban](FBS-4.5.3.md), [le devis](FBS-4.4.md), [les risques](FBS-4.6.md) ;
- les notions : [le reste à engager et le devis actualisé](notions/reste-a-engager.md), [le budget de référence](notions/budget-de-reference.md), [les révisions](notions/revisions.md).
