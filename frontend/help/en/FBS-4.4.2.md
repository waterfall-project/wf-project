# Estimate grid

## What the screen shows

The grid of the screen of the [estimate](FBS-4.4.md): the tasks of the structure read, in the order of the plan, and under each one the estimate lines it bears, before its sub-tasks. A labour line bears a resource role, which sets its category, and an effort in hours; another line bears a quantity and a unit disbursement. A provision line, which the server holds from a risk, is not entered. The totals of the answer are in the footer.

On the differential of an amendment, the column “Change” marks each line: **+** added, **-** removed, **M** modified; the colour doubles the mark, and a removed line is read without being touched.

## Its commands

The gestures of structure, in the menu of a cell and at their keys, as in the planning: **Insert below** (`Insert`), **Insert a sub-task** (`Alt+Insert`), **Indent** (`Alt+Shift+→`), **Outdent** (`Alt+Shift+←`), **Move up** (`Alt+Shift+↑`), **Move down** (`Alt+Shift+↓`), **Delete** (`Ctrl+Delete`); and of its own:

- **Insert a line** (`Ctrl+Insert`) creates an estimate line on the active task, or under the active line. A dialog asks for its category and its quantity, and its label, optional: left empty, the server composes it from the label of the task and, if there is one, that of the role; the rest is entered in the grid. It is not offered from a summary task nor from a milestone, and a completed task no longer receives one (“task not completed”).
- **Subproject** carries the line, or the selection, to a subproject of the project, or to none. It is not offered on a provision line, nor on the line of a started task whose subproject has received actual costs.
- **The paste** of a block copied from a spreadsheet (`Ctrl+V`) is made on the active cell. A preview says how many lines will be written and which are refused, with their reason; **Apply the paste** writes the valid lines, **Abandon** writes nothing. A block that would stretch under a hidden column, over folded rows or rows that the sort, the search or a filter have moved, is refused outright, the cause said.

The entry, the paste and the gestures of line ask for “Edit the estimate”; the gestures of task ask for “Edit the schedule” too.

## Its columns and computed values

The category of a labour line is that of its role: it is not entered. A line that uses a deactivated category or role says so in the column “Deactivated object”. The amounts, computed, are read in the help of the [amount at the reference year](FBS-4.4.3.md).

## Keyboard gestures

- The handle of the row, in the column of the number: `Space` selects it, `Shift+↑` and `Shift+↓` extend the selection, `Esc` lifts it; `Alt+Shift` and an arrow move it, as dragging the handle with the mouse does.
- `Shift+F10` or the Menu key opens the menu of the cell.
- The moves in the grid, the entry and the sort are described in the help of the [estimate](FBS-4.4.md).
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The estimate](FBS-4.4.md), the whole screen, and [its indicators](FBS-4.4.1.md);
- [the planning grid](FBS-4.3.2.md), the same tree without the lines;
- the notions: [the amendment and the differential](notions/avenant-et-differentiel.md), [the provision and the reserve](notions/provision-et-reserve.md).
