# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimate of a risk prepared as a differential: its states, and how the others extend it.

The own estimate of a risk is a differential of the main structure (EP-30, "Les états d'un devis
propre"). **Whole** in the current revision: its structure holds every node of the project, copied
under their lineages, with what it designates, and it has its base. **Pruned** by a marking: its
structure holds only what it designates, without a base, and it names the marked revision against
whose main structure its differences are exact (``CostStructure.pruned_revision_id``), until a
recomposition makes it whole again. **Up to date or out of date** as a differential: up to date
while the main structure of its revision bears the counter it retained (``main_lock_version``),
the write of a provision line set apart (``provision_written``, ``shared``). **Consumed** once its
risk occurred (``is_merged``). ``own_estimate_state`` reads them for one, ``own_estimate_states``
for every own estimate of a revision; ``own_estimate_state_of`` is the rule, on the columns read.

What an own estimate pruned abandons — a node by its lineage, a link by the lineages of its two
tasks — is kept apart (``Abandonment``, the table ``own_estimate_abandonment``): written by the
pruning (``record_abandonments``), read by the recomposition (``abandonments_of``), taken up by the
copy of a revision (``copy_abandonments``), deleted with its structure.

Three registries, filled by the modules above, which this one does not import (EP-30, "Modules"):

- ``register_compose``: the recomposition of an own estimate pruned. Its stages run in their order
  (``COMPOSE_STAGES``), each part of a stage in the order of its registration: ``nodes``, where the
  planning and the estimate each copy their part of the main structure of the revision named into
  the base and into the structure, then lay over the structure what the own estimate keeps — the
  nodes it holds replace or complete those of the copy, what it abandons leaves it —; then ``end``,
  what is done once on the structure all the parts leave: the engine of the dates replayed once, the
  lines priced again.
- ``register_prune``: the pruning of an own estimate whole and up to date, at the marking. ``kept``,
  where each module tells what it keeps of the structure — what it designates against its base, the
  ancestors and the ends of its links — and what it abandons (``OwnEstimatePruning.abandoned``);
  then ``pruned``, where the rest of the structure and the base are deleted.
- ``register_before_marking``: what a module does before a marking, or the merge of an amendment,
  writes anything — the risks update their own estimates, or refuse —; called in the transaction of
  the task (the worker's, or the loader's of the witness), the project locked and the revision
  current: the one marked, locked before its project; or, for a merge, the current revision it is
  asked on, locked before its project, or the one it has just opened when the project had none,
  which no other transaction sees. A refusal fails the task, nothing written.

``compose_parts`` and ``prune_parts`` run the parts registered; the recomposition and the pruning
themselves, which frame them, are the stories' that serve them (US-3070). Declared by US-3070/L1,
with nothing registered.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from sqlalchemy import insert, select

from waterfall.core.revisions.interface.shared import MAIN, RISK
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import CostStructure, OwnEstimateAbandonment
from waterfall.platform.errors import NOT_FOUND, NotFoundError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface.revisions import RevisionCopy
    from waterfall.platform.audit import Act

# The stages of a recomposition and of a pruning, in the order they run.
type ComposeStage = Literal["nodes", "end"]
COMPOSE_STAGES: tuple[ComposeStage, ...] = ("nodes", "end")
type PruneStage = Literal["kept", "pruned"]
PRUNE_STAGES: tuple[PruneStage, ...] = ("kept", "pruned")


@dataclass(frozen=True, slots=True)
class OwnEstimateState:
    """The state of the own estimate of a risk in its revision (EP-30).

    ``pruned_revision_id`` the marked revision its differences are exact against, none while it is
    whole; ``up_to_date`` whether the main structure of its revision bears the counter it retained;
    ``consumed`` whether its risk occurred.
    """

    structure_id: UUID
    risk_id: UUID
    pruned_revision_id: UUID | None
    up_to_date: bool
    consumed: bool

    @property
    def whole(self) -> bool:
        """Tell whether it holds every node of the project, with its base."""
        return self.pruned_revision_id is None

    @property
    def pruned(self) -> bool:
        """Tell whether it holds only what it designates, without a base."""
        return self.pruned_revision_id is not None


def own_estimate_state_of(row: CostStructure, main_counter: int | None) -> OwnEstimateState:
    """Give the state of an own estimate read, ``main_counter`` that of its main structure.

    Up to date while the main structure bears the counter it retained, as a differential is.
    """
    if row.kind != RISK or row.risk_id is None:
        msg = f"the structure {row.id} is no own estimate of a risk"
        raise ValueError(msg)
    return OwnEstimateState(
        structure_id=row.id,
        risk_id=row.risk_id,
        pruned_revision_id=row.pruned_revision_id,
        up_to_date=row.main_lock_version == main_counter,
        consumed=row.is_merged,
    )


def _main_counter(session: Session, project_id: UUID, revision_id: UUID) -> int | None:
    """Give the counter of the main structure of a revision."""
    return session.scalar(
        select(CostStructure.lock_version).where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind == MAIN,
        )
    )


def own_estimate_state(session: Session, project_id: UUID, structure_id: UUID) -> OwnEstimateState:
    """Read the state of the own estimate of a risk; or refuse (404) for any other structure."""
    row = session.scalars(
        select(CostStructure).where(
            CostStructure.project_id == project_id,
            CostStructure.id == structure_id,
            CostStructure.kind == RISK,
        )
    ).first()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    return own_estimate_state_of(row, _main_counter(session, project_id, row.revision_id))


def own_estimate_states(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[OwnEstimateState, ...]:
    """Read the state of every own estimate of a revision, in the order of their identifiers."""
    rows = session.scalars(
        select(CostStructure)
        .where(
            CostStructure.project_id == project_id,
            CostStructure.revision_id == revision_id,
            CostStructure.kind == RISK,
        )
        .order_by(CostStructure.id)
    ).all()
    counter = _main_counter(session, project_id, revision_id)
    return tuple(own_estimate_state_of(row, counter) for row in rows)


# --- What an own estimate pruned abandons --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Abandonment:
    """What an own estimate pruned abandons: a node by its lineage, or a link by its two tasks'.

    ``link`` the lineages of the predecessor and of the successor; exactly one of the two is given.
    """

    lineage_id: UUID | None = None
    link: tuple[UUID, UUID] | None = None

    def __post_init__(self) -> None:
        """Refuse an abandonment of nothing, or of a node and a link at once."""
        if (self.lineage_id is None) == (self.link is None):
            msg = "an abandonment names a node or a link, and not both"
            raise ValueError(msg)


def abandonments_of(
    session: Session, project_id: UUID, structure_id: UUID
) -> tuple[Abandonment, ...]:
    """Read what an own estimate pruned abandons: the nodes, then the links, each in their order."""
    rows = session.execute(
        select(
            OwnEstimateAbandonment.node_lineage_id,
            OwnEstimateAbandonment.predecessor_lineage_id,
            OwnEstimateAbandonment.successor_lineage_id,
        )
        .where(
            OwnEstimateAbandonment.project_id == project_id,
            OwnEstimateAbandonment.structure_id == structure_id,
        )
        .order_by(
            OwnEstimateAbandonment.node_lineage_id.is_(None),
            OwnEstimateAbandonment.node_lineage_id,
            OwnEstimateAbandonment.predecessor_lineage_id,
            OwnEstimateAbandonment.successor_lineage_id,
        )
    ).all()
    return tuple(_abandonment(node, before, after) for node, before, after in rows)


def _abandonment(node: UUID | None, before: UUID | None, after: UUID | None) -> Abandonment:
    """Give the abandonment a row holds: its node, or its link, which its check makes whole."""
    if before is None or after is None:
        return Abandonment(node)
    return Abandonment(link=(before, after))


def record_abandonments(
    session: Session,
    structure: tuple[UUID, UUID, UUID],
    abandoned: Collection[Abandonment],
    act: Act,
) -> None:
    """Write what an own estimate pruned abandons; ``structure`` its project, revision and itself.

    The pruning writes them once, in the transaction of the marking, before the revision is marked.
    """
    if not abandoned:
        return
    project_id, revision_id, structure_id = structure
    session.execute(
        insert(OwnEstimateAbandonment),
        [
            {
                "project_id": project_id,
                "id": new_id(),
                "revision_id": revision_id,
                "structure_id": structure_id,
                "node_lineage_id": each.lineage_id,
                "predecessor_lineage_id": None if each.link is None else each.link[0],
                "successor_lineage_id": None if each.link is None else each.link[1],
                "created_at": act.at,
                "created_by": act.author,
            }
            for each in abandoned
        ],
    )


def copy_abandonments(copy: RevisionCopy) -> None:
    """Copy the abandonments of the own estimates the copy of a revision took up, under their copy.

    Called once the structures are copied: an own estimate consumed, copied empty, is not in
    ``copy.identifiers`` and takes up none (WF-RIS-0060).
    """
    rows = copy.session.scalars(
        select(OwnEstimateAbandonment)
        .where(
            OwnEstimateAbandonment.project_id == copy.project_id,
            OwnEstimateAbandonment.revision_id == copy.source,
        )
        .order_by(OwnEstimateAbandonment.id)
    ).all()
    taken = [row for row in rows if row.structure_id in copy.identifiers]
    if not taken:
        return
    copy.session.execute(
        insert(OwnEstimateAbandonment),
        [
            {
                "project_id": copy.project_id,
                "id": new_id(),
                "revision_id": copy.target,
                "structure_id": copy.identifiers[row.structure_id],
                "node_lineage_id": row.node_lineage_id,
                "predecessor_lineage_id": row.predecessor_lineage_id,
                "successor_lineage_id": row.successor_lineage_id,
                "created_at": copy.at,
                "created_by": copy.author,
            }
            for row in taken
        ],
    )


# --- The recomposition and the pruning, by the modules above -------------------------------------


@dataclass(frozen=True, slots=True)
class OwnEstimateComposing:
    """The recomposition of an own estimate pruned, in its transaction, its structures locked.

    ``structure_id`` the own estimate, in ``revision_id``, the current revision; ``base_id`` its
    base, created empty; ``source`` the marked revision it names and the main structure of that
    revision, which the parts copy; ``abandoned`` what it abandons, which leaves the copy.
    ``shared`` what a part computes once for those after it, under a key of its own.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    base_id: UUID
    source: tuple[UUID, UUID]
    abandoned: tuple[Abandonment, ...]
    act: Act
    shared: dict[str, object] = field(default_factory=dict[str, object])


@dataclass(frozen=True, slots=True)
class OwnEstimatePruning:
    """The pruning of an own estimate whole and up to date, in the transaction of the marking.

    ``structure_id`` the own estimate, ``base_id`` its base, in ``revision_id``, being marked. The
    parts of the stage ``kept`` add to ``abandoned`` what it abandons, which the pruning writes;
    ``shared`` what a part computes once for those after it — what each keeps, under a key of its
    own.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    base_id: UUID
    act: Act
    abandoned: list[Abandonment] = field(default_factory=list[Abandonment])
    shared: dict[str, object] = field(default_factory=dict[str, object])


# What each module does of a recomposition and of a pruning, under its stage, in the order of
# registration: the planning before the estimate, whose lines name its tasks.
_COMPOSES: Registry[tuple[ComposeStage, Callable[[OwnEstimateComposing], None]]] = Registry(
    "revisions.compose"
)
_PRUNES: Registry[tuple[PruneStage, Callable[[OwnEstimatePruning], None]]] = Registry(
    "revisions.prune"
)


def register_compose(
    stage: ComposeStage, part: Callable[[OwnEstimateComposing], None]
) -> Callable[[], None]:
    """Add the part a module takes of a recomposition, under a stage; give its withdrawal.

    A module registers at the import of its interface, which imports this one first.
    """
    return _COMPOSES.register((stage, part))


def register_prune(
    stage: PruneStage, part: Callable[[OwnEstimatePruning], None]
) -> Callable[[], None]:
    """Add the part a module takes of a pruning, under a stage; give its withdrawal."""
    return _PRUNES.register((stage, part))


def compose_parts(composing: OwnEstimateComposing) -> None:
    """Have every module registered do its part of a recomposition, stage by stage."""
    registered = _COMPOSES.entries()
    for stage in COMPOSE_STAGES:
        for held, part in registered:
            if held == stage:
                part(composing)


def prune_parts(pruning: OwnEstimatePruning) -> tuple[Abandonment, ...]:
    """Have every module registered do its part of a pruning, stage by stage; give what it abandons.

    An abandonment told twice — by two parts, or twice by one — is given once, in the order told.
    """
    registered = _PRUNES.entries()
    for stage in PRUNE_STAGES:
        for held, part in registered:
            if held == stage:
                part(pruning)
    return tuple(dict.fromkeys(pruning.abandoned))


# --- Before a marking or a merge -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BeforeMarking:
    """A marking, or the merge of an amendment, about to write, in the transaction of its task.

    ``revision_id`` the current revision the marking or the merge marks: the one marked, or the
    one the merge is asked on, both locked before the project; for a merge without a current
    revision, the one it has just opened, which no other transaction sees. ``merged`` the
    amendment merged in that revision (the copy of the differential, for a revision opened), none
    for a marking. The project is locked.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    act: Act
    merged: UUID | None = None


# What a module does before a marking or a merge writes, in the order of registration: the risks'.
_BEFORE_MARKINGS: Registry[Callable[[BeforeMarking], None]] = Registry("revisions.before_marking")


def register_before_marking(update: Callable[[BeforeMarking], None]) -> Callable[[], None]:
    """Add what a module does before a marking or a merge writes anything; give its withdrawal.

    The risks update the own estimates of the risks identified, or refuse naming them (EP-30,
    US-3090): a refusal raised here fails the task, nothing written.
    """
    return _BEFORE_MARKINGS.register(update)


def before_marking(before: BeforeMarking) -> None:
    """Have each module registered do what it does before a marking or a merge writes.

    Nothing is caught: a refusal rises to the worker, which fails the task with its code.
    """
    for update in _BEFORE_MARKINGS.entries():
        update(before)
