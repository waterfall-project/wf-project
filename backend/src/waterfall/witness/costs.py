# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness: its imports, their lines and the exclusion, at their instants.

Called by the march of the events of the revisions (``witness.revisions``), after the lines, for
each write of the chronology that concerns the actual costs — an import applied, a line excluded,
an extraction expired —: the import of the exchanges at its instant, the entry of the log and the
lines created or updated through the interface of the actual costs, at the identifiers of
``witness_costs.json`` and the instant of the event, the author of the witness for account; the
exclusion at its instant (EP-09, "Le chargeur du témoin"). Nothing is loaded for the remaining to
commit: the copy of the revision 102 from the reference 101 gives it.

Declared by US-1580/L1, it writes nothing yet; US-1650/L2 fills it and the march that calls it. Its
import, chained by the slice of the projects after the lines (``chronology``), gives the loader the
extensions of the actual costs from the socle of EP-09 on (#2180).
"""

from waterfall.core.costs import interface as costs_interface

# The module whose interface the slice writes through, which registers the format of the actual
# costs at its import.
EXTENDING = (costs_interface,)
