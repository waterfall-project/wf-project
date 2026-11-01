# Project workload

## What the screen shows

A leaf of the [costing](FBS-4.4.md), which the screen of the estimate opens in the same context: the estimate translated into a need of resources — how many hours, of which role, which month. It is the view the manager then consolidates over several projects, in the [aggregated workload](FBS-2.2.md).

The **Load by role and by month**: a bar per month, stacked by resource role, the total of the month at its top; the legend names the roles, and the tooltip of a month lists them with their hours. Only the labour lines load. The load of a line is spread over the duration of its task, pro rata to the worked hours of the calendar of its role. On a basis of remaining to commit, the remaining load of a task not completed is spread over the part of its duration alone that follows the date of calculation, and is carried to the month of the date of calculation when the finish of the task is passed.

Under the choice, the basis and the revision the server says it read.

## Its commands

At the top of the plan, then **Show**:

- **Basis**: **Budget of the reference revision**, **Remaining of a marked revision** or **Remaining of the current revision**. Only the bases the project admits are offered: without a reference revision, the current revision alone; the marked revisions, when the project has one.
- **Marked revision**, for the basis of a marked revision: each of those of the project.
- **Organisation node and its descendants** restricts the plan to the roles that come under it; **All nodes** lifts it.

A basis the server refuses — a project without a reference revision, a marked revision that is missing or is not marked — is said unavailable, with its reason, and the rest of the screen is shown.

On the chart:

- **Values of the chart**, under the chart, unfolds the table of its values;
- **Export as PNG** saves the chart, with the project, the revision, the basis, the node and the date of calculation.

## Its columns and computed values

Every figure is the server’s: the hours of each role and the total of each month. The table of the values gives, for each role and each month, the **Load (h)**, the **Capacity (h per month)** of the role and the **Zone** of the month: on alert when the load exceeds the capacity, nominal otherwise, said by its signal and never by the colour alone. A role without load appears there too. The plan of a project presents no load rate — the capacity is that of the whole installation — and does not draw the capacity: the load rate is that of the aggregated plan.

## Keyboard gestures

- `Tab` goes through the choice of the basis, of the revision and of the node, **Show**, then the commands of the chart; `Enter` on **Values of the chart** unfolds or folds the table.
- The table of the values, when it overflows its box, scrolls with the arrows once reached.
- `F1` opens this help.

## See also

- [Costing and estimate](FBS-4.4.md), whose labour lines make the load, and [the remaining to commit](FBS-4.5.md);
- [the aggregated workload](FBS-2.2.md) and [the resource roles](FBS-3.2.2.md), which bear the capacity;
- the notions: [the reference budget](notions/budget-de-reference.md), [the remaining to commit](notions/reste-a-engager.md).
