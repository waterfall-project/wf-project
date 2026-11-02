# Cost and schedule indices

## What the glossary says

> **Cost index** — Designates the indicator that relates the earned value to the actual cost: below 1, the work done cost more than promised.

> **Schedule index** — Designates the indicator that relates the earned value to the planned value: below 1, less work has been done than planned at that date.

> **Cost variance** — Designates the difference between the earned value and the actual cost at a given date. Negative, the work done cost more than promised.

> **Schedule variance** — Designates the difference between the earned value and the planned value at a given date. Negative, less work has been done than planned.

> **Alert thresholds** — Designate the two values, watch and alert, below which a cost or schedule index changes zone. They are defined in the reference data.

## In Waterfall

The indices and the variances are read on the screen of the indicators of the project, at their date of calculation: on the current day in the current revision, or at the date of marking for the kept indicators of a marked revision. All start from the [earned value](valeur-acquise.md): the cost index compares it to the actual cost, the schedule index to the [planned value](valeur-planifiee.md).

An index equal to 1 says that the project keeps its promise; below, it drifts. Each index changes zone under the watch and alert thresholds of the reference data, which the screen shows by a signal, its text and its icon, never by the colour alone. An index that cannot be calculated says so, with the reason the server gives.

## See also

- [The earned value](valeur-acquise.md), [the planned value](valeur-planifiee.md), [the reference budget](budget-de-reference.md), [the revisions](revisions.md).
