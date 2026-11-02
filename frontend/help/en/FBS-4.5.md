# Estimate to complete

## What the screen shows

The remaining to commit of the revision: what remains to be spent to complete the project, re-estimated at each periodic review, line by line. In execution, it is here that the estimate is kept: the estimate of the main structure is read only once the project is In progress, and the remaining expense is re-estimated on this screen.

Above the grid, the [remaining to commit indicators](FBS-4.5.1.md): its total, the margin on the reference budget, the deviation from the previous review, the breakdowns and the risk coverage. Then the [remaining to commit grid](FBS-4.5.2.md), on the main structure: by default the lines of the started tasks alone, which the review re-estimates.

The banner shows only the subproject, the only filter its readings take, and says that it restricts only the grid: the indicators are those of the whole project.

## Its commands

At the top of the screen:

- **Show the tasks not started too** adds to the grid the tasks that have not started; **Show the started tasks only** comes back to the default reading.
- **Kanban — task start** leads to the Kanban, where the tasks are started and completed.
- **Workload**, an icon alone, leads to the monthly breakdown of the loads, by role.
- **Imports and exports**, when the project offers the import of a remaining to commit.

Above the grid: **Work package or order item**, **Search a label**, **Columns**, **Tree**, and **Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Shift+Z`), unavailable as long as the server does not keep the history of the entries.

In the menu of a cell (right click, `Shift+F10` or the Menu key): the gestures of structure, among them **Insert a line** (`Ctrl+Insert`) for an expense that had not been costed, the folding, **Undo** and **Redo**, and the submenu **Subproject**.

The grid is entered only where the main structure lists “Update the estimate to complete” available to you: it is lacking as long as the project is not In progress (“project in progress”), and a line of a completed task is no longer re-estimated (“task not completed”).

## Its columns and computed values

The budgeted amount, the re-estimated at the previous review and the re-estimated amount are calculated by the server; the quantities at the previous review are kept, never entered. Only the current quantity, effort and unit disbursement are entered, one line at a time. The finish of a task is read without being entered, and a finish passed bears its own mark. The column “Subproject” is hidden as long as you do not show it through **Columns**.

## Keyboard gestures

- The grid is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` or `F2` enters a cell, a character typed starts the entry, `Esc` abandons it; `Tab` validates and goes to the next cell, `Enter` to the row below.
- On a header, `Enter` or `Space` sorts the lines under each task, the tasks keeping the order of the plan; the progress and the finish do not sort. `Shift` and the arrows widen or narrow the column.
- `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`. The folding keys go less far there: `⌥` and `-`, `⌥` and `+` answer only in a browser that gives the layout of the keyboard, and `⌥` and `*` never; in Safari and Firefox, none answers, and the menu of a cell then folds and unfolds.
- `F1` opens this help.

## See also

- [The remaining to commit indicators](FBS-4.5.1.md) and [its grid](FBS-4.5.2.md);
- [the Kanban](FBS-4.5.3.md), [the estimate](FBS-4.4.md), [the risks](FBS-4.6.md);
- the notions: [the remaining to commit and the updated estimate](notions/reste-a-engager.md), [the reference budget](notions/budget-de-reference.md), [the revisions](notions/revisions.md).
