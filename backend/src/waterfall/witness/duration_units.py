# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The units of duration of the witness.

``duration_units.json``, written by ``set_duration_units`` of the resource settings, as the
platform. The constants are held when they have been written since the bootstrap — by a manager,
or by the witness already —: the platform is not corrected nor overwritten. A database the
bootstrap has not installed has no constants to set: the slice writes nothing there. The bootstrap
writes them in the transaction that writes the settings the installation shares, which say it.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.api.contract.models import DurationUnits
from waterfall.core.cost_settings.interface import reference_settings_installed
from waterfall.core.resource_settings.interface import Units, get_duration_units, set_duration_units

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

# The version the bootstrap writes the constants at.
BOOTSTRAPPED = 1


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    if not reference_settings_installed(session):
        return False
    current = get_duration_units(session)
    if current.lock_version > BOOTSTRAPPED:
        return False
    declared = witness.read("duration_units.json", DurationUnits)
    units = Units(
        Decimal(declared.hours_per_day.root),
        Decimal(declared.hours_per_week.root),
        Decimal(declared.days_per_month.root),
    )
    set_duration_units(session, units, current.lock_version, witness.act)
    return True
