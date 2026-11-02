# Risk management

## What the screen shows

The register of the risks of the project, as the revision read holds them: their probability, their severity, their provision, the cost at occurrence of a risk occurred, their state. A risk is an uncertain event that would affect the cost or the schedule; its consequences are costed in an estimate of its own, and its provision — its severity weighted by its probability — is filed, as long as it is identified, on a task of the main structure. Occurred, it is no longer a risk but a fact: its own estimate joins the main structure.

From top to bottom: the [provisions of the risks retained](FBS-4.6.2.md) and the risk coverage; the filter by state; the risk matrix, folded behind its command; the [risk register](FBS-4.6.1.md); and, when a risk is chosen, its detail beside the register — its description, its mitigation actions, its provision line with its category and its subproject, the history of its reviews.

## Its commands

At the top of the screen:

- **Identify a risk** opens the form of declaration: label, description, mitigation actions, probability in percent, and, when there is a choice, the category of the provision, the subproject and the task that bears the provision — failing that, the first task of the first level. The risk created, its own estimate opens in the estimate grid. Unavailable without “at least one task” in the main structure, without “an active category of provision for risks”, on a closed project or during a background process.

Above the register:

- **Filter by state**: **Every state**, **Identified**, **Occurred**, **Dismissed**; the provisions, the bubbles of the matrix and the register follow the filter.
- **Chart** unfolds or folds the risk matrix, a cloud of bubbles — the probability on the horizontal axis, the severity as a share of the reference budget on the vertical axis, each bubble as large as the severity in amount —, with under it the count of the risks by cell, all states together. A bubble clicked opens the detail of its risk.
- **Search a label** and **Columns**.

In the detail of a risk:

- **Modify** opens the form of the risk: label, description, mitigation actions and provision, without the probability, which only the review changes; the category, the subproject and the task of the provision change only as long as the risk is identified.
- **Review** confirms or changes the probability and the state — identified or dismissed. The review is dated of the day; confirming it without changing anything produces one, which is added to the history.
- **Delete the risk**, once confirmed, with its own estimate and its provision line. Unavailable for a risk a marked revision cites (“risk cited by no marked revision”): it is then dismissed by a review.
- **Declare occurred**, once confirmed: its own estimate is merged into the main structure of the current revision, with a zero budgeted amount, and its provision line is removed; the risk keeps its cost at occurrence, the total of its own estimate at that instant. The merge is handed to the background processing. The declaration is final: an occurred risk lists all its commands unavailable.
- **Close the detail of the risk**.

These entries are made only on the current revision, where it lists “Edit the risks” for you.

## Its columns and computed values

The severity, the provision and the cost at occurrence are calculated by the server: the severity is the total of the own estimate of the risk; the provision of an identified risk, its severity weighted by its probability, that of a risk occurred or dismissed, the provision it bore in the reference revision; the cost at occurrence, the total of the own estimate when the risk was declared occurred. They are not entered: a computed cell names the rules its value depends on. The footer of the register bears the grand total of the provisions.

## Keyboard gestures

- The register is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Page Up` and `Page Down` by a screen.
- On the label of a risk, `Enter` opens its detail.
- On a header, `Enter` or `Space` sorts the register by the column, except the cell of the matrix; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The risk register](FBS-4.6.1.md) and [the provisions of the risks retained](FBS-4.6.2.md);
- [the estimate](FBS-4.4.md), where the own estimate of a risk is costed, and [the remaining to commit](FBS-4.5.md), with the risk coverage;
- the notions: [the provision and the reserve](notions/provision-et-reserve.md), [the reference budget](notions/budget-de-reference.md), [the revisions](notions/revisions.md).
