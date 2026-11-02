# Project portfolio

## What the screen shows

The value of the portfolio and the list of its projects, over the perimeter you choose. The views of the portfolio consolidate: nothing is entered there. They aggregate all the projects of the perimeter, whether you are a contributor to them or not, and open only those you may consult; another one counts in the totals and appears in the list, without a link.

Under the title, the perimeter the server retained — the states, the number of projects, the period, the organisation node — and the date of calculation, which all the figures of the screen bear. Calculated on the current day, each project contributes through its current revision; on a past date, through its last revision marked before that date, and according to the state it had then.

From top to bottom:

- **Portfolio value**: the **Order book**, sum of the reference budgets of the projects in progress; the **Gross pipeline** and the **Weighted pipeline**, sum of the current estimates of the projects in pricing, gross then weighted by their probabilities of winning; the **Delivered**, sum of the actual costs of the projects completed over the period; and the **Conversion rate**, share of the offers that left pricing over the period which passed to in progress.
- The list of the projects, which the server sorts, searches, filters and pages; its footer says how many projects it keeps.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed, each pressed or not. The last state retained is not released: a perimeter keeps at least one.
- **From** and **To**, the period, and **Calculated on**, the date of calculation, then **Apply**. A period that ends before it starts is refused at its field, the view not read.
- **Organisation node and its descendants** restricts only the labour lines whose role comes under the node; the other totals do not change.

Above the list:

- **Filter by zone of the indices** keeps the projects whose cost index or schedule index is in one of the zones chosen; **Every zone** lifts the filter. A project without an index is in no zone.
- The search field keeps the projects whose label contains the text entered.
- **Columns** chooses the columns shown; **Rows per page**, **Previous projects** and **Next projects** go through the list.

The label of a project you may consult is a link that opens it.

## Its columns and computed values

Every figure is the server’s: a quantity of the portfolio is the sum of those of the projects, an index or a percentage the ratio of these sums, never an average. A project in pricing counts for its amount weighted by its probability of winning, except in the gross pipeline. A value the server cannot calculate says so, with its reason, and is never worth zero. The zone of an index is read by its signal, never by the colour alone.

## Keyboard gestures

- The list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on the label of a project opens it.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- The other views of the portfolio: [the aggregated workload](FBS-2.2.md), [the performance](FBS-2.3.md), [the cost structure](FBS-2.4.md), [the risks](FBS-2.5.md), [the S-curve](FBS-2.6.md), [the project control health](FBS-2.7.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the indices](notions/indices.md), [the revisions](notions/revisions.md).
