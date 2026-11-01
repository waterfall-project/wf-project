# Kanban — task start

## What the screen shows

A leaf of the [estimate to complete](FBS-4.5.md), reached from its header, in the same context: the view through which the project manager declares that a task has begun. This gesture has no other effect than exposing the lines of the task to the re-estimation, in the remaining to commit grid of the same revision; a task that bears lines may also be re-estimated there even before it starts, by **Enter the remaining to commit**. A task is started or it is not: no percentage is shown nor entered.

Three columns, in the order the server gives: **Not started**, **Started**, **Completed**. Each task of the main structure of the current revision is a card: its row number and its label, its finish, and **Finish overdue** when it precedes the date of calculation; completed, the date it was completed on. A milestone not started all of whose predecessors are completed bears “milestone to complete”, by a text and an icon, to invite completing it: nothing completes by itself.

The Kanban reads the draft revision, whatever the revision of the context: on a marked revision, which has no task to start, it says so and shows nothing.

## Its commands

Each card makes the gestures its task offers, and only those, through its menu, by dragging it to a column, or with the keyboard:

- **Start** a task not started that is not a milestone: a milestone never starts. The predecessors are not a condition of it.
- **Complete** a task that bears no line apart from provision: a milestone, even not started — it then takes for start date that of its completion —, or a started task. A task not started that is not a milestone is not completed directly (“the task is a milestone”).
- **Reopen** a completed task: it becomes started again; a milestone becomes not started again, its dates erased.
- **Enter the remaining to commit**, on a task not completed that bears a line apart from provision, leads to the grid of the remaining to commit on this task: it is there that it is completed, by a zero remaining to commit on all its lines.

Starting and completing ask for the **Date of the event**, that of the day by default; a single date is asked at a time. All the gestures ask for a project In progress and no background process running on the revision. An unavailable gesture says its condition on the card, as does a gesture that no rule leads to the column aimed at; a refusal of the server is said on the card.

## Its columns and computed values

The columns are the states of the task, as the server gives them: the screen deduces no gesture from the nature of a task nor from its lines. The finish and the mark of finish overdue are the server’s. A card moved says “Updating…” while the tasks are read again; if the reading again ends without its answer, it says **Not up to date**, and **Retry** reads its tasks again.

## Keyboard gestures

- The arrows choose a card, from one card to the next and from one column to the next.
- `Enter` opens the menu of the gestures of the card chosen.
- `Shift+→` and `Shift+←` move it to the neighbouring column, as the drag does; the focus follows it in its new column.
- On a Mac, `⇧` stands for `Shift`.
- `F1` opens this help.

## See also

- [The estimate to complete](FBS-4.5.md) and [the remaining to commit grid](FBS-4.5.2.md), where the lines of the tasks are re-estimated, started or not;
- [the planning grid](FBS-4.3.2.md), where the dates of start and of completion are read;
- the notion: [the remaining to commit](notions/reste-a-engager.md).
