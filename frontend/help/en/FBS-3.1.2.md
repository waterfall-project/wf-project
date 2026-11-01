# Hourly rates

## What the screen shows

The hourly rate grid of the [cost settings](FBS-3.1.md): a row per labour cost category, with its code, its label and its state, and a column per year, each cell the hourly rate of the category for that year, in the currency of the installation. A year without a rate is an empty cell. The categories of the other cost types bear no rate.

The footer of the grid says how many categories it keeps and the currency of the rates, never a sum. The grid is sorted, searched and paged by the server; the years are those of the whole grid, on each page.

A rate serves the costing of the labour lines of the projects. Its modification touches no marked revision: a revision in progress takes it up by **Apply the rate update**, on the screen of the [revisions](FBS-4.1.md).

## Its commands

These commands are offered only to whoever may modify the cost settings:

- A cell is entered: the entry saves the rate of this category for this year, alone. A rate is not emptied.
- **Add a year to the grid**: the **Year**, then **Add the column**. No column is created by itself: the column added is empty, the rates of the other years unchanged, and it enters the grid of the server only with its first rate entered. A year the grid already has, or outside 2000 to 2100, is refused.
- **Remove the column**, for a year added none of whose rates is entered yet.

Above the grid, for all:

- a filter of state of the categories, when the deactivated ones are shown; they are reactivated in the list of the [categories](FBS-3.1.1.md);
- **Bounds of “Hourly rate grid”**: the **Year of the rate**, the last one by default, and the bounds of the **Hourly rate** of that year. An upper bound under the lower bound is refused at its field, and the grid is not read;
- the search field keeps the categories whose code or label contains the text entered;
- **Columns**, **Rows per page**, **Previous page** and **Next page**.

## Its columns and computed values

Nothing is computed: each rate is the one the server holds, and the rate it answers to an entry takes the place of the cell. Each column is sorted, that of a year by its rate; a category without a rate for the year keeps the order of the code.

## Keyboard gestures

- The grid is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` or `F2` enters a rate, a character typed starts the entry, `Esc` abandons it; `Tab` validates and goes to the next cell, `Enter` to the row below.
- On a header, `Enter` or `Space` sorts the grid; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [The cost settings](FBS-3.1.md) and [the cost types and categories](FBS-3.1.1.md);
- [the resource roles](FBS-3.2.2.md), whose category gives the rate of their hours;
- [revision management](FBS-4.1.md), where a revision in progress applies the rate update.
