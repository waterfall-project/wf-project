# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the gestures of the structure and of the entries of a task (EP-15/US-0460, K3).

The grids create a task beside another or under it, a line under a task; move a selection,
indent a task under the one above it, delete a summary; enter the mode, the dates, the duration
and the description of a task, its predecessors and its inscriptions to the timelines. Each
success is, as every write of the grids, the difference between two readings of one structure,
before and after the gesture (``wftools.mockwrites``, #287): never written by hand. Each refusal
names what the witness names — the tasks of a loop of links, the task that would carry the
project beyond its horizon — by the labels its readings give. A move or an indentation that
would bind a summary to its subordinate, or close a loop through it, is refused as predecessors
entered are (#1164), the structure it would leave refused by ``mockcore.schedule`` too.

Every node the gestures write is one no other write renders at the same version (#421): the
nodes they create are numbered 581 to 584, after the nodes of the skeleton.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mocktext, mockwitness
from wftools.mockcalendar import START_TO_START
from wftools.mockids import universe
from wftools.mockstructure import NETWORK, JsonObject, described
from wftools.mocktree import AT_END, LINE, TASK, cycle, move_loop, placed
from wftools.mockwitness import (
    CONTROL_STATION,
    CORE,
    CUSTOMER,
    EQUIPMENT,
    INSTALLATION,
    STUDIES,
    SUBPROJECT_CONTROL,
    SUBPROJECT_TESTS,
    TIMELINES,
    Line,
    Link,
    N,
    Task,
)
from wftools.mockwrites import (
    amended,
    core_write,
    on_task,
    totals_said,
    volume_write,
    written,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from wftools.mocktree import After

type Node = dict[str, Any]

HORIZON_YEARS = 15
"""The longest a project lasts, from the start of its first task to the finish of its last, in
any of its structures (WF-PLA-0150)."""


# --- The structure created, moved, deleted -----------------------------------------------------

CREATED, CREATED_CHILD, CREATED_LINE, CREATED_SHARED = 581, 582, 583, 584

SIBLING = Task(CREATED, "Note de calcul des protections", days=1, progress="not_started")
"""The task created beside the design file, a label alone sent: a leaf in automatic mode, of one
day, without a predecessor (WF-DEV-0050), not started — nothing starts by itself (WF-RAE-0030)."""

CHILD = Task(CREATED_CHILD, "Relevé des réglages existants", days=1, progress="not_started")
"""The task created under the one created beside the design file, which becomes its summary."""

TEST_SUPPLIES = Line(
    CREATED_LINE,
    "Consommables d'essais",
    EQUIPMENT,
    unit=Decimal("350.00"),
    subproject=SUBPROJECT_TESTS,
    budgeted=Decimal(0),
)
"""The line created under the commissioning, after the reference: its budget nil (WF-RAE-0050)."""


def added(
    number: int, *, child: Task | None = None, line: Line | None = None, after: After = AT_END
) -> Callable[[Task], Task]:
    """Add a subordinate or a line to the task of a number, and to no other, where it is sent.

    At the end of its kind by default, as a creation that names no node to follow (``placed``).
    """

    def add(each: Task) -> Task:
        if each.number != number:
            return each
        new = [(node.number, kind) for node, kind in ((child, TASK), (line, LINE)) if node]
        nodes = {node.number: node for node in (*each.lines, *each.children, child, line) if node}
        lines, tasks = placed(
            [node.number for node in each.lines],
            [node.number for node in each.children],
            new,
            after,
        )
        return replace(
            each,
            lines=tuple(cast("Line", nodes[n]) for n in lines),
            children=tuple(cast("Task", nodes[n]) for n in tasks),
        )

    return add


def node_created() -> JsonObject:
    """Return what createNode answers to a task created beside the design file, the last one."""
    return core_write(amended(CORE, added(N.STUDIES, child=SIBLING)), [CREATED])


def node_created_child() -> JsonObject:
    """Return what createNode answers to a task created under the one created beside the file.

    It follows that creation (``node_created``): the leaf created becomes a summary, its dates
    and its duration drawn from its one subordinate (WF-PLA-0040); the structure is one version
    further still (#421).
    """
    before = amended(CORE, added(N.STUDIES, child=SIBLING))
    after = amended(CORE, added(N.STUDIES, child=replace(SIBLING, children=(CHILD,))))
    return core_write(after, [CREATED_CHILD], following=before)


def estimate_line_created() -> JsonObject:
    """Return what createNode answers to a line created under the commissioning."""
    return core_write(amended(CORE, added(N.COMMISSIONING, line=TEST_SUPPLIES)), [CREATED_LINE])


SHARED_UNDER, SHARED_AFTER = N.CONTROL_STATION, N.FACTORY_ACCEPTANCE
"""The summary a line is created under, and the node it is sent to follow: its last subordinate,
the factory acceptance. The lines of a task precede its subordinates: a line sent after a
subordinate falls back on the boundary, after the last line of the task (#1187)."""

SHARED_TOOLING = Line(
    CREATED_SHARED,
    "Outillage commun du poste",
    EQUIPMENT,
    unit=Decimal("420.00"),
    subproject=SUBPROJECT_CONTROL,
    budgeted=Decimal(0),
)
"""The line created under the control station, a summary that bears no line of its own: sent
after its last subordinate, it becomes its first child, before the wiring of the cabinets."""


def estimate_line_created_after_subtask() -> JsonObject:
    """Return what createNode answers to a line created under the station, after a subordinate.

    The witness renders the lines of a task before its subordinates (``mockcore``): the line
    added last among the lines of the station is at the place the contract gives a line that
    names a subordinate to follow (``NodeCreate``, #1187).
    """
    roots = amended(CORE, added(SHARED_UNDER, line=SHARED_TOOLING, after=SHARED_AFTER))
    return core_write(roots, [CREATED_SHARED])


def network_task(label: str) -> Task:
    """Return a task drawn about the core, by its label."""
    [task] = [each for each in mockcore.tasks_in_order(NETWORK) if each.label == label]
    return task


MOVED_FROM, MOVED_TO = "Conception 1.1.2", "Revue 1.1.3"
MOVED_LINES = ("Matériel", "Sous-traitance")
"""The selection moved: two lines of a task drawn about the core, neither of labour, to the task
after it in its lot — no calendar changes, no task is redated (WF-PLA-0010)."""


def moved_lines() -> tuple[tuple[Task, ...], list[int]]:
    """Return the structure the selection moved leaves, and the lines it moves.

    Sent without a node to follow, they go after the last line of the task (``placed``).
    """
    source, target = network_task(MOVED_FROM), network_task(MOVED_TO)
    lines = [line for line in source.lines if line.label in MOVED_LINES]
    numbers = [line.number for line in lines]

    def move(each: Task) -> Task:
        if each.number == source.number:
            return replace(
                each, lines=tuple(line for line in each.lines if line.number not in numbers)
            )
        if each.number == target.number:
            order, _ = placed(
                [line.number for line in each.lines],
                [child.number for child in each.children],
                [(number, LINE) for number in numbers],
                AT_END,
            )
            by_number = {line.number: line for line in (*each.lines, *lines)}
            return replace(each, lines=tuple(by_number[number] for number in order))
        return each

    return amended(described(), move), numbers


def nodes_moved() -> JsonObject:
    """Return what moveNodes answers to a selection of two lines moved under another task."""
    roots, numbers = moved_lines()
    return volume_write(roots, numbers)


def nodes_indented() -> JsonObject:
    """Return what moveNodes answers when the installation on site is indented under the station.

    The task above it at its level becomes its parent, its subordinates going down a level with
    it: no date, no amount changes; the summary that receives it spans it (WF-PLA-0040).
    """
    station = replace(CONTROL_STATION, children=(*CONTROL_STATION.children, INSTALLATION))
    return core_write((STUDIES, station), [N.INSTALLATION])


def node_summary_deleted() -> JsonObject:
    """Return what deleteNode answers when the installation on site, not started, is deleted.

    With it go its subordinates, their lines and the links that bind them (WF-PLA-0070): the
    milestone drawn after the commissioning follows its other predecessors alone.
    """
    gone = {task.number for task in mockcore.tasks_in_order((INSTALLATION,))}

    def unlinked(each: Task) -> Task:
        links = tuple(link for link in each.links if link.predecessor not in gone)
        return each if links == each.links else replace(each, links=links)

    roots = amended((STUDIES, CONTROL_STATION, *NETWORK), unlinked)
    return written(
        mockcore.whole(mockcore.current()),
        mockcore.whole(mockcore.current(roots)),
        [],
        deleted=[universe(N.INSTALLATION)],
    )


# --- The entries of a task --------------------------------------------------------------------


def dates_of(number: int) -> tuple[date, date]:
    """Return the days a task of the structure starts and finishes, as read today."""
    placed = mockcore.schedule(described())[number]
    return placed.start.day, placed.finish.day


def made_manual() -> Callable[[Task], Task]:
    """Put the commissioning in manual mode at the dates it was computed at (WF-PLA-0020)."""
    return on_task(N.COMMISSIONING, manual=dates_of(N.COMMISSIONING))


ENTERED_DATES = (date(2027, 1, 4), date(2027, 1, 15))
"""The dates entered on the commissioning in manual mode: after the first days of the year."""


def task_mode_changed() -> JsonObject:
    """Return what updateTaskFacet answers when the commissioning passes to manual mode."""
    return core_write(amended(CORE, made_manual()), [N.COMMISSIONING])


def task_dates_entered() -> JsonObject:
    """Return what updateTaskFacet answers to the dates entered on the commissioning, manual.

    It follows the mode changed (``task_mode_changed``): the task at the version that write left.
    """
    return core_write(
        amended(CORE, on_task(N.COMMISSIONING, manual=ENTERED_DATES)),
        [N.COMMISSIONING],
        following=amended(CORE, made_manual()),
    )


ENTERED_DURATION = (3, "w")
DURATION_TASK = "Préparation 1.1.1"
"""The task drawn about the core whose duration is entered in weeks, kept in that unit
(WF-PLA-0160): three weeks, where it lasted ten days."""


def task_duration_entered() -> JsonObject:
    """Return what updateTaskFacet answers to a duration entered in weeks."""
    task = network_task(DURATION_TASK)
    days, unit = ENTERED_DURATION
    return volume_write(
        amended(described(), on_task(task.number, days=days, unit=unit)), [task.number]
    )


DESCRIPTION = "Plans, schémas et nomenclatures remis au client avec la note de conception."


def task_description_entered() -> JsonObject:
    """Return what updateTaskFacet answers to the description entered on the design file."""
    return core_write(
        amended(CORE, on_task(N.DESIGN_FILE, description=DESCRIPTION)), [N.DESIGN_FILE]
    )


def project_start() -> date:
    """Return the day the first task of the structure starts: where the horizon counts from."""
    return min(placed.start.day for placed in mockcore.schedule(described()).values())


def beyond_horizon() -> date:
    """Return fifteen years and a day after the start of the project (Vérif of WF-PLA-0150)."""
    start = project_start()
    return start.replace(year=start.year + HORIZON_YEARS) + timedelta(days=1)


COMPUTED_CORRELATION, HORIZON_CORRELATION = universe(1169), universe(1170)


def task_date_computed() -> JsonObject:
    """Return what updateTaskFacet answers to a finish sent for the mounting, in automatic mode.

    Its dates are computed (WF-PLA-0020): the entry is refused on its field, without a parameter,
    the grid reading what the value depends on (`getComputedValueDependencies`, WF-IHM-0030).
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/finish", "code": "COMPUTED_VALUE"}],
        "correlation_id": COMPUTED_CORRELATION,
    }


def named(number: int) -> JsonObject:
    """Return a task as a refusal names it: its node and its label (`node_id`, `label`)."""
    rows = {row.number: row for row in mockcore.current()}
    return {"node_id": mockwitness.node_id(number), "label": rows[number].label}


def horizon_exceeded(task: JsonObject, correlation: str) -> JsonObject:
    """Return the refusal of an entry that would carry the project beyond fifteen years."""
    return {
        "code": "PROJECT_HORIZON_EXCEEDED",
        "status": 422,
        "params": {"task": task},
        "correlation_id": correlation,
    }


def task_horizon_exceeded() -> JsonObject:
    """Return what updateTaskFacet answers to the finish of the desks entered beyond the horizon."""
    return horizon_exceeded(named(N.DESKS), HORIZON_CORRELATION)


# --- The predecessors and the inscriptions -----------------------------------------------------

LINKED_TASK = "Conception 1.1.2"
LINKED_AFTER = "Préparation 1.1.1"
LINKED_LAG = (1, "w")


def entered_links() -> tuple[Link, ...]:
    """Return the predecessors entered on LINKED_TASK, of two kinds.

    The factory acceptance, finish to start, and LINKED_AFTER, start to start, a week later, the
    lag kept in weeks (WF-PLA-0030, WF-PLA-0160).
    """
    lag, unit = LINKED_LAG
    return (
        Link(N.FACTORY_ACCEPTANCE),
        Link(network_task(LINKED_AFTER).number, START_TO_START, lag, unit),
    )


def predecessors_entered() -> JsonObject:
    """Return what setPredecessors answers to two predecessors of two kinds entered on a task."""
    task = network_task(LINKED_TASK)
    return volume_write(
        amended(described(), on_task(task.number, links=entered_links())), [task.number]
    )


CYCLE_ON = N.FACTORY_ACCEPTANCE
CYCLE_LINKS = (Link(N.WIRING), Link(N.COMMISSIONING))
"""The predecessors sent for the factory acceptance: the wiring, and the commissioning, which
follows it through the mounting — a loop (WF-PLA-0030)."""

FORBIDDEN_ON = N.MOUNTING
FORBIDDEN_LINKS = (Link(N.FACTORY_ACCEPTANCE), Link(N.INSTALLATION))
"""The predecessors sent for the mounting: the factory acceptance, and the installation, its own
summary — a link between a summary and its subordinate (WF-PLA-0030, WF-PLA-0040)."""

HORIZON_ON = N.COMMISSIONING
HORIZON_LAG = (200, "mo")
"""The predecessor sent for the commissioning: the mounting, two hundred months of work later."""

CREATED_BEYOND = "Exploitation et maintenance du poste"
CREATED_DURATION = (200, "mo")
"""A task created under the installation with a duration of two hundred months of work."""

CYCLE_CORRELATION, FORBIDDEN_CORRELATION = universe(1171), universe(1172)
LINK_HORIZON_CORRELATION, CREATE_HORIZON_CORRELATION = universe(1173), universe(1174)


def predecessors_cycle_refused() -> JsonObject:
    """Return what setPredecessors answers to predecessors that would close a loop of links."""
    return {
        "code": "LINK_CYCLE",
        "status": 422,
        "params": {"cycle": [named(number) for number in cycle(CYCLE_ON, CYCLE_LINKS)]},
        "correlation_id": CYCLE_CORRELATION,
    }


def predecessors_forbidden() -> JsonObject:
    """Return what setPredecessors answers to a link between a summary and its subordinate."""
    return {"code": "LINK_FORBIDDEN", "status": 422, "correlation_id": FORBIDDEN_CORRELATION}


INDENTED_FORBIDDEN, INDENTED_UNDER = N.COMMISSIONING, N.MOUNTING
"""The commissioning indented under the mounting, the task above it at its level and its
predecessor: the mounting would become its summary, the link between them binding a summary to
its subordinate (WF-PLA-0030, WF-PLA-0040)."""

LOOP_MOVED, LOOP_UNDER = "Documentation 1.1.7", "Préparation 1.1.1"
"""A task drawn about the core moved under another of its post, which precedes it through a
third: the summary it would receive spans it, and it already follows that summary — a loop
(WF-PLA-0030)."""

MOVE_FORBIDDEN_CORRELATION, MOVE_CYCLE_CORRELATION = universe(1176), universe(1177)

ONE_LINK = 2
"""The tasks of a chain of one link: a summary and its subordinate, bound directly."""


def move_refused(number: int, parent: int, roots: Iterable[Task], correlation: str) -> JsonObject:
    """Return what moveNodes answers to a move that would close a loop through the hierarchy.

    A link between the summary that would receive the task and the task, or one of their
    subordinates, is refused without a parameter (`LINK_FORBIDDEN`); a longer chain is a loop,
    whose tasks the refusal names in the order of the links (`LINK_CYCLE`, WF-PLA-0030).
    """
    loop = move_loop(number, parent, roots)
    if not loop:
        message = f"the move of the task {number} under {parent} closes no loop"
        raise ValueError(message)
    if len(loop) == ONE_LINK:
        return {"code": "LINK_FORBIDDEN", "status": 422, "correlation_id": correlation}
    return {
        "code": "LINK_CYCLE",
        "status": 422,
        "params": {"cycle": [named(each) for each in loop]},
        "correlation_id": correlation,
    }


def nodes_indent_forbidden() -> JsonObject:
    """Return what moveNodes answers when the commissioning is indented under its predecessor."""
    return move_refused(INDENTED_FORBIDDEN, INDENTED_UNDER, CORE, MOVE_FORBIDDEN_CORRELATION)


def loop_move() -> tuple[int, int]:
    """Return the task the looping move moves, and the one it moves it under."""
    return network_task(LOOP_MOVED).number, network_task(LOOP_UNDER).number


def nodes_move_cycle_refused() -> JsonObject:
    """Return what moveNodes answers to a task moved under a task it already follows."""
    moved, under = loop_move()
    return move_refused(moved, under, described(), MOVE_CYCLE_CORRELATION)


def predecessors_horizon_exceeded() -> JsonObject:
    """Return what setPredecessors answers to a lag that carries the project beyond its horizon."""
    return horizon_exceeded(named(HORIZON_ON), LINK_HORIZON_CORRELATION)


def node_create_horizon_exceeded() -> JsonObject:
    """Return what createNode answers to a task created with a duration beyond the horizon.

    The task is not created: it is named by the label sent, its node nil, as the task an import
    would create (`Problem.params`, WF-PLA-0150).
    """
    created: JsonObject = {"node_id": None, "label": CREATED_BEYOND}
    return horizon_exceeded(created, CREATE_HORIZON_CORRELATION)


# --- The place a creation or a move names ------------------------------------------------------

CREATED_UNDER, CREATED_AFTER = N.STUDIES, N.WIRING
"""The parent a task is created under, and the node it is sent to follow: the wiring of the
cabinets, a subordinate of the control station, not of the studies."""

MOVED_AWAY, MOVED_UNDER, MOVED_AFTER = N.BLOCKS, N.COMMISSIONING, N.LABOUR
"""The line moved, the task it is moved under, and the node it is sent to follow: the connection
of the blocks, which stays under the wiring of the cabinets."""

CREATE_PLACE_CORRELATION, MOVE_PLACE_CORRELATION = universe(1178), universe(1179)


def not_sibling(parent: int, after: int, correlation: str, moved: Iterable[int] = ()) -> JsonObject:
    """Return the refusal of a place named after a node that is not a sibling under the parent.

    A creation or a move names the node it follows among the siblings under its parent, never a
    rank (#1183): a node read under another parent, or one of the nodes moved, is refused on
    ``/after_node_id``, without a parameter — the grid names the node it sent.
    """
    rows = {row.number: row for row in mockcore.current()}
    if rows[after].parent == parent and after not in set(moved):
        message = f"the node {after} is a sibling under {parent}"
        raise ValueError(message)
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/after_node_id", "code": "NODE_NOT_SIBLING"}],
        "correlation_id": correlation,
    }


def node_create_after_not_sibling() -> JsonObject:
    """Return what createNode answers to a task created under the studies, after the wiring."""
    return not_sibling(CREATED_UNDER, CREATED_AFTER, CREATE_PLACE_CORRELATION)


def nodes_move_after_not_sibling() -> JsonObject:
    """Return what moveNodes answers to the blocks moved under the commissioning, after a line.

    The line they are sent to follow stays under the wiring of the cabinets.
    """
    return not_sibling(MOVED_UNDER, MOVED_AFTER, MOVE_PLACE_CORRELATION, moved=(MOVED_AWAY,))


MIXED_UNDER, MIXED_AFTER = N.CONTROL_STATION, N.WIRING
MIXED = ((N.BLOCKS, LINE), (N.TRANSPORT, TASK))
"""A selection that mixes a line and a task — the blocks of the wiring of the cabinets and the
exceptional transport of the subtree the occurrence merged —, moved under the control station
after the wiring, its first subordinate: the line falls back on the boundary, the task follows the
wiring (#1187, #1188)."""


def mixed_places() -> tuple[list[int], list[int]]:
    """Return the lines and the subordinates of the station once the mixed selection is placed."""
    under = [row for row in mockcore.current() if row.parent == MIXED_UNDER]
    lines = [row.number for row in under if row.kind == LINE]
    return placed(lines, [row.number for row in under if row.kind == TASK], MIXED, MIXED_AFTER)


def nodes_move_mixed() -> JsonObject:
    """Return the body of moveNodes for a selection of a line and a task, after a subordinate."""
    structures = cast("list[Node]", mockwitness.fixture("structures"))
    [main] = [each for each in structures if each["kind"] == "main"]
    return {
        "node_ids": [mockwitness.node_id(number) for number, _ in MIXED],
        "parent_id": mockwitness.node_id(MIXED_UNDER),
        "after_node_id": mockwitness.node_id(MIXED_AFTER),
        "lock_version": main["lock_version"],
    }


COMPLETED_UNDER = N.DETAILED_STUDIES
COMPLETED_CORRELATION = universe(1186)


def estimate_line_completed_refused() -> JsonObject:
    """Return what createNode answers to a line created under a task completed.

    No line is created, modified, moved or deleted under a task completed, which is reopened from
    the Kanban first (WF-DEV-0050, WF-RAE-0030): the state of the task refuses it, by the condition
    a line under it misses (#1184).
    """
    rows = {row.number: row for row in mockcore.current()}
    if cast("dict[str, Any]", rows[COMPLETED_UNDER].node["task"])["progress"] != "completed":
        message = f"the task {COMPLETED_UNDER} is not completed"
        raise ValueError(message)
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "task_not_completed"},
        "correlation_id": COMPLETED_CORRELATION,
    }


TRACKED_TASK = N.DESIGN_REVIEW


def node_tracked() -> JsonObject:
    """Return what setNodeTracking answers when the design review is inscribed to a timeline."""
    return core_write(
        amended(CORE, on_task(TRACKED_TASK, inscriptions=(CUSTOMER,))), [TRACKED_TASK]
    )


UNTRACKED_TASK = N.COMMISSIONING
MILESTONE_CORRELATION = universe(1180)


def tracking_entries(number: int) -> list[JsonObject]:
    """Return the entries sent for a task: its timelines kept, the time/time tracking added."""
    timelines = mockwitness.INSCRIBED.get(number, ())
    return [
        *({"kind": "timeline", "timeline_id": timeline} for timeline in timelines),
        {"kind": mockwitness.MILESTONE_TRACKING, "timeline_id": None},
    ]


def node_tracking_milestone_refused() -> JsonObject:
    """Return what setNodeTracking answers when the commissioning is sent to the time/time tracking.

    The time/time tracking follows milestones (WF-PLA-0060): a task that is not one is refused on
    the kind of the entry that asks for it, by its rank among the entries sent, and nothing is
    written (#1159).
    """
    rows = {row.number: row for row in mockcore.current()}
    if cast("dict[str, Any]", rows[UNTRACKED_TASK].node["task"])["is_milestone"]:
        message = f"the task {UNTRACKED_TASK} is a milestone"
        raise ValueError(message)
    rank = len(tracking_entries(UNTRACKED_TASK)) - 1
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": f"/entries/{rank}/kind", "code": "MILESTONE_REQUIRED"}],
        "correlation_id": MILESTONE_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def said_on(instant: Node) -> str:
    """Say the day of an instant of work, as French writes it."""
    return mocktext.day(date.fromisoformat(instant["date"]))


def money_said(value: str) -> str:
    """Say an amount the contract carries as a string, as French writes it."""
    return mocktext.amount(Decimal(value))


def _nodes(answer: JsonObject, key: str = "nodes") -> list[Node]:
    return cast("list[Node]", answer[key])


def _task(answer: JsonObject, key: str = "nodes") -> Node:
    return cast("Node", _nodes(answer, key)[0]["task"])


def _labels(answer: JsonObject, key: str) -> str:
    """Say the tasks of a list of an answer by their label, in its order."""
    return mocktext.listed(
        [f"« {node['task']['label']} »" for node in _nodes(answer, key) if node["kind"] == "task"]
    )


def _version(answer: JsonObject) -> str:
    return f"le compteur de la structure passé à {answer['structure_lock_version']}"


NAMED_AT_MOST = 3
"""The tasks redated a summary names by their label; beyond, it counts them."""


def _redated(answer: JsonObject) -> str:
    """Say the tasks an answer schedules anew without writing them, from the answer itself.

    Each by its label, its dates and its float, up to NAMED_AT_MOST; beyond, their count.
    """
    entries = _nodes(answer, "rescheduled")
    if not entries:
        return "aucune autre tâche n'est replanifiée"
    if len(entries) > NAMED_AT_MOST:
        return f"{mocktext.count(len(entries))} tâches replanifiées sans être écrites (rescheduled)"
    labels = {mockwitness.node_id(row.number): row.label for row in mockcore.current()}
    said = mocktext.listed(
        [
            f"« {labels[entry['node_id']]} », {mocktext.span(entry)}, marge de "
            f"{entry['total_float']['value'].replace('.', ',')} j"
            for entry in entries
        ]
    )
    if len(entries) == 1:
        return f"la tâche que l'écriture replanifie sans l'écrire (rescheduled), {said}"
    return f"les tâches que l'écriture replanifie sans les écrire (rescheduled), {said}"


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the gestures of the structure and of the entries of a task."""
    return {
        **_structure_examples(),
        **_entry_examples(),
        **_link_examples(),
        **_move_refusal_examples(),
        **_place_examples(),
    }


def _structure_examples() -> dict[str, JsonObject]:
    created, child, line = node_created(), node_created_child(), estimate_line_created()
    shared = estimate_line_created_after_subtask()
    moved, indented, deleted = nodes_moved(), nodes_indented(), node_summary_deleted()
    rows = {row.number: row for row in mockcore.current()}
    created_task = _task(created)
    [child_parent] = [
        node["task"] for node in _nodes(child, "ancestors") if node["node_id"] == universe(CREATED)
    ]
    [new_line] = _nodes(line)
    [shared_line] = _nodes(shared)
    supplies = cast("Node", new_line["estimate_line"])
    [indented_node] = _nodes(indented)
    gone = [rows[number] for number in (N.MOUNTING, N.COMMISSIONING)]
    gone_lines = [row for row in rows.values() if row.parent in {N.MOUNTING, N.COMMISSIONING}]
    removed = sum((row.amounts.base for row in gone_lines), Decimal(0))
    return {
        "node_created.json": mocktext.example(
            f"La tâche « {SIBLING.label} » créée à côté du « {rows[N.DESIGN_FILE].label} », la "
            f"dernière des « {rows[N.STUDIES].label} », son libellé seul envoyé : une feuille en "
            f"mode automatique d'un jour, sans prédécesseur, qui commence à la date de début de "
            f"planning, le {said_on(created_task['start'])}, non démarrée ; à sa première version "
            f"(201). Avec elle, sa récapitulative, dont rien ne change, {totals_said(created)}, "
            f"et {_version(created)} (WF-DEV-0050, WF-PLA-0020, WF-PLA-0130).",
            created,
        ),
        "node_created_child.json": mocktext.example(
            f"La tâche « {CHILD.label} » créée sous « {SIBLING.label} », que la création "
            f"précédente a ajoutée (node_created) : la feuille devient sa récapitulative, ses "
            f"dates et sa durée tirées de sa seule subordonnée, {mocktext.span(child_parent)}, et "
            f"n'accepte plus ni son mode ni sa durée (editable_fields). Avec elle, ses deux "
            f"ancêtres, {_labels(child, 'ancestors')}, {totals_said(child)}, et {_version(child)} "
            f"(WF-PLA-0040, WF-PLA-0130).",
            child,
        ),
        "estimate_line_created.json": mocktext.example(
            f"La ligne « {TEST_SUPPLIES.label} » créée sous la "
            f"{rows[N.COMMISSIONING].label.lower()}, {money_said(supplies['base_amount'])} de "
            f"matériel au sous-projet « {supplies['subproject_label']} » : ajoutée après la "
            f"référence, son montant budgété est nul, {money_said(supplies['budgeted_amount'])} "
            f"(WF-RAE-0050) ; à sa première version (201). Avec elle, ses ancêtres, "
            f"{_labels(line, 'ancestors')}, dont le montant suit, et {totals_said(line)}, le "
            f"budgété inchangé (WF-DEV-0050).",
            line,
        ),
        "estimate_line_created_after_subtask.json": mocktext.example(
            f"La ligne « {SHARED_TOOLING.label} » créée sous le "
            f"« {rows[SHARED_UNDER].label} », une récapitulative sans ligne propre, après sa "
            f"dernière subordonnée, la « {rows[SHARED_AFTER].label} » (after_node_id) : les "
            f"lignes d'une tâche précèdent toujours ses sous-tâches, et une ligne qui suit une "
            f"sous-tâche se place après la dernière ligne. Elle devient le premier enfant du "
            f"poste, au rang {shared_line['position']}, avant le « {rows[N.WIRING].label} » ; "
            f"{money_said(shared_line['estimate_line']['base_amount'])} de matériel, son "
            f"montant budgété nul (WF-RAE-0050), à sa première version (201). Avec elle, ses "
            f"ancêtres, {_labels(shared, 'ancestors')}, dont le montant suit, et "
            f"{totals_said(shared)}, le budgété inchangé (WF-DEV-0050 ; #1187).",
            shared,
        ),
        "nodes_moved.json": mocktext.example(
            f"Une sélection de deux lignes, « {MOVED_LINES[0]} » et « {MOVED_LINES[1]} » de "
            f"« {MOVED_FROM} », déplacée en une écriture sous « {MOVED_TO} », à sa fin : leur "
            f"tâche porteuse change, une version de plus chacune ; aucune n'est de main-d'œuvre, "
            f"aucun calendrier ne change : {_redated(moved)}. Avec elles, les anciens et les "
            f"nouveaux ancêtres, {_labels(moved, 'ancestors')}, dont les montants suivent, et "
            f"{totals_said(moved)}, inchangés (WF-PLA-0040, WF-DEV-0050).",
            moved,
        ),
        "nodes_indented.json": mocktext.example(
            f"La récapitulative « {rows[N.INSTALLATION].label} » mise en retrait sous la tâche "
            f"au-dessus d'elle à son niveau, « {rows[N.CONTROL_STATION].label} », dont elle "
            f"devient la dernière subordonnée, au niveau {indented_node['level']}, ses "
            f"subordonnées descendant d'un niveau avec elle ; une version de plus. Aucune date ni "
            f"aucun montant ne change : sa nouvelle récapitulative la couvre, "
            f"{mocktext.span(_task(indented, 'ancestors'))}, et en somme les montants, et "
            f"{totals_said(indented)}, inchangés (WF-PLA-0040).",
            indented,
        ),
        "node_summary_deleted.json": mocktext.example(
            f"La récapitulative « {rows[N.INSTALLATION].label} », non démarrée, supprimée avec "
            f"ses subordonnées, {mocktext.listed([f'« {row.label} »' for row in gone])}, leurs "
            f"{mocktext.count(len(gone_lines))} lignes et leurs liaisons : rien à rendre d'elles, "
            f"{_redated(deleted)} ; {totals_said(deleted)} — le devis diminue de "
            f"{mocktext.amount(removed)} — ; {_version(deleted)} (WF-PLA-0070, WF-DAT-0090).",
            deleted,
        ),
    }


def _entry_examples() -> dict[str, JsonObject]:
    manual, dated = task_mode_changed(), task_dates_entered()
    duration, described_ = task_duration_entered(), task_description_entered()
    rows = {row.number: row for row in mockcore.current()}
    commissioning = cast("Node", rows[N.COMMISSIONING].node["task"])
    days, unit = ENTERED_DURATION
    return {
        "task_mode_changed.json": mocktext.example(
            f"La « {rows[N.COMMISSIONING].label} » passée en mode manuel : ses dates, "
            f"{mocktext.span(_task(manual))}, ne sont plus calculées mais saisies, et Waterfall "
            f"ne les recalcule plus (WF-PLA-0020) ; elle n'a plus de marge et accepte désormais "
            f"son début et sa fin (editable_fields) ; une version de plus. Son prédécesseur, que "
            f"la date imposée borne désormais, devient critique : {_redated(manual)}. Avec "
            f"elle, sa récapitulative et {totals_said(manual)}, inchangés (WF-PLA-0100).",
            manual,
        ),
        "task_dates_entered.json": mocktext.example(
            f"Les dates de la « {rows[N.COMMISSIONING].label} », en mode manuel "
            f"(task_mode_changed), saisies {mocktext.span(_task(dated))}, où elles étaient "
            f"{mocktext.span(commissioning)} : la version que le changement de mode lui laissait "
            f"plus un, et {_version(dated)}. Consommée en {ENTERED_DATES[0].year}, sa ligne est "
            f"corrigée de l'inflation (reinflated) ; son prédécesseur retrouve de la marge, "
            f"{_redated(dated)}. Avec elle, sa récapitulative et {totals_said(dated)} "
            f"(WF-PLA-0020, WF-DEV-0040).",
            dated,
        ),
        "task_duration_entered.json": mocktext.example(
            f"La durée de « {DURATION_TASK} », tâche tirée autour du cœur, saisie en semaines, "
            f"{days} {unit}, et conservée dans cette unité (WF-PLA-0160) : elle finit le "
            f"{said_on(_task(duration)['finish'])} ; une version de plus. Ses successeurs suivent, "
            f"{_redated(duration)} ; avec elle, ses récapitulatives et {totals_said(duration)} "
            f"(WF-PLA-0020).",
            duration,
        ),
        "task_description_entered.json": mocktext.example(
            f"La description du « {rows[N.DESIGN_FILE].label} » saisie : « {DESCRIPTION} » ; rien "
            f"d'autre ne change, une version de plus. Avec elle, sa récapitulative et "
            f"{totals_said(described_)}, inchangés (WF-PLA-0130, WF-IHM-0040).",
            described_,
        ),
        "task_date_computed_refused.json": mocktext.example(
            f"Une date de fin envoyée pour le « {rows[N.MOUNTING].label} », en mode automatique, "
            f"dont les dates sont calculées : refusée sur son champ, sans paramètre ; rien n'est "
            f"écrit, et la grille nomme ce dont la valeur dépend en lisant "
            f"getComputedValueDependencies (WF-PLA-0020, WF-IHM-0030).",
            task_date_computed(),
        ),
        "task_horizon_exceeded.json": mocktext.example(
            f"La fin des « {rows[N.DESKS].label} », en mode manuel, saisie au "
            f"{mocktext.day(beyond_horizon())}, quinze ans et un jour après le début du projet, le "
            f"{mocktext.day(project_start())} : la saisie est refusée et la tâche nommée par son "
            f"nœud et son libellé ; rien n'est écrit (WF-PLA-0150).",
            task_horizon_exceeded(),
        ),
    }


def _link_examples() -> dict[str, JsonObject]:
    entered, tracked = predecessors_entered(), node_tracked()
    rows = {row.number: row for row in mockcore.current()}
    lag, unit = LINKED_LAG
    looped = [rows[number].label for number in cycle(CYCLE_ON, CYCLE_LINKS)]
    months, _ = HORIZON_LAG
    timelines = dict(TIMELINES)
    kept = mocktext.listed(
        [
            f"la chronologie « {timelines[timeline]} »"
            for timeline in mockwitness.INSCRIBED.get(UNTRACKED_TASK, ())
        ]
    )
    return {
        "predecessors_entered.json": mocktext.example(
            f"Les prédécesseurs de « {LINKED_TASK} », tâche tirée autour du cœur, saisis à "
            f"nouveau : la « {rows[N.FACTORY_ACCEPTANCE].label} », en fin à début, et "
            f"« {LINKED_AFTER} », en début à début, {lag} {unit} plus tard, le décalage conservé "
            f"dans son unité (WF-PLA-0030, WF-PLA-0160) ; la tâche part le "
            f"{said_on(_task(entered)['start'])}, une version de plus. Ses successeurs suivent, "
            f"{_redated(entered)} ; avec elle, ses récapitulatives et {totals_said(entered)} "
            f"(WF-PLA-0020).",
            entered,
        ),
        "predecessors_cycle_refused.json": mocktext.example(
            f"La « {rows[CYCLE_ON].label} » donnée à suivre le « {rows[N.WIRING].label} » et la "
            f"« {rows[N.COMMISSIONING].label} », qui la suit déjà : la liaison fermerait une "
            f"boucle, refusée, et le refus en nomme les tâches dans l'ordre des liaisons, "
            f"{mocktext.listed([f'« {label} »' for label in looped])} ; rien n'est écrit "
            f"(WF-PLA-0030).",
            predecessors_cycle_refused(),
        ),
        "predecessors_forbidden.json": mocktext.example(
            f"Le « {rows[FORBIDDEN_ON].label} » donné à suivre sa propre récapitulative, "
            f"« {rows[N.INSTALLATION].label} » : une liaison entre une récapitulative et l'une de "
            f"ses subordonnées est refusée, le code en disant la raison ; rien n'est écrit "
            f"(WF-PLA-0030, WF-PLA-0040).",
            predecessors_forbidden(),
        ),
        "predecessors_horizon_exceeded.json": mocktext.example(
            f"La « {rows[HORIZON_ON].label} » donnée à suivre le « {rows[N.MOUNTING].label} » "
            f"avec un décalage de {months} mois de travail : elle finirait plus de quinze ans "
            f"après le début du projet, le {mocktext.day(project_start())}. La saisie est refusée "
            f"et la tâche nommée ; rien n'est écrit (WF-PLA-0150).",
            predecessors_horizon_exceeded(),
        ),
        "node_create_horizon_exceeded.json": mocktext.example(
            f"Une tâche « {CREATED_BEYOND} » créée sous l'« {rows[N.INSTALLATION].label} » avec "
            f"une durée de {CREATED_DURATION[0]} mois de travail : elle finirait plus de quinze "
            f"ans après le début du projet. Refusée, elle est nommée par le libellé envoyé, sans "
            f"nœud, et rien n'est créé (WF-PLA-0150).",
            node_create_horizon_exceeded(),
        ),
        "node_tracking_milestone_refused.json": mocktext.example(
            f"La « {rows[UNTRACKED_TASK].label} », qui n'est pas un jalon, envoyée avec ses "
            f"inscriptions — {kept} — et une entrée au "
            f"suivi temps/temps : le suivi temps/temps est celui des jalons, et la saisie est "
            f"refusée sur le genre de cette entrée, la "
            f"{len(tracking_entries(UNTRACKED_TASK))}e envoyée ; rien n'est écrit (WF-PLA-0060, "
            f"#1159).",
            node_tracking_milestone_refused(),
        ),
        "node_tracked.json": mocktext.example(
            f"La « {rows[TRACKED_TASK].label} » inscrite à la chronologie "
            f"« {timelines[CUSTOMER]} » : ses inscriptions sont celles envoyées, une version de "
            f"plus. Avec elle, sa récapitulative et {totals_said(tracked)}, inchangés "
            f"(WF-PLA-0060).",
            tracked,
        ),
    }


def _parent(rows: dict[int, mockcore.Row], number: int) -> str:
    """Return the label of the task a node of the core is under."""
    parent = rows[number].parent
    if parent is None:
        message = f"the node {number} is a root"
        raise ValueError(message)
    return rows[parent].label


def _move_refusal_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    moved, under = loop_move()
    loop = [rows[number].label for number in move_loop(moved, under, described())]
    through = mocktext.listed([f"« {label} »" for label in loop[1:-1]])
    created_beside, moved_beside = _parent(rows, CREATED_AFTER), _parent(rows, MOVED_AFTER)
    return {
        "node_create_after_not_sibling.json": mocktext.example(
            f"La tâche « {SIBLING.label} » créée sous les « {rows[CREATED_UNDER].label} », "
            f"après le « {rows[CREATED_AFTER].label} », qui est une subordonnée du "
            f"« {created_beside} » : le nœud après lequel se placer n'est pas un frère sous le "
            f"parent visé. La création est refusée sur ce champ, sans paramètre ; rien n'est "
            f"écrit (#1183).",
            node_create_after_not_sibling(),
        ),
        "nodes_move_after_not_sibling.json": mocktext.example(
            f"Les « {rows[MOVED_AWAY].label} » déplacés sous la "
            f"« {rows[MOVED_UNDER].label} », après le « {rows[MOVED_AFTER].label} », qui "
            f"reste sous le « {moved_beside} » : le nœud après lequel se placer n'est pas un "
            f"frère sous le parent visé. Le déplacement est refusé sur ce champ, sans paramètre ; "
            f"rien ne bouge (#1183).",
            nodes_move_after_not_sibling(),
        ),
        "nodes_indent_forbidden.json": mocktext.example(
            f"La « {rows[INDENTED_FORBIDDEN].label} » mise en retrait sous le "
            f"« {rows[INDENTED_UNDER].label} », la tâche au-dessus d'elle à son niveau, qui est "
            f"son prédécesseur : celui-ci deviendrait sa récapitulative, et leur liaison "
            f"relierait une récapitulative à l'une de ses subordonnées. Le déplacement est "
            f"refusé sans paramètre, le code en disant la raison, comme pour des prédécesseurs "
            f"saisis (predecessors_forbidden) ; rien n'est écrit (WF-PLA-0030, WF-PLA-0040).",
            nodes_indent_forbidden(),
        ),
        "nodes_move_cycle_refused.json": mocktext.example(
            f"« {LOOP_MOVED} », tâche tirée autour du cœur, déplacée sous « {LOOP_UNDER} », "
            f"qu'elle suit déjà par {through} : la récapitulative qui la recevrait la couvrirait, "
            f"et ses liaisons fermeraient une boucle. Le déplacement est refusé, et le refus en "
            f"nomme les tâches dans l'ordre des liaisons, de la récapitulative à la tâche "
            f"déplacée, {mocktext.listed([f'« {label} »' for label in loop])} ; rien n'est "
            f"écrit (WF-PLA-0030, WF-PLA-0040).",
            nodes_move_cycle_refused(),
        ),
    }


def _place_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    lines, tasks = mixed_places()
    (line, _), (task, _) = MIXED
    return {
        "nodes_move_mixed.json": mocktext.example(
            f"Une sélection qui mêle une ligne et une tâche, « {rows[line].label} » du "
            f"« {_parent(rows, line)} » et « {rows[task].label} », envoyée sous le "
            f"« {rows[MIXED_UNDER].label} » après le « {rows[MIXED_AFTER].label} », sa première "
            f"subordonnée (after_node_id). Chaque nœud suit la règle, dans l'ordre de node_ids : "
            f"les lignes d'une tâche précèdent ses sous-tâches, et la ligne, envoyée après une "
            f"sous-tâche, se place après la dernière ligne du poste, qui n'en porte aucune — au "
            f"rang {lines.index(line) + 1} — ; la tâche suit le « {rows[MIXED_AFTER].label} », "
            f"au rang "
            f"{len(lines) + tasks.index(task) + 1} (#1187, #1188).",
            nodes_move_mixed(),
        ),
        "estimate_line_completed_refused.json": mocktext.example(
            f"Une ligne créée sous les « {rows[COMPLETED_UNDER].label} », terminées : aucune "
            f"ligne ne se crée sous une tâche terminée, qui se rouvre d'abord depuis le Kanban. "
            f"La création est refusée, la condition nommée ; rien n'est créé (WF-DEV-0050, "
            f"WF-RAE-0030, #1184).",
            estimate_line_completed_refused(),
        ),
    }
