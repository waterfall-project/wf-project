# Project indicators

## What the screen shows

What all the rest exists for: relating the [reference budget](notions/budget-de-reference.md), the [planned value](notions/valeur-planifiee.md), the [earned value](notions/valeur-acquise.md) and the actual cost, with the [remaining to commit](notions/reste-a-engager.md) of the project manager. Everything there is calculated by the server, for the revision read and at a date: that of the marking for a [marked revision](notions/revisions.md), whose indicators and curves are kept as they were, the current day for the current revision.

From top to bottom:

- five cards, each with its date of calculation: the [financial progress](FBS-4.8.1.md), the [projection at completion](FBS-4.8.2.md), the [physical progress](FBS-4.8.3.md), the [cost performance index](FBS-4.8.4.md) and the [schedule performance index](FBS-4.8.5.md), these last two with the evolution of their index;
- the [milestone tracking](FBS-4.8.6.md), the time/time diagram;
- the [cumulative costs](FBS-4.8.7.md), the S-curve;
- the [earned value curves](FBS-4.8.8.md).

The indicators are calculated only from the state In progress on: before, the screen says “Indicators unavailable”, without cards nor curves, and only the milestone tracking remains; only the indicators of the [estimate](FBS-4.4.1.md) exist then.

The banner says the reading context and its filters. A subproject filtered restricts the whole screen except the milestone tracking, which bears on the whole project: a subproject has no milestones; the banner says so on the filter. A subproject the project does not have is refused: “Indicators unavailable”. A date of calculation filtered shows the indicators and the curves of the last revision marked on that date or before, as they were kept at its marking; the banner names this **Revision of the calculation** when it is not that of the address. The evolution of the indices is always calculated up to the current day, its last point on the current revision, or, on a project that has none, on its last marked revision with the actual cost of the day, without the kept indices of the latter changing: when it is not the revision of the indicators, the screen says so at the top, “Computed on another revision”.

## Its commands

- In the banner, each filter is lifted by its link, **Remove the filter**.
- **Shift by the payment delays**, above the cumulative costs, presents them as cash-out; **Remove the shift by the payment delays** brings them back. The shift is kept in the address.
- **Export as PNG** saves the time/time diagram, the S-curve or the earned value curves as an image, with the project, the revision and the date of calculation; when the screen filters a subproject, the image names it, or says, for the milestone tracking, that it bears on the whole project.
- **Values of the chart** unfolds, under each chart, its values as a table.

## Its columns and computed values

All the values are calculated by the server; the front recalculates, sums or shifts none of them. An indicator one quantity of which is zero in the denominator is said **Not computable**, with its reason, never zero nor infinite. Everything monetary is calculated for the project and for each of its subprojects, the set “No subproject” included. A zone is read by its signal, its text and its icon, never by the colour alone.

The curves show jumps, which are read as such: the reference budget changes at each [amendment](notions/avenant-et-differentiel.md), and at nothing else.

## Keyboard gestures

- `Tab` goes through the filters of the banner, the commands, the charts and their values; a table of values wider than the window scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The estimate](FBS-4.4.md), [the remaining to commit](FBS-4.5.md), [the actual costs](FBS-4.7.md), where the quantities come from;
- [the indicator settings](FBS-3.4.md), where the thresholds of the zones are set, and [the portfolio performance](FBS-2.3.md);
- the notions: [the earned value](notions/valeur-acquise.md), [the planned value](notions/valeur-planifiee.md), [the indices](notions/indices.md), [the reference budget](notions/budget-de-reference.md), [the revisions](notions/revisions.md).
