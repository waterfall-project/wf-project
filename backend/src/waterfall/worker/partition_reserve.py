# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``partition_reserve``: make the sets of partitions the creations of projects take.

A creation takes a set of the reserve with no DDL, and deposits this task (US-2830/L4, #4801); the
schedule deposits it too when the reserve holds fewer sets than ``partition_reserve_size``
(``waterfall.worker.schedule``). The worker makes sets until the reserve holds that many, in the
one transaction of the task, under the locks of the creation of partitions: it waits for a marking
or an application of an import that runs, never a request. Those locks are taken without waiting,
again and again for about ten seconds; past them, the task is taken again later
(``RetriedError``), the sets it made undone with it, and fails at its last attempt — the next
creation, or the schedule, deposits another.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from psycopg.errors import LockNotAvailable
from sqlalchemy.exc import OperationalError

from waterfall.core.projects import interface as projects_interface
from waterfall.platform.logs import get_logger
from waterfall.platform.tasks import RetriedError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import ReserveSettings
    from waterfall.platform.tasks import Task

logger = get_logger(__name__)


def _unchanged(_session: Session) -> None:
    """Leave nothing in place of a filling undone: the reserve is as it was."""


@dataclass(frozen=True, slots=True)
class ReserveTask:
    """Fill the reserve of partitions up to the size the settings give."""

    size: int

    @classmethod
    def of(cls, settings: ReserveSettings) -> ReserveTask:
        """Fill up to ``partition_reserve_size``."""
        return cls(settings.partition_reserve_size)

    def __call__(self, session: Session, _task: Task) -> Mapping[str, Any]:
        """Make the sets the reserve lacks, and say how many."""
        try:
            made = projects_interface.fill_partition_reserve(session, self.size)
        except OperationalError as error:
            if not isinstance(error.orig, LockNotAvailable):
                raise
            raise RetriedError(error, _unchanged) from error
        logger.info("partition_reserve.filled", made=made, size=self.size)
        return {"made": made}
