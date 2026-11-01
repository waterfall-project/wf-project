# User management

## What the screen shows

The accounts of the installation, outside any project: each account with its origin, the organisation node it is attached to, its access roles and its state. A deactivated account stays listed and can be reactivated; no screen deletes an account. The roles give the permissions, and the permission only says what an account may do: it is the list of the contributors of a project that says on which projects.

At the top, the report of the last reading of the accounts of the identity provider that succeeded, or the indication that none has succeeded yet: the accounts created — without a role —, updated, deactivated, the identities of local accounts restored in the provider, the local accounts that were removed from it, and what was left as it was, with its reason, under **Details of the last reading**.

Under this report, the **Reading schedule**: the platform reads the accounts of the identity provider by itself, every day by default, at the hour and, for a weekly reading, on the day set; the screen says whether the scheduled reading is active or suspended, its frequency, its day and its hour in universal time (UTC).

Then the table of the accounts, which the server sorts, searches, filters and pages; its footer says how many accounts it keeps.

## Its commands

These commands are offered only to whoever may modify the accounts; to the others, the screen is read only.

- **Read the accounts** asks for a new reading of the accounts of the identity provider. It runs as a background task: the panel of the tasks follows it and offers, at its end, to read the screen again, where its report appears.
- **Create a local account** opens the form: last name, first name and email address, all three required. The account is born without a role nor a means to sign in: its holder receives by email the link that has them set their password. When no invitation could be sent, the form says so and offers **Hand over the link**.
- **Modify the schedule** opens the form of the reading schedule: active or suspended, daily or weekly, the day for a weekly reading only, and the hour in universal time (UTC), with the local hour of this workstation it stands for. The schedule is saved whole; a reading in progress is not interrupted, the setting holds from the next one.
- In the table, the last name and the first name of an account created in Waterfall are entered in their cell; those of an account of the directory or of the identity provider are their own, and are not entered.
- **State**: the switch activates or deactivates the account. Deactivation is unavailable for the last active account that holds the administration permissions (“another active account holding the administration permissions”), and the reactivation of an anonymised account always is.
- **Access roles**: the list of the roles of the installation, to check or uncheck, none, one or several. The server refuses the roles that would take from the last administrator their permissions.
- **Link** gives the link to set the password of an account created in Waterfall, to hand over by another channel: it serves only once, will not be shown again, and asking for another one voids the previous one. Unavailable for a deactivated account (“active account”).
- **Email** has the identity provider send again, to the address of an account created in Waterfall, the email that bears the link to set the password: for a holder who did not receive it, lost it or let it expire. A previous link ceases to hold, and the sending is written in the audit log. Unavailable for a deactivated account (“active account”). When the provider cannot send it — an installation without mail, a mail server failing —, the screen says the refusal, never an email sent: **Link** then gives the link to hand over by another channel.
- **Anonymise**, once confirmed, erases the last name, the first name and the address of a deactivated account, from the table as from the audit log; the operation is final, and the account is no longer reactivated. Offered to the deactivated account alone, unavailable once the account is anonymised.

While a write of a row is in progress, the commands of that row wait for its answer.

Above the table, for all:

- **Filter by origin**, the node of attachment, **Filter by role** — an account that holds one of the roles chosen — and **Account state**; for the creation and the last modification, a period and an author. An author is chosen among those of the page; **Find** finds others among the accounts.
- The search field keeps the accounts whose last name, first name or address contains the text entered.
- **Columns** chooses the columns shown; **Rows per page**, **Previous page** and **Next page** go through the list.

The search and the filters are kept with the settings of the grid: coming back to the screen without asking anything finds them again.

## Its columns and computed values

No value is computed there: each column shows the account as the server holds it. An anonymised account no longer has a name nor an address, and is shown under a neutral label. In the columns of creation and of modification, an author deactivated since keeps their name, and an automatic process is named as such.

## Keyboard gestures

- The table is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` or `F2` enters a name, `Esc` abandons the entry; `Enter` on the switch, the roles, the link, the email or the anonymisation presses the command.
- On a header, `Enter` or `Space` sorts the table by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [Access role management](FBS-1.2.md), where the permissions of the roles are composed;
- [the audit log](FBS-1.5.md), which writes each creation, modification, deactivation and anonymisation of an account;
- [system status monitoring](FBS-1.3.md), which dates the last reading of the accounts of the identity provider.
