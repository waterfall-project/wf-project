# Project work breakdown

## What the screen shows

The first list of the [settings of the project](FBS-4.2.md): the division of the purchase order into work packages, each work package into order items, each order item into deliverables, in a tree, in the order of entry. The work breakdown conditions neither the costing nor the control, which are done without it; its entry is optional, and without it it is worth one work package and one order item with the label of the project, without a deliverable.

It renders two services. It allows to **Generate the planning** once, without entering the structure of the business again: a summary task per work package and per order item, attached to it, a one-day task per deliverable, an end milestone per order item and per work package. And this [attachment](notions/lotissement.md) makes the work breakdown a reading grid: filtering the planning or the estimate on a work package or an order item is filtering the subtree of the task that bears it. The skeleton has no lasting link: renaming an order item does not rename its task.

A search or a filter keeps elements: the tree shows them with the work packages and the order items that contain them, without the rest, and says so above the grid.

## Its commands

The commands of entry follow **Enter the work breakdown**, which the project offers to its project managers. Unavailable, they stay shown and say what they lack: a terminal project, or a background process running that writes in the current revision or freezes it (“no background task running on the object”).

- **New work package**, in the bar of the grid, adds a work package at the end;
- **Add an order item** on a work package, **Add a deliverable** on an order item, in the menu of a cell or in the bar, for the row of the active cell;
- **Rename** changes the label of the element; each work package, order item and deliverable bears a label;
- **Delete**, once confirmed, removes the element with what it contains. The tasks of the current revision that bear a deleted work package or order item remain, and lose their attachment; the marked revisions keep it.

The work breakdown is saved whole, at each gesture, from its last reading whole: entered under a filter, it starts from the whole reading the screen makes beside it. A refusal that aims at the label entered is said at its field; a refusal that aims at another element names it, by its kind and its label; if the work breakdown has changed since its reading, the refusal offers to read the page again. During a write, the commands wait for its answer.

Above the grid, for all: **Filter by kind** keeps the work packages, the order items or the deliverables, **Every kind** lifts the filter; the search field keeps the elements whose label contains the text entered; **Columns**; **Tree** folds and unfolds.

Under the grid, **Generate the planning**, offered as long as the main structure of the current revision has no task (“main structure without any task”) and to whoever may modify the planning. A project without a revision first opens its current revision, then generates. Generated, the screen leads to the [planning grid](FBS-4.3.2.md).

## Its columns and computed values

Nothing is computed: the tree is not sorted, its order is that of the entry. The [estimate indicators](FBS-4.4.1.md) total each work package by the task that bears it; a work package no task bears is shown there without a total.

## Keyboard gestures

- The tree is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Shift+F10` or the Menu key opens the menu of the active cell.
- `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`; **Tree** folds and unfolds where the folding keys do not answer.
- `F1` opens this help.

## See also

- [The settings of the project](FBS-4.2.md), [the planning](FBS-4.3.md), where the filter **Work package or order item** is read, and [the estimate](FBS-4.4.md);
- the notion: [the work breakdown](notions/lotissement.md).
