# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A differential abandoned: its nodes, their facets and the entries of its history deleted.

``abandon_differential`` serves ``deleteCostStructure`` (US-2550/L4): the abandonment of a
differential that is not merged, in the current revision, at the counter read. It is irreversible
and outside of the undoable history, as that of a revision is: the entries of the stacks that
touch the structure and the plans of a paste that aim at it go with it (WF-IHM-0110), its nodes
with their facets and their links, then the structure itself, which the journal inscribes
(``structure_abandon``). Its base goes with it, its nodes and their facets, then the structure
(US-3050). The other structures of the revision, the main one first, are not read nor written; the
inscriptions of the tracking, which the lineage keeps, stay with the main structure.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.history.interface import forget_structure
from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Node
from waterfall.core.planning.writing import (
    Place,
    Writer,
    facts_of,
    hold_before_lock,
    judge_revision,
)
from waterfall.core.revisions.interface import (
    UNMERGED_AMENDMENT_EXISTS,
    abandon_structure,
    differential_base,
    structure_facts,
)
from waterfall.platform.errors import (
    STALE_LOCK_VERSION,
    STATE_FORBIDS_OPERATION,
    ConflictError,
    PreconditionFailedError,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def delete_structure_nodes(session: Session, place: Place) -> None:
    """Delete the nodes of a structure with the facets of the later kinds.

    The facets of the other kinds go first, by their hooks, then the nodes, whose task, links and
    children follow by the keys that cascade inside a revision.
    """
    project_id = place.project_id
    of_structure = (Node.project_id == project_id, Node.structure_id == place.structure_id)
    for kind, hooks in facets().items():
        held = session.scalars(select(Node.id).where(*of_structure, Node.kind == kind)).all()
        if held:
            hooks.delete(session, project_id, held)
    session.execute(delete(Node).where(*of_structure).execution_options(synchronize_session=False))


def abandon_differential(session: Session, place: Place, lock_version: int, writer: Writer) -> None:
    """Abandon a differential at the counter read: the structure and all it holds are deleted.

    The structure named is read first (404), the revision judged under its lock (409
    ``project_not_terminal``, ``revision_draft``, ``no_background_task_running``, in that order),
    then the structure locked, as every write of its tree does, and judged: a structure that is not
    a differential that is not merged — the main structure, the own estimate of a risk, a merged
    differential — is refused (409 ``unmerged_amendment_exists``), then the counter (412).
    Nothing is deleted then. Its base is locked after it, as the update of a differential takes
    them, and deleted with it (US-3050).
    """
    hold_before_lock(session)
    facts_of(session, place, lock=False)
    judge_revision(session, place.project_id, place.revision_id, writer.running)
    facts = facts_of(session, place, lock=True)
    if not facts.is_differential or facts.is_merged:
        missing = {"missing_condition": UNMERGED_AMENDMENT_EXISTS}
        raise ConflictError(STATE_FORBIDS_OPERATION, missing)
    if facts.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": facts.lock_version}
        )
    node_ids = session.scalars(
        select(Node.id).where(
            Node.project_id == place.project_id, Node.structure_id == place.structure_id
        )
    ).all()
    base_id = differential_base(session, place.project_id, place.structure_id)
    if base_id is not None:
        structure_facts(session, place.project_id, base_id, lock=True, base=True)
    forget_structure(session, place.revision_id, place.structure_id, node_ids)
    delete_structure_nodes(session, place)
    if base_id is not None:
        delete_structure_nodes(session, Place(place.project_id, place.revision_id, base_id))
    abandon_structure(session, place.project_id, facts, writer.act)
