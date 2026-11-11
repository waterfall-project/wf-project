# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history of the entries that can be undone, and the plans of a paste (WF-IHM-0110, 0050).

What other modules read goes through ``interface``. An entry is kept in the transaction of the
entry it guards, by revision, account and session; it reads no table of another module: the
planning hands it the snapshots of the rows it writes (EP-06, "L'historique annulable").
"""
