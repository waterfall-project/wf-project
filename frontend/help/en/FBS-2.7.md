# Project control health

## What the screen shows

The signals that say a project in progress of the perimeter is no longer kept in hand. Under the title, the perimeter retained and the date of calculation. A table, **Project control health signals**, gives for each signal its project, what it signals and its zone:

- **Periodic review overdue**: the last marked revision of the project is older than the maximum delay between two reviews that the reference data sets; the signal says for how many weeks.
- **Risks not reviewed**: identified risks have not been reviewed since the last marked revision.
- **No actual cost since the last review**: no actual cost has been imported since the last marked revision.
- **Contractual milestone overdue**: a milestone entered in the time/time tracking has passed its reference date without being completed; the signal names the milestone and its date.

Without a signal, the screen says that the control of the projects of the perimeter is kept in hand.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released. The signals bear only on the projects in progress.
- **Calculated on**, the date of calculation, then **Apply**. This view takes neither a period nor an organisation node.

The name of a project opens it, when you may consult it.

## Its columns and computed values

The signals and their zones are the server’s; the table is neither sorted nor filtered. The zone is read by its signal, never by the colour alone.

## Keyboard gestures

- `Tab` goes through the filters and the links of the projects; `Enter` on the name of a project opens it.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), [the portfolio risks](FBS-2.5.md);
- [revision management](FBS-4.1.md), where the review is marked, and [the timelines](FBS-4.3.1.md), which bear the time/time tracking of the milestones;
- [the indicator settings](FBS-3.4.md), where the maximum delay between two reviews is set;
- the notion: [the revisions](notions/revisions.md).
