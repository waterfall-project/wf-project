# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a role is told of its category (FBS-3.2), in a module with no router.

The resource settings do not read the cost settings, which read them: whoever writes a role asks
the cost settings what a role is told of its category, and passes the answer on. The route and the
loader of the witness (``waterfall.witness``) both import this module, so that the loader depends
on no module of routes.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import CostTypeKind
from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.resource_settings.interface import CategoryAdmission, read_role

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def category_admission(session: Session, category_id: UUID) -> CategoryAdmission | None:
    """Ask the cost settings what a role is told of a category, sharing the lock of the natures.

    Whether its nature is of labour and whether it is active; ``None`` for a category the
    reference does not have. Asked first, before the write locks anything of the resource settings
    — the tree, the role —: the lock holds until the transaction ends, and a change of the kind or
    of the state of the category waits for the role attached to it, or is waited for.
    """
    found = category_labels(session, [category_id], locked=True).get(category_id)
    if found is None:
        return None
    return CategoryAdmission(
        is_labour=found.cost_type_kind == CostTypeKind.labor.value, is_active=found.is_active
    )


def category_admission_for_change(
    session: Session, role_id: UUID, category_id: UUID, lock_version: int
) -> CategoryAdmission | None:
    """Ask for the category of a role changed only if the change moves it, so as not to lock.

    A role that keeps its category is not judged on it (``update_role``), so the lock of the natures
    is taken only by a change of category: a write of a nature or of a category does not wait for
    the others. The role is read without a lock, and its category deemed kept only at the version
    sent: at another version the change is refused (412), or the role was moved meanwhile and the
    category is asked as for a move. A role unknown is refused here (404), as ``update_role`` does.
    """
    role = read_role(session, role_id, may_change=False)
    if role.cost_category_id == category_id and role.lock_version == lock_version:
        return None
    return category_admission(session, category_id)
