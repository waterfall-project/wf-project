# Estimate indicators

## What the screen shows

The cards above the [estimate](FBS-4.4.md) grid, as the server calculates them for the revision read, and for the subproject when the banner filters one; a filter by work package or by order item restricts only the grid. Each card bears its date of calculation. The front calculates nothing there: an amount it cannot read is not shown.

- **Estimate total**: its grand total, provision lines included.
- **Identified provisions**: what the provision lines of the identified risks bear.
- **Deviation from the reference**: the deviation between the total of the estimate of the revision read and that of the [reference revision](notions/revisions.md), provision lines included on both sides, when the project has one.
- **Deviation from the previous marked revision**, when there is one.
- **By nature of cost**, in amount and in share of the total; **By subproject**; **By work package**: the total of the subtree of the task that bears each work package of the work breakdown, a work package without an attached task being shown without a total. A share that cannot be calculated says so, with its reason.

When labour cost categories have no hourly rate for the reference year of the revision, the notice “Missing hourly rates” names them with the year: the estimate cannot be calculated before they have one, and its indicators are said unavailable.

## Its commands

- **Enter the hourly rates** leads to the reference data of the costs, for whoever may modify it; **See the hourly rates**, for whoever may only read it.

## Its columns and computed values

All the values of the cards are calculated by the server, inflation included, at the year of consumption of the lines.

## Keyboard gestures

The cards are read in the order of the page; `Tab` reaches the links of the notice of the missing rates.

## See also

- [The estimate](FBS-4.4.md) and [the estimate grid](FBS-4.4.2.md);
- [the remaining to commit indicators](FBS-4.5.1.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the provision and the reserve](notions/provision-et-reserve.md).
