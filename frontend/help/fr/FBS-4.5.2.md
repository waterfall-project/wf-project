# Grille de reste à engager

## Ce que montre l’écran

La grille de l’écran du [reste à engager](FBS-4.5.md), sur la structure principale de la révision : les tâches dans l’ordre du plan et leurs lignes de devis, par défaut celles des seules tâches démarrées. Pour chaque ligne, le montant budgété, ses grandeurs et son réestimé à la revue précédente, puis ses grandeurs et son réestimé courants : la revue lit ce qui a été estimé la dernière fois, et saisit ce qu’elle estime aujourd’hui.

## Ses commandes

Les gestes de structure, dans le menu d’une cellule et à leurs touches, comme au devis : **Insérer au-dessous** (`Inser`), **Insérer une sous-tâche** (`Alt+Inser`), **Insérer une ligne** (`Ctrl+Inser`), **Indenter** (`Alt+Maj+→`), **Désindenter** (`Alt+Maj+←`), **Monter** (`Alt+Maj+↑`), **Descendre** (`Alt+Maj+↓`), **Supprimer** (`Ctrl+Suppr`). Une ligne ou une tâche ajoutée après la révision de référence est une ligne non anticipée : son montant budgété est nul, elle pèse sur le reste à engager et jamais sur le budget de référence.

Le sous-menu **Sous-projet** porte la ligne, ou la sélection, à un sous-projet ; il n’est pas offert sur une ligne de provision, ni sur la ligne d’une tâche démarrée dont le sous-projet a reçu des coûts réels.

La grille ne prend pas de collage. Elle se saisit là où la structure liste « Réestimer le reste à engager » disponible, et chaque ligne là où elle dit l’accepter : les lignes d’une tâche terminée ne se modifient plus. Une tâche se termine quand toutes ses lignes portent un reste à engager nul ; elle se rouvre depuis le [Kanban](FBS-4.5.3.md).

## Ses colonnes et ses valeurs calculées

Le montant budgété est celui que la révision de référence a fixé ; le montant réestimé suit les revues du reste à engager. Les trois montants sont calculés : une cellule calculée dit de quoi elle dépend. La marque « Tâche démarrée dont la fin est dépassée » vient du serveur.

## Les gestes au clavier

- La poignée de la ligne, dans la colonne du numéro : `Espace` la sélectionne, `Maj+↑` et `Maj+↓` étendent la sélection, `Échap` la lève ; `Alt+Maj` et une flèche la déplacent.
- `Maj+F10` ou la touche Menu ouvre le menu de la cellule.
- Les déplacements dans la grille, la saisie et le tri sont décrits dans l’aide du [reste à engager](FBS-4.5.md).
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.

## Voir aussi

- [Le reste à engager](FBS-4.5.md), l’écran entier, et [ses indicateurs](FBS-4.5.1.md) ;
- [la grille de devis](FBS-4.4.2.md), [le Kanban](FBS-4.5.3.md) ;
- les notions : [le reste à engager et le devis actualisé](notions/reste-a-engager.md), [le budget de référence](notions/budget-de-reference.md).
