# Calendars

## What the screen shows

The third table of the [resource settings](FBS-3.2.md): the calendars, each with its label, unique, and the hours worked on each of the seven days, from Monday to Sunday. A calendar converts a duration into dates for the tasks of the role that uses it; it handles neither public holidays nor part-time work.

One and only one active calendar is designated **Default**, marked in its column: it applies to the tasks that bear no labour line.

## Its commands

These commands are offered only to whoever may modify the resource settings:

- **New calendar** opens the form: the label and the hours of each of the seven days, all required.
- **Modify**, on a row, opens the same form on the calendar.
- **Designate**, in the column **Default**, makes the calendar the default one, in the place of the previous one. Unavailable for a deactivated calendar (“calendar active”).
- **Deactivate** and **Reactivate**, in the column **State**, without confirmation. The default calendar is deactivated only after another one has been designated (“calendar other than the default one”).

An unavailable command stays shown and says the condition it lacks. A label already borne is refused at its field, which names the calendar that bears it.

Above the table, for all: a filter of state when the deactivated ones are shown; the search field, on the label; **Columns**, **Rows per page**, **Previous page** and **Next page**. The hours of a day are not filtered.

## Its columns and computed values

Nothing is computed: each calendar is the one the server holds. Each column is sorted, the hours of each day included. The footer says how many calendars the table keeps.

## Keyboard gestures

- The table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on **Modify**, **Designate**, **Deactivate** or **Reactivate** presses the command.
- On a header, `Enter` or `Space` sorts the table; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The resource settings](FBS-3.2.md) and [the resource roles](FBS-3.2.2.md), which each use a calendar;
- [the planning](FBS-4.3.md), whose Gantt hatches the days off of the calendar of a task.
