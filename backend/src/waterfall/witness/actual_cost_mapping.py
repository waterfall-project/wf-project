# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mapping of the extraction of the actual costs of the witness.

``actual_cost_mapping.json``: the labels of the five columns read and the columns kept, written
whole by the interface of the cost settings. The mapping is held when it names any label or has
been written since its birth (a manager may have emptied it): the platform is not completed,
corrected nor overwritten. The bootstrap makes it, empty, with the settings the installation shares
(#2092): a database the bootstrap has not installed has no mapping to fill, and the slice writes
nothing there.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import ActualCostMapping
from waterfall.core.cost_settings.interface import (
    ActualCostMappingWrite,
    ColumnLabels,
    read_actual_cost_mapping,
    reference_settings_installed,
    replace_actual_cost_mapping,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    if not reference_settings_installed(session):
        return False
    current = read_actual_cost_mapping(session)
    held = current.lock_version > 1 or current.kept_columns
    if held or any(column.labels for column in current.columns):
        return False
    declared = witness.read("actual_cost_mapping.json", ActualCostMapping)
    write = ActualCostMappingWrite(
        columns=[
            ColumnLabels(column.column.value, [label.root for label in column.labels])
            for column in declared.columns
        ],
        kept_columns=[label.root for label in declared.kept_columns],
    )
    replace_actual_cost_mapping(session, write, current.lock_version, witness.act)
    return True
