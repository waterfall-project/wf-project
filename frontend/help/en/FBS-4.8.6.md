# Milestone tracking

## What the screen shows

The **Time/time diagram**, under the cards of the [project indicators](FBS-4.8.md): how the planned dates of the milestones have slipped from one review to the next. Each marked revision is a point on the horizontal axis, at its date of marking; the date it planned for each milestone, a point on the vertical axis. The last point is that of the current day.

- A milestone whose date does not move draws a horizontal line; a milestone that slips rises, and the slope of its curve is the speed of its slipping.
- Completed, its curve stops by a point at its date of completion, on the diagonal of the **Equal dates**, and no revision marked afterwards adds a point to it.
- The revisions marked before the state In progress give no point.

Only the milestones entered in the time/time tracking appear there: a milestone is entered in it from the [planning grid](FBS-4.3.2.md), by **Time/time tracking**, in the submenu **Timelines** of the menu of its cell. Without a milestone entered, the screen says “No milestone is tracked.”

The tracking bears on the whole project, whatever its state: a subproject has no milestones. When the banner filters a subproject, the section says so.

## Its commands

- **Export as PNG** saves the diagram as an image, with the project, the revision and the date of calculation.
- **Values of the chart** unfolds its points as a table.

## Its columns and computed values

All the dates are the server’s. The table of the values gives, for each point, the **Milestone**, the **Revision of** — its date of marking —, the **Forecast date** and the date the milestone was **Completed on**, or **Not completed**.

## Keyboard gestures

- `Tab` reaches **Export as PNG** and **Values of the chart**; the table, wider than the window, scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project indicators](FBS-4.8.md), [the schedule performance index](FBS-4.8.5.md);
- [the planning grid](FBS-4.3.2.md), where the milestones are entered in the tracking, and [the project control health](FBS-2.7.md), which signals a contractual milestone overdue;
- the notion: [the revisions](notions/revisions.md).
