# Subprojects

## What the screen shows

A list of the [settings of the project](FBS-4.2.md): the subprojects, each by the code under which the ERP knows it, its label, and whether actual costs are charged to it. The codes come from the ERP at the entry of the order: they are not known during the costing, and their entry is optional — a project is costed without a subproject.

The subproject is the mesh of the actual costs: the time sheets and the invoices are charged to a code of subproject, never to a task. It is therefore there that the budget and the expense meet, and that the financial progress is calculated. An estimate line bears its subproject; a cost line finds it in its WBS element.

## Its commands

The commands follow **Edit the project**, which the project offers to its project managers; a terminal project offers none.

- **New subproject**, at the top of the list, opens the form: the code and the label, required. The code is unique in the project, and it names the tab of the subproject in the file of remaining to commit: at most 31 characters, without `:`, `\`, `/`, `?`, `*`, `[` nor `]`, and neither “Synthèse” nor “Hors sous-projet”. A code refused is refused at its field, with its reason; a code another subproject already bears names the latter.
- **Modify**, on a row, opens the same form on the subproject.
- **Delete**, on a row, once confirmed. Unavailable for a subproject actual costs are charged to (“no actual cost booked against the subproject”), that a marked revision cites (“subproject cited by no marked revision”), or that lines of estimate of the current revision bear (“no estimate line of the current revision bearing the subproject”): the command stays shown, and its click says what it lacks. In this last case only, a link leads to the estimate of the current revision filtered on the subproject, to move its lines elsewhere; a refusal of the server names the lines one by one.

Above the list, for all: **Actual costs** keeps **With actual costs charged** or **Without actual costs charged**, **Every subproject** lifts the filter; the search field keeps the subprojects whose code or label contains the text entered; **Columns**.

What a write did is said in the region of the list; a refusal of deletion, above it. While a modification is under way, **Modify** waits for its answer on this row.

## Its columns and computed values

Nothing is computed: each column is sorted by the server, and the footer says how many subprojects the list keeps.

## Keyboard gestures

- The list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on **Modify** or **Delete** presses the command.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The settings of the project](FBS-4.2.md);
- [the estimate](FBS-4.4.md), each line of which bears a subproject, and [the remaining to commit](FBS-4.5.md), whose file files each subproject in its tab;
- [the actual costs](FBS-4.7.md), charged by subproject.
