# Cost performance index (CPI)

## What the screen shows

The card of the cost index, among the [project indicators](FBS-4.8.md), with its date of calculation:

- **Cost index**: the [earned value](notions/valeur-acquise.md) over the actual cost, with its zone — nominal, watch or alert — according to the thresholds of the reference data. Below 1, the work done cost more than promised. Not computable as long as the actual cost is zero, before the first import of actual costs.
- **Cost variance**: the earned value minus the actual cost, negative when the work done cost more than its budget; then the **Earned value** and the **Actual cost**.
- **Evolution of the cost index**: a curve for the project and one for each of its meshes — each subproject, and the set “No subproject” —, or for the subproject alone the banner filters. A point per revision marked from the state In progress on, at its date of marking, and the last on the current day; the **Watch threshold** and the **Alert threshold** are drawn across.

An index is read only with its trend: 0.9 rising and 0.9 falling do not ask for the same decision.

## Its commands

**Values of the chart** unfolds the evolution as a table. This chart is not exported.

## Its columns and computed values

All the values are calculated by the server, the zone included: the server ranks it at the reading according to the current thresholds of the [indicator settings](FBS-3.4.md), so that the zone of a kept index may change with the thresholds, never its value. The table of the values gives, for each point, the **Scope**, the **Revision**, the **Date**, the **Index** and the **Zone**; a point not computable leaves a gap in its curve, and its row says why.

The evolution is always calculated up to the current day, its last point on the current revision, or, on a project that has none, on its last marked revision with the actual cost of the day, its kept points unchanged; when the indicators are on another revision, the screen says so at the top.

## Keyboard gestures

- `Tab` reaches **Values of the chart**; the table, wider than the window, scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project indicators](FBS-4.8.md), [the schedule performance index](FBS-4.8.5.md), [the projection at completion](FBS-4.8.2.md);
- [the indicator settings](FBS-3.4.md), where the thresholds are set;
- the notions: [the indices](notions/indices.md), [the earned value](notions/valeur-acquise.md).
