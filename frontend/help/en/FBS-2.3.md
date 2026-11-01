# Portfolio performance

## What the screen shows

The performance of the projects in progress of the perimeter, in earned value. Under the title, the perimeter retained and the date of calculation. From top to bottom:

- **Aggregated indices**: the cost index and the schedule index of the portfolio, each with its zone, the cumulative cost and schedule variances, and the aggregated reference budget.
- **Projections at completion**: for each hypothesis — **At budget**, **Project manager’s**, **At the observed rate** —, the amount projected and its variance to the budget. The first two are the sums of the projections of the projects; the third is the aggregated reference budget divided by the aggregated cost index, and is not calculated as long as the latter is not.
- **Projects by zone**: for each index and each zone, the number of projects.
- **Quarterly evolution of the indices**: the curves of the two aggregated indices, a point per quarter, calculated at the past dates.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released. The performance bears only on the projects in progress.
- **From** and **To**, the period, and **Calculated on**, the date of calculation, then **Apply**. A period that ends before it starts is refused at its field, the view not read.
- **Organisation node and its descendants**.

The chart:

- **Export as PNG** saves the evolution of the indices as an image, with the perimeter and the date of calculation;
- **Values of the chart** unfolds the two indices of each quarter, as a table.

## Its columns and computed values

An index of the portfolio is a ratio of sums — the earned value of all the projects over their actual cost, or over their planned value —, never the average of the indices of the projects. A value the server cannot calculate says so, with its reason, and is never worth zero; in the chart, it leaves a gap in its curve. The zones are read by their signal, never by the colour alone.

## Keyboard gestures

- `Tab` goes through the filters, the tables and the commands of the chart.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), which gives the indices of each project, and [the S-curve](FBS-2.6.md);
- [the indicators of a project](FBS-4.8.md);
- the notions: [the indices](notions/indices.md), [the earned value](notions/valeur-acquise.md), [the planned value](notions/valeur-planifiee.md), [the reference budget](notions/budget-de-reference.md).
