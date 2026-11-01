# Inflation rate

## What the screen shows

The **Annual inflation rate** of the project, among the settings of the project, on the screen of the [settings of the project](FBS-4.2.md). The costing uses only the hourly rates of the reference year of the revision; the inflation rate is the hypothesis that projects them onto the following years, whose rates are not known yet.

It is worth 0 % by default and is modified at any time, as long as the project is not terminal. Its modification touches no marked revision, whose reference budget is frozen: it applies to the current revision, for the lines whose year of consumption follows the reference year.

## Its commands

- **Edit the project** opens the form of the settings, where the field **Annual inflation rate (%)** is entered in percent: “3” for 3 %. The server keeps it between 0 and 100 %; a rate outside these bounds is refused at its field, with the bound. The command is that of the project managers, and a terminal project does not offer it.

## Its columns and computed values

The rate is shown as the server holds it, in percent. In the estimate, the **Re-estimated amount** of a line depends on it: it is the amount of the reference year projected onto the year of consumption of the line, at this rate; the tooltip of the column names the reference year and the rate of the revision when the screen knows them.

## Keyboard gestures

- `Tab` reaches **Edit the project**; in the form, `Tab` goes through the fields and `Enter` saves.
- `Esc` closes the form without saving anything.
- `F1` opens this help.

## See also

- [The settings of the project](FBS-4.2.md);
- [the estimate](FBS-4.4.md) and [the amount at the reference year](FBS-4.4.3.md);
- [the hourly rates](FBS-3.1.2.md) of the reference data;
- the notion: [the reference budget](notions/budget-de-reference.md).
