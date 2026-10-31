# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the writes of the grids, generated from what each write changes (EP-02/L22).

A write of a grid answers what it changed (`NodesWritten`): the nodes written; the tasks it
redated, by their schedule (`rescheduled`); the lines and the tasks it moved in time, by their
amounts inflation included (`reinflated`); the summaries above all of them, whole (`ancestors`);
the totals of the whole structure, and the version the structure moved on to (WF-IHM-0040,
WF-PLA-0020, WF-DEV-0040). Here each answer is the difference between two
readings of one structure, before and after the write, never written by hand (#287).

The writes of the witness are made on its core: its description (``wftools.mockwitness``) is
amended, dated and priced again (``wftools.mockcore``), and read whole. Those the journeys make
on the structure of a thousand tasks the fake back serves first (``wftools.mockstructure``) are
made on it: a duration lengthened, a label entered, a block pasted. And the plans of a paste
and its refusal are read from the block and from the reference data, as the server reads them.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import REPOSITORY, mockcore, mockdating, mocktext, mockwitness
from wftools.mockids import universe
from wftools.mockstructure import (
    CATEGORY_LABELS,
    NETWORK,
    REFERENCE_YEAR,
    JsonObject,
    JsonValue,
    described,
    labels,
)
from wftools.mockwitness import (
    CABLE_FITTER,
    CORE,
    FACTORY_ACCEPTANCE,
    FIRST_ITEM,
    FIRST_LOT,
    GENERATED,
    LABOUR,
    SUBPROJECT_CONTROL,
    SUBPROJECT_TESTS,
    WIRING,
    Line,
    Link,
    N,
    Task,
    fixture,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

type Node = dict[str, Any]

SCHEDULE = ("start", "finish", "total_float", "is_critical", "link_conflicts", "finish_overdue")
"""The fields of a task a write may redate without writing it (`NodeSchedule`)."""

INFLATION = ("budgeted_amount", "reestimated_amount", "consumption_year")
"""The fields of a line or a task a write may move in time without writing it (`NodeInflation`)."""


def written(
    before: JsonObject,
    after: JsonObject,
    writes: Sequence[str],
    *,
    deleted: Sequence[str] = (),
    structure_version: int = 2,
) -> JsonObject:
    """Return what a write answers, from the readings of the whole structure before and after.

    The nodes written, whole, their version one further — a node created, at its first —; the
    tasks, not summaries, whose schedule changed without being written; the lines and the tasks,
    not summaries, whose amounts inflation included or year of consumption changed, but those
    the ancestors render whole; the ancestors of the nodes written, those they had before a move
    with those they have after, of the node deleted — read before, as it is gone after — and of
    the tasks redated, whole, but those written. Each list in the order of the plan, each node once
    (`NodesWritten`).
    """
    was, now = _by_id(before), _by_id(after)
    existing = [node_id for node_id in writes if node_id in was]
    moved = [
        node_id
        for node_id, node in now.items()
        if node_id not in writes
        and _is_activity(node)
        and _changed(node["task"], was[node_id]["task"], SCHEDULE)
    ]
    above = (_ancestors(now, [*writes, *moved]) | _ancestors(was, [*existing, *deleted])) - {
        *writes
    }
    reinflated: list[JsonValue] = []
    for node_id, node in now.items():
        if node_id in writes or node_id in above or not (_is_activity(node) or _is_line(node)):
            continue
        facet, old = _facet(node), _facet(was[node_id])
        if _changed(facet, old, INFLATION):
            reinflated.append({"node_id": node_id, **{key: facet.get(key) for key in INFLATION}})
    return {
        "nodes": [
            {
                **now[node_id],
                "lock_version": was[node_id]["lock_version"] + 1 if node_id in was else 1,
            }
            for node_id in writes
        ],
        "ancestors": [node for node_id, node in now.items() if node_id in above],
        "rescheduled": [
            {"node_id": node_id, **{key: now[node_id]["task"].get(key) for key in SCHEDULE}}
            for node_id in moved
        ],
        "reinflated": reinflated,
        "totals": after["totals"],
        "structure_lock_version": structure_version,
    }


def _by_id(answer: JsonObject) -> dict[str, Node]:
    """Return the nodes of an answer by their identifier, in the order of the plan."""
    return {node["node_id"]: node for node in cast("list[Node]", answer["items"])}


def _facet(node: Node) -> Node:
    return cast("Node", node[node["kind"]])


def _is_activity(node: Node) -> bool:
    """Whether a node is a task that is not a summary: one a write may redate."""
    return node["kind"] == "task" and not node["task"]["is_summary"]


def _is_line(node: Node) -> bool:
    return node["kind"] == "estimate_line"


def _changed(facet: Node, old: Node, keys: Iterable[str]) -> bool:
    return any(facet.get(key) != old.get(key) for key in keys)


def _ancestors(nodes: dict[str, Node], of: Iterable[str]) -> set[str]:
    """Return the ancestors of some nodes, each once."""
    found: set[str] = set()
    for node_id in of:
        parent = nodes[node_id]["parent_id"]
        while parent is not None:
            found.add(parent)
            parent = nodes[parent]["parent_id"]
    return found


# --- The writes of the witness, made on its core ----------------------------------------------


def amended(
    roots: Iterable[Task],
    task: Callable[[Task], Task] = lambda each: each,
    line: Callable[[Line], Line | None] = lambda each: each,
) -> tuple[Task, ...]:
    """Return the description of the core with each task and each line changed, or a line gone."""

    def walk(each: Task) -> Task:
        lines = tuple(kept for kept in (line(below) for below in each.lines) if kept is not None)
        return task(
            replace(each, lines=lines, children=tuple(walk(child) for child in each.children))
        )

    return tuple(walk(root) for root in roots)


def on_task(number: int, **changes: Any) -> Callable[[Task], Task]:
    """Change the fields of the task of a number, and of no other."""
    return lambda each: replace(each, **changes) if each.number == number else each


def on_line(number: int, **changes: Any) -> Callable[[Line], Line | None]:
    """Enter fields of the line of a number, and of no other.

    Its budget stays the one the reference revision gave it, whatever is entered: the
    re-estimate follows the quantities, the budget does not (WF-DEV-0020).
    """

    def entered(each: Line) -> Line:
        budgeted = mockdating.price(each, REFERENCE_YEAR).budgeted
        return replace(each, budgeted=budgeted, **changes)

    return lambda each: entered(each) if each.number == number else each


def removed(number: int) -> Callable[[Line], Line | None]:
    """Remove the line of a number."""
    return lambda each: None if each.number == number else each


def core_write(
    roots: Iterable[Task],
    writes: Sequence[int],
    deleted: Sequence[int] = (),
    *,
    following: Iterable[Task] | None = None,
) -> JsonObject:
    """Return what a write of the core answers: the structure read whole today, then as amended.

    The core amended, the thousand tasks drawn about it as they are: the tasks the write redates
    and the totals are those of the whole structure, the core incrusted in it (#376).

    A write that follows another reads the core as that one left it, the nodes it wrote one
    version further, and leaves the structure one version further still: two answers never
    render one node at one version with two contents (#421).
    """
    if following is None:
        before, version = mockcore.whole(mockcore.current()), 2
    else:
        before, version = copy.deepcopy(mockcore.whole(mockcore.current(described(following)))), 3
        for node in cast("list[Node]", before["items"]):
            if node["node_id"] in {universe(number) for number in writes}:
                node["lock_version"] += 1
    after = mockcore.whole(mockcore.current(described(roots)))
    return written(
        before,
        after,
        [universe(number) for number in writes],
        deleted=[universe(number) for number in deleted],
        structure_version=version,
    )


MILESTONE = FACTORY_ACCEPTANCE
CONTROL_STATION, BLOCKS = N.CONTROL_STATION, N.BLOCKS
MOUNTING, WIRING_ON_SITE, COMMISSIONING_TASK, COMMISSIONING_LINE = (
    N.MOUNTING,
    N.WIRING_ON_SITE,
    N.COMMISSIONING,
    N.COMMISSIONING_LINE,
)
"""The nodes of the core the writes are about (``mockwitness``)."""

RENAMED = "Câblage et repérage des armoires"
SITE_DELAY = 2
"""The working days the cabinets take to reach the site, after the factory acceptance."""
LABOUR_HOURS = Decimal(14)
REESTIMATED_HOURS = Decimal(10)


def task_renamed() -> JsonObject:
    """Return what updateTaskFacet answers when the wiring of the cabinets is renamed."""
    return core_write(amended(CORE, on_task(WIRING, label=RENAMED)), [WIRING])


def task_attached() -> JsonObject:
    """Return what updateTaskFacet answers when the factory acceptance bears the post 1.1.

    The milestone of the deliverable of the post, the report of the factory acceptance, bears
    the post of the one lot of the witness, which the summary above it bears: a leaf may bear a
    post, and the task of the post is in the subtree of the task of its lot (WF-PLA-0170, #817).
    Of the writes here, none other renders the milestone; the Kanban's completion of it
    (``wftools.mockkanban``, `milestone_completed`) follows this one, one version further: two
    answers never render it at one version (#421).
    """
    return core_write(amended(CORE, on_task(MILESTONE, bears=FIRST_ITEM)), [MILESTONE])


def estimate_line_updated() -> JsonObject:
    """Return what updateEstimateLine answers when the labour of the wiring takes 14 hours."""
    return core_write(amended(CORE, line=on_line(LABOUR, hours=LABOUR_HOURS)), [LABOUR])


def remaining_reestimated() -> JsonObject:
    """Return what setLineRemaining answers when the labour of the wiring is re-estimated at 10 h.

    The re-estimate follows the figures entered, the budget the reference fixed does not
    (WF-RAE-0040, WF-DEV-0020). It follows the 14 hours entered (`estimate_line_updated`):
    the line is read at the version that write left (#421).
    """
    return core_write(
        amended(CORE, line=on_line(LABOUR, hours=REESTIMATED_HOURS)),
        [LABOUR],
        following=amended(CORE, line=on_line(LABOUR, hours=LABOUR_HOURS)),
    )


COMPLETION_CORRELATION = universe(965)


def completion_date_required() -> JsonObject:
    """Return what setLineRemaining answers to a re-estimate that completes its task undated.

    The last open line of the wiring of the cabinets set to nothing completes the task, at a
    date the validation asks for (WF-RAE-0040, WF-PLA-0130): without one, the entry is refused,
    the task named, and nothing is written.
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/completed_on",
                "code": "COMPLETION_DATE_REQUIRED",
                "params": {"task_node_id": universe(WIRING)},
            }
        ],
        "correlation_id": COMPLETION_CORRELATION,
    }


def estimate_line_subproject_changed() -> JsonObject:
    """Return what updateEstimateLine answers when the commissioning passes to its subproject.

    The line of the commissioning on site, borne by a task not started, leaves the control
    station, charged with actual costs, for the tests and the commissioning: a line of a task not
    started changes its subproject (WF-PRJ-0050). Only its subproject changes, not its budget,
    the offer's (#467), nor any amount: the ventilation of the project alone.
    """

    def moved(each: Line) -> Line:
        return (
            replace(each, subproject=SUBPROJECT_TESTS)
            if each.number == COMMISSIONING_LINE
            else each
        )

    return core_write(amended(CORE, line=moved), [COMMISSIONING_LINE])


SUBPROJECT_CORRELATION = universe(1168)


def estimate_line_subproject_has_actual_costs() -> JsonObject:
    """Return what updateEstimateLine answers when the labour of the wiring leaves its subproject.

    The wiring of the cabinets is started, and the control station, the subproject of its labour
    line, received the invoice of the screens: a share of those costs is the line's, which may
    not leave it (WF-PRJ-0050, #1066). The refusal names the subproject, by its identifier and
    its label, on the field sent; nothing is written.
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/subproject_id",
                "code": "SUBPROJECT_HAS_ACTUAL_COSTS",
                "params": {
                    "subproject": {
                        "subproject_id": SUBPROJECT_CONTROL,
                        "label": labels()[SUBPROJECT_CONTROL],
                    }
                },
            }
        ],
        "correlation_id": SUBPROJECT_CORRELATION,
    }


def node_deleted() -> JsonObject:
    """Return what deleteNode answers when the terminal blocks are deleted from the estimate."""
    return core_write(amended(CORE, line=removed(BLOCKS)), [], [BLOCKS])


def predecessor_set() -> JsonObject:
    """Return what setPredecessors answers when the mounting waits two days after the acceptance.

    The predecessors of the mounting on site, not started, set anew: the factory acceptance,
    finish to start, two days later — the cabinets on their way to the site (WF-PLA-0030).
    """
    links = (Link(MILESTONE, lag=SITE_DELAY),)
    return core_write(amended(CORE, on_task(MOUNTING, links=links)), [MOUNTING])


def estimate_line_redated() -> JsonObject:
    """Return what updateEstimateLine answers when the wiring on site goes to the cable fitter.

    The mounting then has two roles on two calendars, and works the days both work, the fewest
    hours of each (WF-PLA-0010): it finishes later, and the commissioning after it.
    """
    roots = amended(CORE, line=on_line(WIRING_ON_SITE, role=CABLE_FITTER))
    return core_write(roots, [WIRING_ON_SITE])


# --- The writes the journeys make on the structure of a thousand tasks -----------------------

LENGTHENED = "Revue 2.1.27"
"""The work task whose duration the example lengthens: it finishes on Friday 25 December 2026,
with forty days of float, and its one successor in its chain, « Reprise 2.1.30 », starts the
Monday after."""

LENGTHENED_BY = 4
"""The working days the duration grows by: the task finishes on 31 December, and its successor
starts on the first working day of 2027 — its lines are consumed a year later, corrected anew at
the inflation of the witness project (WF-DEV-0040) —, within the float: the milestone of the lot
does not move, nor anything after it."""


def volume_write(
    roots: Iterable[Task],
    writes: Sequence[int],
    *,
    before: JsonObject | None = None,
    structure_version: int = 2,
) -> JsonObject:
    """Return what a write of the structure answers: the whole structure read, then as amended."""
    read = mockcore.whole(mockcore.current()) if before is None else before
    after = mockcore.whole(mockcore.current(roots))
    return written(
        read,
        after,
        [mockwitness.node_id(number) for number in writes],
        structure_version=structure_version,
    )


def task_lengthened() -> JsonObject:
    """Return what updateTaskFacet answers when the duration of LENGTHENED grows by its days."""
    [task] = [each for each in mockdating.tasks_in_order(NETWORK) if each.label == LENGTHENED]
    roots = amended(described(), on_task(task.number, days=task.days + LENGTHENED_BY))
    return volume_write(roots, [task.number])


LINE = NETWORK[0].children[0].children[0].lines[0].number
"""The first line drawn after the core, « Heures d'ingénierie », on which the journeys enter a
label and paste a block (`test_the_marks_the_journeys_read`)."""

ROW = LINE - GENERATED
"""The row of LINE in the structure as described."""

ENTERED = "Heures de câblage"


def estimate_line_entered() -> JsonObject:
    """Return what updateEstimateLine answers to the label of LINE entered.

    The structure is at its third version: the line and the structure were written twice since
    they were read, and this answer is the second (#178).
    """
    return volume_write(
        amended(described(), line=on_line(LINE, label=ENTERED)),
        [LINE],
        structure_version=ENTERED_VERSION,
    )


ENTERED_VERSION = 3
"""The version of the structure the label entered leaves: the paste follows it (#421)."""

BLOCK = (
    ("Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"),
    ("Heures d'essais", "Mise en service", "Technicien de mise en service", "1"),
    ("Matériel de câblage", "Matériel électrique", "", "24"),
)
"""A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
copies it, pasted on the label of the first line: the rows of the journeys and of the tests."""

UNKNOWN_CATEGORY = (BLOCK[0], ("Heures d'essais", "Essais", "", "1"), BLOCK[2])
"""The same block, its second row naming a category the reference data does not know."""

REJUDGED = (BLOCK[0], ("Heures d'essais", BLOCK[0][1], BLOCK[0][2], "1"), BLOCK[2])
"""The same block, its second row moving its line to the category and the role the first keeps:
the category deactivated between the preview and the confirmation refuses the second row alone,
the first naming the category its line bears already (#764, #747)."""

PASTES = (universe(991), universe(992))
TOO_WIDE_CORRELATION = universe(973)
STALE_PASTE_CORRELATION = universe(1555)


def known() -> tuple[dict[str, str], dict[str, str]]:
    """Return the categories and the roles of the universe by their label."""
    roles = {role["label"]: role["resource_role_id"] for role in fixture("resource_roles")["items"]}
    return {label: key for key, label in CATEGORY_LABELS.items()}, roles


def paste_plan(block: Sequence[Sequence[str]], paste_id: str) -> JsonObject:
    """Return what previewPaste answers for a block: each row accepted, or refused by its cell.

    A category or a role the reference data does not name is refused, its row and its column
    named; an empty role writes nothing (WF-IHM-0050).
    """
    categories, roles = known()
    rejected: list[JsonValue] = []
    for row, (_, category, role, _) in enumerate(block):
        if category not in categories:
            rejected.append(
                {"row": row, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"}
            )
        elif role and role not in roles:
            rejected.append(
                {"row": row, "column": "resource_role", "code": "UNKNOWN_RESOURCE_ROLE"}
            )
    return {"paste_id": paste_id, "accepted": len(block) - len(rejected), "rejected": rejected}


def paste_applied(
    block: Sequence[Sequence[str]] = BLOCK, refused: Sequence[JsonObject] | None = None
) -> JsonObject:
    """Return what applyPaste answers for a block: its valid rows written on the lines from LINE.

    Each line takes the label, the category, the role and the quantity of its row; its amount
    follows its quantity, its budget, the reference's, does not (WF-DEV-0020); its task and the
    summaries above follow its amount, and the totals — read again from the structure written,
    as any write of the structure (#376). The paste follows the label entered on LINE
    (`estimate_line_entered`): it reads the line at the version that write left, so that two
    answers never render one node at one version with two contents (#421). A row the plan refuses
    is not written, its line left as it was, and the answer says it again as the plan did
    (`PasteApplied.rejected`, WF-IHM-0050): a partial success. The refusals are the plan's, or
    those given, which the confirmation adds judging the rows again (`rejudged`).
    """
    entered = amended(described(), line=on_line(LINE, label=ENTERED))
    before = copy.deepcopy(mockcore.whole(mockcore.current(entered)))
    for node in cast("list[Node]", before["items"]):
        if node["node_id"] == mockwitness.node_id(LINE):
            node["lock_version"] += 1
    roots, targets, rejected = pasted(block, refused)
    written = volume_write(roots, targets, before=before, structure_version=ENTERED_VERSION + 1)
    return {**written, "rejected": cast("list[JsonValue]", rejected)}


def pasted_task() -> Task:
    """Return the task of LINE, whose lines a block pasted on LINE writes."""
    [task] = [each for each in mockdating.tasks_in_order(NETWORK) if LINE in _numbers(each.lines)]
    return task


def pasted_lines(block: Sequence[Sequence[str]]) -> list[Line]:
    """Return the lines a block pasted on LINE writes, one per row, in the order of the plan."""
    return list(pasted_task().lines[: len(block)])


def rejudged(block: Sequence[Sequence[str]], deactivated: str) -> list[JsonObject]:
    """Return the refusals the confirmation adds once a category is deactivated since the preview.

    A row whose category cell changes its line to the deactivated category is refused by
    `INACTIVE_REFERENCE_OBJECT`; one that names the category its line bears already changes
    nothing, and is not (`PasteRejection`, EP-14/L42j, #747).
    """
    categories, _ = known()
    return [
        {"row": row, "column": "cost_category", "code": "INACTIVE_REFERENCE_OBJECT"}
        for row, (line, (_, category, _, _)) in enumerate(
            zip(pasted_lines(block), block, strict=True)
        )
        if categories[category] == deactivated != line.category
    ]


def paste_applied_rejudged() -> JsonObject:
    """Return what applyPaste answers for REJUDGED, its category deactivated after the preview.

    The preview accepts the three rows, as it does the block of the journeys; the confirmation
    judges them again (`PasteApplied`): the second row, which moves its line to the deactivated
    category, is refused and not written, the others are. The line written that keeps the
    category says it uses an object deactivated (`EstimateLine.uses_inactive_object`, WF-REF-0010).
    """
    categories, _ = known()
    deactivated = categories[REJUDGED[0][1]]
    # The readings are cached and shared with the other answers: this one is marked on its copy.
    applied = copy.deepcopy(paste_applied(REJUDGED, rejudged(REJUDGED, deactivated)))
    for node in cast("list[Node]", applied["nodes"]):
        line = node["estimate_line"]
        line["uses_inactive_object"] = line["cost_category_id"] == deactivated
    return applied


def paste_stale() -> JsonObject:
    """Return the 412 of a paste confirmed once another write moved its structure on."""
    return {
        "code": "STALE_LOCK_VERSION",
        "status": 412,
        "params": {"expected_lock_version": ENTERED_VERSION + 1},
        "correlation_id": STALE_PASTE_CORRELATION,
    }


def pasted(
    block: Sequence[Sequence[str]], refused_rows: Sequence[JsonObject] | None = None
) -> tuple[tuple[Task, ...], list[int], list[JsonObject]]:
    """Return the structure a block leaves, the lines its valid rows write, and its refusals.

    The structure follows the label entered on LINE; a row the plan refuses, or the confirmation
    when it is given its refusals, leaves its line as that write left it (WF-IHM-0050).
    """
    entered = amended(described(), line=on_line(LINE, label=ENTERED))
    rejected = (
        cast("list[JsonObject]", paste_plan(block, PASTES[0])["rejected"])
        if refused_rows is None
        else list(refused_rows)
    )
    refused = {cast("int", each["row"]) for each in rejected}
    rows = list(zip(_numbers(pasted_lines(block)), block, strict=True))
    targets = [number for row, (number, _) in enumerate(rows) if row not in refused]
    categories, roles = known()
    roots = entered
    for number, (label, category, role, quantity) in (
        pair for row, pair in enumerate(rows) if row not in refused
    ):
        roots = amended(
            roots,
            line=on_line(
                number,
                label=label,
                category=categories[category],
                role=roles.get(role),
                quantity=Decimal(quantity),
            ),
        )
    return tuple(roots), targets, rejected


def _numbers(lines: Iterable[Line]) -> list[int]:
    return [line.number for line in lines]


NODE_COLUMNS = REPOSITORY / "docs" / "api" / "components" / "schemas" / "revisions.yaml"
"""Where the contract lists the columns of the grids, in the order a paste fills them."""


def node_columns(text: str | None = None) -> list[str]:
    """Return the columns of the grids, in their order (`NodeColumn`), read from the contract."""
    lines = (NODE_COLUMNS.read_text(encoding="utf-8") if text is None else text).splitlines()
    start = lines.index("NodeColumn:")
    enum = next(index for index in range(start, len(lines)) if lines[index].strip() == "enum:")
    columns: list[str] = []
    for line in lines[enum + 1 :]:
        if not line.startswith("    - "):
            break
        columns.append(line.removeprefix("    - ").strip())
    return columns


def line_width(columns: Sequence[str]) -> int:
    """Return how many columns a line of the estimate offers from its label (`NodeColumn`).

    Its label, then those from the category to the last: the columns of a line.
    """
    return 1 + len(columns) - columns.index("cost_category")


def paste_too_wide() -> JsonObject:
    """Return what previewPaste answers to a block one column wider than a line from its label."""
    return {
        "code": "PASTE_TOO_WIDE",
        "status": 422,
        "params": {"max_columns": line_width(node_columns())},
        "correlation_id": TOO_WIDE_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def _node(answer: JsonObject, number: int, key: str = "ancestors") -> Node:
    """Return a node of the core an answer renders, by its number, in one of its lists."""
    return next(
        node for node in cast("list[Node]", answer[key]) if node["node_id"] == universe(number)
    )


def _money(value: JsonValue) -> str:
    return mocktext.amount(Decimal(str(value)))


def _on(instant: JsonValue) -> str:
    return mocktext.day(date.fromisoformat(cast("dict[str, str]", instant)["date"]))


def totals_said(answer: JsonObject) -> str:
    """Say the totals of the structure an answer gives: its lines, hours and amounts."""
    totals = cast("dict[str, str]", answer["totals"])
    return (
        f"les totaux de la structure, {mocktext.count(int(totals['estimate_line_count']))} "
        f"lignes, {totals['hours'].replace('.', ',')} h, {_money(totals['base_amount'])} à "
        f"l'année de référence, dont {_money(totals['budgeted_amount'])} budgétés"
    )


def latest_finish(nodes: Iterable[Node]) -> tuple[str, Decimal]:
    """Return the latest finish of the tasks of a reading: the end of the structure."""
    return max(
        (node["task"]["finish"]["date"], Decimal(node["task"]["finish"]["hours"]))
        for node in nodes
        if node["kind"] == "task"
    )


def end_after(answer: JsonObject, before: JsonObject) -> tuple[str, Decimal]:
    """Return the end of the structure a write leaves: the reading before, as the answer redates."""
    nodes = _by_id(before)
    for node in [*cast("list[Node]", answer["nodes"]), *cast("list[Node]", answer["ancestors"])]:
        nodes[node["node_id"]] = node
    for entry in cast("list[Node]", answer["rescheduled"]):
        nodes[entry["node_id"]] = {
            **nodes[entry["node_id"]],
            "task": {**nodes[entry["node_id"]]["task"], "finish": entry["finish"]},
        }
    return latest_finish(nodes.values())


def _margin(answer: JsonObject, before: JsonObject) -> str:
    """Say what bounds the tasks a write redates, and where the end of the structure goes.

    Their successors that the write does not redate — milestones, or tasks —, agreed to their
    number; and the end of the structure, the same or moved, from the readings themselves.
    """
    entries = cast("list[Node]", answer["rescheduled"])
    if not entries:
        return ""
    nodes, moved = _by_id(before), {entry["node_id"] for entry in entries}
    followers = [
        node
        for node in nodes.values()
        if node["node_id"] not in moved
        and any(link["predecessor_node_id"] in moved for link in node.get("predecessors", []))
    ]
    one, alone = len(entries) == 1, len(followers) == 1
    kind = "jalon" if all(node["task"]["is_milestone"] for node in followers) else "tâche"
    article = ("le " if kind == "jalon" else "la ") if alone else "les "
    what = f"{article}{kind}{'' if alone else 's'}"
    bound = (
        f"dans la marge que {'lui' if one else 'leur'} {'laisse' if alone else 'laissent'} "
        f"{what} qu'{'elle précède' if one else 'elles précèdent'}"
    )
    was, now = latest_finish(nodes.values()), end_after(answer, before)
    end = (
        "la fin de la structure ne bouge pas"
        if was == now
        else f"la fin de la structure passe du {mocktext.day(date.fromisoformat(was[0]))} au "
        f"{mocktext.day(date.fromisoformat(now[0]))}"
    )
    return f"{bound} : {end}"


def _redated(answer: JsonObject, rows: dict[int, mockcore.Row]) -> str:
    """Say the tasks a write redates, from what it answers: each by its label and its dates."""
    labels = {mockwitness.node_id(number): row.label for number, row in rows.items()}
    return mocktext.listed(
        [
            f"« {labels[entry['node_id']]} », {mocktext.span(entry)}"
            for entry in cast("list[Node]", answer["rescheduled"])
        ]
    )


def _plural(answer: JsonObject) -> str:
    return "" if len(cast("list[Node]", answer["rescheduled"])) == 1 else "s"


def _which(answer: JsonObject) -> str:
    return (
        "la tâche qu'" if len(cast("list[Node]", answer["rescheduled"])) == 1 else "les tâches qu'"
    )


def writes() -> dict[str, JsonObject]:
    """Return the named examples of the writes of the grids, by file name."""
    return {**_core_writes(), **_volume_writes()}


def _core_writes() -> dict[str, JsonObject]:
    renamed, updated, attached = task_renamed(), estimate_line_updated(), task_attached()
    reestimated = remaining_reestimated()
    [reestimated_line] = cast("list[Node]", reestimated["nodes"])
    deleted, linked, redated = node_deleted(), predecessor_set(), estimate_line_redated()
    changed = estimate_line_subproject_changed()
    [line] = cast("list[Node]", updated["nodes"])
    [mounting] = cast("list[Node]", linked["nodes"])
    unmoved = "" if linked["reinflated"] else " — aucun montant ne change d'année —"
    whole = mockcore.whole(mockcore.current())
    later = {entry["node_id"]: entry for entry in cast("list[Node]", redated["rescheduled"])}
    priced = {entry["node_id"]: entry for entry in cast("list[Node]", redated["reinflated"])}
    commissioning = universe(COMMISSIONING_TASK)
    before = {row.number: row for row in mockcore.current()}
    mounted = cast("Node", before[MOUNTING].node["task"])
    acceptance = cast("Node", before[MILESTONE].node["task"])
    return {
        "task_renamed.json": mocktext.example(
            f"La tâche « {before[WIRING].label} » renommée « {RENAMED} » ; une version de plus. "
            f"Avec elle, sa récapitulative « {before[CONTROL_STATION].label} », dont rien ne "
            f"change, et {totals_said(renamed)}, inchangés (WF-PLA-0130, WF-IHM-0040).",
            renamed,
        ),
        "task_attached.json": mocktext.example(
            f"Le jalon « {before[MILESTONE].label} » rattaché au poste « {FIRST_ITEM.label} » du "
            f"lot « {FIRST_LOT.label} », que porte sa récapitulative "
            f"« {before[CONTROL_STATION].label} » : une feuille peut porter un poste, et la tâche "
            f"du poste reste dans le sous-arbre de la tâche de son lot ; il porte le poste, nommé "
            f"pour la colonne du lotissement, et aucun lot, une version de plus. Avec lui, sa "
            f"récapitulative, dont rien ne change, et {totals_said(attached)}, inchangés "
            f"(WF-PLA-0170, WF-IHM-0040).",
            attached,
        ),
        "estimate_line_updated.json": mocktext.example(
            f"La ligne de main-d'œuvre du devis, « {before[LABOUR].label} », dont la charge "
            f"passe de {mocktext.amount(before[LABOUR].hours, 1)} à "
            f"{LABOUR_HOURS} h : le montant réestimé recalculé depuis ses grandeurs, "
            f"{_money(line['estimate_line']['reestimated_amount'])}, le budgété inchangé, "
            f"{_money(line['estimate_line']['budgeted_amount'])}, fixé par la référence ; une "
            f"version de plus. Avec elle, sa tâche « {before[WIRING].label} », portée à "
            f"{_money(_node(updated, WIRING)['task']['base_amount'])}, la récapitulative "
            f"« {before[CONTROL_STATION].label} » au-dessus, à "
            f"{_money(_node(updated, CONTROL_STATION)['task']['base_amount'])}, et "
            f"{totals_said(updated)}, le budgété inchangé (WF-DEV-0020, WF-DEV-0030, "
            f"WF-DEV-0050).",
            updated,
        ),
        "remaining_reestimated.json": mocktext.example(
            f"La réestimation de la ligne de main-d'œuvre « {before[LABOUR].label} », budgétée à "
            f"{mocktext.amount(before[LABOUR].hours, 1)} h : une charge de "
            f"{REESTIMATED_HOURS} h donne un montant réestimé de "
            f"{_money(reestimated_line['estimate_line']['reestimated_amount'])}, recalculé "
            f"depuis ses grandeurs et jamais saisi, le budgété inchangé, "
            f"{_money(reestimated_line['estimate_line']['budgeted_amount'])}, fixé par la "
            f"référence ; une version de plus que celle que la saisie de {LABOUR_HOURS} h "
            f"(estimate_line_updated) lui laissait, et la structure à "
            f"{reestimated['structure_lock_version']}. Avec elle, sa tâche "
            f"« {before[WIRING].label} », "
            f"à {_money(_node(reestimated, WIRING)['task']['reestimated_amount'])} réestimés, "
            f"la récapitulative « {before[CONTROL_STATION].label} » au-dessus, à "
            f"{_money(_node(reestimated, CONTROL_STATION)['task']['reestimated_amount'])}, et "
            f"{totals_said(reestimated)}, le budgété inchangé (WF-RAE-0040, WF-DEV-0020).",
            reestimated,
        ),
        "estimate_line_subproject_changed.json": mocktext.example(
            f"La ligne « {before[COMMISSIONING_LINE].label} » de la "
            f"{before[COMMISSIONING_TASK].label.lower()}, non démarrée, passée du sous-projet "
            f"« {labels()[SUBPROJECT_CONTROL]} », qui a reçu des coûts réels, au sous-projet "
            f"« {labels()[SUBPROJECT_TESTS]} » : une ligne d'une tâche non démarrée change de "
            f"sous-projet ; une version de plus, ses montants et son budget inchangés. Avec elle, "
            f"ses ancêtres, dont rien ne change, et {totals_said(changed)}, inchangés : seule la "
            f"ventilation du projet change (WF-PRJ-0050).",
            changed,
        ),
        "estimate_line_subproject_has_actual_costs.json": mocktext.example(
            f"La ligne de main-d'œuvre « {before[LABOUR].label} » du "
            f"« {before[WIRING].label} », démarré, envoyée hors du sous-projet "
            f"« {labels()[SUBPROJECT_CONTROL]} », qui a reçu la facture des écrans : une part de "
            f"ces coûts lui revient, et elle ne le quitte pas. Le refus nomme le sous-projet sur "
            f"le champ envoyé, et rien n'est écrit ; la ligne ne nommait pas ce champ parmi ceux "
            f"qu'elle accepte (editable_fields, WF-PRJ-0050).",
            estimate_line_subproject_has_actual_costs(),
        ),
        "remaining_completion_date_required.json": mocktext.example(
            f"Variante contrefactuelle déclarée : la charge de « {before[LABOUR].label} » mise à "
            f"zéro, les borniers et la provision du risque 751 supposés déjà réestimés à zéro, "
            f"sans date de terminaison. La saisie terminerait le « {before[WIRING].label} », "
            f"démarré, à une date que la validation demande : elle est refusée sur "
            f"`/completed_on`, la tâche nommée, et rien n'est écrit ; l'écran demande la date, "
            f"proposée au jour courant, et rejoue la saisie (WF-RAE-0040, WF-PLA-0130).",
            completion_date_required(),
        ),
        "node_deleted.json": mocktext.example(
            f"La ligne de débours « {before[BLOCKS].label} », "
            f"{mocktext.amount(before[BLOCKS].amounts.base)}, supprimée du devis du lot "
            f"« {before[CONTROL_STATION].label} » : rien à rendre d'elle, sa tâche "
            f"« {before[WIRING].label} » recalculée à "
            f"{_money(_node(deleted, WIRING)['task']['base_amount'])} et la récapitulative "
            f"au-dessus à {_money(_node(deleted, CONTROL_STATION)['task']['base_amount'])}, "
            f"{totals_said(deleted)}, et le compteur de la structure, passé à 2 (WF-DEV-0050, "
            f"WF-IHM-0110).",
            deleted,
        ),
        "predecessor_set.json": mocktext.example(
            f"Les prédécesseurs du montage des armoires sur site, non démarré, saisis à nouveau : "
            f"la réception usine du {_on(acceptance['finish'])}, en fin à début, avec "
            f"{SITE_DELAY} jours ouvrés de décalage, le temps d'acheminer les armoires. Le "
            f"montage, écrit, part le {_on(mounting['task']['start'])} et finit le "
            f"{_on(mounting['task']['finish'])} ; une version de plus. Sans être écrite"
            f"{_plural(linked)}, {_which(linked)}il redate : {_redated(linked, before)}"
            f"{unmoved}, {_margin(linked, whole)}. Aucune date passée ne bouge : la réception "
            f"usine reste au "
            f"{_on(acceptance['finish'])}. Les récapitulatives au-dessus, entières ; les totaux de "
            f"la structure ne changent pas (WF-PLA-0020, WF-PLA-0030, WF-PLA-0100).",
            linked,
        ),
        "estimate_line_redated.json": mocktext.example(
            f"La ligne « {before[WIRING_ON_SITE].label} » du montage des armoires sur site "
            f"confiée au monteur câbleur, sur la semaine de quatre jours de dix heures ; une "
            f"version de plus, ses montants inchangés. Le montage, dont l'autre ligne reste au "
            f"technicien de mise en service sur la semaine standard, ne travaille plus que les "
            f"jours de ses deux rôles, à huit heures (WF-PLA-0010) : il finit le "
            f"{_on(later[universe(MOUNTING)]['finish'])} au lieu du "
            f"{_on(mounted['finish'])}, et la mise en service qui le suit "
            f"démarre le {_on(later[commissioning]['start'])} (rescheduled). Consommée en 2027, "
            f"sa ligne, « {before[COMMISSIONING_LINE].label} », est réestimée inflation comprise, "
            f"à 3 % du projet, "
            f"{_money(priced[universe(COMMISSIONING_LINE)]['reestimated_amount'])} "
            f"au lieu de {mocktext.amount(before[COMMISSIONING_LINE].amounts.reestimated)}, et la "
            f"mise en service avec elle (reinflated) ; leur budgété, projeté sur l'année où la "
            f"référence les consommait, et leur montant aux taux de l'année de référence ne "
            f"changent pas (WF-DEV-0020). Redatée{_plural(redated)}, {_redated(redated, before)} "
            f"{'reste' if len(cast('list[Node]', redated['rescheduled'])) == 1 else 'restent'} "
            f"{_margin(redated, whole)} ; le montage et les récapitulatives "
            f"au-dessus des tâches redatées, entiers ; les totaux, dont le seul montant réestimé "
            f"change (WF-PLA-0010, WF-PLA-0020, WF-DEV-0040).",
            redated,
        ),
    }


def _volume_writes() -> dict[str, JsonObject]:
    applied = paste_applied()
    [_, _, third] = cast("list[Node]", applied["nodes"])
    line = third["estimate_line"]
    columns = node_columns()
    partial = paste_applied(UNKNOWN_CATEGORY)
    [first, last] = cast("list[Node]", partial["nodes"])
    rejudged_answer = paste_applied_rejudged()
    [rejudged_first, rejudged_last] = cast("list[Node]", rejudged_answer["nodes"])
    return {
        "estimate_line_entered.json": mocktext.example(
            f"La ligne {ROW} de la structure du témoin, « Heures d'ingénierie », première ligne "
            f"tirée après le cœur, dont le libellé "
            f"est saisi « {ENTERED} » : rien d'autre ne change, pas même ses montants ; une "
            f"version de plus. Avec elle, ses trois ancêtres, inchangés, les totaux de la "
            f"structure, et son compteur, passé à 3 après deux écritures. Le faux back la rend à "
            f"toute écriture d'une ligne, qui ne garde rien de ce qu'on lui envoie (WF-DEV-0020, "
            f"WF-IHM-0040).",
            estimate_line_entered(),
        ),
        "paste_plan.json": mocktext.example(
            f"Un bloc de trois lignes et quatre colonnes — libellé, catégorie, rôle, quantité — "
            f"collé sur le libellé de la ligne {ROW} de la structure du témoin : les trois lignes "
            f"seront écrites, aucune n'est refusée ; rien n'est encore écrit (WF-IHM-0050).",
            paste_plan(BLOCK, PASTES[0]),
        ),
        "paste_plan_unknown_category.json": mocktext.example(
            f"Le même bloc, dont la deuxième ligne porte une catégorie qu'aucune du référentiel "
            f"ne nomme, « {UNKNOWN_CATEGORY[1][1]} » : cette ligne est refusée, sa cellule nommée "
            f"par sa colonne, et les deux autres seraient écrites ; confirmé, le collage écrira "
            f"les deux autres et non celle-ci (paste_applied_partial), abandonné, il n'écrira "
            f"rien (WF-IHM-0050).",
            paste_plan(UNKNOWN_CATEGORY, PASTES[1]),
        ),
        "paste_too_wide.json": mocktext.example(
            f"Un bloc de {mocktext.count(line_width(columns) + 1)} colonnes collé sur le libellé "
            f"d'une ligne de devis, quand sa facette n'en a que "
            f"{mocktext.count(line_width(columns))} à partir de lui (NodeColumn) : le collage est "
            f"refusé, et rien n'est écrit (WF-IHM-0050).",
            paste_too_wide(),
        ),
        "paste_applied.json": mocktext.example(
            f"Le bloc de trois lignes et quatre colonnes appliqué sur les lignes {ROW} à {ROW + 2} "
            f"de la structure du témoin : leurs libellés « {BLOCK[0][0]} », « {BLOCK[1][0]} » et "
            f"« {BLOCK[2][0]} », la quantité de la troisième portée à {line['quantity']} et son "
            f"montant réestimé recalculé, {_money(line['reestimated_amount'])} — "
            f"{line['quantity']} fois {_money(line['unit_disbursement'])} —, le budgété inchangé, "
            f"{_money(line['budgeted_amount'])}, fixé par la référence ; une version de plus "
            f"chacune — la ligne {ROW}, écrite d'abord par la saisie de son libellé "
            f"(estimate_line_entered), passe à la version 3. Avec elles, leurs trois ancêtres, "
            f"dont le montant réestimé suit, les totaux de la structure, et le compteur de la "
            f"structure, passé à {ENTERED_VERSION + 1}, celui que la saisie laissait plus un. "
            f"Le faux back les "
            f"rend à tout collage confirmé, qui ne garde rien de ce qu'on lui envoie "
            f"(WF-IHM-0050, WF-DEV-0020).",
            applied,
        ),
        "paste_applied_partial.json": mocktext.example(
            f"Le même bloc, dont la deuxième ligne porte la catégorie inconnue « "
            f"{UNKNOWN_CATEGORY[1][1]} » (paste_plan_unknown_category), confirmé : un succès "
            f"partiel. Les deux lignes valides sont écrites en une seule opération sur les lignes "
            f"{first['row_number']} et {last['row_number']} de la structure du témoin, « "
            f"{UNKNOWN_CATEGORY[0][0]} » et « {UNKNOWN_CATEGORY[2][0]} », la quantité de la "
            f"seconde portée à {last['estimate_line']['quantity']} ; la ligne refusée n'est pas "
            f"écrite, la ligne {ROW + 1} reste ce qu'elle était, et son refus est redit tel que "
            f"l'aperçu l'a annoncé, sa cellule nommée par sa colonne (rejected). Avec elles, "
            f"leurs ancêtres, les totaux de la structure, et son compteur, passé à "
            f"{ENTERED_VERSION + 1} (WF-IHM-0050, WF-DEV-0020).",
            partial,
        ),
        "paste_applied_rejudged.json": mocktext.example(
            f"Variante contrefactuelle déclarée : un bloc de trois lignes collé sur la ligne "
            f"{ROW}, dont la deuxième passe sa ligne à la catégorie « {REJUDGED[0][1]} » que la "
            f"première garde ; l'aperçu les accepte toutes trois, comme paste_plan, puis la "
            f"catégorie est désactivée avant la confirmation. Le référentiel n'ayant pas de "
            f"compteur, la confirmation juge de nouveau les lignes acceptées : la deuxième, qui "
            f"changerait sa "
            f"catégorie pour la catégorie désactivée, est refusée par son motif, que l'aperçu ne "
            f"donnait pas, et n'est pas écrite ; la première, qui nomme la catégorie que sa ligne "
            f"porte déjà, ne la change pas et est écrite, la ligne signalée comme employant un "
            f"objet désactivé (uses_inactive_object). Un succès partiel, "
            f"lignes {rejudged_first['row_number']} et {rejudged_last['row_number']} écrites, "
            f"le compteur de la structure passé à {ENTERED_VERSION + 1} (WF-IHM-0050, "
            f"WF-REF-0010).",
            rejudged_answer,
        ),
        "paste_stale.json": mocktext.example(
            f"Le bloc de paste_plan confirmé quand une autre écriture a changé la structure depuis "
            f"l'aperçu : le plan, jugé sur la structure à la version {ENTERED_VERSION}, est "
            f"refusé quel que soit le compteur envoyé, et la version courante, "
            f"{ENTERED_VERSION + 1}, est nommée ; rien n'est écrit (WF-IHM-0050, WF-IHM-0110).",
            paste_stale(),
        ),
    }
