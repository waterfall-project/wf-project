# Risk register

## What the screen shows

The grid of the screen of [risk management](FBS-4.6.md): a row per risk the filter by state keeps, as the revision read holds them. The server sorts it, searches it and filters it as the address asks; the footer bears the grand total of the provisions of the risks retained. The register is read only: a risk is declared, modified and reviewed through the commands of the screen and of its detail.

The label of a risk is a link to its detail, which opens beside the register. The state of a risk occurred is a link to the estimate filtered on the lines that came of it, for whoever reads the estimate, or to the planning filtered on the tasks and lines that came of it, for whoever reads the planning without the estimate.

## Its commands

- **Search a label** keeps the risks whose label contains the text entered.
- **Column filters** unfolds, under the cards, the bar of the filters that follow; it is folded by default, and opens by itself when one of these filters is active.
- **Filter by zone** keeps the risks whose cell of the matrix is in the zones chosen.
- **Bounds of the probability** and **Bounds of the amounts** keep, for each column of figures — probability, severity, provision, cost at occurrence, reestimated of occurred —, the risks whose value lies between a minimum and a maximum, both included; the probability is written from 0 to 1. An identified or dismissed risk, which has neither a cost at occurrence nor a reestimated amount, is kept by no bound of these two columns.
- **Period of the last review** keeps the risks whose last review falls between two days, the end included.
- **Not reviewed since the last marking** sets the end of that period to the day of the last marking of the project: the periodic review shows the risks whose probability has not been reviewed since. The server filters, and the totals follow.
- **Columns** chooses the columns shown.
- A header sorts the register by its column; the reestimated of occurred and the cell of the matrix are not sorted.

## Its columns and computed values

The severity, the provision and the cost at occurrence are computed, whole columns, and bear Σ in their header: a cell pressed names the rules its value depends on, as the risk states them. The cell of the matrix is read by its signal and its zone, never by the colour alone. A risk occurred or dismissed no longer bears a provision line: its provision is the one it bore in the reference revision, zero if it was not identified there. Only an occurred risk bears a cost at occurrence: the total of its own estimate when it was declared occurred. The reestimated of occurred, beside it, is the sum of the current reestimated amounts of the lines that came of it: it shows the drift of the risk, outside the coverage variance.

## Keyboard gestures

- The register is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on the label of a risk opens its detail; on a computed cell, the explanation of its value, which `Esc` closes.
- On a header, `Enter` or `Space` sorts; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.

## See also

- [Risk management](FBS-4.6.md) and [the provisions of the risks retained](FBS-4.6.2.md);
- the notion: [the provision and the reserve](notions/provision-et-reserve.md).
