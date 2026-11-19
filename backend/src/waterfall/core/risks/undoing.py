# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entries of the risks undone and redone, private to the module (US-2590/L2).

The history hands the risks the risk to bring back as an entry kept it (``recording``), or the
risk to delete, and the risks restore it in the frame of the undoing (``register_undoable``, EP-08,
"Modules"): locked in the order of their writes — the own estimate of the risk, the main structure
that bears its line, the risk —, judged by the history on the counter of the risk (409
``UNDO_CONFLICT``, naming it), then restored under the rules of the entry (WF-IHM-0110):

- a risk absent from the entry kept is deleted with its own estimate and its line — the undoing of
  a declaration, the redoing of a deletion —, as a deletion deletes it;
- a risk absent now is created again under its identifier — the undoing of a deletion, the redoing
  of a declaration —, its own estimate with its nodes, its evaluation, its reviews and its line;
- a risk present has its evaluation brought back — its probability, its state, the category, the
  subproject and the task of its provision —, the reviews of the revision the entry kept, and its
  line removed, created again under its identifier, or moved back and written again at the
  probability, its severity weighted by it (WF-RIS-0010).

A line created again goes under the task that bore it if that is still a task of the main structure,
else under the task the risk designates, else under the first task of the first level, as a return
to the identified state does (WF-RIS-0020). The rules of the entry refuse, in the order of
``CommandCondition`` (409 ``STATE_FORBIDS_OPERATION``, #795): a line to create again on a main
structure without a task (``at_least_one_task``), a subproject deleted since that the provision
would name again (``restored_subproject_exists``, #732), a line to create again, or a category to
bring back, that is no longer active and of the provision kind (``active_provision_category``).
Nothing is restored then. The counter of the risk advances, never going back; the risk, its line and
the nodes of its own estimate brought back are handed to the frame as they are left.
"""

from contextlib import suppress
from datetime import date
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, insert, select, update

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.interface import (
    ProvisionEntry,
    round_to_cent,
    set_provision,
    set_provision_bearing,
    structure_amount,
)
from waterfall.core.history.interface import ObjectState, Undoable
from waterfall.core.planning.interface import (
    Place,
    Writer,
    delete_borne_line,
    first_task,
    move_borne_line,
    recreate_borne_line,
    restore_structure_nodes,
    snapshot,
    task_of,
    task_of_lineage,
)
from waterfall.core.projects.interface import (
    ACTIVE_PROVISION_CATEGORY,
    AT_LEAST_ONE_TASK,
    subproject_labels,
)
from waterfall.core.revisions.interface import (
    aimed_structure,
    create_own_estimate,
    main_structure_has_task,
    structure_facts,
)
from waterfall.core.risks.commands import WRITE
from waterfall.core.risks.declaring import refuse
from waterfall.core.risks.deleting import remove
from waterfall.core.risks.following import advance_risks
from waterfall.core.risks.reading import PROVISION_KIND, evaluation_of, found_risk
from waterfall.core.risks.recording import amount, decoded_nodes, identifier, instant
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, Restoring, Snapshot, UndoneKind
    from waterfall.platform.audit import Act

RESTORED_SUBPROJECT_EXISTS = "restored_subproject_exists"
# The kinds of entry of the risks (``UndoneKind``), which the risks undo and redo.
RISK_KINDS: tuple[UndoneKind, ...] = ("risk_create", "risk_update", "risk_review", "risk_delete")


def _rows(state: ObjectState, name: str) -> Mapping[str, JsonValue]:
    """Give the rows of a risk an entry keeps under a name: its identity, its evaluation."""
    return cast("Mapping[str, JsonValue]", state.rows[name])


def _revision_of(state: ObjectState) -> UUID:
    """Give the revision the evaluation of a risk an entry keeps is of."""
    return cast("UUID", identifier(_rows(state, "evaluation"), "revision_id"))


def _main(session: Session, project_id: UUID, revision_id: UUID) -> Place:
    """Give the main structure of a revision, which bears the provision lines; or refuse (404)."""
    main = aimed_structure(session, project_id, revision_id, None)
    if main is None:
        raise NotFoundError(NOT_FOUND)
    return Place(project_id, revision_id, main)


def lock_risks(session: Session, project_id: UUID, states: Snapshot) -> None:
    """Lock what the risks of an entry name, in the order of their writes, absent ones passed.

    The own estimate of each, which a deletion takes away; the main structure of its revision; the
    risk.
    """
    kept = {state.object_id: state for state in states}
    for risk_id, state in sorted(kept.items()):
        structure_id = cast("UUID", identifier(_rows(state, "evaluation"), "structure_id"))
        # A risk the entry deleted, or whose declaration was undone, has no own estimate to hold.
        with suppress(NotFoundError):
            structure_facts(session, project_id, structure_id, lock=True)
        place = _main(session, project_id, _revision_of(state))
        structure_facts(session, project_id, place.structure_id, lock=True)
        of_risk = (Risk.project_id == project_id, Risk.id == risk_id)
        session.scalars(select(Risk.id).where(*of_risk).with_for_update()).first()


def read_risks(session: Session, project_id: UUID, risk_ids: tuple[UUID, ...]) -> Snapshot:
    """Give the risks named as they are, at their counter; absent ones left out."""
    found = {
        risk_id: (counter, label)
        for risk_id, counter, label in session.execute(
            select(Risk.id, Risk.lock_version, Risk.label).where(
                Risk.project_id == project_id, Risk.id.in_(list(risk_ids))
            )
        )
    }
    return tuple(
        ObjectState(each, found[each][0], found[each][1], {}) for each in risk_ids if each in found
    )


def _is_provision(session: Session, category_id: UUID) -> bool:
    """Tell whether a category is active, of an active nature, and of the provision kind."""
    label = category_labels(session, [category_id], locked=True).get(category_id)
    return (
        label is not None
        and label.is_active
        and label.cost_type_is_active
        and label.cost_type_kind == PROVISION_KIND
    )


def _judge(
    session: Session, place: Place, state: ObjectState, current: RiskEvaluation | None
) -> None:
    """Refuse a risk brought back that the rules of the entry no longer admit (409, #795).

    In the order of ``CommandCondition``: a line to create again on a main structure without a task,
    a subproject deleted since, a category of the line that is no longer of the provision.
    """
    kept = _rows(state, "evaluation")
    line = identifier(kept, "provision_node_id")
    category = cast("UUID", identifier(kept, "provision_cost_category_id"))
    subproject = identifier(kept, "provision_subproject_id")
    created = line is not None and (current is None or current.provision_node_id is None)
    if created and not main_structure_has_task(session, place.project_id, place.revision_id):
        raise refuse(AT_LEAST_ONE_TASK)
    if (
        subproject is not None
        and (current is None or current.provision_subproject_id != subproject)
        and not subproject_labels(session, place.project_id, [subproject], held=True)
    ):
        raise refuse(RESTORED_SUBPROJECT_EXISTS)
    changed = current is None or current.provision_cost_category_id != category
    if line is not None and (created or changed) and not _is_provision(session, category):
        raise refuse(ACTIVE_PROVISION_CATEGORY)


def _bearer(session: Session, place: Place, state: ObjectState) -> UUID:
    """Give the task a line brought back goes under: the one that bore it, designated, or first."""
    project_id, structure_id = place.project_id, place.structure_id
    bore = identifier(state.rows, "task_id")
    if bore is not None and task_of(session, project_id, structure_id, bore) is not None:
        return bore
    lineage = identifier(_rows(state, "evaluation"), "provision_task_lineage_id")
    named = None if lineage is None else task_of_lineage(session, project_id, structure_id, lineage)
    named = named or first_task(session, project_id, structure_id)
    if named is None:
        raise refuse(AT_LEAST_ONE_TASK)
    return named.node_id


def _provision(session: Session, project_id: UUID, state: ObjectState) -> Decimal:
    """Give the provision of a risk brought back: its severity, as it is, weighted, to the cent."""
    kept = _rows(state, "evaluation")
    own = cast("UUID", identifier(kept, "structure_id"))
    return round_to_cent(structure_amount(session, project_id, own) * amount(kept, "probability"))


def _line_created(session: Session, place: Place, state: ObjectState, writer: Writer) -> UUID:
    """Create again, under its identifier, the provision line an entry kept of a risk."""
    kept = _rows(state, "evaluation")
    entry = ProvisionEntry(
        cast("str", _rows(state, "risk")["label"]),
        cast("UUID", identifier(kept, "provision_cost_category_id")),
        identifier(kept, "provision_subproject_id"),
        _provision(session, place.project_id, state),
    )
    line = cast("UUID", identifier(kept, "provision_node_id"))
    borne = (_bearer(session, place, state), line)
    return recreate_borne_line(session, place, borne, entry, writer)


def _reviews(session: Session, project_id: UUID, state: ObjectState) -> None:
    """Bring the reviews of the risk in its revision back to those the entry kept, by identifier."""
    risk_id, revision_id = state.object_id, _revision_of(state)
    wanted = {
        cast("UUID", identifier(row, "id")): row
        for row in cast("list[Mapping[str, JsonValue]]", state.rows["reviews"])
    }
    of_risk = (
        RiskReview.project_id == project_id,
        RiskReview.risk_id == risk_id,
        RiskReview.revision_id == revision_id,
    )
    held = set(session.scalars(select(RiskReview.id).where(*of_risk)))
    session.execute(
        delete(RiskReview)
        .where(*of_risk, RiskReview.id.in_(list(held - set(wanted))))
        .execution_options(synchronize_session=False)
    )
    for review_id, row in wanted.items():
        if review_id in held:
            continue
        session.execute(
            insert(RiskReview).values(
                project_id=project_id,
                id=review_id,
                risk_id=risk_id,
                revision_id=revision_id,
                reviewed_on=_day(cast("str", row["reviewed_on"])),
                probability=amount(row, "probability"),
                severity=amount(row, "severity"),
                state=row["state"],
                created_at=instant(row, "created_at"),
                created_by=identifier(row, "created_by"),
            )
        )


def _created_again(session: Session, place: Place, state: ObjectState, writer: Writer) -> Snapshot:
    """Create again a risk absent now, as the entry kept it; give the nodes written back.

    The risk at the counter kept, its own estimate under its identifier and its nodes, its line,
    then its evaluation and its reviews, each after what it names.
    """
    project_id, revision_id, act = place.project_id, place.revision_id, writer.act
    identity, kept = _rows(state, "risk"), _rows(state, "evaluation")
    label = cast("str", identity["label"])
    session.execute(
        insert(Risk).values(
            id=state.object_id,
            project_id=project_id,
            label=label,
            description=identity["description"],
            mitigation_notes=identity["mitigation_notes"],
            lock_version=state.lock_version,
            created_at=instant(identity, "created_at"),
            created_by=identifier(identity, "created_by"),
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    own = cast("UUID", identifier(kept, "structure_id"))
    estimate = _rows(state, "own_estimate")
    start = cast("str", estimate["planning_start_on"])
    create_own_estimate(
        session,
        (project_id, revision_id),
        (state.object_id, label),
        act,
        (own, _day(start)),
    )
    nodes = restore_structure_nodes(
        session, Place(project_id, revision_id, own), decoded_nodes(estimate["nodes"]), writer
    )
    line = None
    if identifier(kept, "provision_node_id") is not None:
        line = _line_created(session, place, state, writer)
    session.add(
        RiskEvaluation(
            project_id=project_id,
            risk_id=state.object_id,
            revision_id=revision_id,
            probability=amount(kept, "probability"),
            state=cast("str", kept["state"]),
            structure_id=own,
            provision_node_id=line,
            provision_cost_category_id=identifier(kept, "provision_cost_category_id"),
            provision_subproject_id=identifier(kept, "provision_subproject_id"),
            provision_task_lineage_id=identifier(kept, "provision_task_lineage_id"),
            occurrence_cost=None,
            created_at=instant(kept, "created_at"),
            created_by=identifier(kept, "created_by"),
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    session.flush()
    _reviews(session, project_id, state)
    return nodes


def _day(value: str) -> date:
    """Give a day a row keeps."""
    return date.fromisoformat(value)


def _brought_back(
    session: Session, place: Place, state: ObjectState, held: RiskEvaluation, writer: Writer
) -> None:
    """Bring a risk present back to the evaluation, the reviews and the line an entry kept.

    A line to create again is created before the evaluation names it, and one to remove removed
    once the evaluation no longer names it, the state and the line tied by the constraint of the
    evaluation (``provision_when_identified``).
    """
    kept, act = _rows(state, "evaluation"), writer.act
    current, wanted = held.provision_node_id, identifier(kept, "provision_node_id") is not None
    created = None
    if wanted and current is None:
        created = _line_created(session, place, state, writer)
    held.probability = amount(kept, "probability")
    held.state = cast("str", kept["state"])
    held.provision_node_id = (created or current) if wanted else None
    held.provision_cost_category_id = cast("UUID", identifier(kept, "provision_cost_category_id"))
    held.provision_subproject_id = identifier(kept, "provision_subproject_id")
    held.provision_task_lineage_id = identifier(kept, "provision_task_lineage_id")
    held.updated_at, held.updated_by = act.at, act.author
    session.flush()
    if current is not None and not wanted:
        # The evaluation no longer names the line, which can now go.
        delete_borne_line(session, place, current, writer)
    elif current is not None:
        move_borne_line(session, place, current, _bearer(session, place, state), writer)
        bearing = (held.provision_cost_category_id, held.provision_subproject_id)
        set_provision_bearing(session, place, current, bearing)
        set_provision(session, place, current, _provision(session, place.project_id, state))
    _reviews(session, place.project_id, state)


def _removed(session: Session, project_id: UUID, state: ObjectState, writer: Writer) -> None:
    """Delete a risk the entry did not hold, as a deletion deletes it."""
    place = _main(session, project_id, _revision_of(state))
    risk = found_risk(session, project_id, state.object_id, lock=True)
    evaluation = evaluation_of(session, project_id, state.object_id, place.revision_id)
    if evaluation is None:
        raise NotFoundError(NOT_FOUND)
    remove(session, place, (risk, evaluation), writer)


def restore_risks(session: Session, project_id: UUID, restoring: Restoring, act: Act) -> None:
    """Restore the risks an entry gives back, delete those it takes away; hand them as left."""
    writer = Writer(act, None)
    kept = {state.object_id: state for side in restoring.written for state in side}
    present: list[ObjectState] = []
    for risk_id in restoring.removed:
        _removed(session, project_id, kept[risk_id], writer)
    for state in restoring.restored:
        place = _main(session, project_id, _revision_of(state))
        held = evaluation_of(session, project_id, state.object_id, place.revision_id)
        _judge(session, place, state, held)
        before = None if held is None else held.provision_node_id
        if held is None:
            present.extend(_created_again(session, place, state, writer))
        else:
            _brought_back(session, place, state, held, writer)
        session.execute(
            update(Risk)
            .where(Risk.project_id == project_id, Risk.id == state.object_id)
            .values(updated_at=act.at, updated_by=act.author)
            .execution_options(synchronize_session=False)
        )
        advance_risks(session, project_id, [state.object_id])
        lines = {
            each
            for each in (before, identifier(_rows(state, "evaluation"), "provision_node_id"))
            if each is not None
        }
        present.extend(snapshot(session, project_id, sorted(lines)))
    present.extend(read_risks(session, project_id, tuple(kept)))
    restoring.keep_present(tuple(present))


# How the risks lock, read and restore the entries of their kinds, under ``risks.write``.
UNDOABLE = Undoable((WRITE,), lock_risks, read_risks, restore_risks)
