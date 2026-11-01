# Gantt

## What the screen shows

The last column of the [planning grid](FBS-4.3.2.md), pinned to the right: each row draws its task on the scale of time there, aligned on the grid. A task is a bar — solid on the critical path, hollow elsewhere —, a summary task a bracket, a milestone a diamond; the links join the tasks as their type says. Nothing there is read by the colour alone: each bar is named by its dates, and “critical” when it is. The days off of the calendar of the task are hatched.

The Gantt is read, it is not entered: the dates change through the grid. A row folded in the grid is folded in the Gantt too; the button before the bracket of a summary task folds or unfolds it.

## Its commands

In the corner of the header of the Gantt:

- **Zoom in** (`Ctrl++`) tightens the scale, down to the worked hours of a day; unavailable when the zoom is at its strongest.
- **Zoom out** (`Ctrl+-`) widens the scale; unavailable when the zoom is at its weakest.
- **Fit to project** sets the scale to show the whole project; unavailable when it already shows it.
- **Export as PNG** saves the Gantt as an image, over its whole extent at the zoom level chosen, a row per task shown, with the project, the revision and the date of calculation. Unavailable when the image would be too large for the browser: zoom out, or fold summary tasks.

The zoom and the export are also found in the menu of a cell of the Gantt. On a Mac, `⌘` stands for `Ctrl`.

## Its columns and computed values

The dates the Gantt draws are those the grid shows, calculated by the server for a task in automatic mode.

## Keyboard gestures

- The handle on the left edge of the column sets its width: with the mouse, or from the header, `Shift` and the arrows, the left arrow widening it. The width is kept as that of the other columns.
- `Ctrl++` and `Ctrl+-` zoom from the grid.

## See also

- [The planning](FBS-4.3.md) and [the planning grid](FBS-4.3.2.md);
- [the timelines](FBS-4.3.1.md), a view as a frieze of the tasks chosen;
- the notion: [the critical path and the float](notions/chemin-critique.md).
