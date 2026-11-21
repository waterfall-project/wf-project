# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The keys of the advisory locks the API and the worker share, and the order they are taken in.

A backup is deposited by the API (``startBackup``) and by the planned command of the worker; a
restoration by the API (``startRestore``). Both look for a pending task, then deposit, under these
locks, always taken in this order: ``SCHEDULE_LOCK`` (the planned command alone), ``BACKUP_LOCK``,
then ``RESTORE_LOCK``, shared by whoever deposits a backup or writes the schedule or a mark,
exclusive by whoever deposits a restoration. Nothing waits for an earlier lock while holding a
later one, so none of them interlocks. A backup takes its two by one function of the module of the
backups (``lock_backup_deposit``).
"""

# The key under which a schedule looks for a pending task, then deposits.
SCHEDULE_LOCK = 3_700_010
# The key under which a request looks for a backup pending, then deposits one.
BACKUP_LOCK = 3_700_150
# The key under which a request looks for a pending restoration, then deposits.
RESTORE_LOCK = 3_700_160
