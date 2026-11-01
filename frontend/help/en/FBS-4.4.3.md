# Amount at the reference year

## What the screen shows

The column “Amount (reference year)” of the [estimate grid](FBS-4.4.2.md): the amount of each line, of each task — summary task included — and of the total, costed at the hourly rates of the reference year of the revision, without inflation. Beside it, “Amount corrected for inflation” projects this same amount onto the year of consumption of the line, which the planning gives, at the inflation rate of the project.

The reference year is the one whose hourly rates cost the revision: retained at its creation, it no longer changes. The following years are projected by the inflation rate of the project, set in its settings.

The estimate shows neither the budgeted amount nor the re-estimated amount: the first is read in the [remaining to commit](FBS-4.5.md) and founds the [reference budget](notions/budget-de-reference.md); the second is the re-estimation of the reviews.

## Its commands

The column is not entered, and has no command of its own. A header sorts the lines under each task by their amount.

## Its columns and computed values

The amount of a labour line is the product of its quantity, of its effort and of the hourly rate of its category for the reference year; that of a non-labour line, the product of its quantity and of its unit disbursement; that of a task, the sum of the lines it bears and of its subordinates. A category without an hourly rate for the reference year prevents the calculation: the screen of the estimate says so above the grid.

## Keyboard gestures

- On the cell, `Enter` or `F2` opens the explanation: what the value depends on, and the lines it comes from; `Esc` closes it.
- On the header, the hover or the focus opens the tooltip that defines the column.

## See also

- [The estimate grid](FBS-4.4.2.md) and [the estimate indicators](FBS-4.4.1.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the revisions](notions/revisions.md).
