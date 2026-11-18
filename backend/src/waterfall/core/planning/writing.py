# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How a write of the tree is framed, private to the module (EP-06, "Modules").

A write of the nodes of a structure judges the state of its revision under the lock of the
revision, read ``FOR SHARE`` (``revision_draft``): refused on a terminal project
(``project_not_terminal``), on a marked revision (``revision_draft``), while a background task
other than the writer's own — the application of an import — writes in the project
(``no_background_task_running``), in that order (409, WF-CYC-0100, WF-DAT-0020, WF-IHM-0090).
It then opens its entry of the history (``history.recording``), which
locks the stack of its writer, and only then locks its structure (``cost_structure`` ``FOR
UPDATE``) and reads the tree under that lock: the locks come in one order — the revision, the
stack, the structure — whatever the write, an undoing included. Before them all, the facets of the
other kinds take what they must hold first (``FacetHooks.before_lock``): the estimate shares the
lock of the natures of cost, which a change of a nature takes before the structures it prices again
(#2615).

Under the lock, the write hands the history the nodes it touches as they are (``snapshot``),
writes, replays the engine on the whole structure and keeps what it computes (``dating``), moves
the instant of the structure's dates on and advances its counter, hands the nodes as they now are,
and gives back what it wrote (``NodesWritten``) before its transaction commits. The tree is read
once, under the lock: the write hands it to the replay, which brings it to what the write made of
it — the nodes it created, deleted or moved — rather than read it again (``Write.redate``,
``reshaped``, US-2250).

A write that can move no date nor change an amount — every column it sends inert, as the facet of
its kind declares them (``INERT_TASK_FIELDS``, ``FacetHooks.inert``) — takes the short path
(``Write.count``, US-2250, #3169): no engine replayed, no tree read again, the instant of the
structure's dates left as it is (the contract dates ``scheduled_at`` by the last write that
redated the structure), its counter advanced, on which the front leans every write. It gives back
what the whole path would, the nodes written and their ancestors read from the tree it holds. That
tree is read as rows, the nodes it writes alone as objects of the session, when the write knows
before its lock that it takes the short path (``Write.inert``, US-2250/L2, #3540): an entry of a
cell, of a line or of the inscriptions of a task.

A writer whose token carries no session of sign-in (``sid``) has no stack: its write is made, and
no entry kept (#2472).
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.history import interface as history
from waterfall.core.history.interface import RecordedChange, Recording, UndoStack
from waterfall.core.planning.dating import conflicts_of
from waterfall.core.planning.interface.facets import (
    calendars_of,
    facets,
    refused_at,
)
from waterfall.core.planning.rescheduling import Blamed, Holding, Named, replayed
from waterfall.core.planning.snapshotting import taken
from waterfall.core.planning.tree import (
    read_inert,
    read_link_rows,
    read_links,
    read_tree,
)
from waterfall.core.planning.views import NodeView, Reading, ScheduleView
from waterfall.core.projects.interface import (
    NO_BACKGROUND_TASK_RUNNING,
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    no_background_task_running,
    project_facts,
)
from waterfall.core.revisions.interface import (
    revision_draft,
    structure_counted,
    structure_facts,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    STATE_FORBIDS_OPERATION,
    ConflictError,
    NotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Mapping, Sequence
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import UndoneKind
    from waterfall.core.planning.interface.facets import Amounts
    from waterfall.core.planning.scheduling import Origin
    from waterfall.core.planning.tables import Node, Task
    from waterfall.core.planning.tree import (
        InertTree,
        LinkColumns,
        NodeColumns,
        TaskColumns,
        Tree,
    )
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Place:
    """The structure a request names: its project, its revision, itself."""

    project_id: UUID
    revision_id: UUID
    structure_id: UUID


@dataclass(frozen=True, slots=True)
class Writer:
    """Who writes, and when: the act, and the session of sign-in its stack is kept by.

    ``running`` is the background task that writes, the application of an import, which does not
    suspend its own writes; none for a write of a request.
    """

    act: Act
    session_id: str | None
    running: UUID | None = None


@dataclass(frozen=True, slots=True)
class InflationView:
    """The amounts of a node a write priced again without writing it (``NodeInflation``)."""

    node_id: UUID
    budgeted: Decimal
    reestimated: Decimal
    consumption_year: int | None


@dataclass(frozen=True, slots=True)
class StructureTotals:
    """The totals of a whole structure (``NodeTotals``): its lines counted, their figures summed."""

    line_count: int
    amounts: Amounts


@dataclass(frozen=True, slots=True)
class NodesWritten:
    """What a write of the tree gives back (``NodesWritten``), the totals of the structure.

    ``nodes`` the nodes written, ``ancestors`` the summaries above them and above the tasks it
    redated, ``rescheduled`` the other tasks it redated, ``reinflated`` the nodes of the other kinds
    and the tasks whose amounts it changed without writing them, each in the order of the plan;
    ``totals`` none for a write that read no structure (a paste that writes nothing).
    """

    nodes: tuple[NodeView, ...]
    ancestors: tuple[NodeView, ...]
    rescheduled: tuple[ScheduleView, ...]
    task_count: int
    structure_lock_version: int
    reinflated: tuple[InflationView, ...] = ()
    totals: StructureTotals | None = None


def facts_of(session: Session, place: Place, *, lock: bool) -> StructureFacts:
    """Read the structure a request names, of its revision and its project; or refuse (404)."""
    facts = structure_facts(session, place.project_id, place.structure_id, lock=lock)
    if facts.revision_id != place.revision_id:
        raise NotFoundError(NOT_FOUND)
    return facts


def judge_revision(
    session: Session, project_id: UUID, revision_id: UUID, running: UUID | None = None
) -> None:
    """Refuse a write the state forbids, the first missing condition named (409).

    The revision is read under ``FOR SHARE``: its marking and its abandonment wait for the write,
    and the project of a current revision cannot leave its cycle meanwhile (``exitProject`` asks
    it to have none). ``running`` is the background task that writes, which is not counted.
    """
    try:
        revision_draft(session, revision_id)
    except ConflictError:
        if project_facts(session, project_id).state in TERMINAL:
            raise ConflictError(
                STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL}
            ) from None
        raise
    if not no_background_task_running(session, project_id, running):
        raise ConflictError(
            STATE_FORBIDS_OPERATION, {"missing_condition": NO_BACKGROUND_TASK_RUNNING}
        )


@contextmanager
def _recorded(
    session: Session, place: Place, writer: Writer, change: tuple[UndoneKind, tuple[UUID, ...]]
) -> Generator[Recording]:
    """Open the entry of the history of a write, or a frame that keeps nothing without a stack."""
    author, session_id = writer.act.author, writer.session_id
    if author is None or session_id is None:
        yield Recording()
        return
    kind, node_ids = change
    stack = UndoStack(place.revision_id, author, session_id)
    entry = RecordedChange(place.project_id, stack, kind, node_ids, writer.act.at)
    # Named through its package: the function bears the name of the file that declares it.
    with history.recording(session, entry) as frame:
        yield frame


class Write:
    """A write of the tree under the lock of its structure, the tree read under that lock."""

    def __init__(
        self,
        session: Session,
        place: Place,
        writer: Writer,
        frame: Recording,
        inert: Collection[UUID] = (),
    ) -> None:
        """Lock the structure, then read it, its tree and its links under the lock.

        The links in conflict are taken before the write, so that the replay that follows judges
        what moved against them, whatever links the write deletes (``kept``); the links themselves
        are what the short path reads the nodes it gives back with (``count``). A write whose
        columns are all inert names the nodes it writes (``inert``): its structure and its links
        are read as rows, those nodes alone as objects of the session (``read_inert``, #3540).
        """
        self.session = session
        self.place = place
        self.writer = writer
        self.frame = frame
        self.facts = facts_of(session, place, lock=True)
        project_id, structure_id = place.project_id, place.structure_id
        self._tree: Tree | None = None
        self.inert: InertTree | None = None
        self.links: Sequence[LinkColumns]
        if inert:
            self.inert = read_inert(session, project_id, structure_id, inert)
            self.links = read_link_rows(session, project_id, structure_id)
        else:
            self._tree = read_tree(session, project_id, structure_id)
            self.links = read_links(session, project_id, structure_id)
        self.touched: set[UUID] = set()
        self.conflicts = conflicts_of(self.links)

    @property
    def tree(self) -> Tree:
        """Give the tree of the structure as objects of the session, read under the lock.

        Read with the structure but for a write whose columns are all inert, which holds it as rows
        (``inert``), and reads it only if it takes the whole path after all (``redate``).
        """
        if self._tree is None:
            self._tree = read_tree(self.session, self.place.project_id, self.place.structure_id)
        return self._tree

    def name(self, node_ids: tuple[UUID, ...]) -> None:
        """Name the nodes of the entry when the write knows them only once its rows are judged."""
        self.frame.name(node_ids)

    def before(self, node_ids: Collection[UUID]) -> None:
        """Hand the history the nodes the write touches, as they are before it."""
        self.touched.update(node_ids)
        self.frame.keep_before(taken(self.session, self.place.project_id, node_ids))

    def redate(
        self,
        blamed: tuple[UUID | None, str] | None,
        origin: Origin = None,
        repriced: Collection[UUID] = (),
        entered: tuple[str, ...] = (),
        among: Mapping[UUID, Named] | None = None,
    ) -> Redated:
        """Replay the engine on the structure written, keep what it computes, advance it.

        Beyond the horizon (WF-PLA-0150), refused naming the task written — its node, null for a
        task created, and its label (422 ``PROJECT_HORIZON_EXCEEDED``) —, or, for a write that
        writes no task (``blamed`` none), the task that finishes last; a loop of links named from
        ``origin`` (422 ``LINK_CYCLE``). Nothing is written. The facts of the structure read under
        its lock are handed to the replay, not read again (#2492). The nodes of the other kinds the
        tasks ``repriced`` bear are priced again with those of the tasks redated, and those of the
        nodes it touches (``before``): a task written, or the task a line written is under. A node
        priced again beyond its column is refused at ``entered``, the pointers of the fields of the
        request that redate (``RepricedBeyondColumnError``, #3094); without them, without a field.
        The tree read under the lock is handed to the replay, which brings it to what the write
        made of it rather than read it again (``reshaped``, US-2250); the write holds it after. A
        write of several tasks names ``among`` them, by task, what each is called when the engine
        finds it beyond the horizon — a paste, the row of its block (#3624) —, a task none of them
        as the tree has it (a successor pushed); ``among`` given, ``blamed`` is none.
        """
        if among is not None and blamed is not None:
            msg = "a write names one task or several, not both"
            raise ValueError(msg)
        named = (
            Blamed(among, origin)
            if among is not None
            else None
            if blamed is None
            else Blamed(Named(*blamed), origin)
        )
        priced = (*repriced, *self.touched)
        held = Holding(self.facts, named, self.conflicts, priced, self.tree)
        with refused_at(entered):
            redated = redated_structure(self.session, self.place, self.writer.act, held)
        self._tree = redated.reading.tree
        return redated

    def count(self) -> Redated[NodeColumns, TaskColumns] | Redated:
        """Count a write that can move no date nor change an amount; give the structure it leaves.

        The short path (US-2250): the engine is not replayed and the tree not read again; the
        instant of the structure's dates stays, its counter advances (``structure_counted``). The
        nodes it touched (``before``) and their ancestors are read from the tree it holds — as rows
        but the nodes it wrote, for a write that named them inert (``inert``) —, on the calendars of
        their tasks alone, as the whole path reads them: no task moved, no node priced again.
        """
        session, place = self.session, self.place
        session.flush()
        counter = structure_counted(session, place.project_id, place.structure_id)
        if self.inert is None:
            return self._counted(self.tree, counter)
        return self._counted(self.inert.tree, counter)

    def _counted[N: NodeColumns, T: TaskColumns](
        self, tree: Tree[N, T], counter: int
    ) -> Redated[N, T]:
        """Give the structure a write counted leaves, read from the tree it holds."""
        session, place = self.session, self.place
        shown = {each for node_id in self.touched for each in (node_id, *tree.ancestors(node_id))}
        calendars = calendars_of(session, place.project_id, shown & tree.tasks.keys())
        structure = (place, self.facts.scheduled_at, self.facts.is_main)
        reading = Reading(session, structure, tree, self.links, calendars)
        return Redated(reading, frozenset(), counter)

    def after(self, node_ids: Collection[UUID]) -> None:
        """Hand the history the nodes the write touched, as they are after it, redated."""
        self.frame.keep_after(taken(self.session, self.place.project_id, node_ids))


def redated_structure(
    session: Session,
    place: Place,
    act: Act,
    held: Holding,
) -> Redated:
    """Replay the engine on a structure its caller holds the lock of; give it as it now stands.

    What a write of the tree does once it has written (``Write.redate``), and an undoing or a
    redoing, whose frame holds the lock of the structure (``history.undo``). ``held`` is what the
    caller read under that lock (``Holding``): the facts of the structure, what it names if the
    engine refuses, the links in conflict read before the write, the tasks whose nodes of the other
    kinds are priced again whether they moved or not, and the tree it read before it wrote, brought
    to what it made of it rather than read again (``reshaped``, US-2250).
    """
    done = replayed(session, place.project_id, place.structure_id, act.at, held)
    reading = Reading(session, (place, act.at, done.is_main), done.tree, done.links, done.calendars)
    return Redated(reading, done.moved, done.counter, done.reinflated)


@dataclass(frozen=True, slots=True)
class Redated[N: NodeColumns = Node, T: TaskColumns = Task]:
    """A structure written and redated: its reading, the tasks moved, its counter, what it priced.

    ``reinflated`` the nodes of the other kinds whose amounts or year their hooks changed. Its
    reading is of objects of the session, or of rows but the nodes written (``Write.count``).
    """

    reading: Reading[N, T]
    moved: frozenset[UUID]
    counter: int
    reinflated: frozenset[UUID] = frozenset()

    def written(self, node_ids: Collection[UUID], former: Collection[UUID] = ()) -> NodesWritten:
        """Give what the write gives back: its nodes, their ancestors and the tasks it moved.

        The ancestors are those of the nodes written and of the tasks moved, and ``former`` — the
        ancestors a deletion or a move left, still in the structure —, but the written; the moved
        are the tasks, not summaries nor ancestors, it redated without writing them. The reinflated
        are the nodes of the other kinds priced again without being written, and the leaves that
        bear them, but the written and the ancestors; the totals those of the whole structure.
        """
        tree = self.reading.tree
        written = set(node_ids)
        left = {each for each in former if each in tree.nodes and each not in written}
        rescheduled = {
            each for each in self.moved if each not in written | left and not tree.is_summary(each)
        }
        above = left | {
            ancestor
            for each in written | rescheduled
            for ancestor in tree.ancestors(each)
            if ancestor not in written
        }
        reading = self.reading
        priced = {each for each in self.reinflated if each in tree.nodes and each not in written}
        bearing = {
            parent
            for each in priced
            if (parent := tree.nodes[each].parent_id) is not None
            and parent not in written | above
            and not tree.is_summary(parent)
        }
        reading.prefetch([*written, *above])
        lines = [each for each in tree.nodes if each not in tree.tasks]
        return NodesWritten(
            nodes=tuple(reading.node(each) for each in tree.ordered(written)),
            ancestors=tuple(reading.node(each) for each in tree.ordered(above)),
            rescheduled=tuple(reading.schedule(each) for each in tree.ordered(rescheduled)),
            task_count=len(tree.tasks),
            structure_lock_version=self.counter,
            reinflated=tuple(self._inflation(each) for each in tree.ordered(priced | bearing)),
            totals=StructureTotals(len(lines), reading.totals(lines)),
        )

    def _inflation(self, node_id: UUID) -> InflationView:
        """Give the amounts of a node priced again: a line's own, a task's summed."""
        reading = self.reading
        if node_id in reading.tree.tasks:
            summed = reading.sums[node_id]
            return InflationView(node_id, summed.budgeted, summed.reestimated, None)
        own = reading.figures[node_id]
        return InflationView(node_id, own.budgeted, own.reestimated, own.consumption_year)


def hold_before_lock(session: Session) -> None:
    """Take what the facets of the other kinds hold before the lock of a structure (#2615).

    Taken by every write of the tree, not only by those of a line: the lock is shared, so cheap
    when nothing changes a nature, and a single order of locks (the natures, then the structure)
    leaves no write to guess whether it may reach a line — a deletion of a task does.
    """
    for hooks in facets().values():
        hooks.before_lock(session)


@contextmanager
def writing(
    session: Session,
    place: Place,
    writer: Writer,
    change: tuple[UndoneKind, tuple[UUID, ...]],
    inert: Collection[UUID] = (),
) -> Generator[Write]:
    """Frame a write of the tree: judged, recorded, under the lock of its structure.

    The structure named is read first (404), the revision judged under its lock (409), the entry
    of the history opened, then the structure locked and its tree read; what the facets hold
    before the structure is taken first (``FacetHooks.before_lock``, #2615). The block hands the
    snapshots (``Write.before``, ``Write.after``); a block that raises keeps nothing. ``inert``
    the nodes a write whose columns are all inert writes, the others read as rows (``Write``).
    """
    hold_before_lock(session)
    facts_of(session, place, lock=False)
    judge_revision(session, place.project_id, place.revision_id, writer.running)
    with _recorded(session, place, writer, change) as frame:
        yield Write(session, place, writer, frame, inert)
