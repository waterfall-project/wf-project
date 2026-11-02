# Planning

## What the screen shows

The planning of a revision: the tree of the tasks of the structure read, with their durations, their dates and their links, and the Gantt in the last column of the grid, row for row. It is the view of the cost structure on the side of time; the estimate is its view on the side of money, on the same tree.

The banner at the top says the reading context: the project, the revision read, the structure read — the main structure by default, a differential of amendment or the own estimate of a risk — and the active filters. It offers to change structure. On a marked revision, it says that nothing is entered: a [marked revision](notions/revisions.md) is frozen.

The dates of the tasks in automatic mode are calculated by the server, from their duration, their links and their calendar: the screen shows them as it renders them, and dates nothing itself. The planning is the source of the years of consumption of the estimate and of the [planned value](notions/valeur-planifiee.md) when the revision becomes the reference.

## Its commands

At the top of the screen:

- **Timelines**, **Imports and exports**, **Task tree** lead to the screens next to the planning, in the same context.
- **Contractualise the amendment**, on the differential of an amendment only: reads the report of the merge — tasks, lines and links added, modified, removed, started tasks that will be completed, reasons that refuse it —, asks for the version name of the revision produced, then hands the merge to the background processing. Unavailable as long as the revision has no amendment to merge (“an unmerged amendment”); refused by the reasons the report names.

Above the grid:

- **Planning start date** says the day the automatic tasks without a predecessor start on, as the server gives it. **Change the planning start date**, where the structure is entered, asks for the new day and confirms it: the server redates the tasks that depend on it, and refuses a day without a worked hour in the default calendar, naming the next working day.
- **Work package or order item** filters the grid on the task that bears a work package or an order item of the work breakdown, with its subordinates and its ancestors. The banner shows the filter and allows to lift it.
- **Search a label** keeps the tasks whose label contains the text entered.
- **Columns** chooses the columns shown; **Tree** folds everything, unfolds everything, or folds down to a level.
- **Undo** (`Ctrl+Z`) and **Redo** (`Ctrl+Shift+Z`), where the structure is entered. They stay unavailable as long as the server does not keep the history of the entries.
- **Insert a task**, in an empty grid, creates its first task.
- **Generate the planning**, in the empty grid of the main structure: generates the skeleton from the work breakdown — a summary task per work package and per order item, a task per deliverable and their end milestones. Unavailable once the structure holds a task.

In the menu of a cell (right click, `Shift+F10` or the Menu key): **Insert below**, **Insert a sub-task**, **Indent**, **Outdent**, **Move up**, **Move down**, **Delete**, the folding of the row, **Undo** and **Redo**, and two submenus: **Timelines**, to inscribe the task — or the selection — to a timeline, and **Time/time tracking** for a milestone. The detail of these gestures and of their keys is in the help of the [planning grid](FBS-4.3.2.md); the zoom and the export of the Gantt in that of the [Gantt](FBS-4.3.3.md).

The grid is entered, and offers its gestures, only where the structure read lists “Edit the schedule” available to you: a marked revision, a closed project or a background process running leave it read only. A computed cell is never entered: it says what its value depends on.

## Its columns and computed values

A column whose header bears Σ is computed by the server; a computed cell is greyed and marked Σ. The dates of a task in automatic mode, the duration and the progress of a summary task, the total float are computed. The column “Timelines” is hidden as long as you do not show it through **Columns**.

## Keyboard gestures

- The grid is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` or `F2` enters a cell; a character typed starts the entry; `Esc` abandons it. Validated, the entry goes to the next cell: `Tab` along the row, `Enter` to the row below.
- The planning keeps the order of the plan: no column is sorted. On a header, `Shift` and the arrows widen or narrow the column.
- `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`. The folding keys go less far there: `⌥` and `-`, `⌥` and `+` answer only in a browser that gives the layout of the keyboard, and `⌥` and `*` never; in Safari and Firefox, none answers, and the menu of a cell then folds and unfolds.
- `F1` opens this help.

## See also

- [The planning grid](FBS-4.3.2.md) and [the Gantt](FBS-4.3.3.md), the two parts of the screen;
- [the timelines](FBS-4.3.1.md), [the imports and exports](FBS-4.3.4.md), [the task tree](FBS-4.3.5.md);
- [the estimate](FBS-4.4.md), the same structure on the side of money;
- the notions: [the revisions](notions/revisions.md), [the critical path and the float](notions/chemin-critique.md), [the work breakdown](notions/lotissement.md), [the amendment and the differential](notions/avenant-et-differentiel.md).
