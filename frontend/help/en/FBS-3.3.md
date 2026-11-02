# Risk settings

## What the screen shows

The risk matrix of the installation, common to all the projects, outside any project. Two tables:

- **Bounds of the risk matrix**: on the axis of the probability, three bounds in percent; on that of the severity, three bounds in percent of the base of the project — its reference budget or, as long as it has none, the total without provisions of the estimate of its current revision. The three bounds of an axis delimit four levels on it; a value equal to a bound comes under the upper level.
- **Zones of the risk matrix**: the sixteen cells, a row per level of probability, from the highest to the lowest, a column per level of severity, each cell with its zone — **Nominal**, **Watch** or **Alert**.

A revision does not keep these settings: a marked revision is always read with their current values, and only the zone that qualifies a risk may change through them.

## Its commands

**Modify the risk matrix**, offered to whoever may modify the risk settings, opens the form: the three bounds of each axis, in percent, strictly increasing, and the zone of each of the sixteen cells. A bound that is not above the previous one is signalled at its field before the sending; the server judges the rest. If the settings have changed since their reading, the refusal offers to read the page again. To the others, the screen is read only.

## Its columns and computed values

Nothing is computed: bounds and zones are those the server holds. A zone is read by its signal and its name, never by the colour alone.

## Keyboard gestures

- `Tab` goes through the command, then, in the form, the bounds and the zones, row by row; `Esc` closes the form without saving anything.
- `F1` opens this help.

## See also

- [Risk management](FBS-4.6.md), whose matrix places each risk, and [the portfolio risks](FBS-2.5.md);
- the notion: [the provision and the reserve](notions/provision-et-reserve.md).
