# Portfolio risks

## What the screen shows

The risks of the projects of the perimeter and their coverage. Under the title, the perimeter retained and the date of calculation. From top to bottom:

- **Risk provisions**: the total of the provisions of the identified risks, then, over the period, the provisions of the risks occurred and those of the risks dismissed.
- **Risk coverage**: the reference reserve, against the remaining provisions and the cost of the risks occurred, and the coverage variance. It bears only on the projects in progress and completed: a project in pricing has no reference.
- **Heaviest risks**: the identified risks, all projects together, ranked by provision amount, each with its project.
- **Risk matrix**: a cloud of bubbles, the probability on the horizontal axis and the severity, as a share of the reference budget, on the vertical axis, each bubble as large as the severity in amount; under it, the count of the risks by cell.

A project in pricing, when it is retained, brings its identified risks and their provisions as they are, without weighting.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released.
- **From** and **To**, the period of the occurrences and of the dismissals, and **Calculated on**, the date of calculation, then **Apply**. A period that ends before it starts is refused at its field, the view not read.

In the view:

- the name of a project, in the heaviest risks, opens it when you may consult it; a bubble of the matrix likewise opens the project of its risk;
- **Export as PNG** saves the matrix as an image, with the perimeter and the date of calculation; **Values of the chart** unfolds its values, as a table.

## Its columns and computed values

All the sums are calculated by the server and marked Σ. The provision of a risk is its severity weighted by its probability. A value the server cannot calculate says so, with its reason, and is never worth zero. A risk whose severity cannot be related to the budget is not plotted in the matrix, and the matrix says how many and why. The zone of a cell is read by its signal, never by the colour alone.

## Keyboard gestures

- `Tab` goes through the filters, the tables, the links and the commands of the matrix; `Enter` on the name of a project opens it.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), [the project control health](FBS-2.7.md), which signals the risks not reviewed;
- [the risk management of a project](FBS-4.6.md);
- the notion: [the provision and the reserve](notions/provision-et-reserve.md).
