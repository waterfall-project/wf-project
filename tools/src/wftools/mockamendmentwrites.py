# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The gestures and the entries of the estimate made on the amendment 2, and their refusals.

The main structure of a project in progress no longer edits its estimate: its grid of estimate
offers no entry and no command of writing, while that of a differential offers them (Vérif of
WF-DEV-0050, ``structures``). The lines the grid of estimate creates and moves are so written on
the amendment 2, « reprise des essais », the differential not merged of the current revision
(``wftools.mockamendment``): a line created under the commissioning, one created under the
control station after a subordinate, a selection of two lines moved under another task
(EP-15/US-0460, #1214); and the cell and the block the journeys enter and paste on it, which the
fake back serves at the address of the differential: the hours of the line the amendment adds,
then a block of three rows pasted from it (#1277), and a block of two rows that skips the line the
amendment withdraws, without refusal (#1278). As every write of the grids, each answer is the
difference between two readings of the differential, before and after the gesture
(``wftools.mockwrites.written``), each node named by its identifier in the differential
(``mockamendment.own_id``) and marked against the main structure; never written by hand.

Their refusals on the same differential: the body of a move that mixes a line and a task, the
line created under a task completed, and the line moved to it (WF-DEV-0050, WF-RAE-0030, #1184);
and a line the move carried one version further, deleted at the counter read before it (#1210).
"""

from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import mockamendment, mockcore, mocktext
from wftools.mockgestures import added, money_said, network_task, tasks_said
from wftools.mockids import universe
from wftools.mocktree import AT_END, LINE, TASK, placed
from wftools.mockwitness import EQUIPMENT, SUBPROJECT_CONTROL, SUBPROJECT_TESTS, Line, N, Task
from wftools.mockwrites import amended, known, node_columns, totals_said, written

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from wftools.mockstructure import JsonObject, JsonValue

type Node = dict[str, Any]


def reading(roots: Iterable[Task] | None = None) -> JsonObject:
    """Return the whole differential read today, marked, as described or as a write leaves it."""
    rows = mockamendment.rows(roots)
    return {
        "items": cast("list[Any]", mockamendment.marked(roots)),
        "totals": mockcore.whole(rows)["totals"],
    }


def amendment_write(
    roots: Iterable[Task],
    writes: Sequence[int],
    *,
    following: tuple[Iterable[Task], Sequence[int]] | None = None,
) -> JsonObject:
    """Return what a write of the differential answers: the differential read, then as amended.

    The nodes written by their identifiers in the differential; the structure one version further
    than the counter `structures` lists (WF-IHM-0110). A write that follows another — the
    differential that one left, and the nodes it wrote — reads them one version further, and
    leaves the structure one version further still: two answers never render one node at one
    version with two contents (#421).
    """
    version = cast("int", mockamendment.structure("amendment")["lock_version"]) + 1
    before = reading()
    if following is not None:
        previous, numbers = following
        before = copy.deepcopy(reading(previous))
        ids = {mockamendment.own_id(number) for number in numbers}
        for node in cast("list[Node]", before["items"]):
            if node["node_id"] in ids:
                node["lock_version"] += 1
        version += 1
    return written(
        before,
        reading(roots),
        [mockamendment.own_id(number) for number in writes],
        structure_version=version,
    )


# --- The lines created and moved ---------------------------------------------------------------

CREATED_LINE, CREATED_SHARED = 583, 584
"""The lines the grid of estimate creates, of the numbers of the gestures (``mockgestures``)."""

TEST_SUPPLIES = Line(
    CREATED_LINE,
    "Consommables d'essais",
    EQUIPMENT,
    unit=Decimal("350.00"),
    subproject=SUBPROJECT_TESTS,
)
"""The line created under the commissioning: its quantities are the reference ones the amendment
bears, from which the merge draws its budget (WF-REV-0050), as the rework of the trials."""


def estimate_line_created() -> JsonObject:
    """Return what createNode answers to a line created under the commissioning."""
    roots = amended(mockamendment.amendment(), added(N.COMMISSIONING, line=TEST_SUPPLIES))
    return amendment_write(roots, [CREATED_LINE])


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
)
"""The line created under the control station, a summary that bears no line of its own: sent
after its last subordinate, it becomes its first child, before the wiring of the cabinets."""


def estimate_line_created_after_subtask() -> JsonObject:
    """Return what createNode answers to a line created under the station, after a subordinate.

    The witness renders the lines of a task before its subordinates (``mockcore``): the line
    added last among the lines of the station is at the place the contract gives a line that
    names a subordinate to follow (``NodeCreate``, #1187).
    """
    line = added(SHARED_UNDER, line=SHARED_TOOLING, after=SHARED_AFTER)
    return amendment_write(amended(mockamendment.amendment(), line), [CREATED_SHARED])


MOVED_FROM, MOVED_TO = "Conception 1.1.2", "Revue 1.1.3"
MOVED_LINES = ("Matériel", "Sous-traitance")
"""The selection moved: two lines of a task drawn about the core, neither of labour, to the task
after it in its lot — no calendar changes, no task is redated (WF-PLA-0010)."""


def moved_lines() -> tuple[tuple[Task, ...], list[int]]:
    """Return the differential the selection moved leaves, and the lines it moves.

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

    return amended(mockamendment.amendment(), move), numbers


def nodes_moved() -> JsonObject:
    """Return what moveNodes answers to a selection of two lines moved under another task."""
    roots, numbers = moved_lines()
    return amendment_write(roots, numbers)


STALE_CORRELATION = universe(1194)


def node_delete_stale() -> JsonObject:
    """Return what deleteNode answers to the first line moved deleted at a counter gone stale.

    Sent with the counter the grid of the amendment 2 read, while the move of the selection since
    (``nodes_moved``) carried the line one version further: the refusal names the counter that
    write left (#1210).
    """
    line = _moved_first()
    return {
        "code": "STALE_LOCK_VERSION",
        "status": 412,
        "params": {"expected_lock_version": line["lock_version"]},
        "correlation_id": STALE_CORRELATION,
    }


def _moved_first() -> Node:
    """Return the first line of the selection, as the move leaves it."""
    [line] = [
        node
        for node in cast("list[Node]", nodes_moved()["nodes"])
        if node["estimate_line"]["label"] == MOVED_LINES[0]
    ]
    return line


# --- The body of a mixed move and the refusals -------------------------------------------------

MIXED_UNDER, MIXED_AFTER = N.CONTROL_STATION, N.WIRING
MIXED = ((N.BLOCKS, LINE), (N.TRANSPORT, TASK))
"""A selection that mixes a line and a task — the blocks of the wiring of the cabinets and the
exceptional transport of the subtree the occurrence merged —, moved under the control station
after the wiring, its first subordinate: the line falls back on the boundary, the task follows the
wiring (#1187, #1188). A line moved changes its task."""


def mixed_places() -> tuple[list[int], list[int]]:
    """Return the lines and the subordinates of the station on the amendment 2, the mix placed."""
    under = [row for row in mockamendment.rows() if row.parent == MIXED_UNDER]
    lines = [row.number for row in under if row.kind == LINE]
    return placed(lines, [row.number for row in under if row.kind == TASK], MIXED, MIXED_AFTER)


def nodes_move_mixed() -> JsonObject:
    """Return the body of moveNodes for a line and a task, on the amendment 2, by its own ids."""
    return {
        "node_ids": [mockamendment.own_id(number) for number, _ in MIXED],
        "parent_id": mockamendment.own_id(MIXED_UNDER),
        "after_node_id": mockamendment.own_id(MIXED_AFTER),
        "lock_version": mockamendment.structure("amendment")["lock_version"],
    }


COMPLETED_UNDER = N.DETAILED_STUDIES
COMPLETED_MOVED = N.BLOCKS
COMPLETED_CORRELATION, MOVE_COMPLETED_CORRELATION = universe(1186), universe(1195)


def completed_refused(correlation: str) -> JsonObject:
    """Return the refusal of a line written under the detailed studies, completed (#1184).

    No line is created, modified, moved or deleted under a task completed, which is reopened from
    the Kanban first (WF-DEV-0050, WF-RAE-0030): the state of the task refuses it, by the condition
    a line under it misses.
    """
    rows = {row.number: row for row in mockamendment.rows()}
    if cast("dict[str, Any]", rows[COMPLETED_UNDER].node["task"])["progress"] != "completed":
        message = f"the task {COMPLETED_UNDER} is not completed"
        raise ValueError(message)
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "task_not_completed"},
        "correlation_id": correlation,
    }


def estimate_line_completed_refused() -> JsonObject:
    """Return what createNode answers to a line created under a task completed."""
    return completed_refused(COMPLETED_CORRELATION)


def nodes_move_completed_refused() -> JsonObject:
    """Return what moveNodes answers to the blocks moved under a task completed (#1214).

    « Le déplacement d'une ligne vers elle, est refusé » (Vérif of WF-DEV-0050): the blocks of the
    wiring, a task not completed, sent under the detailed studies.
    """
    rows = {row.number: row for row in mockamendment.rows()}
    bearer = rows[cast("int", rows[COMPLETED_MOVED].parent)]
    if cast("dict[str, Any]", bearer.node["task"])["progress"] == "completed":
        message = f"the line {COMPLETED_MOVED} is under a task completed"
        raise ValueError(message)
    return completed_refused(MOVE_COMPLETED_CORRELATION)


# --- The cell entered and the block pasted (#1277) ---------------------------------------------

ENTERED_LINE = N.TESTS_RESUMED_LINE
ENTERED_HOURS = Decimal(48)
"""The line the grid of estimate enters on the amendment, the assistance to the rework of the
trials it adds, and the hours entered: forty-eight instead of forty. On a differential its budget
follows its quantities, which the merge draws its budget from (WF-REV-0050)."""


def entered_roots() -> tuple[Task, ...]:
    """Return the differential the hours entered leave."""

    def entered(each: Line) -> Line:
        return replace(each, hours=ENTERED_HOURS) if each.number == ENTERED_LINE else each

    return amended(mockamendment.amendment(), line=entered)


def estimate_line_updated_amendment() -> JsonObject:
    """Return what updateEstimateLine answers to the hours of the line added by the amendment."""
    return amendment_write(entered_roots(), [ENTERED_LINE])


DELAYED_LINE = N.LABOUR
DELAYED_DAYS = 30
"""The labour line whose payment delay the grid of estimate enters on the amendment, the
connection of the terminal blocks, which no other write of the differential renders, and the
delay entered: a month, as the terminal blocks of the same task, instead of the nought labour has
by default (WF-DEV-0020, #785)."""


def estimate_line_payment_delay_amendment() -> JsonObject:
    """Return what updateEstimateLine answers to the payment delay of a labour line (#785).

    « Saisissable sur toute ligne autre qu'une ligne de provision » (WF-DEV-0020): the delay
    changes no amount and no date, only when the curve of cash out pays the line (WF-IND-0100).
    """

    def delayed(each: Line) -> Line:
        return (
            replace(each, payment_delay_days=DELAYED_DAYS) if each.number == DELAYED_LINE else each
        )

    return amendment_write(amended(mockamendment.amendment(), line=delayed), [DELAYED_LINE])


type Block = tuple[tuple[str, str, str, str], ...]
"""A block pasted: rows of four cells — label, category, role, quantity."""


AMENDMENT_BLOCK: Block = (
    (
        "Assistance à la reprise des essais de câblage",
        "Mise en service",
        "Technicien de mise en service",
        "2",
    ),
    ("Mise en service de l'installation", "", "", ""),
    (
        "Mise en service et réception sur site",
        "Mise en service",
        "Technicien de mise en service",
        "1",
    ),
)
"""A block of three rows and four columns — label, category, role, quantity —, pasted on the label
of the line ENTERED_LINE: each row writes the row of the grid at the same distance under it, in
the order of the plan of the reading of the installation (``nodes_amendment``), the commissioning
and its line. The commissioning is a task: its label is written, and its empty cells, which fall on
columns of a line, write nothing (`PastePreview`)."""

AMENDMENT_PASTE = universe(994)

SKIPPING_TARGET = N.WIRING_ON_SITE
SKIPPING_BLOCK: Block = (
    ("Câblage sur site", "Ingénierie électrique", "Ingénieur électricien", "2"),
    ("Essais et reprise sur site", "", "", ""),
)
"""A block of two rows pasted on the label of the wiring on site, the line before the one the
amendment withdraws, the assistance to the trials of wiring: the first row writes the wiring, two
engineers instead of one; the second skips the line withdrawn, read only at its row, and writes
the node after it, the trials on site the amendment adds, which takes its label (#1278)."""

SKIPPING_PASTE = universe(995)


def paste_targets(count: int = len(AMENDMENT_BLOCK), target: int = ENTERED_LINE) -> list[int]:
    """Return the nodes the rows of a block write, by their number, in the order of the plan.

    The ``count`` rows of the grid from the line ``target`` — those of the block pasted, the block
    of the example on ENTERED_LINE by default —, as the installation is read on the differential
    (``nodes_amendment``; #1296). A node withdrawn holds its row, read only: the paste skips it,
    without refusal, and the row of the block writes the next node that is not (#1278).
    """
    by_id = {mockamendment.own_id(row.number): row.number for row in mockamendment.rows()}
    ids = [
        cast("str", node["node_id"])
        for node in cast("list[Node]", mockamendment.nodes_amendment()["items"])
        if node["difference"] != "removed"
    ]
    start = ids.index(mockamendment.own_id(target))
    return [by_id[node_id] for node_id in ids[start : start + count]]


def paste_plan_amendment(
    block: Block = AMENDMENT_BLOCK, target: int = ENTERED_LINE, paste_id: str = AMENDMENT_PASTE
) -> JsonObject:
    """Return what previewPaste answers to a block on the amendment: each row judged by its node.

    The columns are those of a line from its label (`NodeColumn`). On a line, a category or a role
    the reference data does not name is refused, its row and its column named; on a task, a cell
    past its label that is not empty falls on a column the task does not accept, and is refused;
    an empty cell writes nothing (WF-IHM-0050). A node withdrawn is skipped, not refused (#1278).
    The block of the example by default.
    """
    columns = node_columns()
    line_columns = ["label", *columns[columns.index("cost_category") :]]
    categories, roles = known()
    kinds = {row.number: row.kind for row in mockamendment.rows()}
    refusals: list[tuple[int, str, str]] = []
    targets = paste_targets(len(block), target)
    for index, (number, cells) in enumerate(zip(targets, block, strict=True)):
        _, category, role, _ = cells
        if kinds[number] == TASK:
            refusals.extend(
                (index, line_columns[column], "FIELD_NOT_ACCEPTED")
                for column, cell in enumerate(cells)
                if column > 0 and cell
            )
        elif category not in categories:
            refusals.append((index, "cost_category", "UNKNOWN_COST_CATEGORY"))
        elif role and role not in roles:
            refusals.append((index, "resource_role", "UNKNOWN_RESOURCE_ROLE"))
    rejected: list[JsonValue] = [
        {"row": row, "column": column, "code": code} for row, column, code in refusals
    ]
    return {
        "paste_id": paste_id,
        "accepted": len(block) - len({row for row, _, _ in refusals}),
        "rejected": rejected,
    }


def paste_applied_amendment(block: Block = AMENDMENT_BLOCK) -> JsonObject:
    """Return what applyPaste answers to a block on the amendment, confirmed, refused in none.

    The paste follows the hours entered (``estimate_line_updated_amendment``): it reads the line
    at the version that write left, and leaves the structure one version further still (#421).
    Each line takes the label, the category, the role and the quantity of its row, the task its
    label; amounts follow, the budget with them on a differential (WF-REV-0050), and the summaries
    above, and the totals.
    """
    return _applied(block, ENTERED_LINE, entered_roots(), (entered_roots(), [ENTERED_LINE]))


def paste_plan_amendment_skipping() -> JsonObject:
    """Return what previewPaste answers to the block that skips the line the amendment withdraws."""
    return paste_plan_amendment(SKIPPING_BLOCK, SKIPPING_TARGET, SKIPPING_PASTE)


def paste_applied_amendment_skipping() -> JsonObject:
    """Return what applyPaste answers to the block that skips the line withdrawn, confirmed.

    A write of the differential read today: the wiring and the trials on site one version
    further, the structure one version further than `structures` lists (#421, #1278).
    """
    return _applied(SKIPPING_BLOCK, SKIPPING_TARGET, mockamendment.amendment(), None)


def _applied(
    block: Block,
    target: int,
    roots: tuple[Task, ...],
    following: tuple[Iterable[Task], Sequence[int]] | None,
) -> JsonObject:
    """Return what applyPaste answers to a block on the amendment from ``target``, on ``roots``."""
    if paste_plan_amendment(block, target)["rejected"]:
        message = "the block pasted on the amendment is refused in part"
        raise ValueError(message)
    categories, roles = known()
    targets = paste_targets(len(block), target)
    labels = dict(zip(targets, block, strict=True))

    def task(each: Task) -> Task:
        return replace(each, label=labels[each.number][0]) if each.number in labels else each

    def line(each: Line) -> Line:
        if each.number not in labels:
            return each
        label, category, role, quantity = labels[each.number]
        return replace(
            each,
            label=label,
            category=categories[category],
            role=roles.get(role),
            quantity=Decimal(quantity),
        )

    answer = amendment_write(amended(roots, task, line), targets, following=following)
    return {**answer, "rejected": []}


# --- The examples ------------------------------------------------------------------------------


def _nodes(answer: JsonObject) -> list[Node]:
    return cast("list[Node]", answer["nodes"])


def _parent(rows: dict[int, mockcore.Row], number: int) -> str:
    """Return the label of the task a node of the differential is under."""
    return rows[cast("int", rows[number].parent)].label


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the gestures of the estimate on the amendment 2."""
    rows = {row.number: row for row in mockamendment.rows()}
    amendment = mockamendment.structure("amendment")
    on = f"Sur l'« {amendment['label']} », différentiel non fusionné de la révision courante"
    open_ = f"{on}, dont le devis se saisit quel que soit l'état du projet (WF-DEV-0050)"
    line, shared, moved = (
        estimate_line_created(),
        estimate_line_created_after_subtask(),
        nodes_moved(),
    )
    [new_line] = _nodes(line)
    [shared_line] = _nodes(shared)
    supplies = cast("Node", new_line["estimate_line"])
    lines, tasks = mixed_places()
    (mixed_line, _), (mixed_task, _) = MIXED
    read = {cast("str", node["node_id"]): node for node in cast("list[Node]", reading()["items"])}
    stale_line = _moved_first()
    return {
        "estimate_line_created.json": mocktext.example(
            f"{open_}, la ligne « {TEST_SUPPLIES.label} » créée sous la "
            f"{rows[N.COMMISSIONING].label.lower()}, {money_said(supplies['base_amount'])} de "
            f"matériel au sous-projet « {supplies['subproject_label']} » : ses grandeurs sont "
            f"celles de référence que l'avenant porte, d'où la fusion tirera son budget "
            f"(WF-REV-0050) ; à sa première version (201), ajoutée à la structure principale "
            f"(difference). Avec elle, ses ancêtres, {tasks_said(line, 'ancestors')}, dont le "
            f"montant suit, {totals_said(line)}, et le compteur du différentiel passé à "
            f"{line['structure_lock_version']} (#1214).",
            line,
        ),
        "estimate_line_created_after_subtask.json": mocktext.example(
            f"{open_}, la ligne « {SHARED_TOOLING.label} » créée sous le "
            f"« {rows[SHARED_UNDER].label} », une récapitulative sans ligne propre, après sa "
            f"dernière subordonnée, la « {rows[SHARED_AFTER].label} » (after_node_id) : les "
            f"lignes d'une tâche précèdent toujours ses sous-tâches, et une ligne qui suit une "
            f"sous-tâche se place après la dernière ligne. Elle devient le premier enfant du "
            f"poste, au rang {shared_line['position']}, avant le « {rows[N.WIRING].label} » ; "
            f"{money_said(shared_line['estimate_line']['base_amount'])} de matériel, à sa "
            f"première version (201). Avec elle, ses ancêtres, {tasks_said(shared, 'ancestors')}, "
            f"dont le montant suit, et {totals_said(shared)} (#1187, #1214).",
            shared,
        ),
        "nodes_moved.json": mocktext.example(
            f"{open_}, une sélection de deux lignes, « {MOVED_LINES[0]} » et "
            f"« {MOVED_LINES[1]} » de « {MOVED_FROM} », déplacée en une écriture sous "
            f"« {MOVED_TO} », à sa fin : leur tâche porteuse change, une version de plus "
            f"chacune, modifiées par leur parent (changes) ; aucune n'est de main-d'œuvre, aucun "
            f"calendrier ne change. Avec elles, les anciens et les nouveaux ancêtres, "
            f"{tasks_said(moved, 'ancestors')}, dont les montants suivent, et "
            f"{totals_said(moved)}, inchangés (WF-PLA-0040, #1214).",
            moved,
        ),
        "node_delete_stale.json": mocktext.example(
            f"{on}, la ligne « {MOVED_LINES[0]} » supprimée avec le compteur que la grille avait "
            f"lu, {read[stale_line['node_id']]['lock_version']}, alors que le déplacement de la "
            f"sélection (nodes_moved) l'a porté à {stale_line['lock_version']} : la suppression "
            f"est refusée, le compteur courant rendu, et rien n'est supprimé ; la grille propose "
            f"de relire (WF-IHM-0110, #1210).",
            node_delete_stale(),
        ),
        "nodes_move_mixed.json": mocktext.example(
            f"{on}, une sélection qui mêle une ligne et une tâche, « {rows[mixed_line].label} » "
            f"du « {_parent(rows, mixed_line)} » et « {rows[mixed_task].label} », envoyée sous "
            f"le « {rows[MIXED_UNDER].label} » après le « {rows[MIXED_AFTER].label} », sa "
            f"première subordonnée (after_node_id). Chaque nœud suit la règle, dans l'ordre de "
            f"node_ids : les lignes d'une tâche précèdent ses sous-tâches, et la ligne, envoyée "
            f"après une sous-tâche, se place après la dernière ligne du poste, qui n'en porte "
            f"aucune — au rang {lines.index(mixed_line) + 1} — ; la tâche suit le "
            f"« {rows[MIXED_AFTER].label} », au rang {len(lines) + tasks.index(mixed_task) + 1} "
            f"(#1187, #1188).",
            nodes_move_mixed(),
        ),
        "estimate_line_completed_refused.json": mocktext.example(
            f"{on}, une ligne créée sous les « {rows[COMPLETED_UNDER].label} », terminées : "
            f"aucune ligne ne se crée sous une tâche terminée, qui se rouvre d'abord depuis le "
            f"Kanban. La création est refusée, la condition nommée ; rien n'est créé "
            f"(WF-DEV-0050, WF-RAE-0030, #1184).",
            estimate_line_completed_refused(),
        ),
        "nodes_move_completed_refused.json": mocktext.example(
            f"{on}, les « {rows[COMPLETED_MOVED].label} » du "
            f"« {_parent(rows, COMPLETED_MOVED)} » déplacés sous les "
            f"« {rows[COMPLETED_UNDER].label} », terminées : aucune ligne ne se déplace vers une "
            f"tâche terminée, qui se rouvre d'abord depuis le Kanban. Le déplacement est refusé, "
            f"la condition nommée ; rien ne bouge (WF-DEV-0050, WF-RAE-0030, #1214).",
            nodes_move_completed_refused(),
        ),
        **edit_examples(),
    }


def edit_examples() -> dict[str, JsonObject]:
    """Return the named examples of the cell entered and of the block pasted on the amendment 2.

    The fake back serves them at the address of the differential (``wftools.mock``, #1277).
    """
    rows = {row.number: row for row in mockamendment.rows()}
    on = (
        f"Sur l'« {mockamendment.structure('amendment')['label']} », différentiel non fusionné "
        f"de la révision courante, dont le devis se saisit quel que soit l'état du projet "
        f"(WF-DEV-0050)"
    )
    updated, plan, applied = (
        estimate_line_updated_amendment(),
        paste_plan_amendment(),
        paste_applied_amendment(),
    )
    [line] = _nodes(updated)
    facet = cast("Node", line["estimate_line"])
    before = rows[ENTERED_LINE]
    [first, task, last] = AMENDMENT_BLOCK
    written = {cast("str", node["node_id"]): node for node in _nodes(applied)}
    pasted = cast("Node", written[mockamendment.own_id(ENTERED_LINE)]["estimate_line"])
    commissioning = rows[paste_targets()[1]]
    return {
        "estimate_line_updated_amendment.json": mocktext.example(
            f"{on}, la ligne de main-d'œuvre « {before.label} », que l'avenant ajoute, dont la "
            f"charge passe de {cast('JsonObject', before.node['estimate_line'])['hours']} à "
            f"{ENTERED_HOURS} h : son montant recalculé depuis ses grandeurs, "
            f"{money_said(facet['base_amount'])}, et son budgété avec lui, "
            f"{money_said(facet['budgeted_amount'])} — sur un différentiel, les grandeurs sont "
            f"celles de référence, d'où la fusion tirera le budget (WF-REV-0050) — ; une version "
            f"de plus. Avec elle, ses ancêtres, {tasks_said(updated, 'ancestors')}, dont le "
            f"montant suit, {totals_said(updated)}, et le compteur du différentiel passé à "
            f"{updated['structure_lock_version']} ; aucune date ne bouge (WF-DEV-0020, "
            f"WF-DEV-0030, #1277).",
            updated,
        ),
        "paste_plan_amendment.json": mocktext.example(
            f"{on}, un bloc de trois lignes et quatre colonnes — libellé, catégorie, rôle, "
            f"quantité — collé sur le libellé de « {before.label} » : chaque ligne du bloc écrit "
            f"la ligne de la grille à la même distance sous elle, la tâche "
            f"« {commissioning.label} » puis sa ligne ; la tâche ne prend que son libellé, ses "
            f"trois cellules vides n'écrivant rien. Les {plan['accepted']} lignes seront écrites, "
            f"aucune n'est refusée ; rien n'est encore écrit (WF-IHM-0050, #1277).",
            plan,
        ),
        "paste_applied_amendment.json": mocktext.example(
            f"{on}, le bloc de trois lignes et quatre colonnes appliqué "
            f"(paste_plan_amendment) : « {first[0]} », dont la quantité passe à "
            f"{pasted['quantity']} et le montant à {money_said(pasted['base_amount'])}, à la "
            f"version {written[mockamendment.own_id(ENTERED_LINE)]['lock_version']} — la saisie "
            f"de sa charge (estimate_line_updated_amendment) l'avait écrite d'abord — ; la tâche "
            f"renommée « {task[0]} » et sa ligne « {last[0]} », une version de plus chacune. Avec "
            f"elles, leurs ancêtres, {tasks_said(applied, 'ancestors')}, dont le montant suit, "
            f"{totals_said(applied)}, et le compteur du différentiel passé à "
            f"{applied['structure_lock_version']}, celui que la saisie laissait plus un ; aucune "
            f"ligne refusée (WF-IHM-0050, WF-REV-0050, #1277).",
            applied,
        ),
        "estimate_line_payment_delay_amendment.json": _delay_example(on),
        **skipping_examples(),
    }


def _delay_example(on: str) -> JsonObject:
    """Return the example of the payment delay entered on a labour line of the amendment."""
    delayed = estimate_line_payment_delay_amendment()
    [line] = _nodes(delayed)
    facet = cast("Node", line["estimate_line"])
    before = cast("Node", {row.number: row for row in mockamendment.rows()}[DELAYED_LINE].node)
    return mocktext.example(
        f"{on}, le délai de paiement de la ligne de main-d'œuvre « {facet['label']} » saisi à "
        f"{facet['payment_delay_days']} jours au lieu de "
        f"{cast('Node', before['estimate_line'])['payment_delay_days']}, celui de la "
        f"main-d'œuvre par défaut : le délai se saisit sur toute ligne autre qu'une ligne de "
        f"provision, et la ligne le nomme parmi ses champs saisissables (editable_fields). Une "
        f"version de plus ; aucun montant ne change, ni aucune date : seule la courbe des "
        f"décaissements paie la ligne un mois plus tard. Avec elle, ses ancêtres, "
        f"{tasks_said(delayed, 'ancestors')}, {totals_said(delayed)}, et le compteur du "
        f"différentiel passé à {delayed['structure_lock_version']} (WF-DEV-0020, WF-IND-0100, "
        f"#785).",
        delayed,
    )


def skipping_examples() -> dict[str, JsonObject]:
    """Return the named examples of the block that skips the line the amendment withdraws (#1278).

    Named examples beside the ``amendment`` ones, which the fake back serves first at the address
    of the differential (``wftools.mock``).
    """
    rows = {row.number: row for row in mockamendment.rows()}
    [removed_label] = [
        cast("str", node[node["kind"]]["label"])
        for node in cast("list[Node]", mockamendment.nodes_amendment()["items"])
        if node["difference"] == "removed"
    ]
    on = (
        f"Sur l'« {mockamendment.structure('amendment')['label']} », différentiel non fusionné "
        f"de la révision courante, dont le devis se saisit quel que soit l'état du projet "
        f"(WF-DEV-0050)"
    )
    plan, applied = paste_plan_amendment_skipping(), paste_applied_amendment_skipping()
    wiring, trials = paste_targets(len(SKIPPING_BLOCK), SKIPPING_TARGET)
    written = {cast("str", node["node_id"]): node for node in _nodes(applied)}
    pasted = cast("Node", written[mockamendment.own_id(wiring)]["estimate_line"])
    block = (
        f"un bloc de deux lignes et quatre colonnes — libellé, catégorie, rôle, quantité — collé "
        f"sur le libellé de « {rows[wiring].label} », la ligne qui précède « {removed_label} », "
        f"que l'avenant retire et que la grille montre à sa place, en lecture seule"
    )
    return {
        "paste_plan_amendment_skipping.json": mocktext.example(
            f"{on}, {block} : la première ligne du bloc écrit « {rows[wiring].label} » ; la "
            f"seconde saute la ligne retirée, sans refus, et écrit le nœud suivant, la tâche "
            f"« {rows[trials].label} » que l'avenant ajoute, qui ne prend que son libellé, ses "
            f"trois cellules vides n'écrivant rien. Les {plan['accepted']} lignes seront "
            f"écrites, aucune n'est refusée ; rien n'est encore écrit (WF-IHM-0050, #1278).",
            plan,
        ),
        "paste_applied_amendment_skipping.json": mocktext.example(
            f"{on}, le bloc qui saute la ligne retirée appliqué "
            f"(paste_plan_amendment_skipping) : « {rows[wiring].label} », dont la quantité "
            f"passe à {pasted['quantity']} et le montant à {money_said(pasted['base_amount'])}, "
            f"et la tâche « {rows[trials].label} » renommée « {SKIPPING_BLOCK[1][0]} », une "
            f"version de plus chacune ; « {removed_label} », retirée, n'est pas écrite. Avec "
            f"elles, leurs ancêtres, {tasks_said(applied, 'ancestors')}, dont le montant suit, "
            f"{totals_said(applied)}, et le compteur du différentiel passé à "
            f"{applied['structure_lock_version']} ; aucune ligne refusée (WF-IHM-0050, "
            f"WF-REV-0050, #1278).",
            applied,
        ),
    }
