# System status monitoring

## What the screen shows

The state of the platform, outside any project, as the server gives it at the moment the screen is read; under the title, the version installed. From top to bottom:

- **Current alerts**: each alert with its level, what it signals and since when — a component unavailable, the queue of the processes blocked, the failure of a scheduled backup or of its external copy, the failure of the reading of the accounts of the identity provider, a storage almost full, an abnormal error rate. The alert names what it concerns: the component, the space used and free, the external location and the reason for the failure. Without an alert, the screen says “No current alert.”
- **Components**: each component of the platform, available or unavailable, the date of its last check and its version.
- **Storage**: the space used and the space available.
- **Operating parameters**: the values in force of what the operator sets at deployment — the validity of the cache of the indicators, the retention of the result of a background task, the maximum size of an avatar, the wait of a task in the queue and the rates of storage use and of errors that raise an alert, with the window where the error rate is measured. No screen modifies them.
- **Last operations**: the last reading of the accounts of the identity provider, the last backup, the last external copy of a backup and the last restore test, each dated with its result and the reason for a failure — or “Never run”.

## Its commands

The screen is read only: it has no command. It shows the state at the moment of its reading; reading it again, through the browser, gives a more recent one. The backups are launched and scheduled from the screen of the [backups](FBS-1.4.md), and the reading of the accounts from that of the [users](FBS-1.1.md).

## Its columns and computed values

The tables of the screen are neither sorted nor filtered. Every value is the server’s, nothing is computed here. The level of an alert is read by its signal and its label, never by the colour alone. The dates are in the time of this workstation.

## Keyboard gestures

- `Tab` goes through the screen; a table wider than the window scrolls with the keyboard.
- `F1` opens this help.

## See also

- [Backup and restore](FBS-1.4.md), [user management](FBS-1.1.md);
- [the audit log](FBS-1.5.md).
