# Financial progress

## What the screen shows

The first card of the [project indicators](FBS-4.8.md), with its date of calculation: where the expense stands compared to what it will end up being.

- **Financial progress**: the actual cost over the sum of the actual cost and of the [remaining to commit](notions/reste-a-engager.md), in percent. Not computable when the actual cost and the remaining to commit are both zero.
- **Budget consumption**: the same actual cost over the [reference budget](notions/budget-de-reference.md), in percent.
- The quantities they are deduced from: **Actual cost**, **Remaining to commit** and **Reference budget**.

The two percentages are read together: they say whether one spends fast, and whether one spends too much. A financial progress of 50 % with a consumption of 70 % announces an overrun of 40 %. It is the only indicator that does not depend on the earned value.

## Its commands

The card has no command: it is read, for the project or for the subproject the banner filters.

## Its columns and computed values

All the values are calculated by the server. The actual cost is that of the lines of the tracked scope whose document date precedes the date of calculation or equals it; a line excluded from the [actual costs](FBS-4.7.md) does not enter the calculation of the day. The kept indicators of a marked revision keep the lines known at its marking, with the amount and the scope they had then: a line imported, updated or excluded afterwards does not change them. A value not computable says so, with its reason, and is never worth zero.

## Keyboard gestures

The cards are read in the order of the page, before the charts.

## See also

- [The project indicators](FBS-4.8.md) and [the projection at completion](FBS-4.8.2.md), which starts from the same quantities;
- [the remaining to commit](FBS-4.5.md), [the actual costs](FBS-4.7.md);
- the notions: [the remaining to commit](notions/reste-a-engager.md), [the reference budget](notions/budget-de-reference.md).
