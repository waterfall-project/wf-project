# Resource roles

## What the screen shows

The second table of the [resource settings](FBS-3.2.md): the resource roles, each a position or a function of the company, which the labour estimate lines use. Each with its label, its code, unique, its organisation node, its labour cost category, whose hourly rate costs its hours, its calendar, which gives its working days to the tasks that use it, and its capacity: the hours available per month and the headcount they correspond to. The capacity does not vary over time, and only the hours are compared to the workload.

The three attachments are required and designate, when they are made, active objects; the table names them as the server resolves them, active or not. The node of a role no longer changes after its creation: a role that changes department is deactivated, and created again under the new node.

## Its commands

These commands are offered only to whoever may modify the resource settings:

- **New role** opens the form: code, unique, label, node, labour category, calendar, hours per month and headcount, all required.
- **Modify**, on a row, opens the same form, without the node, which the form names.
- **Deactivate** and **Reactivate**, in the column **State**, without confirmation. The reactivation of a role whose node is deactivated is unavailable (“organisation node active”): the command stays shown and says the condition it lacks.

A code or a label already borne is refused at its field, which names the role that bears it; a value outside its bounds, with the bound crossed.

Above the table, for all:

- **Role code**; **Organisation node**, which keeps the roles of the node and of its descendants; **Cost category**; **Calendar** — each with its choice “Every …” —; a filter of state when the deactivated ones are shown;
- **Bounds of “Resource roles”**: the hours per month and the headcount between two bounds. An upper bound under the lower bound is refused at its field, and the table is not read;
- the search field keeps the roles whose code or label contains the text entered;
- **Columns**, **Rows per page**, **Previous page** and **Next page**.

## Its columns and computed values

Nothing is computed: each role is the one the server holds. The footer says how many roles the table keeps.

## Keyboard gestures

- The table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on **Modify**, **Deactivate** or **Reactivate** presses the command; a form closed gives the focus back to the cell it was opened from.
- On a header, `Enter` or `Space` sorts the table; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The organisation tree](FBS-3.2.1.md), [the calendars](FBS-3.2.3.md), [the hourly rates](FBS-3.1.2.md);
- [the aggregated workload](FBS-2.2.md), which compares the load of each role to its capacity;
- [the estimate](FBS-4.4.md), each labour line of which bears a role.
