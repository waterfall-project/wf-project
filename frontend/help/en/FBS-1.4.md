# Backup and restore

## What the screen shows

The backups of the platform, outside any project. A backup holds the whole platform; restoring is replacing the platform with it.

From top to bottom:

- **Schedule**: the state of the scheduled backup — active or suspended —, its frequency, its day for a weekly backup, its hour in universal time (UTC), its retention — how many backups the platform keeps — and its external copy: the location, the folder and the number of copies kept, or “None”.
- The list of the backups, each with its date, its size, its verification, its trigger and its retention, which the server sorts — the most recent first —, filters and pages; its footer says how many it keeps.
- For whoever may restore the platform, **Restore a backup of another installation**.

## Its commands

- **Modify the schedule**, for whoever may modify the backups, opens its form, which saves it whole: state, frequency, day, hour (UTC) — the hour of this workstation it stands for today is said beside it —, backups kept, and the external copy to one of the locations the installation declares, in a relative folder, with at least as many copies kept as backups kept, and the state of the copy, active or suspended; **No copy** removes it. **Test the location** has a witness file written then erased at the location chosen, and says the result.
- **Back up now**, for whoever may modify the backups, launches a backup; its progress is followed in the panel of the tasks.

On each backup, the commands it lists, each in its column, present when a backup of the page offers it; an unavailable command says the condition it lacks:

- **Keep** marks the backup to keep: the rotation does not delete it; **Stop keeping** lifts the mark.
- **Download** the archive of the backup; unavailable while it is not verified (“backup verified”).
- **Restore** opens the restoration of the platform from the backup. Unavailable for a backup not verified, during a backup (“no backup running”) or another restoration (“no restoration running”). The dialog says what will be lost — everything entered since —, that the users will be signed out and that the restoration will be written in the audit log; it restores only once the identifier of the backup is entered. The restoration launched, the screen gives way to that of the maintenance, which follows it to its end and then offers to sign in again.

During a restoration, only the download stays available. No command deletes a backup: the rotation sees to it, according to the retention.

**Restore a backup of another installation**: **Deposit** sends, piece by piece, the **Archive of the backup** downloaded on an installation of the same version or an older one; deposited, **Restore this backup** opens the same dialog of restoration.

Above the list:

- **Period of the backups**, **Filter by trigger**, **Filter by verification**, **Retention** and, between two bounds, the size in bytes.
- **Columns** chooses the columns shown; **Rows per page**, **Previous page** and **Next page** go through the list.

## Its columns and computed values

Every value is the server’s. The size is written in the unit that suits it; the filter on the size, for its part, is bounded in bytes. The date is in the time of this workstation; the hour of the schedule is in universal time.

## Keyboard gestures

- The list is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on a command of the list presses it; pressed while unavailable, it says the condition it lacks.
- On a header, `Enter` or `Space` sorts the list by the column; `Shift` and the arrows widen or narrow the column.
- In a dialog, `Esc` closes it without doing anything — except while a restoration is being sent, which waits for the answer of the server.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [System status monitoring](FBS-1.3.md), which dates the last backup, its external copy and the last restore test, and signals their failures;
- [the audit log](FBS-1.5.md), which writes the backups and the restorations.
