# Portfolio S-curve

## What the screen shows

The cumulative costs of the projects of the perimeter, month by month, over the horizon chosen. Under the title, the perimeter retained and the date of calculation.

**Cumulative costs of the portfolio** shows three curves, each the sum of those of the projects: the cumulative reference budget, the cumulative actual cost up to the date of calculation, then, beyond it, the projection of the project managers. A project in pricing, when it is retained, enters it through its current estimate weighted by its probability of winning: without the provision lines for the curve of the budget, provisions included for the projection.

Read as cash-out, the curve becomes **Cumulative cash-out of the portfolio**: each project shifted by its payment delays and bearing the provisions of its identified risks. A second chart, **Cash-out by month**, then details, month by month, what is paid out and what remains to be paid out.

## Its commands

- **Read as cash-out** turns the curve into cash-out; **Back to the cumulative costs** brings it back.
- **Export as PNG** saves a chart as an image, with the perimeter, the horizon and the date of calculation; **Values of the chart** unfolds its values, as a table.

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released.
- **Calculated on**, the date of calculation, then **Apply**. This view takes neither a period nor an organisation node.
- **Horizon**: 6, 12 or 24 months, or **Default**, that of the server.

## Its columns and computed values

Each point is the sum of the points of the projects, as the server calculates it; nothing is summed nor shifted in the browser. The curve of the actual cost rises by steps, at the date of each document. A value the server cannot calculate leaves a gap in its curve, and its row of the table says why. The curves are told apart without their colour: each is named at its end.

## Keyboard gestures

- `Tab` goes through the filters and the commands of the charts; the table of the values, wider than the window, scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), [the portfolio performance](FBS-2.3.md);
- [the indicators of a project](FBS-4.8.md), which bear its own S-curve;
- the notions: [the reference budget](notions/budget-de-reference.md), [the provision and the reserve](notions/provision-et-reserve.md).
