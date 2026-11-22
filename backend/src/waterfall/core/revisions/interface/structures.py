# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cost structures of a revision: its main one here (WF-REV-0100), and their commands.

The main structure is created with the first revision of a project, and is its only one; a
revision created from a marked one takes up its structures but the merged ones (``is_merged``: an
amendment consumed by its merge, the own estimate of a risk that occurred), each under an
identifier of its own and the lineage of the one it copies (WF-DAT-0030, #1759). The amendments
and the risks' own come with EP-08, which adds their kinds.

The date a structure's planning starts on is the day of its first creation by default, which a
copy keeps (``CostStructure.planning_start_on``), and the instant its dates were computed is that
of its creation until EP-06 schedules it (``scheduled_at``): both are written at the creation and
taken up by the copy (#2170). A row the migration ``0023`` did not fill reads them as they were
derived before: the day of the creation of the origin of its lineage, which is always there — the
revision it was created in was marked, since a copy takes up only a marked revision's —, or, were
it missing, the day of its own creation rather than vanish from its list.

What the planning asks of a structure (EP-06, "Modules"): its facts, read or under its lock
(``structure_facts``), which every write of its nodes takes, and the instant of its dates moved on
with its counter (``structure_rescheduled``), at each write that redates it (US-1380/L2), or its
counter alone (``structure_counted``), at a write that can move no date (US-2250); the
condition of the phase an entry lacks, by the rule its commands state
(``structure_phase_conditions``, US-1380/L4); its start and its label written
(``write_structure``, ``updateCostStructure``), and the structures of the current revisions,
their revisions read ``FOR SHARE`` (``current_structures``), which a change of the reference
redates (US-1390/L2).

A differential is born with its base (US-3050/L2): the copy of the main structure it is read
against, which no operation serves — neither listed, nor read by its identifier (``structure_facts``
refuses it as an unknown structure, but for what sweeps every structure of a revision), nor counted
by what reads the structures of a revision —, which the abandonment of the differential deletes and
the copy of a revision takes up with a differential not merged, its state with it (``bases``). A
differential keeps the counter the main structure bore when its base was taken: it is up to date
while the main structure bears it (``CostStructure.is_up_to_date``), and lists its update
(``rebase``) available once out of date.

The own estimate of a risk is born with its risk, in the current revision (``create_own_estimate``,
E-09; US-2570/L1), labelled as its risk. Its counter is the risk's too: each time it advances —
whatever writes the tree, once the write has priced its lines —, the modules registered follow it
(``register_own_estimate_counted``): the risks advance the counter of the risk and take its
severity from the total of the structure again (#1453, WF-RIS-0010).

Filled by US-0960. The witness loads no structure of its own: the main one is born with its
revision, the others are EP-06's and EP-07's.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import aliased

from waterfall.core.projects.interface import (
    CommandAvailability,
    contributor_kind,
    current_day,
    project_facts,
)
from waterfall.core.revisions.commands import (
    DIFFERENTIAL_NATURE,
    MAIN_NATURE,
    UP_TO_DATE_NATURE,
    StructureNature,
    phase_conditions,
    structure_commands_of,
)
from waterfall.core.revisions.interface.shared import (
    AMENDMENT,
    BASE,
    MAIN,
    RISK,
    inscribe_structure,
    writing_provision,
)
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.states import revision_state
from waterfall.core.revisions.tables import CostStructure, OwnEstimateAbandonment, Revision
from waterfall.platform.errors import NOT_FOUND, NotFoundError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.revisions.interface.revisions import RevisionCopy
    from waterfall.platform.audit import Act

# The kind of a differential, the amendment a negotiation prepares (``StructureKind``), is
# ``AMENDMENT``, which ``shared`` holds for the modules that cannot import this one.
# The kind of the own estimate of a risk, and that of the base of a differential, which no
# operation serves (US-3050), are ``RISK`` and ``BASE``, which ``shared`` derives from the kinds
# the table constrains.
# The label of the main structure at its creation, as the examples of the contract name it.
MAIN_LABEL = "Structure principale"
# The counter of a structure at its creation, its own or a copy's: every resource is born at 1
# (``LockVersion`` of the contract; E-16, #2542).
FIRST_VERSION = 1
# The counter of the main structure a differential copied out of date keeps: below
# ``FIRST_VERSION``, the main structure never bears it (US-3050).
NEVER_BORNE = 0


@dataclass(frozen=True, slots=True)
class StructureView:
    """A cost structure as it is read: its attributes and its commands for the reader."""

    structure_id: UUID
    revision_id: UUID
    kind: str
    label: str
    planning_start_on: date
    is_merged: bool
    commands: tuple[CommandAvailability, ...]
    lock_version: int
    risk_id: UUID | None = None
    # Whether a differential not merged is up to date; ``None`` for any other structure (US-3050).
    is_up_to_date: bool | None = None


@dataclass(frozen=True, slots=True)
class DifferentialName:
    """What names the differential to create: its label, and the identifier the witness imposes.

    The identifier is none for the service, which draws it (US-2650/L1).
    """

    label: str
    imposed: UUID | None = None


@dataclass(frozen=True, slots=True)
class OpenedDifferential:
    """A differential just created, and its base: two structures the caller copies the main into."""

    structure_id: UUID
    base_id: UUID


@dataclass(frozen=True, slots=True)
class OwnEstimateCounted:
    """The own estimate of a risk whose counter just advanced, in the transaction of the write.

    Under the lock of the structure, once the write has written and priced its lines.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    risk_id: UUID


# What follows the counter of the own estimate of a risk, in the order of registration.
_OWN_ESTIMATES: Registry[Callable[[OwnEstimateCounted], None]] = Registry(
    "revisions.own_estimate_counted"
)


def register_own_estimate_counted(
    follower: Callable[[OwnEstimateCounted], None],
) -> Callable[[], None]:
    """Add what follows the counter of the own estimate of a risk; give its withdrawal.

    The risks register at the import of their interface (EP-08, US-2570/L1).
    """
    return _OWN_ESTIMATES.register(follower)


def _counted(
    session: Session, project_id: UUID, structure_id: UUID, values: dict[str, object]
) -> int:
    """Advance the counter of a structure with the values given; give it, its followers told.

    The own estimate of a risk tells what follows it (``register_own_estimate_counted``). The main
    structure, written for a provision line (``provision_written``), carries the own estimates of
    its revision that were up to date over to its new counter: the counter advances by one under
    the lock of the structure, so those that bore the one before were up to date until now (EP-30).
    """
    row = session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id == structure_id)
        .values(lock_version=CostStructure.lock_version + 1, **values)
        .returning(
            CostStructure.lock_version,
            CostStructure.revision_id,
            CostStructure.risk_id,
            CostStructure.kind,
        )
        .execution_options(synchronize_session=False)
    ).first()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    counter, revision_id, risk_id, kind = row
    if kind == MAIN and writing_provision(session):
        session.execute(
            update(CostStructure)
            .where(
                CostStructure.project_id == project_id,
                CostStructure.revision_id == revision_id,
                CostStructure.kind == RISK,
                CostStructure.main_lock_version == counter - 1,
            )
            .values(main_lock_version=counter)
            .execution_options(synchronize_session=False)
        )
        # The statement does not synchronize the session: an own estimate it holds reads its
        # counter again, as ``rename_own_estimates`` does of a label (#4041).
        for held in tuple(session.identity_map.values()):
            if isinstance(held, CostStructure) and held.kind == RISK:
                session.expire(held, ["main_lock_version"])
    if risk_id is not None:
        counted = OwnEstimateCounted(session, project_id, revision_id, structure_id, risk_id)
        for follower in _OWN_ESTIMATES.entries():
            follower(counted)
    return counter


def create_main_structure(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> UUID:
    """Create the main structure of the first revision of a project, its only one (WF-REV-0100)."""
    structure_id = new_id()
    session.add(
        CostStructure(
            project_id=project_id,
            id=structure_id,
            revision_id=revision_id,
            kind=MAIN,
            label=MAIN_LABEL,
            is_merged=False,
            lineage_id=structure_id,
            planning_start_on=current_day(act.at),
            scheduled_at=act.at,
            lock_version=FIRST_VERSION,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    session.flush()
    return structure_id


def create_own_estimate(
    session: Session,
    revision: tuple[UUID, UUID],
    risk: tuple[UUID, str],
    act: Act,
    kept: tuple[UUID, date] | None = None,
) -> UUID:
    """Create the own estimate of a risk in a revision, empty, labelled as it is; give it (E-09).

    ``revision`` is the project and its current revision, ``risk`` the risk and its label. Its
    planning starts on the day of its creation, as the main structure's; the risks judge the
    revision before. ``kept`` the identifier and the start of an own estimate deleted with its risk,
    which the undoing of the deletion, or the redoing of the declaration, creates again
    (US-2590/L2).
    """
    (project_id, revision_id), (risk_id, label) = revision, risk
    structure_id, start = (new_id(), current_day(act.at)) if kept is None else kept
    # Born up to date with the main structure, as a differential is (EP-30).
    main_counter = session.scalar(
        select(CostStructure.lock_version).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind == MAIN,
        )
    )
    session.add(
        CostStructure(
            project_id=project_id,
            id=structure_id,
            revision_id=revision_id,
            kind=RISK,
            label=label,
            is_merged=False,
            lineage_id=structure_id,
            risk_id=risk_id,
            main_lock_version=NEVER_BORNE if main_counter is None else main_counter,
            planning_start_on=start,
            scheduled_at=act.at,
            lock_version=FIRST_VERSION,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    session.flush()
    return structure_id


def delete_own_estimate(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Delete the own estimate of a risk deleted with it, its nodes already deleted (US-2590/L1).

    The structure is locked by the caller, which has deleted the evaluation that names it and the
    nodes it holds; what it abandons goes with it (EP-30).
    """
    _delete_abandonments(session, project_id, OwnEstimateAbandonment.structure_id == structure_id)
    session.delete(
        session.scalars(
            select(CostStructure).where(
                CostStructure.project_id == project_id,
                CostStructure.id == structure_id,
                CostStructure.kind == RISK,
            )
        ).one()
    )
    session.flush()


def consume_own_estimate(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Mark the own estimate of a risk occurred merged, its counter advanced (WF-RIS-0060).

    The occurrence consumes it: it is read ``is_merged`` in the revision it occurred in, and the
    next revision does not take its content up (``copy_structures``, ``copy_consumed_estimate``).
    Under the lock of the structure, which the caller holds; the followers of an own estimate
    counted (``register_own_estimate_counted``) are not told, the risk being written by the caller.
    """
    session.execute(
        update(CostStructure)
        .where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind == RISK,
        )
        .values(is_merged=True, lock_version=CostStructure.lock_version + 1)
        .execution_options(synchronize_session=False)
    )


def copy_consumed_estimate(copy: RevisionCopy, structure_id: UUID) -> UUID:
    """Copy the own estimate of a risk occurred into the revision opened, empty; give its copy.

    The evaluation of a risk occurred is taken up by the next revision, with its cost at occurrence,
    and it names a structure of its own revision and of its risk: the structure is copied as the
    row it is — merged, its lineage and its start kept — but not its content, which the occurrence
    consumed and which is read in the revision it occurred in (WF-REV-0100, WF-RIS-0060). Its nodes,
    its lines and its images are not taken up: ``copy_structures`` leaves it out of the identifiers
    the copies of the planning and of the estimate follow.
    """
    row = copy.session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == copy.project_id, CostStructure.id == structure_id
        )
    ).one()
    copied = new_id()
    copy.session.add(
        CostStructure(
            project_id=copy.project_id,
            id=copied,
            revision_id=copy.target,
            kind=row.kind,
            label=row.label,
            is_merged=True,
            lineage_id=row.lineage_id,
            risk_id=row.risk_id,
            main_lock_version=NEVER_BORNE,
            pruned_revision_id=row.pruned_revision_id,
            planning_start_on=row.planning_start_on,
            scheduled_at=row.scheduled_at or row.created_at,
            lock_version=FIRST_VERSION,
            created_at=copy.at,
            created_by=copy.author,
            updated_at=copy.at,
            updated_by=copy.author,
        )
    )
    copy.session.flush()
    return copied


def create_differential(
    session: Session,
    revision: tuple[UUID, UUID],
    main: StructureFacts,
    named: DifferentialName,
    act: Act,
) -> OpenedDifferential:
    """Create a differential in a revision and its base, copies of its main structure; give them.

    ``revision`` is the project and the revision, ``main`` the facts of its main structure, read
    under its lock. Both start their planning the day the main structure does and hold its dates as
    it computed them (``scheduled_at``); their nodes are copied after them (``open_differential``).
    The differential keeps the counter of the main structure read: it is up to date while the main
    structure bears it (US-3050). The lineage of each structure is its own: the next revision copies
    them under it (WF-REV-0100, WF-DAT-0030). The label is not unique: several differentials
    coexist; the base bears its differential's, which nothing reads. ``named`` the label, and the
    identifier the witness imposes on the differential, none for the service (US-2650/L1); the base
    is drawn.
    """
    project_id, revision_id = revision
    structure_id, base_id = named.imposed or new_id(), new_id()
    for each, kind, differential in (
        (structure_id, AMENDMENT, None),
        (base_id, BASE, structure_id),
    ):
        session.add(
            CostStructure(
                project_id=project_id,
                id=each,
                revision_id=revision_id,
                kind=kind,
                label=named.label,
                is_merged=False,
                lineage_id=each,
                differential_id=differential,
                main_lock_version=main.lock_version if kind == AMENDMENT else None,
                planning_start_on=main.planning_start_on,
                scheduled_at=main.scheduled_at,
                lock_version=FIRST_VERSION,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
        # The base names its differential, which is written first.
        session.flush()
    return OpenedDifferential(structure_id, base_id)


def copy_structures(copy: RevisionCopy) -> None:
    """Copy the structures of the source but the merged ones, each keeping its lineage (#1759).

    The own estimate of a risk keeps its risk (``risk_id``, EP-08), which is not revised. The base
    of a differential not merged is copied after it, naming its copy; that of a merged one is not
    copied, as its differential is not (US-3050, WF-REV-0100). A differential's counter of the main
    structure is ``NEVER_BORNE`` here, the main structure of the copy never bearing it: the state of
    each differential is given once every table is copied and the main structure redated
    (``keep_differential_states``).

    Each is copied under an identifier of its own, the one the witness imposes if it does
    (``RevisionCopy.imposed``, US-2650/L1). Each keeps the date its planning starts on and the
    instant its dates were computed (#2170): a
    null date stays null, read by the lineage the copy keeps; a null instant is the creation of the
    structure copied. The planning then redates, at the opening, those that hold a node, with the
    reference of the day (``redate_copy``, EP-06).
    """
    rows = copy.session.scalars(
        select(CostStructure)
        .where(
            CostStructure.project_id == copy.project_id,
            CostStructure.revision_id == copy.source,
            CostStructure.is_merged.is_(False),
        )
        .order_by(CostStructure.id)
    ).all()
    taken = {row.id for row in rows}
    # The differentials before their bases, which name their copies.
    for row in sorted(rows, key=lambda row: row.kind == BASE):
        if row.differential_id is not None and row.differential_id not in taken:
            continue
        copied = copy.imposed.structure(row.kind, row.lineage_id) or new_id()
        copy.identifiers[row.id] = copied
        copy.session.add(
            CostStructure(
                project_id=copy.project_id,
                id=copied,
                revision_id=copy.target,
                kind=row.kind,
                label=row.label,
                is_merged=False,
                lineage_id=row.lineage_id,
                risk_id=row.risk_id,
                differential_id=None
                if row.differential_id is None
                else copy.identifiers[row.differential_id],
                main_lock_version=None if row.main_lock_version is None else NEVER_BORNE,
                pruned_revision_id=row.pruned_revision_id,
                planning_start_on=row.planning_start_on,
                scheduled_at=row.scheduled_at or row.created_at,
                lock_version=FIRST_VERSION,
                created_at=copy.at,
                created_by=copy.author,
                updated_at=copy.at,
                updated_by=copy.author,
            )
        )
    copy.session.flush()


def delete_structures(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Delete the structures of a revision being abandoned, row by row (WF-DAT-0010).

    What the own estimates abandon first, then the bases, which name their differentials
    (US-3050, EP-30).
    """
    _delete_abandonments(session, project_id, OwnEstimateAbandonment.revision_id == revision_id)
    rows = session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id, CostStructure.revision_id == revision_id
        )
    ).all()
    for row in sorted(rows, key=lambda row: row.kind != BASE):
        session.delete(row)
        if row.kind == BASE:
            session.flush()
    session.flush()


def _delete_abandonments(
    session: Session, project_id: UUID, criterion: ColumnElement[bool]
) -> None:
    """Delete what own estimates abandon, of a project, as the criterion retains (EP-30)."""
    session.execute(
        delete(OwnEstimateAbandonment)
        .where(OwnEstimateAbandonment.project_id == project_id, criterion)
        .execution_options(synchronize_session=False)
    )


def _structures(
    session: Session, project_id: UUID, revision_id: UUID
) -> list[tuple[CostStructure, datetime]]:
    """Read the structures of a revision, the main one first, with the birth of their lineage.

    A structure whose lineage lost its origin is born with itself: it is listed all the same. The
    bases are not read (US-3050).
    """
    origin = aliased(CostStructure)
    rows = session.execute(
        select(CostStructure, func.coalesce(origin.created_at, CostStructure.created_at))
        .outerjoin(
            origin,
            (origin.project_id == CostStructure.project_id)
            & (origin.id == CostStructure.lineage_id),
        )
        .where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind != BASE,
        )
        .order_by((CostStructure.kind != MAIN), CostStructure.label, CostStructure.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def revision_structures(session: Session, project_id: UUID, revision_id: UUID) -> tuple[UUID, ...]:
    """Give the structures of a revision, in the order of their identifiers, unlocked.

    The caller locks them (``structure_facts``, ``lock=True``, ``base=True``), in that order. The
    bases come with the others: what prices or redates every structure of a revision writes them
    too, so that a differential and its base are read alike (US-3050).
    """
    return tuple(
        session.scalars(
            select(CostStructure.id)
            .where(CostStructure.project_id == project_id, CostStructure.revision_id == revision_id)
            .order_by(CostStructure.id)
        )
    )


def structure_counters(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[tuple[UUID, int], ...]:
    """Give the counter of every structure of a revision, by identifier, bases and estimates too.

    What the key of the cache of the indicators reads: every write of a structure advances its
    counter under its lock, a differential or the own estimate of a risk as the main structure
    (``structure_counted``), and one that opens or ends moves the list (US-2630/L1, #3629).
    """
    return tuple(
        (row[0], row[1])
        for row in session.execute(
            select(CostStructure.id, CostStructure.lock_version)
            .where(CostStructure.project_id == project_id, CostStructure.revision_id == revision_id)
            .order_by(CostStructure.id)
        )
    )


def _up_to_date(row: CostStructure, main_counter: int | None) -> bool | None:
    """Tell whether a differential not merged is up to date; ``None`` for any other structure.

    Up to date while the main structure bears the counter its base was taken at (US-3050); a
    merged differential, consumed, has no update left, and says nothing of it.
    """
    if row.kind != AMENDMENT or row.is_merged:
        return None
    return row.main_lock_version == main_counter


def _nature(row: CostStructure, main_counter: int | None) -> StructureNature:
    """Tell what the commands of a structure read of it: the main one, a differential not merged.

    ``main_counter`` that of the main structure of its revision: a differential up to date has
    nothing to carry over (US-3050).
    """
    if row.kind == MAIN:
        return MAIN_NATURE
    if row.kind == AMENDMENT:
        if row.is_merged:
            return "amendment"
        return UP_TO_DATE_NATURE if _up_to_date(row, main_counter) else DIFFERENTIAL_NATURE
    return "risk"


def list_cost_structures(
    session: Session, project_id: UUID, revision_id: UUID, viewer: Viewer
) -> list[StructureView]:
    """List the structures of a revision, with their commands (``listCostStructures``); or 404.

    The bases are not listed (US-3050).
    """
    revision = revision_state(session, project_id, revision_id)
    state = project_facts(session, project_id).state
    kind = contributor_kind(session, project_id, viewer.user_id)
    rows = _structures(session, project_id, revision_id)
    main_counter = next((row.lock_version for row, _ in rows if row.kind == MAIN), None)
    return [
        StructureView(
            structure_id=row.id,
            revision_id=row.revision_id,
            kind=row.kind,
            label=row.label,
            planning_start_on=row.planning_start_on or born.date(),
            is_merged=row.is_merged,
            commands=tuple(
                CommandAvailability(command, missing)
                for command, missing in structure_commands_of(
                    viewer.permissions,
                    kind,
                    state,
                    revision,
                    nature=_nature(row, main_counter),
                )
            ),
            lock_version=row.lock_version,
            risk_id=row.risk_id,
            is_up_to_date=_up_to_date(row, main_counter),
        )
        for row, born in rows
    ]


def aimed_structure(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID | None
) -> UUID | None:
    """Give the structure of a revision an import aims at: the one named, or the main one.

    ``None`` when the structure named is not one of the revision — unknown, of another revision or
    of another project, or a base (US-3050) —, which the opening of an import refuses (404, EP-06).
    """
    criteria = [
        CostStructure.project_id == project_id,
        CostStructure.revision_id == revision_id,
        CostStructure.kind != BASE,
    ]
    if structure_id is None:
        criteria.append(CostStructure.kind == MAIN)
    else:
        criteria.append(CostStructure.id == structure_id)
    return session.scalar(select(CostStructure.id).where(*criteria))


def main_structures_of(session: Session, revision_ids: Collection[UUID]) -> dict[UUID, UUID]:
    """Give the main structure of each of the revisions that has one, in one statement."""
    rows = session.execute(
        select(CostStructure.revision_id, CostStructure.id).where(
            CostStructure.revision_id.in_(revision_ids), CostStructure.kind == MAIN
        )
    )
    return {row[0]: row[1] for row in rows}


def structure_in_revision(
    session: Session, project_id: UUID, structure_id: UUID, revision_id: UUID
) -> UUID | None:
    """Give the structure of a revision that is ``structure_id``, or the copy of its lineage.

    An import analysed on a structure of the last marked revision applies to the copy the current
    revision holds of it (WF-INTF-0090, EP-06); ``None`` when the revision holds none, and for a
    base, which no import aims at (US-3050).
    """
    lineage = session.scalar(
        select(CostStructure.lineage_id).where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind != BASE,
        )
    )
    if lineage is None:
        return None
    return session.scalar(
        select(CostStructure.id).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.lineage_id == lineage,
        )
    )


def read_cost_structure(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID, viewer: Viewer
) -> StructureView:
    """Read a structure of a revision as the list gives it, with its commands; or 404."""
    for view in list_cost_structures(session, project_id, revision_id, viewer):
        if view.structure_id == structure_id:
            return view
    raise NotFoundError(NOT_FOUND)


def structure_commands(
    session: Session, project_id: UUID, revision_id: UUID, structure_id: UUID, viewer: Viewer
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a structure of a revision and the conditions each lacks; or 404."""
    return read_cost_structure(session, project_id, revision_id, structure_id, viewer).commands


def structure_phase_conditions(command: str, state: str, *, main: bool) -> tuple[str, ...]:
    """Name the condition of the phase of the project an entry of a structure lacks, if any.

    The rule the commands of a structure state in advance (``structure_commands``), for an entry
    sent in spite of them: on the main structure, ``project_before_in_progress`` for the estimate
    and ``project_in_progress`` for the remaining to commit; nothing for the planning, nor on
    another structure (WF-DEV-0050, WF-RAE-0040; #2494). A terminal project is judged before.
    """
    return tuple(phase_conditions(command, state, main=main))


def abandon_structure(
    session: Session, project_id: UUID, structure: StructureFacts, act: Act
) -> None:
    """Delete the row of a differential and inscribe its abandonment (``structure_abandon``).

    To be called under the lock of the structure, once the modules that hold rows of its own
    (``abandon_differential``: the history, the nodes and their facets, its base's too) have
    deleted them; its base goes before it, which names it (US-3050). The inscription names the
    structure by its label of the moment, in its revision, which is current and bears no name yet
    (WF-SEC-0030).
    """
    inscribe_structure(session, project_id, structure, act)
    for criterion in (
        CostStructure.differential_id == structure.structure_id,
        CostStructure.id == structure.structure_id,
    ):
        session.execute(
            delete(CostStructure)
            .where(CostStructure.project_id == project_id, criterion)
            .execution_options(synchronize_session=False)
        )
    session.flush()


@dataclass(frozen=True, slots=True)
class StructureFacts:
    """What the planning reads of a structure: its revision, its kind, its start, its instant.

    ``planning_start_on`` and ``scheduled_at`` are derived as the list reads them when the
    migration left them null (#2170); ``lock_version`` is the counter of its writes, ``kind`` its
    nature.
    """

    structure_id: UUID
    revision_id: UUID
    is_main: bool
    planning_start_on: date
    scheduled_at: datetime
    lock_version: int
    label: str
    kind: str = MAIN
    is_merged: bool = False

    @property
    def is_differential(self) -> bool:
        """Tell whether the structure is a differential, read against the main one (WF-REV-0100)."""
        return self.kind == AMENDMENT


def structure_facts(
    session: Session, project_id: UUID, structure_id: UUID, *, lock: bool, base: bool = False
) -> StructureFacts:
    """Read a structure of a project; or refuse (404).

    ``lock`` takes it ``FOR UPDATE`` and reads it under the lock: every write of its nodes does,
    after the revision and the stack of the history (EP-06, "L'historique annulable"). The base of
    a differential is refused as an unknown structure, no operation serving it, unless ``base``
    asks it: what sweeps every structure of a revision to price or redate it, and the reading of a
    differential against its base (US-3050).
    """
    query = select(CostStructure).where(
        CostStructure.project_id == project_id, CostStructure.id == structure_id
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = session.scalars(query).first()
    if row is None or (row.kind == BASE and not base):
        raise NotFoundError(NOT_FOUND)
    start, at = row.planning_start_on, row.scheduled_at or row.created_at
    if start is None:
        origin = session.scalar(
            select(CostStructure.created_at).where(
                CostStructure.project_id == project_id, CostStructure.id == row.lineage_id
            )
        )
        start = (origin or row.created_at).date()
    return StructureFacts(
        row.id,
        row.revision_id,
        row.kind == MAIN,
        start,
        at,
        row.lock_version,
        row.label,
        row.kind,
        row.is_merged,
    )


def structure_rescheduled(
    session: Session, project_id: UUID, structure_id: UUID, at: datetime
) -> int:
    """Move the instant of the dates of a structure on to ``at``, advance its counter; give it.

    To be called under the lock of the structure (``structure_facts``), by a write that redates it,
    once it has priced its lines: the own estimate of a risk tells what follows it.
    """
    return _counted(session, project_id, structure_id, {"scheduled_at": at})


def structure_counted(session: Session, project_id: UUID, structure_id: UUID) -> int:
    """Advance the counter of a structure, the instant of its dates left as it is; give it.

    To be called under the lock of the structure (``structure_facts``), by a write that can move
    no date (US-2250): the front leans every write on the counter, and ``scheduled_at`` is the
    instant of the last write that redated the structure, which this one does not. The own
    estimate of a risk tells what follows it.
    """
    return _counted(session, project_id, structure_id, {})


def write_structure(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    change: tuple[date | None, str | None],
    act: Act,
) -> None:
    """Write the start and the label of a structure, each when given (``updateCostStructure``).

    To be called under the lock of the structure (``structure_facts``); its counter advances with
    the redating that follows (``structure_rescheduled``), once per write.
    """
    planning_start_on, label = change
    values: dict[str, object] = {"updated_at": act.at, "updated_by": act.author}
    if planning_start_on is not None:
        values["planning_start_on"] = planning_start_on
    if label is not None:
        values["label"] = label
    session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id == structure_id)
        .values(**values)
        .execution_options(synchronize_session=False)
    )


def rename_own_estimate(
    session: Session, project_id: UUID, structure_id: UUID, label: str, act: Act
) -> None:
    """Write the label of the own estimate of a risk, its counter advancing; tell no follower.

    The risks rename it with their risk (``updateRisk``, #3980), and advance the counter of the
    risk themselves, so that the followers of the own estimate (``register_own_estimate_counted``)
    are not told a second time. To be called under the lock of the structure (``structure_facts``).
    """
    session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id == structure_id)
        .values(
            label=label,
            lock_version=CostStructure.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .execution_options(synchronize_session=False)
    )


def rename_own_estimates(session: Session, project_id: UUID, labels: dict[UUID, str]) -> None:
    """Label the own estimates of a revision opened by their risks' labels, in one statement.

    ``labels`` maps each own estimate to the label of its risk: the copy of a revision names them
    from the risk, not from the structures it copies (#3980). They are new, at their first version.

    The copy added their objects to the session with the label it copied, and the statement does not
    synchronize the session: the label of each object the session holds is expired, so that a
    reading by the ORM in the same transaction gives the new one (#4041).
    """
    if not labels:
        return
    session.execute(
        update(CostStructure)
        .where(CostStructure.project_id == project_id, CostStructure.id.in_(labels))
        .values(label=case(labels, value=CostStructure.id))
        .execution_options(synchronize_session=False)
    )
    for held in tuple(session.identity_map.values()):
        if isinstance(held, CostStructure) and held.id in labels:
            session.expire(held, ["label"])


@dataclass(frozen=True, slots=True)
class CurrentStructure:
    """A structure of a current revision: its project, its revision, itself."""

    project_id: UUID
    revision_id: UUID
    structure_id: UUID


def current_structures(
    session: Session, *, lock: bool, reference_year: int | None = None
) -> tuple[CurrentStructure, ...]:
    """Give the structures of the current revisions, in the order of (``project_id``, ``id``).

    ``reference_year`` keeps the revisions of that year of reference alone, before the lock: the
    others are not shared (US-1500/L2).

    ``lock`` reads their revisions ``FOR SHARE``: a revision marked or abandoned meanwhile is left
    out, and none is until the transaction ends — what a change of the reference takes before it
    locks each structure in this order to redate it (EP-06, "Ce que le cadrage décide").
    """
    query = (
        select(CostStructure.project_id, CostStructure.revision_id, CostStructure.id)
        .join(
            Revision,
            (Revision.project_id == CostStructure.project_id)
            & (Revision.id == CostStructure.revision_id),
        )
        .where(Revision.status == "draft")
        .order_by(CostStructure.project_id, CostStructure.id)
    )
    if reference_year is not None:
        query = query.where(Revision.reference_year == reference_year)
    if lock:
        query = query.with_for_update(read=True, of=Revision)
    return tuple(CurrentStructure(*row) for row in session.execute(query))
