# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste that creates the tasks past the last row, and the undo and the redo (US-1450/L4).

A block pasted on the grid of planning writes the nodes below the cell aimed at; its rows that
fall past the last node of the structure create tasks, siblings of that last node, the anchor —
same parent, ranked after it in the order of the block —, each with its label, which a row without
one is refused for (`PastePreview`, decision of the user of 2026-11-08, #2559). The plan says how
many rows create (`PastePlan.created`); the confirmation renders the tasks created among the nodes
it writes. The fake back creates tasks alone: a line of the estimate created by a paste is EP-07's.

The undo of an entry, and its redo, answer what a write answers (`UndoResult`, WF-IHM-0110): here,
the renaming of the wiring of the cabinets (``mockwrites.task_renamed``) undone, then redone, each
one version further, so that no two answers render the wiring at one version with two contents
(#421, #2564).

Each answer is, as every write of the grids, the difference between two readings of one structure
(``mockwrites.written``), never written by hand. ``mockwrites.writes`` calls this module, and this
module reads ``mockwrites`` by its attributes, at a call, never at its import: the two import each
other.
"""

import copy
from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mocktext, mockwrites
from wftools.mockids import universe
from wftools.mockstructure import JsonObject, JsonValue, described
from wftools.mockwitness import CORE, WIRING, Task

if TYPE_CHECKING:
    from collections.abc import Sequence

type Node = dict[str, Any]


# --- The paste that creates --------------------------------------------------------------------

CREATING_BLOCK = (
    ("Fin du lot 9.3", "Procès-verbal de réception signé"),
    ("Levée des réserves du lot 9.3", "Réserves du procès-verbal levées"),
    ("Dossier des ouvrages exécutés du lot 9.3", "Plans et notes de calcul mis à jour"),
    ("", "Archivage du dossier"),
)
"""A block of four rows and two columns — label, description —, pasted on the label of the last
node of the structure of a thousand tasks, the milestone « Fin du lot 9.3 »: its first row writes
the milestone, the next two create two tasks after it, and the last, without a label, is refused."""

CREATING_PASTE = universe(993)


def anchor() -> mockcore.Row:
    """Return the last node of the structure of a thousand tasks, the one the block is pasted on."""
    return mockcore.current()[-1]


def created_numbers(block: Sequence[Sequence[str]] = CREATING_BLOCK) -> list[int]:
    """Return the numbers of the tasks the rows past the anchor create, those with a label.

    Numbered after the last node, in the order of the block, as the generated nodes are.
    """
    labelled = [cells for cells in block[1:] if cells[0]]
    return [anchor().number + rank for rank in range(1, len(labelled) + 1)]


def creating_refusals(block: Sequence[Sequence[str]] = CREATING_BLOCK) -> list[JsonValue]:
    """Return the refusals of a block pasted on the anchor: a row past it without a label.

    Its label is required, the block starting at the `label` column: `VALIDATION_FAILED`, the
    column named (`PastePreview`, #2559).
    """
    return [
        {"row": row, "column": "label", "code": "VALIDATION_FAILED"}
        for row, cells in enumerate(block)
        if row > 0 and not cells[0]
    ]


def paste_plan_creating() -> JsonObject:
    """Return what previewPaste answers to the block pasted on the last node of the structure."""
    rejected = creating_refusals()
    return mocktext.paste_plan_of(
        CREATING_PASTE,
        len(CREATING_BLOCK) - len(rejected),
        rejected,
        created=len(created_numbers()),
    )


CREATING_LINES_BLOCK = (
    ("Borniers à vis", "Matériel électrique"),
    ("Goulottes", "Matériel électrique"),
    ("Repères de câbles", "Matériel électrique"),
    ("", "Matériel électrique"),
    ("Essais de mise en service", "Essais"),
)
"""A block of five rows and two columns — label, category —, pasted on the label of a line of the
estimate that would be the last node of the structure: its first row writes the line, the next two
create two lines after it, the fourth, without a label, and the fifth, whose category the reference
does not know, are refused (`PastePreview`, US-1560, #2559, #2624)."""

CREATING_LINES_PASTE = universe(998)


def creating_lines_refusals() -> list[JsonValue]:
    """Return the refusals of the block of lines, each by its column.

    A row past the last node without a label, a row whose category no object of the reference
    bears (`UNKNOWN_COST_CATEGORY`).
    """
    return [
        {"row": 3, "column": "label", "code": "VALIDATION_FAILED"},
        {"row": 4, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"},
    ]


def paste_plan_creating_lines() -> JsonObject:
    """Return what previewPaste answers to the block of lines pasted on the last line."""
    rejected = creating_lines_refusals()
    return mocktext.paste_plan_of(
        CREATING_LINES_PASTE, len(CREATING_LINES_BLOCK) - len(rejected), rejected, created=2
    )


def creating_roots() -> tuple[Task, ...]:
    """Return the structure the block leaves: the anchor described, its new siblings after it.

    Each task created is a leaf in automatic mode, of one day, without a predecessor, as a
    creation gives it (`createNode`, WF-DEV-0050), not started, with the description of its row.
    """
    last = anchor()
    rows = [cells for cells in CREATING_BLOCK[1:] if cells[0]]
    siblings = tuple(
        Task(number, label, days=1, progress="not_started", description=description)
        for number, (label, description) in zip(created_numbers(), rows, strict=True)
    )

    def append(each: Task) -> Task:
        if each.number != last.parent:
            return each
        return replace(each, children=(*each.children, *siblings))

    written = mockwrites.on_task(last.number, description=CREATING_BLOCK[0][1])
    return mockwrites.amended(described(), lambda each: append(written(each)))


def paste_applied_creating() -> JsonObject:
    """Return what applyPaste answers to the block confirmed: the anchor written, two tasks created.

    The tasks created are among the nodes written, at their first version, in the order of the
    plan (`PasteApplied`, #2559); the row refused is said again, nothing created for it.
    """
    applied = mockwrites.volume_write(creating_roots(), [anchor().number, *created_numbers()])
    return {**applied, "rejected": creating_refusals()}


# --- The undo and the redo ---------------------------------------------------------------------


def _bumped(reading: JsonObject, number: int, by: int) -> JsonObject:
    """Return a reading with the node of a number some versions further, as writes left it."""
    bumped = copy.deepcopy(reading)
    for node in cast("list[Node]", bumped["items"]):
        if node["node_id"] == universe(number):
            node["lock_version"] += by
    return bumped


def _renamed() -> JsonObject:
    """Return the reading of the structure once the wiring is renamed (``task_renamed``)."""
    roots = mockwrites.amended(CORE, mockwrites.on_task(WIRING, label=mockwrites.RENAMED))
    return mockcore.whole(mockcore.current(described(roots)))


def undo_task_renamed() -> JsonObject:
    """Return what undoLastChange answers once the wiring is renamed: its label given back.

    The undo is a write like any other (WF-IHM-0110): the wiring one version further than the
    renaming left it, the structure too; nothing remains to undo.
    """
    before = _bumped(_renamed(), WIRING, 1)
    after = mockcore.whole(mockcore.current())
    return _undone(mockwrites.written(before, after, [universe(WIRING)], structure_version=3))


def redo_task_renamed() -> JsonObject:
    """Return what redoLastUndo answers once the renaming is undone: the wiring renamed again.

    One version further than the undo left it; nothing remains to redo.
    """
    before = _bumped(mockcore.whole(mockcore.current()), WIRING, 2)
    return _undone(mockwrites.written(before, _renamed(), [universe(WIRING)], structure_version=4))


def _undone(written: JsonObject) -> JsonObject:
    """Return an undo or a redo of a cell of the wiring, what it wrote, nothing left after it."""
    return {
        "undone": {"kind": "cell", "node_ids": [universe(WIRING)], "risk_ids": []},
        "written": written,
        "remaining_depth": 0,
    }


# --- The examples ------------------------------------------------------------------------------


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the paste that creates, and of the undo and the redo."""
    last = anchor()
    applied = paste_applied_creating()
    _, *created = cast("list[Node]", applied["nodes"])
    starts = date.fromisoformat(created[0]["task"]["start"]["date"])
    above = [f"« {node['task']['label']} »" for node in cast("list[Node]", applied["ancestors"])]
    wiring = next(row.label for row in mockcore.current() if row.number == WIRING)
    renamed = mockwrites.RENAMED
    undone, redone = undo_task_renamed(), redo_task_renamed()
    undone_written = cast("Node", undone["written"])
    redone_written = cast("Node", redone["written"])
    [undone_node], [redone_node] = undone_written["nodes"], redone_written["nodes"]
    return {
        "paste_plan_creating.json": mocktext.example(
            f"Un bloc de quatre lignes et deux colonnes — libellé, description — collé sur le "
            f"libellé du jalon « {last.label} », dernier nœud de la structure du témoin, ligne "
            f"{last.node['row_number']} : la première ligne écrira le jalon, les deux suivantes, "
            f"au-delà du dernier nœud, créeront deux tâches sœurs du jalon, à sa suite (created), "
            f"comptées aussi parmi les lignes acceptées ; la dernière, sans libellé, est refusée "
            f"sur sa colonne label, et rien ne sera créé pour elle ; rien n'est encore écrit "
            f"(WF-IHM-0050).",
            paste_plan_creating(),
        ),
        "paste_plan_creating_lines.json": mocktext.example(
            "Variante contrefactuelle déclarée : un bloc de cinq lignes et deux colonnes — "
            "libellé, catégorie — collé sur le libellé de la dernière ligne de devis d'une "
            "structure dont elle serait le dernier nœud (celle du témoin se termine par le jalon "
            f"« {last.label} », aucune de ses données ne le produit) : la première ligne écrira "
            "cette ligne, les deux suivantes, au-delà du dernier nœud, créeront deux lignes de "
            "devis sœurs de la dernière, à sa suite, sous la même tâche (created), comptées aussi "
            "parmi les lignes acceptées ; la quatrième, sans libellé, est refusée sur sa colonne "
            "label, la cinquième, dont la catégorie « Essais » n'est celle d'aucun objet du "
            "référentiel, sur sa colonne cost_category, et rien ne sera créé pour elles ; rien "
            "n'est encore écrit (WF-IHM-0050, WF-DEV-0050).",
            paste_plan_creating_lines(),
        ),
        "paste_applied_creating.json": mocktext.example(
            f"Le bloc de paste_plan_creating confirmé : le jalon « {last.label} » reçoit la "
            f"description de sa ligne, une version de plus, et les deux tâches créées, "
            f"{mocktext.listed([f'« {node["task"]["label"]} »' for node in created])}, lignes "
            f"{created[0]['row_number']} et {created[-1]['row_number']}, sont rendues parmi les "
            f"nœuds écrits, à leur première version : des feuilles en mode automatique d'un jour, "
            f"sans prédécesseur, non démarrées, sœurs du jalon sous la même récapitulative, qui "
            f"commencent à la date de début de planning, le {mocktext.day(starts)}. Avec elles, "
            f"leurs ancêtres, {mocktext.listed(above)}, qui commencent avec elles, "
            f"{mockwrites.totals_said(applied)}, et le compteur de la structure, passé à "
            f"{applied['structure_lock_version']} ; la ligne sans libellé est redite refusée, et "
            f"rien n'est créé pour elle (WF-IHM-0050, WF-DEV-0050).",
            applied,
        ),
        "undo_task_renamed.json": mocktext.example(
            f"La dernière modification de l'appelant sur la révision annulée, le renommage de la "
            f"tâche « {wiring} » en « {renamed} » (task_renamed) : la tâche reprend son libellé, "
            f"à la version {undone_node['lock_version']}, une de plus que le renommage ; une "
            f"annulation est une écriture comme une autre, rendue comme elle, et le compteur de "
            f"la structure passe à {undone_written['structure_lock_version']}. Plus rien à "
            f"annuler (WF-IHM-0110).",
            undone,
        ),
        "redo_task_renamed.json": mocktext.example(
            f"L'annulation précédente rétablie (undo_task_renamed) : la tâche « {wiring} » "
            f"renommée de nouveau « {renamed} », à la version {redone_node['lock_version']}, et "
            f"le compteur de la structure passé à {redone_written['structure_lock_version']}. "
            f"Plus rien à rétablir (WF-IHM-0110).",
            redone,
        ),
    }
