# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures of cost of the witness.

``cost_types.json``; the nature of provision of the bootstrap stays, those of the witness are
added. Written by ``create_cost_type`` with the identifiers the witness imposes, then those it
says deactivated are, which deactivates their categories: a nature deactivated holds no category
of the witness, the categories being written after it.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import CostType
from waterfall.core.cost_settings.interface import (
    CostTypeDraft,
    create_cost_type,
    present_cost_types,
    set_cost_type_activation,
)
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


class CostTypes(BaseModel):
    """The value of ``listCostTypes`` the witness describes its natures by."""

    items: list[CostType]


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    natures = witness.read("cost_types.json", CostTypes).items
    imposed = {nature.cost_type_id.root for nature in natures}
    if is_loaded(imposed, present_cost_types(session, imposed)):
        return False
    for nature in natures:
        draft = CostTypeDraft(nature.code, nature.label, nature.kind.value)
        created = create_cost_type(session, draft, witness.act, identifier=nature.cost_type_id.root)
        if not nature.is_active:
            set_cost_type_activation(
                session,
                created.cost_type_id,
                is_active=False,
                lock_version=created.audit.lock_version,
                act=witness.act,
            )
    return bool(natures)
