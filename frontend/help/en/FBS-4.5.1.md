# Remaining to commit indicators

## What the screen shows

The cards above the grid of the [remaining to commit](FBS-4.5.md), as the server calculates them for the revision read, each with its date of calculation. They bear on the whole project: the subproject filter of the banner and the filter by work package or by order item restrict only the grid.

- **Remaining to commit**: the grand total of what remains to be spent.
- **Margin on the reference budget**: the projection of the project manager — the actual cost plus the remaining to commit — minus the [reference budget](notions/budget-de-reference.md). It is signed in the direction of the drift: positive, the project costs more than planned. Absent on a project without a reference revision.
- **Deviation from the previous review**: the remaining to commit minus that of the previous marked revision, when the latter was marked in the state In progress; absent rather than zero otherwise. Positive, the review has raised the remaining expense.
- **By nature of cost**: the remaining to commit of each cost type, with its share.
- **Remaining to commit by sub-project, and margin on the budget**: for each subproject, and for the set “No subproject”, its remaining to commit and the deviation between the sum of its actual cost and of its remaining to commit and its budget, with the signal of the zone the server gives: a subproject whose budget is exceeded is signalled. The subprojects add up to the total of the project.
- **Risk coverage**: the risk reserve of the reference, the remaining provisions, the cost of the risks occurred, and the coverage variance.

When the API does not find the indicators, the screen says them unavailable and shows the rest.

## Its commands

The cards have no command: they are read.

## Its columns and computed values

All the values are calculated by the server; the front recalculates none of them. A signal is read by its text and its icon, never by its colour alone.

## Keyboard gestures

The cards are read in the order of the page, before the grid.

## See also

- [The remaining to commit](FBS-4.5.md) and [its grid](FBS-4.5.2.md);
- [the estimate indicators](FBS-4.4.1.md), [the provisions of the risks](FBS-4.6.2.md);
- the notions: [the remaining to commit and the updated estimate](notions/reste-a-engager.md), [the reference budget](notions/budget-de-reference.md), [the provision and the reserve](notions/provision-et-reserve.md).
