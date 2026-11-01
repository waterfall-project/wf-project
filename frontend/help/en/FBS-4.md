# Projects

## What the screen shows

The home page of Waterfall: the list of the projects, from which each one opens. A project bears all that is done in it, from its creation to its closing — its revisions, its settings, its planning, its estimate, its remaining to commit, its risks, its actual costs, its indicators. What is modified in it depends on its state: a marked revision no longer moves, a terminal project neither.

The list opens on the projects you are a contributor to, in the state **Pricing** or **In progress**: two filters that the screen states, above the list, as long as they apply. The server filters, sorts, searches and pages; the footer of the list says how many projects it keeps. Above, when the common reference data does not yet have the minimum a project asks for, the box **Incomplete reference data** names what is missing: no project is created before.

**The page of a project**, which its label opens, opens this help too. Under the banner of its reading context, it says what the project is — its code, its state, the date of receipt of its order, its description — and lists its revisions, each a link that opens it in the same context. A project without a revision says so and leads, for whoever may read them, to [revision management](FBS-4.1.md); it then also offers its imports, since an import of planning, of estimate or of remaining to commit creates the revision it applies to — an import of actual costs, for its part, writes in no revision. As long as the main structure of the current revision has no task, the box **Start the project** offers to launch the planning.

## Its commands

At the top of the list:

- **Create a project**, offered to whoever has the permission, opens the form: the **Label**, required, the **Project code**, which may wait for the order, the **Client** and the **Description**, optional. The project is born in the state Created, and you are its project manager. Unavailable as long as the reference data is incomplete. A code another project already bears is refused at its field.
- **Show all projects** lifts the filter “contributor”, for whoever may consult all the projects; **Show only my projects** puts it back. For the others, the filter stays, without a link: it does not restrict what they may read, it says what the list shows.

Above the list:

- **Filter by state**: a button per state, pressed when it is retained, and **Every state** to lift them. A choice of states other than the default one is kept in your preferences.
- **Modification period**, **From** and **To**, then **Filter**: an end that precedes the start is refused at its field, the list not read.
- The search field keeps the projects whose label or code contains the text entered.
- **Columns** chooses the columns shown; **Rows per page** and the links of the pages go through the list.

On the page of a project, the box **Start the project**, offered to whoever may modify the planning:

- **Automatic planning from the work breakdown** leads to the [work breakdown of the project](FBS-4.2.1.md), where the planning is generated once the work breakdown is entered;
- **Import an MS Project file** opens the drop zone of an .xml file: its report is shown on the page, and is applied or abandoned as in the [imports and exports](FBS-4.3.4.md);
- **Later** folds the box; **Start the project** unfolds it, as long as the structure stays empty.

## Its columns and computed values

Nothing is computed here: the list shows the projects as the server holds them. The date of modification is shown in the time of your workstation. The client of a project appears only on its settings, neither in the list nor in the portfolio.

## Keyboard gestures

- The list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on the label of a project opens it.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [Revision management](FBS-4.1.md), [the settings of the project](FBS-4.2.md), [the project lifecycle](FBS-4.9.md);
- [the project portfolio](FBS-2.1.md), which consolidates all the projects;
- the notions: [the revisions](notions/revisions.md), [the work breakdown](notions/lotissement.md).
