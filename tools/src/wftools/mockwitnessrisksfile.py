# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks and the amendments of the witness, written for the loader (US-2650/L1).

Two files beside the examples under ``fixtures/api/``, as ``witness_tasks.json`` is for the tasks
(``wftools.mockwitnesstasks``): the back reads them with models of its own and never imports
``wftools``; the chronology says when each is written (``wftools.mockchronology``).

``witness_risks.json``, ``{"risks": [...]}``: the three risks of PRJ-001 in the order of their
declaration (``mockwitnessrisks.REGISTER``). A risk is:

- ``risk_id``, ``label``, ``description``, ``mitigation_notes``: what its user entered;
- ``probability``: the one of its declaration, its first review;
- ``provision_task_lineage_id``: the task its provision line goes under, by its lineage;
  ``provision_cost_category_id``, ``provision_subproject_id``: what that line bears;
- ``provision_lineage_id``: the lineage of its provision line, the identifier the declaration gives
  it in the revision 101; ``provision_node_id``: the identifier of its copy in the revision 102;
- ``structures``: its own estimate in each revision, ``{"revision", "structure_id"}``;
- ``estimates``: what its own estimate holds in a revision where it is entered,
  ``{"revision", "read_in", "planning_start_on", "tasks", "lines"}``, the day its planning starts
  on, the day the risk was declared, and the tasks and the lines as
  ``witness_tasks.json`` and ``witness_lines.json`` write them; ``read_in`` tells that the examples
  read them in that revision, under the identifiers given, which another revision derives;
- ``grafted``: the nodes its occurrence grafts into the main structure, ``{"lineage_id",
  "node_id", "copy_lineage_id"}`` — the lineage of a node of its own estimate, then the identifier
  and the lineage of its copy, as the examples read them (``nodes_risk_occurred``) —, empty for a
  risk that does not occur.

``witness_structures.json``, ``{"main": [...], "amendments": [...]}``: the main structure of the
revisions 101 and 102, ``{"revision", "structure_id"}``, as ``structures_amendments`` and
``structures`` name them, and the two amendments of the revision 101. An amendment is
``structure_id``, ``label``, ``revision`` — the one it is opened in —, ``rows_of`` — the revision
whose tasks and lines ``witness_tasks.json`` and ``witness_lines.json`` give its content —,
``copies`` — its copy in each revision that takes it up, ``{"revision", "structure_id"}`` —, then
what it changes of them: ``tasks`` and ``lines`` it adds or changes, as those files write them,
``removed_lineage_ids`` the lineages it withdraws; and ``node_ids``, the nodes of it the examples
name, ``{"lineage_id", "node_id"}``. The amendment 1 holds the reference 101 entered whole, what
separates the offer from the reference: its merge produces the reference; the amendment 2, the
revision 102 with its trials of the wiring resumed (``mockamendment``).

No address and no label of a real project is here: the labels are the witness's, fictitious.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mocktext, mockwitnesslines
from wftools.mockids import universe
from wftools.mockreview import OWN_ESTIMATE_OFFSET, delivery_delay_estimate
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CONTROL_STATION,
    GENERATED,
    LINEAGE_OFFSET,
    REWORK_ESTIMATE,
    RISK_SCALE,
    RISKS_IDENTIFIED,
    SUBCONTRACTING,
    Line,
    N,
    Task,
    lineage_id,
    node_id,
)
from wftools.mockwitnessrisks import REGISTER, Risk
from wftools.mockwitnesstasks import task_entry

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from wftools.mockstructure import JsonObject, JsonValue

RISKS_NAME = "witness_risks.json"
STRUCTURES_NAME = "witness_structures.json"
"""The files the risks and the amendments are written to, under ``fixtures/api/``."""

REFERENCE, CURRENT = 101, 102
"""The numbers of the revisions of the witness the risks and the amendments are written in."""

OWN_STRUCTURES = {751: (214, 204), 752: (215, 205), 753: (216, 206)}
"""The own estimate of each risk in the reference 101 and in the revision 102, as ``structures``
and ``structures_amendments`` name them."""

PROVISION_TASKS = {751: N.WIRING, 752: N.CONTROL_STATION, 753: N.COMMISSIONING}
"""The task that bears the provision line of each risk (``risks``, ``REFERENCE_PROVISIONS``)."""

AMENDMENT_1, AMENDMENT_2 = universe(212), universe(213)
AMENDMENT_1_LABEL = "Avenant 1 — extension du poste"
"""The amendments of the revision 101, as ``structures_amendments`` names them."""

REWIRING_IDENTIFIED = Decimal("750.00") * RISK_SCALE
"""The rewiring of the cabinets, as the identification of 751 estimated it: the own estimate then
totals 1,000,000, the severity its first review retained, the 250,000 more its review of 2 February
brought coming with the rewiring (``mockwitnessrisks.REWORK``)."""

SUBSTITUTE = Task(
    575,
    "Mise en service par un automaticien de remplacement",
    days=10,
    lines=(
        Line(
            576,
            "Automaticien de remplacement",
            SUBCONTRACTING,
            unit=Decimal("12000.00") * RISK_SCALE,
        ),
    ),
)
"""The own estimate of 753, the unavailability of the automation engineer: a substitute hired for
the commissioning, 12,000,000 at the scale of the structure, its severity. No example reads it."""


def _estimates() -> dict[int, list[tuple[int, int, tuple[Task, ...]]]]:
    """Return the own estimate of each risk by revision entered: revision, read in, its tasks."""
    identified = tuple(
        replace(
            task,
            lines=tuple(
                replace(line, unit=REWIRING_IDENTIFIED) if line.number == N.REWIRING_LINE else line
                for line in task.lines
            ),
        )
        for task in REWORK_ESTIMATE
    )
    return {
        751: [(REFERENCE, CURRENT, identified), (CURRENT, CURRENT, REWORK_ESTIMATE)],
        752: [(REFERENCE, REFERENCE, delivery_delay_estimate())],
        753: [(REFERENCE, CURRENT, (SUBSTITUTE,))],
    }


def _rows(roots: Iterable[Task], day: date) -> list[mockcore.Row]:
    """Return an own estimate as read on a day, its planning starting the day it was declared."""
    return mockcore.core(tuple(roots), day, start=RISKS_IDENTIFIED.on)


def _entries(revision: int, rows: list[mockcore.Row]) -> tuple[list[JsonValue], list[JsonValue]]:
    """Return the tasks and the lines of a structure, as the files of the loader write them."""
    lineages = {
        cast("str", row.node["node_id"]): cast("str", row.node["lineage_id"])
        for row in rows
        if row.kind == mockcore.TASK
    }
    tasks: list[JsonValue] = [
        task_entry(revision, row, lineages) for row in rows if row.kind == mockcore.TASK
    ]
    lines: list[JsonValue] = [
        mockwitnesslines.line_entry(revision, row, lineages)
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    ]
    return tasks, lines


def _grafted(risk: Risk) -> list[JsonValue]:
    """Return the nodes the occurrence of a risk grafts, by the lineage of its own node."""
    if risk.merged is None:
        return []
    [merged] = [each for each in CONTROL_STATION.children if each.number == risk.merged]
    numbers: list[int] = []

    def walk(task: Task) -> None:
        numbers.append(task.number)
        numbers.extend(line.number for line in task.lines)
        for child in task.children:
            walk(child)

    walk(merged)
    return [
        {
            "lineage_id": lineage_id(number - OWN_ESTIMATE_OFFSET),
            "node_id": node_id(number),
            "copy_lineage_id": lineage_id(number),
        }
        for number in sorted(numbers)
    ]


def _risk(risk: Risk) -> JsonObject:
    """Return a risk of the register as the loader declares it."""
    line = risk.reference_provision_line
    if line is None:
        message = f"the risk {risk.number} bore no provision line in the reference"
        raise ValueError(message)
    reference, current = OWN_STRUCTURES[risk.number]
    estimates: list[JsonValue] = []
    for revision, read_in, roots in _estimates()[risk.number]:
        day = AMENDMENT_MERGED.on if revision == REFERENCE else mockcore.READ_ON
        tasks, lines = _entries(revision, _rows(roots, day))
        estimates.append(
            {
                "revision": revision,
                "read_in": read_in,
                "planning_start_on": RISKS_IDENTIFIED.on.isoformat(),
                "tasks": tasks,
                "lines": lines,
            }
        )
    return {
        "risk_id": universe(risk.number),
        "label": risk.label,
        "description": risk.description,
        "mitigation_notes": risk.mitigation_notes,
        "probability": str(risk.reviews[0].probability),
        "provision_task_lineage_id": lineage_id(PROVISION_TASKS[risk.number]),
        "provision_cost_category_id": risk.provision_category,
        "provision_subproject_id": risk.provision_subproject,
        "provision_lineage_id": universe(line + LINEAGE_OFFSET),
        "provision_node_id": universe(line),
        "structures": [
            {"revision": REFERENCE, "structure_id": universe(reference)},
            {"revision": CURRENT, "structure_id": universe(current)},
        ],
        "estimates": estimates,
        "grafted": _grafted(risk),
    }


def risks() -> JsonObject:
    """Return the risks of the witness, in the order of their declaration."""
    return {"risks": [_risk(risk) for risk in REGISTER]}


_LAID = ("start", "finish", "is_summary", "inscriptions", "order_item_id", "work_package_id")
"""What the loader does not take from a task of an amendment: its dates and whether it is a summary,
which the engine computes, and what a differential does not bear (WF-PLA-0170)."""


def _changed(before: list[JsonValue], after: list[JsonValue]) -> list[JsonValue]:
    """Return the entries of ``after`` that ``before`` does not hold as they are, by lineage."""

    def kept(entry: JsonValue) -> JsonObject:
        return {
            key: value
            for key, value in cast("JsonObject", entry).items()
            if key not in {*_LAID, "node_id"}
        }

    held = {cast("JsonObject", each)["lineage_id"]: kept(each) for each in before}
    return [
        each for each in after if held.get(cast("JsonObject", each)["lineage_id"]) != kept(each)
    ]


def _second() -> JsonObject:
    """Return the amendment 2: the revision 102, its trials of the wiring resumed."""
    main_tasks, main_lines = _entries(CURRENT, mockcore.current())
    tasks, lines = _entries(CURRENT, mockamendment.rows())
    held = {cast("str", cast("JsonObject", each)["lineage_id"]) for each in (*tasks, *lines)}
    removed = sorted(
        cast("str", cast("JsonObject", each)["lineage_id"])
        for each in (*main_tasks, *main_lines)
        if cast("JsonObject", each)["lineage_id"] not in held
    )
    named: list[JsonValue] = [
        {"lineage_id": lineage_id(row.number), "node_id": mockamendment.own_id(row.number)}
        for row in sorted(mockamendment.rows(), key=lambda row: lineage_id(row.number))
        if row.number < GENERATED
    ]
    return {
        "structure_id": AMENDMENT_2,
        "label": mockamendment.LABEL,
        "revision": REFERENCE,
        "rows_of": CURRENT,
        "copies": [{"revision": CURRENT, "structure_id": universe(203)}],
        "tasks": _changed(main_tasks, tasks),
        "lines": _changed(main_lines, lines),
        "removed_lineage_ids": cast("list[JsonValue]", removed),
        "node_ids": named,
    }


MAIN_STRUCTURES = {REFERENCE: 211, CURRENT: 201}
"""The main structure of the revisions 101 and 102, as the examples name them."""


def structures() -> JsonObject:
    """Return the main structures and the amendments of the witness, in the order of opening."""
    first: JsonObject = {
        "structure_id": AMENDMENT_1,
        "label": AMENDMENT_1_LABEL,
        "revision": REFERENCE,
        "rows_of": REFERENCE,
        "copies": [],
        "tasks": [],
        "lines": [],
        "removed_lineage_ids": [],
        "node_ids": [],
    }
    main: list[JsonValue] = [
        {"revision": revision, "structure_id": universe(number)}
        for revision, number in MAIN_STRUCTURES.items()
    ]
    return {"main": main, "amendments": [first, _second()]}


def examples() -> dict[str, JsonObject]:
    """Return the risks and the amendments of the witness, by file."""
    return {
        RISKS_NAME: mocktext.example(
            "Les risques du projet témoin, pour le chargeur : les trois risques de PRJ-001 dans "
            "l'ordre de leur déclaration, chacun avec son identité, la probabilité de sa "
            "déclaration, la tâche, la catégorie et le sous-projet de sa ligne de provision, la "
            "lignée de cette ligne et son identifiant dans la révision 102, son devis propre dans "
            "chaque révision et ce qu'il y porte, et les nœuds que sa survenance greffe "
            "(WF-RIS-0010, WF-RIS-0060, WF-QUA-0040-A). Lus par `waterfall-api load-witness` sans "
            "importer `wftools`.",
            risks(),
        ),
        STRUCTURES_NAME: mocktext.example(
            "Les structures du projet témoin, pour le chargeur : la principale des révisions 101 "
            "et 102, et ses avenants : l'avenant 1, qui porte la "
            "référence 101 saisie entière, ce qui sépare l'offre de la référence, et l'avenant 2, "
            "la révision "
            "102 dont les essais de câblage sont repris — la révision qu'il copie, ce qu'il en "
            "ajoute, change ou retire, et les identifiants de ses nœuds que les exemples nomment "
            "(WF-REV-0050, WF-REV-0100, WF-QUA-0040-A). Lus par `waterfall-api load-witness` sans "
            "importer `wftools`.",
            structures(),
        ),
    }
