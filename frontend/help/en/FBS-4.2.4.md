# Contributors

## What the screen shows

A list of the [settings of the project](FBS-4.2.md): who takes part in this business, each with their capacity — **Project manager** or **Contributor** — and the state of their account. A multi-trade business comes under no department: the project manager structures it, the managers of the trades cost its effort. The list changes with each business, unlike the organisation tree.

It does not replace the access rights: an access role says what a user has the right to do, the list says on which projects they do it. The consultation and the entry of a project are reserved to its contributors, each under its permission, and its settings to its project managers; the permission to consult all the projects opens the others to reading. The creator of a project is its first project manager, and a non-terminal project always keeps at least one, with an active account. A single exception to the reservation of the project managers: when none of them has an active account any more, whoever holds the settings of the projects and the permission to consult all the projects may, without being a contributor, modify the list to inscribe a project manager with an active account in it — nothing else is opened to them.

## Its commands

- **Modify the contributors**, offered to the project managers as long as the project is not terminal — and, in the exception above, to whoever comes to inscribe a project manager —, opens the list in a dialog. There the capacity of a contributor is changed, a contributor is withdrawn (**Withdraw**), and one inscribes, one by one (**Inscribe**), the **Proposed contributors**: the accounts of the departments whose resource roles are used by the lines of the estimate, each with its organisation node and the roles that propose it. Nothing proposed is applied without you; nothing is written before **Save**, which writes the whole list. Under the command, a sentence names the accounts proposed that await your confirmation.
- A list without a project manager with an active account is refused before any sending. A contributor whose account has been deactivated since their inscription stays in the list, as is; only the inscription of a deactivated account or the change of its capacity are refused, at its row, as an account the installation does not have; if the list has changed since its reading, the refusal offers to read the page again.

Above the list, for all: **Filter by capacity** and **Account state** — **Active accounts** or **Deactivated accounts** — keep contributors, **Every capacity** and **Every account** lift the filters; the search field keeps the contributors whose name contains the text entered; **Columns**.

While a saving is under way, **Modify the contributors** waits for its answer, to open the list again on the version it brings.

## Its columns and computed values

Nothing is computed: each column is sorted by the server. A project manager is marked by an icon beside their capacity; an anonymised account keeps the name the server gives it.

## Keyboard gestures

- The list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- In the dialog, `Tab` goes through the capacities, the withdrawals, the proposals and the commands; `Esc` closes it without saving anything.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The settings of the project](FBS-4.2.md);
- [user management](FBS-1.1.md) and [the access roles](FBS-1.2.md);
- [the resource roles](FBS-3.2.2.md), whose use in the estimate founds the proposals.
