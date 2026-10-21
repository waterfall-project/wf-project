# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The gestures of the estimate made on the amendment 2, and their refusals (EP-15/US-0460, #1214).

The main structure of a project in progress no longer edits its estimate: its grid of estimate
offers no entry and no command of writing, while that of a differential offers them (Vérif of
WF-DEV-0050, ``structures``). The lines the grid of estimate creates and moves are so written on
the amendment 2, « reprise des essais », the differential not merged of the current revision
(``wftools.mockamendment``): a line created under the commissioning, one created under the
control station after a subordinate, a selection of two lines moved under another task. As every
write of the grids, each answer is the difference between two readings of the differential,
before and after the gesture (``wftools.mockwrites.written``), each node named by its identifier
in the differential (``mockamendment.own_id``) and marked against the main structure; never
written by hand.

Their refusals on the same differential: the body of a move that mixes a line and a task, the
line created under a task completed, and the line moved to it (WF-DEV-0050, WF-RAE-0030, #1184).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import mockamendment, mockcore, mocktext
from wftools.mockgestures import added, money_said, network_task, tasks_said
from wftools.mockids import universe
from wftools.mocktree import AT_END, LINE, TASK, placed
from wftools.mockwitness import EQUIPMENT, SUBPROJECT_CONTROL, SUBPROJECT_TESTS, Line, N, Task
from wftools.mockwrites import amended, totals_said, written

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from wftools.mockstructure import JsonObject

type Node = dict[str, Any]


def reading(roots: Iterable[Task] | None = None) -> JsonObject:
    """Return the whole differential read today, marked, as described or as a write leaves it."""
    rows = mockamendment.rows(roots)
    return {
        "items": cast("list[Any]", mockamendment.marked(roots)),
        "totals": mockcore.whole(rows)["totals"],
    }


def amendment_write(roots: Iterable[Task], writes: Sequence[int]) -> JsonObject:
    """Return what a write of the differential answers: the differential read, then as amended.

    The nodes written by their identifiers in the differential; the structure one version further
    than the counter `structures` lists (WF-IHM-0110).
    """
    version = cast("int", mockamendment.structure("amendment")["lock_version"]) + 1
    return written(
        reading(),
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
    }
