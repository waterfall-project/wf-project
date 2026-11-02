# Project settings

## What the screen shows

What a project bears of its own, outside its revisions. A project bears few settings, and none is blocking: the work breakdown has a default value, the inflation rate is worth zero, the codes come from the ERP when the order arrives. This is what allows a project to be created and costing to start without anything decided.

Under the title, the state of the project. Then, from top to bottom:

- the **Project settings**: its label, its code, its client, the date of receipt of its order, its description, its [inflation rate](FBS-4.2.2.md) and its [probability of winning](FBS-4.2.5.md); a value that is missing reads “Not set”;
- the [work breakdown](FBS-4.2.1.md): the work packages, the order items and the deliverables of the order, in a tree;
- the [subprojects](FBS-4.2.3.md), each by the code the ERP gives it;
- the [contributors](FBS-4.2.4.md), who work on this business, each with their capacity.

Each list keeps its own search, its filters and its sort, which the server applies, and its settings of columns. A list says it is empty only when nothing restricts it: a search or a filter that keeps nothing keeps its grid, to be changed.

## Its commands

The settings of the project are those of its project managers: each command follows what the project offers, available or naming the condition it lacks. A terminal project offers none.

- **Edit the project** opens the form of the settings: the label, the project code, the client, the description, the date of receipt of the order, the inflation rate and the probability of winning, these last two in percent. The probability of winning is no longer modified from the state In progress on: the field is then shown frozen, with its condition. A code another project bears is refused at its field; a rate outside its bounds too, with the bound.
- The commands of the work breakdown, of the subprojects and of the contributors are described in the help of each list.
- **Generate the planning**, under the work breakdown, when the main structure of the current revision has no task yet: a summary task per work package and per order item, a task per deliverable and their end milestones. Generated, the screen leads to the planning grid.

While a write is under way, the command that would open its form again waits, inactive, “Saving in progress…”: the form opens again on the version the answer brings. If the project has changed since its reading, the refusal offers to read the page again.

## Its columns and computed values

Nothing is computed here: the lists show what the server holds, in the order it gives. The definitions of the columns of the three lists follow.

## Keyboard gestures

- Each list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` on a command of a cell presses it; `Shift+F10` or the Menu key opens the menu of a cell of the work breakdown.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- In the work breakdown, `Alt` and `-` folds the row, `Alt` and `+` unfolds it, `Alt` and `*` unfolds everything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The work breakdown](FBS-4.2.1.md), [the inflation rate](FBS-4.2.2.md), [the subprojects](FBS-4.2.3.md), [the contributors](FBS-4.2.4.md), [the probability of winning](FBS-4.2.5.md);
- [the page of the project and the list of the projects](FBS-4.md), [the project lifecycle](FBS-4.9.md);
- the notion: [the work breakdown](notions/lotissement.md).
