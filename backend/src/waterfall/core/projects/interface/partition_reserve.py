# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve of sets of partitions a creation of a project takes (US-2830/L4, #4801).

Making the partitions of a project locks ``SHARE ROW EXCLUSIVE`` the tables their keys bind, which
a marking or the application of an import holds until it commits (#4735). The worker makes sets
in advance — the task ``partition_reserve``, deposited after each set taken and by the schedule —,
by the function that made them for a creation, under its very locks: it is the worker that waits
for a marking, never a request. A creation takes a set with no DDL (``take_partitions``), and makes
its own as before only when the reserve has none free. Both through the functions of the owner of
the tables (migration ``0055``), the identifiers drawn by the service.
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.projects.tables import PartitionReserve
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def take_partitions(session: Session) -> UUID | None:
    """Take a whole set of the reserve, in the transaction that creates its project; give its id.

    Its row is deleted, skipping those another creation holds: two creations together take two
    sets. ``None`` when the reserve has none free, the creation then making its own partitions.
    Undone with the transaction, the set goes back to the reserve.
    """
    return session.scalar(select(func.take_project_partitions()))


def fill_partition_reserve(session: Session, size: int) -> int:
    """Make sets until the reserve holds ``size`` whole ones; give how many were made.

    The sets that lack a partition are dropped first, and made again whole.

    Each under the locks of the creation of partitions, which it takes without waiting while it
    holds one and gives up after ten seconds (``lock_not_available``): a marking that runs keeps the
    reserve as it is until it commits.
    """
    made = 0
    while session.scalar(select(func.reserve_project_partitions(new_id(), size))):
        made += 1
    return made


def partition_reserve_short(session: Session, size: int) -> bool:
    """Tell whether the reserve holds fewer whole sets than ``size``.

    A set counts as the taking counts it: whole, a partition in every table partitioned by the
    identifier of a project. One that lacks a partition is made again by the filling.
    """
    counted = (
        select(func.count())
        .select_from(PartitionReserve)
        .where(func.project_partition_set_whole(PartitionReserve.id))
    )
    held = session.scalar(counted) or 0
    return held < size
