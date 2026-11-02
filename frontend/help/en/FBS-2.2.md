# Aggregated workload

## What the screen shows

The load of the projects of the perimeter, by resource role and by month, against the capacity of each role. The load of a project in progress is that of its remaining to commit; that of a project in pricing, when it is retained, that of its estimate weighted by its probability of winning. Under the title, the perimeter retained and the date of calculation.

From top to bottom:

- **Stacked load by role and by month**: a bar per month, divided by role, in hours, the total of the month at its top, and the capacity of the perimeter — the sum of the capacities of the roles retained — dotted.
- **Load by role and by month**: for each role, its monthly capacity, then, month by month, its load in hours and its load rate, ratio of the load to the capacity, with the signal of its zone.

Without load over the perimeter and the horizon chosen, the screen says so.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released.
- **Calculated on**, the date of calculation, then **Apply**. This view takes no period.
- **Organisation node and its descendants** restricts the load and the capacity to the roles that come under the node.
- **Horizon**: 6, 12 or 24 months, or **Default**, that of the server.
- **Under-load threshold**: 30 %, 50 % or 70 %, or **Default**, the one the server retains. A month whose load rate is under the threshold is signalled, as a month where it exceeds 100 %.

The chart:

- **Export as PNG** saves the chart as an image, with the perimeter, the horizon, the node and the date of calculation;
- **Values of the chart** unfolds the total of each month, as a table.

The horizon, the threshold and the organisation node live in the address of the view, and are kept from one consultation to the next, as the settings of a grid: a setting the address does not name finds the last one chosen again, and “Default” — “All nodes” for the node — removes it.

## Its columns and computed values

Every value is the server’s: the load of a role is the sum of the loads of the projects of the perimeter, the total of a month that of the roles, the capacity of the perimeter that of the roles retained. A rate the server cannot calculate says so, with its reason, and is never worth zero. The zones — overload, under-load — are read by their signal, never by the colour alone.

## Keyboard gestures

- `Tab` goes through the filters, the commands of the chart and its tables; a table wider than the window scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), [the cost structure](FBS-2.4.md), which breaks the labour down by node;
- [the workload of a project](FBS-4.4.4.md);
- the notion: [the remaining to commit and the updated estimate](notions/reste-a-engager.md).
