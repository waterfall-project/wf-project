# Critical path and total float

## What the glossary says

> **Critical path** — Designates the set of the tasks in automatic mode whose total float is zero or negative: any delay on one of them delays the end of the project, or a date imposed by a task in manual mode.

> **Total float** — Designates, for a task in automatic mode, the difference between its late date and its early date: the delay it may take without delaying the end of the project nor a date imposed by a task in manual mode. It is negative when the task cannot satisfy a link that ties it to a manual task.

> **Link** — Designates the relation between a predecessor task and a successor task. It bears a type — finish to start, start to start, finish to finish, start to finish — and a lag.

> **Predecessor** — Designates the task whose execution conditions the start or the finish of another task, called successor, through a link.

## In Waterfall

The server calculates, for each task in automatic mode, its early and late dates, and the float that separates them; the front calculates nothing. A task in manual mode is an imposed date: it bounds the floats of its predecessors and of its successors, and bears none. A predecessor that cannot satisfy its link with a manual task bears a negative float, and the conflict is signalled.

A summary task bears the smallest float of those of its subordinates that bear one, and belongs to the critical path as soon as one of them is on it.

In the [planning grid](../FBS-4.3.2.md), the column “Float” gives the total float, in bold on the critical path, and a critical task bears the icon “Critical path”. In the [Gantt](../FBS-4.3.3.md), its bar is solid, hollow elsewhere, and its name says “critical”: nothing is read by the colour alone.

## See also

- [The planning](../FBS-4.3.md), [the planning grid](../FBS-4.3.2.md), [the Gantt](../FBS-4.3.3.md);
- [the work breakdown](lotissement.md), whose skeleton sets the first links.
