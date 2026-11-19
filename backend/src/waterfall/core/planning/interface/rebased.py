# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A differential updated from the main structure (``rebaseCostStructure``; US-3050/L4).

``rebase_differential`` applies the update the report presented (``getStructureRebaseReport``):
what the planning and the estimate find of it, by the same function, written under the lock of the
project and of the three structures — the revision shared first, then the project, then the main
structure, the differential and its base in the order of their identifiers, as every write that
prices the structures of a revision locks them (``revision_structures``). Refused as its report is
(404, then 409, the first condition its command ``rebase`` lacks: ``rebasing_of``), then at the
counters of the confirmation (412, the counter of the differential named, the object the path
names, even when only the main structure moved), then by the first reason of the report (422, its
code and its parameters, as an import refuses): nothing is written then, the reasons being judged
before the first write. The main structure is not written. The update is neither an entry of the
history — an entry of the differential made before it is undone, unless it holds a node the update
wrote, which the rule of conflict refuses by naming it (WF-IHM-0110) — nor of the journal.

``load_rebase`` is the same update without a report to confirm, for the loader of the witness.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from waterfall.core.planning.writing import (
    Place,
    Writer,
    facts_of,
    hold_before_lock,
    judge_revision,
)
from waterfall.core.projects.interface import lock_project
from waterfall.core.revisions.interface import (
    aimed_structure,
    differential_base,
    rebase_parts,
    rebasing_of,
    structure_facts,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def rebase_differential(
    session: Session, place: Place, writer: Writer, counters: tuple[int, int] | None
) -> None:
    """Update a differential from the main structure, at the counters of the report confirmed.

    ``counters`` the counter of the main structure and that of the differential the report read,
    none for the witness's, which confirms no report. Nothing is written if it is refused.
    """
    project_id, revision_id = place.project_id, place.revision_id
    hold_before_lock(session)
    facts_of(session, place, lock=False)
    judge_revision(session, project_id, revision_id, writer.running)
    lock_project(session, project_id)
    main_id = aimed_structure(session, project_id, revision_id, None)
    if main_id is None:
        raise NotFoundError(NOT_FOUND)
    held = {main_id, place.structure_id}
    base_id = differential_base(session, project_id, place.structure_id)
    if base_id is not None:
        held.add(base_id)
    for each in sorted(held):
        structure_facts(session, project_id, each, lock=True, base=True)
    asked = (project_id, revision_id, place.structure_id)
    rebasing, main, differential = rebasing_of(session, asked, writer.act, applying=False)
    if counters is not None and counters != (main.lock_version, differential.lock_version):
        expected = {"expected_lock_version": differential.lock_version}
        raise PreconditionFailedError(STALE_LOCK_VERSION, expected)
    refusals = rebase_parts(rebasing).refusals
    if refusals:
        first = refusals[0]
        params = cast("Mapping[str, Any]", first["params"])
        raise UnprocessableError(str(first["code"]), params)
    rebase_parts(replace(rebasing, applying=True))
    # The counters moved by statements: the rows the session read are read again.
    session.expire_all()


def load_rebase(session: Session, place: Place, act: Act) -> None:
    """Update a differential from the main structure without a report, for the witness (US-3050).

    As ``rebase_differential`` writes it, the counters not confirmed: a differential that is not
    out of date, or whose update a reason refuses, is refused.
    """
    rebase_differential(session, place, Writer(act, None), None)
