# Schedule performance index (SPI)

## What the screen shows

The card of the schedule index, among the [project indicators](FBS-4.8.md), with its date of calculation:

- **Schedule index**: the [earned value](notions/valeur-acquise.md) over the [planned value](notions/valeur-planifiee.md) at the same date, with its zone — nominal, watch or alert — according to the thresholds of the reference data. Below 1, less work has been done than the reference planned at that date. Not computable as long as the planned value is zero, in particular before the start of the first task of the reference that bears a budgeted line.
- **Schedule variance**: the earned value minus the planned value, negative when late, positive when ahead; then the **Earned value** and the **Planned value**.
- **Evolution of the schedule index**: a curve for the project and one for each of its meshes — each subproject, and the set “No subproject” —, or for the subproject alone the banner filters. A point per revision marked from the state In progress on, at its date of marking, and the last on the current day; the **Watch threshold** and the **Alert threshold** are drawn across.

The planned value is read on the dates of the reference revision, the earned value on the actual dates of completion: the index measures a delay without any date of the current revision coming in.

## Its commands

**Values of the chart** unfolds the evolution as a table. This chart is not exported.

## Its columns and computed values

All the values are calculated by the server, the zone included: the server ranks it at the reading according to the current thresholds of the [indicator settings](FBS-3.4.md), so that the zone of a kept index may change with the thresholds, never its value. The table of the values gives, for each point, the **Scope**, the **Revision**, the **Date**, the **Index** and the **Zone**; a point not computable leaves a gap in its curve, and its row says why.

The evolution is always calculated up to the current day, its last point on the current revision, or, on a project that has none, on its last marked revision with the actual cost of the day, its kept points unchanged; when the indicators are on another revision, the screen says so at the top.

## Keyboard gestures

- `Tab` reaches **Values of the chart**; the table, wider than the window, scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project indicators](FBS-4.8.md), [the cost performance index](FBS-4.8.4.md), [the milestone tracking](FBS-4.8.6.md);
- [the indicator settings](FBS-3.4.md), where the thresholds are set;
- the notions: [the indices](notions/indices.md), [the planned value](notions/valeur-planifiee.md), [the earned value](notions/valeur-acquise.md).
