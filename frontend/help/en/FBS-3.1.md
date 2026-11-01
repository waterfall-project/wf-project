# Cost settings

## What the screen shows

The cost settings of the installation, outside any project, which each project uses. Under the title, the single currency of the installation, in which all the amounts are expressed: it is chosen at installation, is not modified, and Waterfall converts no amount. Then the name of the company, which the exported files bear.

From top to bottom, each part under its title:

- [the cost types and categories](FBS-3.1.1.md): two tables, the **Cost types** then the **Cost categories**;
- the [hourly rates](FBS-3.1.2.md): a row per labour category, a column per year.

Each table is sorted, searched, filtered and paged by the server, and keeps its own height. The lists show only the active objects, unless the deactivated ones are asked for too: nothing is deleted in the reference data, an object is deactivated and can be reactivated. A deactivated object is no longer offered for entry, and stays readable wherever it is used.

## Its commands

At the top of the screen:

- **Show the deactivated ones too** adds to the three tables the deactivated objects, and adds to them a filter of state; **Hide the deactivated ones** comes back from it. Offered to whoever may read the cost settings.
- **Actual cost mapping** leads to the [actual cost extraction mapping](FBS-3.1.3.md).
- **Modify the company name** opens its form: the name is required, of 200 characters at most.

The commands that write — the name of the company, the creation, the modification, the deactivation and the reactivation of a cost type or of a category, the entry of a rate, the addition of a year — are offered only to whoever may modify the cost settings; to the others, the screen is read only. Their detail is in the help of each part.

A modification of the reference data touches no marked revision, which keeps the values used at its marking.

## Its columns and computed values

Nothing is computed here: each table shows the objects as the server holds them, and its footer says how many it keeps. The definitions of the columns of the three tables follow.

## Keyboard gestures

- Each table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on a command of a cell — **Modify**, **Deactivate**, **Reactivate** — presses it; `Enter` or `F2` enters a rate, `Esc` abandons the entry.
- On a header, `Enter` or `Space` sorts the table by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The cost types and categories](FBS-3.1.1.md), [the hourly rates](FBS-3.1.2.md), [the actual cost extraction mapping](FBS-3.1.3.md);
- [the resource settings](FBS-3.2.md), where each resource role is attached to a labour category;
- [the portfolio cost structure](FBS-2.4.md), which breaks the amounts down by cost type.
