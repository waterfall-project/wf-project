# Access role management

## What the screen shows

The access roles of the installation, outside any project, and the permissions each one gives. A role is predefined — delivered with the installation — or composed by an administrator; an account holds none, one or several roles, and has its permissions from their union. A permission says what an account may do, never on which project.

From top to bottom: the table of the roles, each with its kind and the number of accounts that hold it, which the server sorts, searches and filters; then the matrix **Permissions by function**: a row per permission of the catalogue, filed under the name of the function it covers, and a column per role the table keeps, in its order, each box saying whether the role holds the permission. No screen creates a permission: the catalogue is that of the installation.

## Its commands

These commands are offered only to whoever may modify the roles; to the others, the screen is read only.

- **New role** and **Create a role**, at the top of the table, create a role made of its label alone, without a permission: its permissions are then checked in the matrix. A label left empty is refused at its field.
- The label of a role is entered in its cell, which renames it.
- **Delete**, once confirmed, deletes the role; nothing restores it, and a role created again under the same label is never predefined. Unavailable while an account holds the role: the command says how many.
- In the matrix, each box is a checkbox: checked or unchecked, it saves the permissions of the role at once. The other boxes of the role wait for the answer of the server; a refusal is said above the matrix, and the box takes back its former state.

Above the table, for all:

- **Kind** keeps the predefined roles or the composed roles; **Holding accounts**, between two bounds, the roles by the number of their holders; for the creation and the last modification, a period and an author.
- The search field keeps the roles whose label contains the text entered.
- **Columns** chooses the columns shown.

The matrix follows the table: a filter or a search that leaves out a role removes its column too.

## Its columns and computed values

The number of holding accounts is the one the server counts; nothing is computed here. The footer of the table says how many roles it holds.

## Keyboard gestures

- The table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row.
- `Enter` or `F2` enters a label, `Esc` abandons the entry; `Enter` on **Delete** presses the command.
- On a header, `Enter` or `Space` sorts the table by the column; `Shift` and the arrows widen or narrow the column.
- In the matrix, `Tab` goes from one box to the next, `Space` checks or unchecks.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [User management](FBS-1.1.md), where the roles are given to the accounts;
- [the audit log](FBS-1.5.md), which writes each creation, modification and deletion of a role.
