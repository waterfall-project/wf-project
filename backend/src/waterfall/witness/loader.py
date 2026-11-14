# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The order the witness is loaded in: one slice per object, after the slices it names.

A slice is the function ``load`` of its file: it writes its objects through the interfaces of the
modules, with the identifiers the witness imposes, unless the platform already holds them, and
tells whether it wrote. An empty slice writes nothing — its objects, none, are held. The story of
an object fills its file and never touches this order, which EP-05 fixes ("Le chargeur du témoin");
the slices of the projects come after it, ordered in their own entry (EP-04, ``chronology``).

What "the platform holds them" means, for every slice (EP-05, "Le chargeur du témoin"):

- all the objects of the slice, found by the identifier the witness imposes, are there: the slice
  writes nothing and returns ``False`` — a second execution on a loaded platform succeeds, saying
  the witness is there;
- none is there: the slice writes them all and returns ``True``; any object that bears the code or
  the label of one of them without its identifier is refused by the rule of its module (a
  ``ServiceError``), which stops the command;
- some are there and not all, a platform half loaded: the slice writes nothing of the missing
  ones. It raises the collision (409 ``ALREADY_EXISTS``) that stops the command, nothing written
  by any slice, one transaction. ``description.is_loaded`` makes the three cases one call.

A slice never completes, corrects or overwrites what the platform holds, and looks for it by the
identifier, not by the code or the label.
"""

from typing import TYPE_CHECKING

from waterfall.core.exchanges import interface as exchanges_interface
from waterfall.core.history import interface as history_interface
from waterfall.core.planning import interface as planning_interface
from waterfall.witness import (
    actual_cost_mapping,
    calendars,
    chronology,
    cost_categories,
    cost_types,
    duration_units,
    hourly_rates,
    org_nodes,
    projects,
    reference_settings,
    resource_roles,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

type Slice = Callable[[Session, Witness], bool]

# The modules that fill the registries of the others at the import of their interface (#2180):
# imported here, so that no revision the witness opens or marks lacks their part.
EXTENDING = (exchanges_interface, history_interface, planning_interface)

# The settings and the units name nothing; a category names its nature, a rate its category, a
# node its parent, a role its node, its category and its calendar; the mapping comes last of the
# reference. The projects follow, which their creation asks the minimal reference of (EP-04): one
# entry, which orders the slices of the projects (``chronology``).
SLICES: tuple[tuple[str, Slice], ...] = (
    ("reference_settings", reference_settings.load),
    ("duration_units", duration_units.load),
    ("cost_types", cost_types.load),
    ("cost_categories", cost_categories.load),
    ("hourly_rates", hourly_rates.load),
    ("calendars", calendars.load),
    ("org_nodes", org_nodes.load),
    ("resource_roles", resource_roles.load),
    ("actual_cost_mapping", actual_cost_mapping.load),
    ("chronology", chronology.load),
)


def load_slices(session: Session, witness: Witness) -> list[str]:
    """Load each slice in its order, in the transaction of ``session``; name those that wrote.

    The partitions of the projects first, before any slice writes (``projects.partition``).
    """
    projects.partition(session, witness)
    return [name for name, load in SLICES if load(session, witness)]
