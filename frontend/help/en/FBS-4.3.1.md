# Timelines

## What the screen shows

A leaf of the [planning](FBS-4.3.md), reached from the header of the planning, in the same reading context. A timeline is a synthetic view meant to be shown — to a steering committee, to a client, to a team: it presents only the tasks and the milestones inscribed to it. A project may bear several, each named and kept.

At the top, the timelines of the project, each a link that shows it; the first one is shown when the address names none. Below, the **frieze** of the timeline shown, on the time axis of the Gantt: each task inscribed is a rectangle from its start to its finish, which bears its name, and each milestone a vertical line, its name and its date at its foot. The rectangles are arranged in lanes, by themselves in the order of the plan, or where you placed them. Under the frieze, a table reads the same tasks, their dates and their lanes.

The inscriptions are made from the [planning grid](FBS-4.3.2.md), by **Timelines** in the menu of a cell: nothing is inscribed here. The tasks read are those of the revision of the context, restricted to the subproject filtered.

## Its commands

The commands that write follow **Manage timelines**, which the project offers; unavailable, they stay shown and say what they lack — a terminal project.

- **New timeline** opens the form: a **Name**, required.
- **Delete**, on the timeline shown, once confirmed: its inscriptions disappear with it, the tasks and the milestones keep their dates. The screen then shows the first timeline that remains.

On the frieze, for all:

- **Zoom in**, **Zoom out** and **Fit to project** set the scale of time;
- **Automatic layout** arranges the tasks by themselves again, forgetting the lanes chosen by hand; unavailable as long as no task has been placed;
- **Export as PNG** saves the frieze as it is laid out, with the name of the timeline, the project, the revision and the date of calculation of the dates.

A task is dragged with the mouse from one lane to another. The lanes are a display preference of each one, by timeline: moving a task does not modify it. A move where the rectangle would overlap another one is refused, and said.

## Its columns and computed values

The dates are those the server calculated: nothing is planned here. A name too long for its rectangle is cut, and is read whole in its tooltip and in the table; a task without dates is not drawn, and the table says so.

## Keyboard gestures

- The frieze is a single tab stop: `←` and `→` go from one task to the next, the axis scrolling to keep it in view.
- `Alt+↑` and `Alt+↓` change the lane of the active task; `Esc` abandons a drag.
- `Tab` reaches the links of the timelines and the commands.
- On a Mac, `⌥` stands for `Alt`.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md), [the planning grid](FBS-4.3.2.md), where the tasks are inscribed, and [the Gantt](FBS-4.3.3.md), whose axis the frieze takes up;
- [the task tree](FBS-4.3.5.md), the other view meant to be shown.
