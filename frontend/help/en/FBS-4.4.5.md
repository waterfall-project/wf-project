# Project spending projection

## What the screen shows

A leaf of the [costing](FBS-4.4.md), which the screen of the estimate and that of the remaining to commit open in the same context: what the project will spend, month by month and by cost type, labour and disbursements together. It is the view of the spending to come, beside the [workload](FBS-4.4.4.md), which is that of the hours.

The **Spending by cost type and by month**: a bar per month, stacked by cost type, the total of the month at its top; the legend names the cost types, and the tooltip of a month lists them with their amounts. The cost types are told apart by their colour; the **Series patterns** preference of “My account” gives each a pattern besides. The currency of the installation titles the axis. The values of the chart are also read in a table. A provision line appears under no cost type.

The amount of each labour and disbursement line is spread over the duration of its task, pro rata to the worked hours, in parts rounded to the cent whose sum is the amount of the line. On a basis of remaining to commit, only the remaining of the line is spread, over the part of the task that follows the date of calculation, and is carried to the month of that date when the finish of the task is passed: no month precedes the date of calculation, and the total of the projection is the remaining to commit of the project without its provisions. On the basis of the reference revision, the projection also presents the months before the date of calculation. For a marked revision, it is computed when read, on its images.

Under the choice, the basis and the revision the server says it read, and the date. Under the chart, the **Spending by cost type and by category**: a grid from the cost type to the category, read only, a column for each month, the total of each row and, at the foot, that of each month and that of the projection. It has no setting of its own: it is computed on the basis, the date and the subproject chosen for the chart.

## Its commands

At the top of the projection, then **Show**:

- **Basis**: **Budget of the reference revision**, **Remaining of a marked revision** or **Remaining of the current revision**. Only the bases the project admits are offered: the budget of the reference when the project has a reference revision, the remaining of a marked revision when it has one, the current revision always.
- **Marked revision**, for the basis of a marked revision: each of those of the project.
- **Date**: **Date of consumption**, the spending in the month it is consumed, or **Date of payment**, the spending shifted by the payment delay of each line — the cash-out.
- **Subproject** restricts the projection to a subproject; **Outside any subproject** retains what belongs to none, **Whole project** lifts the filter.

A projection the server refuses — a project without a reference revision, a marked revision that is missing or is not marked, an unknown subproject, a labour category without an hourly rate for the reference year — is said unavailable, with its reason.

On the chart:

- **Values of the chart**, under the chart, unfolds the table of its values;
- **Export as PNG** saves the chart, with the project, the revision, the basis, the date, the subproject and the date of calculation.

In the grid, the bar offers **Columns** and **Tree**, which folds or unfolds the cost types; the button of the label of a cost type folds or unfolds its categories.

## Its columns and computed values

Every amount is the server’s: that of each category, each cost type, each month, and the total of the projection. The total of each month is the sum of the cost types of that month, and that of each cost type the sum of its categories; the screen sums nothing. A month without amount stays blank in the grid.

## Keyboard gestures

- `Tab` goes through the choice of the basis, of the revision, of the date and of the subproject, **Show**, then the commands of the chart; `Enter` on **Values of the chart** unfolds or folds the table.
- The table of the values, when it overflows its box, scrolls with the arrows once reached.
- The grid is a single `Tab` stop: the arrows move the active cell; `Alt` and `-` folds a cost type, `Alt` and `+` unfolds it.
- `F1` opens this help.

## See also

- [Costing and estimate](FBS-4.4.md), whose lines make the spending, [the workload](FBS-4.4.4.md) and [the remaining to commit](FBS-4.5.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the remaining to commit](notions/reste-a-engager.md).
