# Cumulative costs

## What the screen shows

The **S-curve**, under the milestone tracking of the [project indicators](FBS-4.8.md): the budgetary view of the project, what it was to cost, what it has cost, what it will cost. It does not speak of progress, only of money over time, month by month, each point bearing the cumulative total at the end of the month.

- **Reference budget**: at each date, that of the reference revision in force at that date, read on its own dates. Each [amendment](notions/avenant-et-differentiel.md) makes a step in it, dated and drawn across: it is not a drift, it is an event of the contract. It reaches the reference budget at the end of the reference.
- **Actual cost**: cumulated by the document dates, up to the date of calculation; it rises by steps.
- **Project manager’s projection**: beyond, the [remaining to commit](notions/reste-a-engager.md) of each line spread over the part of the duration of its task that follows the date of calculation, or carried whole to the date of calculation when the finish of the task is passed.

Shifted by the payment delays, the curve becomes **Cash out**: each amount is shifted by the payment delay of its line, the provisions of the identified risks staying at the date of their task; the actual cost is not shifted. The table **Cash out by month** then gives, month by month, the **Paid out** and what remains **To pay out**.

When nothing comes under the mesh read — a subproject without a line nor an actual cost —, the section says so instead of drawing a zero; a curve alone without a point is named under the chart.

## Its commands

- **Shift by the payment delays** presents the curve as cash-out; **Remove the shift by the payment delays** brings it back. When there is nothing to draw, only the second stays offered, to leave the shift.
- **Export as PNG** saves the curve as an image, with the project, the revision and the date of calculation, and the subproject when the banner filters one.
- **Values of the chart** unfolds its points as a table.

## Its columns and computed values

All the values are calculated by the server, the shift included: nothing is summed nor shifted in the browser. The table of the values gives, for each point, the **Curve**, the **Date** and the **Amount**; the **Steps of the reference budget**, their **Date**, their **Cause** and the **Amount of the step**, signed.

## Keyboard gestures

- `Tab` reaches the commands of the section and **Values of the chart**; a table wider than the window scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project indicators](FBS-4.8.md), [the earned value curves](FBS-4.8.8.md), [the projection at completion](FBS-4.8.2.md);
- [the portfolio S-curve](FBS-2.6.md), [the estimate](FBS-4.4.md), where the payment delay of a line is entered;
- the notions: [the reference budget](notions/budget-de-reference.md), [the amendment and the differential](notions/avenant-et-differentiel.md), [the provision and the reserve](notions/provision-et-reserve.md).
