# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares, as the witness sets them.

``reference_settings.json``: the matrix, the thresholds and the delay of the witness, judged by
the rules a writing of the API is judged by, and written by the interface of the cost settings as
the platform; the currency and the name stay those of the bootstrap. The settings are held when
they have been written since the bootstrap — by a manager, or by the witness already —: the
platform is not corrected nor overwritten. A database the bootstrap has not installed has no
settings to set: the slice writes nothing there.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import ReferenceSettings
from waterfall.api.reference_settings_write import SettingsWrite, change_of
from waterfall.core.cost_settings.interface import (
    read_reference_settings,
    reference_settings_installed,
    write_reference_settings,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

# The version the bootstrap writes the settings at.
BOOTSTRAPPED = 1
# What the witness sets: the currency and the name are the bootstrap's.
SET = ("risk_matrix", "index_thresholds", "max_weeks_between_reviews")


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    if not reference_settings_installed(session):
        return False
    current = read_reference_settings(session)
    if current.lock_version > BOOTSTRAPPED:
        return False
    declared = witness.read("reference_settings.json", ReferenceSettings).model_dump(mode="json")
    sent = {name: declared[name] for name in SET} | {"lock_version": current.lock_version}
    change = change_of(SettingsWrite.model_validate(sent))
    write_reference_settings(session, change, current.lock_version, witness.act)
    return True
