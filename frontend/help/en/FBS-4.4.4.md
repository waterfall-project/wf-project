# Project workload

## What the screen shows

A leaf of the [costing](FBS-4.4.md), which the screen of the estimate opens in the same context: the estimate translated into a need of resources — how many hours, of which role, which month. It is the view the manager then consolidates over several projects, in the [aggregated workload](FBS-2.2.md).

The **Load by role and by month**: a bar per month, stacked by resource role, the total of the month at its top; the legend names the roles, and the tooltip of a month lists them with their hours. The roles are told apart by their colour; the **Series patterns** preference of “My account” gives each a pattern besides, which the legend and the exported image bear too. Only the labour lines load. The load of a line is spread over the duration of its task, pro rata to the worked hours of the calendar of its role. On a basis of remaining to commit, the remaining load of a task not completed is spread over the part of its duration alone that follows the date of calculation, and is carried to the month of the date of calculation when the finish of the task is passed.

Under the choice, the basis and the revision the server says it read. The service computes the whole plan — the load of each role and month, the capacity of each role, the totals without gaps and the zone — from the estimate of the revision; the screen only shows it. A task already finished carries no load on the remaining of a revision.

Under the chart, the **Detail by role and by task**: a grid from the role to the task, read only, a column for each month of the plan. Under each role, each of the tasks that bear one of its labour lines, ordered by start date, then in the order of the planning; two lines of the role under the same task make one row there. The detail has no setting of its own: it is computed on the basis and under the organisation node chosen for the chart. The label of a task leads to its row in the planning grid of the revision the basis reads — the current revision, the reference or the marked revision chosen —, which unfolds its summaries and sets the cursor on it. Without the right to read the planning, the task is named without a link.

## Its commands

At the top of the plan, then **Show**:

- **Basis**: **Budget of the reference revision**, **Remaining of a marked revision** or **Remaining of the current revision**. Only the bases the project admits are offered: the budget of the reference when the project has a reference revision, the remaining of a marked revision when it has one, the current revision always — alone, with neither.
- **Marked revision**, for the basis of a marked revision: each of those of the project.
- **Organisation node and its descendants** restricts the plan to the roles that come under it; **All nodes** lifts it.

A basis the server refuses — a project without a reference revision, a marked revision that is missing or is not marked — is said unavailable, with its reason, and the rest of the screen is shown.

On the chart:

- **Values of the chart**, under the chart, unfolds the table of its values;
- **Export as PNG** saves the chart, with the project, the revision, the basis, the node and the date of calculation.

In the detail, the bar of the grid offers **Columns** and **Tree**, which folds or unfolds the roles; the button of the label of a role folds or unfolds its tasks.

## Its columns and computed values

Every figure is the server’s: the hours of each role and the total of each month. The table of the values gives, for each role and each month, the **Load (h)**, the **Capacity (h per month)** of the role and the **Zone** of the month: on alert when the load exceeds the capacity, nominal otherwise, said by its signal and never by the colour alone. A role without load appears there too. The plan of a project presents no load rate — the capacity is that of the whole installation — and does not draw the capacity: the load rate is that of the aggregated plan.

The detail sums nothing: the load of a month of a role is the chart’s, that of a task the part the server gives it, and a month without load stays blank. The hours of a task are the sum the server computes; those of a role are not repeated. At the foot, the total of each month is the plan’s.

## Keyboard gestures

- `Tab` goes through the choice of the basis, of the revision and of the node, **Show**, then the commands of the chart; `Enter` on **Values of the chart** unfolds or folds the table.
- The table of the values, when it overflows its box, scrolls with the arrows once reached.
- The grid of the detail is a single `Tab` stop: the arrows move the active cell, `Enter` on the label of a task follows its link to the planning grid; `Alt` and `-` folds a role, `Alt` and `+` unfolds it.
- `F1` opens this help.

## See also

- [Costing and estimate](FBS-4.4.md), whose labour lines make the load, [the planning](FBS-4.3.md), where a task of the detail leads, and [the remaining to commit](FBS-4.5.md);
- [the aggregated workload](FBS-2.2.md) and [the resource roles](FBS-3.2.2.md), which bear the capacity;
- the notions: [the reference budget](notions/budget-de-reference.md), [the remaining to commit](notions/reste-a-engager.md).
