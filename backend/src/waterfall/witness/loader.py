# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The order the witness is loaded in: one slice per object, after the slices it names.

A slice is the function ``load`` of its file: it writes its objects through the interfaces of the
modules unless the platform already holds them, and tells whether it wrote. An empty slice writes
nothing — its objects, none, are held. The story of an object fills its file and never touches
this order, which EP-05 fixes ("Le chargeur du témoin").
"""

from typing import TYPE_CHECKING

from waterfall.witness import (
    actual_cost_mapping,
    calendars,
    cost_categories,
    cost_types,
    duration_units,
    hourly_rates,
    org_nodes,
    reference_settings,
    resource_roles,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

type Slice = Callable[[Session, Witness], bool]

# The settings and the units name nothing; a category names its nature, a rate its category, a
# node its parent, a role its node, its category and its calendar; the mapping comes last.
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
)


def load_slices(session: Session, witness: Witness) -> list[str]:
    """Load each slice in its order, in the transaction of ``session``; name those that wrote."""
    return [name for name, load in SLICES if load(session, witness)]
