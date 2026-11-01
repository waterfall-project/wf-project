# Indicator settings

## What the screen shows

The settings of the indicators of the installation, common to all the projects, outside any project:

- **Alert thresholds of the indices**: for the cost index and for the schedule index, a **Watch threshold** and an **Alert threshold**, values of the index below 1. An index greater than or equal to the watch threshold is nominal; under it and at least equal to the alert threshold, on watch; under the alert threshold, on alert.
- **Pace of the reviews**: the maximum delay expected, in weeks, between two marked revisions of a project in progress. A project whose last marked revision is older is signalled by the project control health.

A revision does not keep these settings: a marked revision is always read with their current values. Its indicators kept do not change; only the zone that qualifies them may change.

## Its commands

**Modify the thresholds and the delay**, offered to whoever may modify the indicator settings, opens the form: each threshold between 0 and 1, excluded, the alert threshold under the watch threshold of its index, and the delay in whole weeks. An alert threshold that is not under the watch threshold is signalled at its field before the sending; the server judges the rest. If the settings have changed since their reading, the refusal offers to read the page again. To the others, the screen is read only.

## Its columns and computed values

Nothing is computed here: the thresholds and the delay are those the server holds, which ranks each index in its zone.

## Keyboard gestures

- `Tab` goes through the command, then, in the form, the thresholds and the delay; `Esc` closes the form without saving anything.
- `F1` opens this help.

## See also

- [The project control health](FBS-2.7.md), which signals the reviews overdue, and [the portfolio performance](FBS-2.3.md);
- the notion: [the cost and schedule indices](notions/indices.md).
