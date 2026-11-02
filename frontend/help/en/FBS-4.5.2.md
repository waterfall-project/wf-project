# Remaining to commit grid

## What the screen shows

The grid of the screen of the [remaining to commit](FBS-4.5.md), on the main structure of the revision: the tasks in the order of the plan and their estimate lines, by default those of the started tasks alone. For each line, the budgeted amount, its quantities and its re-estimated at the previous review, then its current quantities and re-estimated: the review reads what was estimated the last time, and enters what it estimates today.

## Its commands

The gestures of structure, in the menu of a cell and at their keys, as in the estimate: **Insert below** (`Insert`), **Insert a sub-task** (`Alt+Insert`), **Insert a line** (`Ctrl+Insert`), **Indent** (`Alt+Shift+→`), **Outdent** (`Alt+Shift+←`), **Move up** (`Alt+Shift+↑`), **Move down** (`Alt+Shift+↓`), **Delete** (`Ctrl+Delete`). A line or a task added after the reference revision is an unanticipated line: its budgeted amount is zero, it weighs on the remaining to commit and never on the reference budget.

The submenu **Subproject** carries the line, or the selection, to a subproject; it is not offered on a provision line, nor on the line of a started task whose subproject has received actual costs.

The grid takes no paste. It is entered where the structure lists “Update the estimate to complete” available, and each line where it says it accepts it: the lines of a completed task are no longer modified. A task is completed when all its lines bear a zero remaining to commit; it is reopened from the [Kanban](FBS-4.5.3.md).

## Its columns and computed values

The budgeted amount is the one the reference revision set; the re-estimated amount follows the reviews of the remaining to commit. The three amounts are computed: a computed cell says what it depends on. The mark “Started task past its finish” comes from the server.

## Keyboard gestures

- The handle of the row, in the column of the number: `Space` selects it, `Shift+↑` and `Shift+↓` extend the selection, `Esc` lifts it; `Alt+Shift` and an arrow move it.
- `Shift+F10` or the Menu key opens the menu of the cell.
- The moves in the grid, the entry and the sort are described in the help of the [remaining to commit](FBS-4.5.md).
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The remaining to commit](FBS-4.5.md), the whole screen, and [its indicators](FBS-4.5.1.md);
- [the estimate grid](FBS-4.4.2.md), [the Kanban](FBS-4.5.3.md);
- the notions: [the remaining to commit and the updated estimate](notions/reste-a-engager.md), [the reference budget](notions/budget-de-reference.md).
