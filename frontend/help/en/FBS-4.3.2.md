# Planning grid

## What the screen shows

The grid of the screen of [planning](FBS-4.3.md): a row per task of the structure read, in the order of the plan, each summary task above its subordinates, the handle and the row number at the start, the Gantt in the last column. The totals of the answer are in the footer. The planning shows no estimate line: they are read in the estimate.

A task is entered with the keyboard, cell by cell, where the structure read lists “Edit the schedule” available: its label, its description, its scheduling mode, its duration, its dates when they are not calculated, its predecessors, its attachment to the work breakdown. An entry refused is said above the grid, and its cell is marked.

## Its commands

The gestures of structure, in the menu of a cell and at their keys:

- **Insert below** (`Insert`) creates a task at the same level, under the active row; **Insert a sub-task** (`Alt+Insert`) creates it under the task of the row. A milestone has no sub-task. The task is named in a dialog: it is created a leaf, in automatic mode, of one day, without a predecessor.
- **Indent** (`Alt+Shift+→`), **Outdent** (`Alt+Shift+←`), **Move up** (`Alt+Shift+↑`) and **Move down** (`Alt+Shift+↓`) move the active row, or the selection when the row is part of it; a summary task takes its subordinates with it. A move is offered only if the rows moved are sisters that follow one another and the neighbour it rests on is shown: a search or a filter may take it away. One does not indent under a milestone.
- **Delete** (`Ctrl+Delete`) deletes the active row; a summary task, once confirmed, with its subordinates, their lines and their links.
- **Timelines** checks the timelines the task is inscribed to; **Time/time tracking** inscribes a milestone to the tracking of the contractual milestones. **Create a timeline…** creates one, when the project has none.

The gestures and the entry are offered only where the structure read lists “Edit the schedule” available. A write in progress holds the following gestures until the grid is read again, which says it is busy.

## Its columns and computed values

The duration is typed with its unit: “2 d”, “1 wk”, “1 mo” for a month, “30 min”, “4 h”; a number alone is a number of days. A date is typed in its short form, or in the form 2026-05-31; the server completes the hours according to the calendar.

The predecessors are entered as in MS Project, separated by semicolons: the row number, the type of the link — FS (finish to start, which may be left out), SS, FF, SF —, then the lag, positive or negative, with its unit or in percent: “3FS+2 d; 5SS”. A number the grid does not know leaves the entry open; a loop of links is refused, with the tasks it goes through.

The columns “Started on” and “Completed on” say when the task changed state: the server sets them, they are not entered, and that of a summary task is the first of its started subordinates. A link that the manual task cannot respect — it is dated before the finish of its automatic predecessor — is marked by an icon in the column of the predecessors, on the manual task as on its predecessor, and named: the row of the predecessor, the type of the link, the row of the task. The Gantt says it in the name of the bar.

The mode and the progress are read by a named icon; a task of the [critical path](notions/chemin-critique.md) bears the icon “Critical path”, and its float is in bold. A summary task bears the smallest float of its subordinates, and the critical path as soon as one of them is on it. The physical progress of a summary task is calculated, or said not computable with its reason.

## Keyboard gestures

- The cell of the number is the handle of the row: `Space` selects it, `Shift+↑` and `Shift+↓` extend the selection, `Esc` lifts it. With the mouse, a click selects a row, `Shift` and a click extend the selection, and the handle drags the selection before, after or under another row.
- `Alt+Shift` and an arrow move the selection, as dragging the handle does.
- `Shift+F10` or the Menu key opens the menu of the cell.
- The moves in the grid and the entry are described in the help of the [planning](FBS-4.3.md).
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The planning](FBS-4.3.md), the whole screen, and [the Gantt](FBS-4.3.3.md);
- [the estimate grid](FBS-4.4.2.md), the same tree with its lines;
- the notions: [the critical path and the float](notions/chemin-critique.md), [the work breakdown](notions/lotissement.md).
