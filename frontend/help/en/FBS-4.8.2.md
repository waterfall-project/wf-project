# Projection at completion

## What the screen shows

The second card of the [project indicators](FBS-4.8.md), with its date of calculation: three estimates of the final cost, each named by its hypothesis on the remaining work, with its **Variance from budget**, the projection minus the [reference budget](notions/budget-de-reference.md), positive when it exceeds it.

- **At budget**: the rest will cost what was planned — the actual cost plus the share of the reference budget not yet earned.
- **Project manager’s**: the rest will cost what they estimate — the actual cost plus the [remaining to commit](notions/reste-a-engager.md).
- **Projection at the observed rate**: the rest will cost what the work done cost in proportion — the reference budget divided by the [cost index](FBS-4.8.4.md). Not computable as long as the index is not, before any actual cost, or when it is zero, the earned value being so — no completed task bears a budgeted amount yet; its variance from budget is then not shown.

None is truer than the others: it is their difference that informs. A projection of the project manager lower than that of the observed rate supposes that the drift will stop; it is this hypothesis that the review examines.

## Its commands

The card has no command: it is read, for the project or for the subproject the banner filters.

## Its columns and computed values

The first two projections form a table: **Hypothesis**, **Amount**, **Variance from budget**. The third follows, with its own mention when it is not computable. All the values are calculated by the server.

## Keyboard gestures

The cards are read in the order of the page, before the charts.

## See also

- [The project indicators](FBS-4.8.md), [the financial progress](FBS-4.8.1.md), [the cost performance index](FBS-4.8.4.md);
- [the margin on the reference budget](FBS-4.5.1.md), in the remaining to commit indicators, which starts from the projection of the project manager;
- the notions: [the earned value](notions/valeur-acquise.md), [the indices](notions/indices.md), [the remaining to commit](notions/reste-a-engager.md).
