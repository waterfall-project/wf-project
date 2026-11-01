# Organisation tree

## What the screen shows

The first table of the [resource settings](FBS-3.2.md): the organisation nodes — a service, a department —, in a tree without a limit of depth, each with its label, indented under its parent, its code, unique, and its level, 1 for a root. The tree is read whole, in its order, never by pages, and is not sorted.

The resource roles are attached to the nodes, and the aggregated workload is filtered by node, its descendants included. Deactivating a node deactivates its descendants and the roles attached to them.

A search or a filter keeps nodes, and the tree shows them with their ancestors.

## Its commands

These commands are offered only to whoever may modify the resource settings:

- **New node** opens the form: code, unique, label, and **Parent** — **None — root** for a root. A node takes its place only under an active node.
- **Modify**, on a row, opens the same form on the node. Moved under another parent, it takes its descendants and its roles with it; never under itself nor under one of its descendants. Its deactivated parent is kept.
- **Deactivate** and **Reactivate**, in the column **State**, without confirmation. The reactivation of a node whose parent is deactivated is unavailable (“parent node active”): the command stays shown and says the condition it lacks.

Above the tree, for all:

- **Code of the node** keeps the nodes whose code contains the text entered; **Level** keeps a level; **Bounds of “Organisation tree”**, a minimum and maximum level;
- a filter of state when the deactivated ones are shown;
- the search field keeps the nodes whose code or label contains the text entered;
- **Columns**; **Tree** folds everything, unfolds everything, or folds down to a level; the button of a label folds or unfolds its row.

## Its columns and computed values

Nothing is computed. The footer says how many nodes the tree shows, ancestors of the nodes kept included.

## Keyboard gestures

- The tree is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- `Enter` on **Modify**, **Deactivate** or **Reactivate** presses the command.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`. The folding keys go less far there: `⌥` and `-`, `⌥` and `+` answer only in a browser that gives the layout of the keyboard, and `⌥` and `*` never; **Tree** then folds and unfolds.

## See also

- [The resource settings](FBS-3.2.md) and [the resource roles](FBS-3.2.2.md);
- [user management](FBS-1.1.md), where each account is attached to a node;
- [the aggregated workload](FBS-2.2.md), filtered by organisation node.
