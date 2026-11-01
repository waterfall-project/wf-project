# Cost types and categories

## What the screen shows

Two tables of the [cost settings](FBS-3.1.md), one under the other:

- the **Cost types**: each with its code, unique, its label and its kind — labour, non-labour or risk provision;
- the **Cost categories**: each with its code, its label, its cost type and its accounting code, unique and for documentation.

A category is attached to a cost type, whose kind it takes: only the labour categories bear [hourly rates](FBS-3.1.2.md) and are attached to the resource roles; a provision line of a risk bears a category of a cost type of risk provision. Deactivating a cost type deactivates its categories.

An empty list says so; a search or a filter that keeps nothing keeps the table, to be changed.

## Its commands

These commands are offered only to whoever may modify the cost settings:

- **New nature** opens the form of the cost type: code, unique, label and kind, all required.
- **New category** opens that of the category: code and accounting code, both unique, label and cost type, all required.
- **Modify**, on a row, opens the same form on the object. The kind of a cost type is no longer modified once one of its categories is used by a line of estimate or of remaining to commit, bears an hourly rate or is attached to a resource role; the form says which of these conditions is lacking. A category is then attached only to a cost type of the same kind.
- **Deactivate** and **Reactivate**, in the column **State**, change the state of the object, without confirmation. The reactivation of a category whose cost type is deactivated is unavailable (“cost type active”): the command stays shown and says the condition it lacks.

A code or a label already borne is refused at its field, which names the object that bears it. What a write does is said above the table; a refusal that names an object to reactivate first says so too.

Above each table, for all:

- **Kinds of cost type** keeps the cost types of the kinds chosen; **Cost type** keeps the categories of a cost type;
- a filter of state — **Every state**, **Active**, **Deactivated** — when the deactivated ones are shown;
- the search field keeps the objects whose code or label contains the text entered, and, for the categories, the accounting code;
- **Columns**, **Rows per page**, **Previous page** and **Next page**.

## Its columns and computed values

Nothing is computed: each object is the one the server holds, the cost type of a category named as the server resolves it, active or not. The footer of each table says how many objects it keeps.

## Keyboard gestures

- Each table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on **Modify**, **Deactivate** or **Reactivate** presses the command; a form closed gives the focus back to the cell it was opened from.
- On a header, `Enter` or `Space` sorts the table; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The cost settings](FBS-3.1.md) and [the hourly rates](FBS-3.1.2.md);
- [the resource roles](FBS-3.2.2.md), attached to a labour category;
- the notion: [the provision and the reserve](notions/provision-et-reserve.md).
