# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The questions of the minimal reference this module answers, and the lock that guards them.

Whether the default calendar counts hours in its week (WF-CYC-0120); whether an active role of
resources exists is answered by ``resource_roles``. The route of the minimal reference composes
them with those of the cost settings.

The lock of the reference (``REFERENCE_LOCK``) orders the creation of a project, which asks the
four questions and must find the answers true until it commits, and every write that could turn
one of them false (#2154). It lives in this module because the cost settings already import the
resource settings, never the opposite: both can reach it without a cycle. Taken first by every
write, before the lock of the natures, the one of the tree or of the designation and any row, so
that none waits for another in a circle.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, func, or_, select

from waterfall.core.resource_settings.tables import DAYS, Calendar

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# The key of the advisory lock of the minimal reference. A fixed number, distinct from every other
# advisory key of the service (the installation, the migrations, the natures, the tree, the
# default calendar, the administrators, the restoration, the witness, the forgetting, the
# scheduler and the runs of the worker).
REFERENCE_LOCK = 4_200_830


def default_calendar_has_hours(session: Session) -> bool:
    """Tell whether the default calendar, active, works one day of the week at least.

    ``default_calendar_with_hours``: a week without any hour leaves a task no day to be worked.
    """
    worked = or_(*(getattr(Calendar, day) > 0 for day in DAYS))
    held = select(exists().where(Calendar.is_default, Calendar.is_active, worked))
    return bool(session.scalar(held))


def lock_reference(session: Session) -> None:
    """Take the lock of the reference, exclusively, until the transaction ends.

    By every write that can turn a question of the minimal reference false — a calendar made the
    default or given no hour, a category or a nature of labour or of provision deactivated or of
    another kind, a role or a node deactivated —, before it reads anything or takes any other lock.
    It waits for the creations of a project in progress, and they wait for it. The update of a
    cost type, a cost category or a calendar takes it even for a change of label alone: the effect
    of a write is only known under the lock, and these writes are rare — accepted.

    The activation of a calendar (``set_calendar_activation``) is the one writer of ``is_active``
    that does not take it: the default calendar, which the minimal reference reads, is never
    deactivated (``calendar_not_default``), so that no deactivation can empty it. Were that refusal
    lifted, the activation would take the lock; a test pins the refusal (``test_reference_lock``).
    The units of duration take it too (``set_duration_units``), as every write that redates the
    plannings of the current revisions, which the opening of a revision shares (EP-06).
    """
    session.execute(select(func.pg_advisory_xact_lock(REFERENCE_LOCK)))


def share_reference(session: Session) -> None:
    """Share the lock of the reference until the transaction ends.

    By the creation of a project, before it asks the four questions: the writes that could change
    an answer (``lock_reference``) wait for it, or are waited for; two creations do not wait for
    each other. By the opening of a revision too, which a change that redates the current
    revisions must see, or be seen by (EP-06): it may hold the lock of its project already, which
    no holder of this lock waits for.
    """
    session.execute(select(func.pg_advisory_xact_lock_shared(REFERENCE_LOCK)))
