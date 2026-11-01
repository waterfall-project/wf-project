# Audit log

## What the screen shows

The audit log of the platform, outside any project: an entry per action that commits — the marking of a revision, the designation of the reference, the contractualisation of an amendment, the occurrence of a risk, the exit from the lifecycle, the exclusion or the reinstatement of a cost line, the application of an import, the life of the accounts and of the access roles, the backups and the restorations. Each one says its date, its author, its action and, under it, what it did — the fields modified, the state a project exited in and its reason, the backup restored, the kind of an import, the roles or permissions given and taken away, the former label —, the kind and the name of its object, its project and the correlation of the request that produced it.

A project without a code yet is named by its label alone, in the table as in the export. Each name is that of the moment of the action: an account deactivated since keeps its own, an anonymised account appears under a neutral label. The log is read only: nothing modifies nor deletes an entry. That of a project closed long ago is read as that of a project in progress, through the filter of the project.

The server sorts the log — by default, the most recent first —, searches it, filters it and pages it; under the title, the number of entries it keeps.

## Its commands

The log has no command that writes. To read it:

- **Period**, **From** and **Before**, to the minute and in the time of this workstation, then **Apply**: the start is included, the end excluded. An end that precedes the start is refused at its field.
- **Filter by kind of author** — an account or the platform — and **Author**, a given account.
- The actions, to check in their menu, one or several.
- **Project** and **Kind of object**.
- **Correlation**: the identifier of a request, letters, digits, “.”, “_” and “-”, 64 characters at most.
- The search field keeps the entries whose name of the object contains the text entered.
- **Columns** chooses the columns shown; **Rows per page**, **Previous page** and **Next page** go through the log.

The authors and the projects offered are those the whole log cites, even for whoever cannot read the accounts. In the table:

- The object and the project are links when the server says you may consult the project: the project; a revision; a risk, in the risks of its revision, its detail open; an import, in the imports and exports of its revision, its report shown; the differential of an amendment, in the cost structures of its revision. An account, a role, a backup or a cost line have no screen of their own: their name is read alone.
- **History of the object** filters the log on this object alone; **Lift** takes this filter off.
- The correlation leads to the entries of its request alone.

## Its columns and computed values

Nothing is computed there: each entry keeps what it wrote. What an action did is written in the language of the interface from what the entry keeps. The log is always sorted by one of its columns: a header goes from one direction to the other without lifting the sort, and that of the date puts the log back in its default order. The action and the kind are sorted in the order of their list, not in the alphabetical order of their words.

## Keyboard gestures

- The table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on a link — the object, the project, the history, the correlation — follows it.
- On a header, `Enter` or `Space` sorts the table by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [User management](FBS-1.1.md) and [access role management](FBS-1.2.md), each change of which the log writes;
- [backup and restore](FBS-1.4.md);
- [revision management](FBS-4.1.md), where the revisions are marked and the reference designated;
- the notion: [the revisions](notions/revisions.md).
