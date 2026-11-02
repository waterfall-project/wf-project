# Task tree

## What the screen shows

A leaf of the [planning](FBS-4.3.md), reached from the header of the planning, in the same reading context: the division of the business rather than its calendar, without a time axis nor links. It is the view one puts in a review file or shows to the client, where the Gantt serves to work.

Under a root node that stands for the project, the summary tasks of the main structure, each named by its number and its label: the first level side by side, each following level in a column under its parent, a layout designed for the A4 page in portrait. Neither the milestones nor the leaf tasks appear there: they come under the work to do, not the division. A planning without a summary task comes down to the node of the project, and the screen says so.

The tasks are read as the planning grid reads them, restricted to the subproject filtered. The tree is read only: nothing is entered there.

## Its commands

- **Level shown**: a link per level the structure counts, **Level 1**, **Level 2**… Beyond the level chosen, the subordinate tasks are not represented: it is what sets the bulk. A planning of several hundred tasks is not shown; its first three levels, yes.
- The image of the tree is exported from the [imports and exports](FBS-4.3.4.md), by **Task tree image**, at the level you give. It has the size its content demands, without pagination nor reduction.

## Its columns and computed values

No computed value: the numbers and the labels are those of the planning, as the server gives them, and the levels offered are those it says the structure counts.

## Keyboard gestures

- The tree is a single tab stop: `↑` and `↓` go through the tasks in their order, `←` leads to the parent, `→` to the first child, `Home` and `End` to the first and the last.
- Nothing is folded: the level chosen decides what is shown. No key changes a task.
- `Tab` reaches the links of the levels.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md) and [the planning grid](FBS-4.3.2.md), where the summary tasks are created;
- [the timelines](FBS-4.3.1.md), the other view meant to be shown;
- [the imports and exports](FBS-4.3.4.md), from which the image is exported.
