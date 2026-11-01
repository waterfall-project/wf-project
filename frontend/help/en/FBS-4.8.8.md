# Earned value curves

## What the screen shows

The chart **Planned value, earned value and actual cost**, at the bottom of the [project indicators](FBS-4.8.md): the performance view of the project, month by month, each point bearing the cumulative total at the end of the month.

- **Planned value**: cumulated on the dates of the reference revision, extended up to the end of the reference, where it reaches the [reference budget](notions/budget-de-reference.md).
- **Earned value**: cumulated by the dates of completion of the tasks, up to the date of calculation; a completed task makes a step in it at the month of its completion.
- **Actual cost**: cumulated by the document dates, up to the date of calculation.

The vertical differences are read as the variances of the indices: between earned value and actual cost, the cost variance; between earned value and planned value, the schedule variance in value. The horizontal difference between these last two is the delay in time. Where the S-curve says how much, these curves say whether one has done what one should, and at what price.

When nothing comes under the mesh read — a subproject without a line nor an actual cost —, the section says so instead of drawing a zero; a curve alone without a point is named under the chart.

## Its commands

- **Export as PNG** saves the curves as an image, with the project, the revision and the date of calculation, and the subproject when the banner filters one.
- **Values of the chart** unfolds their points as a table.

## Its columns and computed values

All the values are calculated by the server; nothing is summed in the browser. The table of the values gives, for each point, the **Curve**, the **Date** and the **Amount**.

## Keyboard gestures

- `Tab` reaches **Export as PNG** and **Values of the chart**; the table, wider than the window, scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project indicators](FBS-4.8.md), [the cost performance index](FBS-4.8.4.md), [the schedule performance index](FBS-4.8.5.md), [the cumulative costs](FBS-4.8.7.md);
- the notions: [the planned value](notions/valeur-planifiee.md), [the earned value](notions/valeur-acquise.md), [the indices](notions/indices.md).
