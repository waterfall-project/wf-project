# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import applies only on the structure its report read, private to the module (US-3210).

"Between the analysis and the confirmation, no data of the project has changed" (WF-ARC-0100): the
analysis keeps the counter of the structure it read (``import_report.structure_lock_version``) —
a planning of MS Project, an estimate, a remaining to commit; none for the actual costs, which write
in no structure, nor for an import analysed without a structure —, and the application compares it
at the request, then again when its task runs, under the lock of the structure: any write of the
tree since — a cell, a paste, a move, a creation, a deletion — has advanced the counter, and the
import is refused for good (409 ``import_structure_unchanged``, #4420).

The structure the application writes is not always the one read. Analysed in the last marked
revision, or without any revision, the import writes in the current revision opened since, if one
was: the structure read is compared — marked, it no longer moves —, and the one written must be as
its opening left it, which the planning judges (``register_structure_guard``, the exchanges
reading no planning). The revision the task of the application opens itself is not compared:
nothing has written in it. A report analysed before the counter was kept applies without
comparison, during the twenty-four hours it lives: refusing it would name a condition no one can
tell is lacking.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.exchanges.judgments import refused
from waterfall.core.exchanges.states import STRUCTURE_UNCHANGED
from waterfall.core.revisions.interface import (
    aimed_structure,
    structure_facts,
    structure_in_revision,
)
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.judgments import ImportTarget
    from waterfall.core.exchanges.tables import ImportReport


@dataclass(frozen=True, slots=True)
class StructureGuard:
    """What the planning answers of the structure an application writes (US-3210).

    ``hold`` takes the lock of the structure — the project, the structure — as a write of its tree
    takes it, what the facets hold before it first (#2615); ``unwritten`` tells whether a structure
    of a revision opened is as its opening left it — the project, the structure, the one it copies,
    ``None`` for the main structure of a first revision.
    """

    hold: Callable[[Session, UUID, UUID], None]
    unwritten: Callable[[Session, UUID, UUID, UUID | None], bool]


_GUARDS: Registry[StructureGuard] = Registry("exchanges.structure_guards")


def register_structure_guard(guard: StructureGuard) -> Callable[[], None]:
    """Add what guards the structure an application writes; give its withdrawal (the planning's)."""
    return _GUARDS.register(guard)


def _guard() -> StructureGuard:
    """Give the guard of the structures; none registered is a defect of the process (500)."""
    guards = _GUARDS.entries()
    if not guards:
        msg = "no guard of the structures is registered"
        raise LookupError(msg)
    return guards[0]


def hold_written(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Take the lock of the structure an application writes, as a write of its tree takes it."""
    _guard().hold(session, project_id, structure_id)


def counter_read(session: Session, target: ImportTarget) -> int | None:
    """Give the counter of the structure an analysis reads, in its transaction; none without one.

    Read in the transaction the format analyses in, frozen at its first read (#2679): the counter
    and the tree the report is computed on are of one instant.
    """
    if target.structure_id is None:
        return None
    return structure_facts(session, target.project_id, target.structure_id, lock=False).lock_version


def written_at_request(session: Session, row: ImportReport, current: UUID | None) -> UUID | None:
    """Give the structure an application asked now would write; ``None`` when it opens it.

    The current revision's, the copy of the one read when that was of the last marked revision, its
    main structure when none was read. One the current revision no longer holds is ``None`` too:
    the request refuses it later, by the 404 the contract places after the state of the project.
    """
    if current is None:
        return None
    if row.structure_id is None:
        return aimed_structure(session, row.project_id, current, None)
    return structure_in_revision(session, row.project_id, row.structure_id, current)


def judge_unchanged(session: Session, row: ImportReport, written: UUID | None) -> None:
    """Refuse an import whose structure was written since its analysis (409); or let it pass.

    ``written`` is the structure the application writes, ``None`` when it opens its revision
    itself. The structure read must bear the counter kept; the one written, when it is another —
    a revision opened since the analysis —, the counter its opening left it. The caller holds the
    lock of ``written`` when its judgment decides a write (the task of the application).
    """
    project_id, read = row.project_id, row.structure_id
    if read is not None:
        if row.structure_lock_version is None:
            # Analysed before the counter was kept: applied without comparison.
            return
        facts = structure_facts(session, project_id, read, lock=False)
        if facts.lock_version != row.structure_lock_version:
            raise refused(STRUCTURE_UNCHANGED)
    if written is None or written == read:
        return
    if not _guard().unwritten(session, project_id, written, read):
        raise refused(STRUCTURE_UNCHANGED)
