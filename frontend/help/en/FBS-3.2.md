# Resource settings

## What the screen shows

The resource settings of the installation, outside any project. Three settings that complete one another, then the units of duration, from top to bottom:

- the [organisation tree](FBS-3.2.1.md): the departments of the company, in a tree without a limit of depth;
- the [resource roles](FBS-3.2.2.md): each attached to a node, to a labour category and to a calendar, with its capacity;
- the [calendars](FBS-3.2.3.md): the hours worked on each day of the week, one of them by default;
- the **Units of duration**: the hours per day, the hours per week and the days per month, by which a duration entered in days, in weeks or in months is converted into hours.

Each table is searched and filtered by the server, and keeps its own height; the roles and the calendars are also sorted and paged by it. The lists show only the active objects, unless the deactivated ones are asked for too: nothing is deleted in the reference data, an object is deactivated and can be reactivated. Each object names those it is attached to, active or not.

## Its commands

At the top of the screen, **Show the deactivated ones too** adds to the three tables the deactivated objects, and adds to them a filter of state; **Hide the deactivated ones** comes back from it. Offered to whoever may read the resource settings.

The commands that write are offered only to whoever may modify the resource settings; to the others, the screen is read only:

- the creation, the modification, the deactivation and the reactivation of a node, of a role or of a calendar, and the designation of the default calendar, detailed in the help of each table;
- **Modify the units of duration** opens their form: each strictly positive. The change holds for all the projects: the plannings of the revisions in progress are recalculated, a marked revision keeps the hours it calculated.

A modification of the reference data touches no marked revision, which keeps the values used at its marking.

## Its columns and computed values

Nothing is computed here: each table shows the objects as the server holds them, and its footer says how many it keeps. The definitions of the columns of the three tables follow.

## Keyboard gestures

- Each table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on a command of a cell — **Modify**, **Deactivate**, **Reactivate**, **Designate** — presses it.
- On a header, `Enter` or `Space` sorts the table by the column; `Shift` and the arrows widen or narrow the column.
- In the organisation tree, `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The organisation tree](FBS-3.2.1.md), [the resource roles](FBS-3.2.2.md), [the calendars](FBS-3.2.3.md);
- [the cost settings](FBS-3.1.md), where the labour categories and their rates are held;
- [the aggregated workload](FBS-2.2.md), which compares the load to the capacity of the roles.
