# Costing and estimate

## What the screen shows

The estimate of a revision: the tasks of the structure read and the estimate lines they bear, each attached to a cost category. It is the view of the cost structure on the side of money; the planning is its view on the side of time, on the same tree.

Above the grid, the [estimate indicators](FBS-4.4.1.md) — its total, its provisions, its variances, its breakdowns —, with their date of calculation; and, when some are missing, the hourly rates the calculation needs. The banner says the reading context and the structure read — the main structure, a differential of amendment or the own estimate of a risk —, and offers to change it.

The estimate is entered as long as the project is in pricing: on the main structure of a project In progress, it is read only, and the remaining expense is re-estimated in the [remaining to commit](FBS-4.5.md). The differential of an amendment and the own estimate of a risk are still entered. A line costs at the reference year of the revision; the server projects it onto its year of consumption, which the planning gives, at the inflation rate of the project.

## Its commands

At the top of the screen:

- **Workload** leads to the monthly breakdown of the loads of the revision, by role;
- **Imports and exports** leads to the screen where an estimate is imported from a file, when the project offers this import.

Above the grid:

- **Work package or order item** filters the grid on a work package or an order item of the work breakdown; the indicators stay those of the project, or of the subproject filtered.
- **Search a label**, **Columns**, **Tree**;
- **Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Shift+Z`), where the structure is entered. They stay unavailable as long as the server does not keep the history of the entries.
- **Enter the hourly rates**, in the notice of the missing rates, leads to the reference data of the costs for whoever may modify it; **See the hourly rates** for whoever reads it.

In the menu of a cell (right click, `Shift+F10` or the Menu key): the gestures of structure — among them **Insert a line** (`Ctrl+Insert`) —, the folding, **Undo** and **Redo**, and the submenu **Subproject**, which carries the line, or the selection, to a subproject. Their detail is in the help of the [estimate grid](FBS-4.4.2.md).

The grid is entered, and takes a paste, only where the structure read lists “Edit the estimate” available to you. Creating, moving or deleting a task writes the planning too: these gestures ask for “Edit the schedule” besides.

## Its columns and computed values

The amounts are calculated by the server, never entered: a labour line is worth its quantity, its effort and the hourly rate of its category for the reference year; a non-labour line, its quantity and its unit disbursement; a task, its lines and its subordinates. A computed cell, greyed and marked Σ, says what its value depends on when one tries to enter it. The subproject of a provision line comes from its risk: it is computed.

The header of the amount corrected for inflation names, in its tooltip, the reference year of the revision and the inflation rate of the project. The column “Subproject” is hidden as long as you do not show it through **Columns**.

## Keyboard gestures

- The grid is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` or `F2` enters a cell, a character typed starts the entry, `Esc` abandons it; `Tab` validates and goes to the next cell, `Enter` to the row below.
- On a header, `Enter` or `Space` sorts the lines under each task by the column, the tasks keeping the order of the plan; `Shift` and the arrows widen or narrow the column.
- `Ctrl+V` pastes a block copied from a spreadsheet on the active cell, after a preview.
- `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`. The folding keys go less far there: `⌥` and `-`, `⌥` and `+` answer only in a browser that gives the layout of the keyboard, and `⌥` and `*` never; in Safari and Firefox, none answers, and the menu of a cell then folds and unfolds.
- `F1` opens this help.

## See also

- [The estimate indicators](FBS-4.4.1.md), [the estimate grid](FBS-4.4.2.md), [the amount at the reference year](FBS-4.4.3.md);
- [the workload](FBS-4.4.4.md), [the planning](FBS-4.3.md), [the remaining to commit](FBS-4.5.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the revisions](notions/revisions.md), [the provision and the reserve](notions/provision-et-reserve.md), [the remaining to commit and the updated estimate](notions/reste-a-engager.md).
