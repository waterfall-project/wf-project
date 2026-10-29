# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a paste and an import refuse of a line held by its subproject, and of the estimate.

A line whose task is started or completed does not leave a subproject charged with actual costs,
a share of those costs being its own (WF-PRJ-0050, C-359): the line read does not name its
subproject among the fields it accepts (``mockstructure.line_fields``). Held is judged as the
entry of the line judges it, on the state of its task and the actual costs of its subproject; a
cell of a block pasted, or a line of a file imported, that would move it elsewhere is refused by
the code the entry of the line gives, `SUBPROJECT_HAS_ACTUAL_COSTS`, which names that
subproject (#1152). The import of the estimate is refused on the main structure of a project in
progress, the condition named as the main structure names it (WF-INTF-0100, C-358, #1153). Each
refusal is judged on the readings of the witness, as the server judges it, never written by hand.

And the first extraction of April as its analysis presented it, before it was applied: the lines
it added, and the line of another project it rejected for its element of the work breakdown
structure (WF-CRE-0020, US-0701/L7); and the export of a revision of another project, refused as an
unknown one (WF-ADM-0110). An import says the structure, the revision and the period its opening
received (``opened_on``, I-08).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mockcosts, mocktext
from wftools.mockhistory import stamp
from wftools.mockids import hex_identifier, universe
from wftools.mockstructure import charged_subprojects
from wftools.mockwitness import (
    SUBPROJECT_CONTROL,
    SUBPROJECT_TESTS,
    N,
    fixture,
)
from wftools.mockwitnesscosts import APRIL, CostLine

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wftools.mockstructure import JsonObject, JsonValue

type Node = dict[str, Any]


def read() -> dict[int, Node]:
    """Return the nodes of the structure of the witness read today, by their number."""
    return {row.number: row.node for row in mockcore.current()}


def task_of(nodes: dict[int, Node], line: Node) -> Node:
    """Return the task that bears a line, its parent among the nodes read."""
    [task] = [each for each in nodes.values() if each["node_id"] == line["parent_id"]]
    return task


def is_held(nodes: dict[int, Node], line: Node) -> bool:
    """Whether a line is held by its subproject, as the entry of the line judges it.

    Its task is started or completed, and its subproject received actual costs
    (`Subproject.has_actual_costs`, WF-PRJ-0050, #1066), as ``mockcore`` reads it to leave the
    subproject out of the fields the line accepts. A provision computes its subproject from its
    risk, refused by `COMPUTED_VALUE` instead (WF-RIS-0010): it is never held.
    """
    facet = line["estimate_line"]
    return (
        not facet["is_computed"]
        and task_of(nodes, line)["task"]["progress"] != "not_started"
        and facet["subproject_id"] in charged_subprojects()
    )


def held_refusal(
    nodes: dict[int, Node], line: Node, subproject: str | None, *, pasted: bool
) -> JsonObject | None:
    """Return the refusal of a subproject sent to a line, or None if the line takes it.

    A line held by its subproject refuses any other: it names the subproject it may not leave, by
    its identifier and its label, as `updateEstimateLine` does. Its own subproject sent again
    moves nothing, and is not refused. None sent differs: an empty cell pasted writes nothing
    (`PastePreview`), and is not refused; an empty cell of an estimate imported, like the tab
    « Hors sous-projet » of a remaining to commit, would leave the line out of any subproject,
    refused then (`ImportRejection`).
    """
    facet = line["estimate_line"]
    if pasted and subproject is None:
        return None
    if not is_held(nodes, line) or subproject == facet["subproject_id"]:
        return None
    return {
        "code": "SUBPROJECT_HAS_ACTUAL_COSTS",
        "params": {
            "subproject": {
                "subproject_id": facet["subproject_id"],
                "label": facet["subproject_label"],
            }
        },
    }


def subprojects() -> dict[str, str]:
    """Return the subprojects of the witness by their label, as a cell or a tab names them."""
    return {entry["label"]: entry["subproject_id"] for entry in fixture("subprojects")}


# --- A subproject pasted on a line held by its own ---------------------------------------------

PASTED_ON = N.LABOUR
"""The line the block is pasted on, the labour of the wiring of the cabinets, started."""

PASTED = (SUBPROJECT_TESTS, SUBPROJECT_CONTROL)
"""The subprojects of the block of one column, from the line pasted on: the tests and the
commissioning for the labour, the control station, its own, for the line below it."""

HELD_PASTE = universe(993)


def pasted_lines(nodes: dict[int, Node], count: int) -> list[Node]:
    """Return the lines of the structure a block of ``count`` rows writes, from PASTED_ON.

    Each row writes the node at the same distance below the node pasted on, in the order of the
    plan (`PastePreview`).
    """
    ordered = list(nodes.values())
    first = ordered.index(nodes[PASTED_ON])
    return ordered[first : first + count]


def paste_plan(block: Sequence[str | None]) -> JsonObject:
    """Return what previewPaste answers to a block of one column of subprojects, from PASTED_ON.

    A row whose subproject cell would move a held line elsewhere is refused, its column named and
    the subproject it may not leave with it; a row naming the line's own subproject moves nothing,
    and is accepted, as is an empty cell, None, which writes nothing (WF-IHM-0050, WF-PRJ-0050).
    """
    nodes = read()
    rejected: list[JsonValue] = []
    for row, (line, subproject) in enumerate(
        zip(pasted_lines(nodes, len(block)), block, strict=True)
    ):
        refusal = held_refusal(nodes, line, subproject, pasted=True)
        if refusal is not None:
            rejected.append({"row": row, "column": "subproject", **refusal})
    return {"paste_id": HELD_PASTE, "accepted": len(block) - len(rejected), "rejected": rejected}


def paste_plan_subproject_held() -> JsonObject:
    """Return what previewPaste answers to the block PASTED, on a line held by its own."""
    return paste_plan(PASTED)


# --- A remaining to commit imported, a line in the tab of another subproject -------------------

TAB = SUBPROJECT_TESTS
"""The tab of the file the two lines are placed in: the tests and the commissioning."""


def tab_name(subproject: str) -> str:
    """Return the name of the tab of a subproject, as the file names it: its code (ANNEXE B).

    The code of a subproject is bounded so that it names a tab (`DeclaredSubprojectCode`,
    WF-PRJ-0050; EP-16/US-0610); its label is not.
    """
    [name] = [
        entry["code"] for entry in fixture("subprojects") if entry["subproject_id"] == subproject
    ]
    return cast("str", name)


IMPORTED = (N.COMMISSIONING_LINE, N.LABOUR)
"""The lines of that tab, from its second row, the first being its headings: the commissioning
on site, of a task not started, and the labour of the wiring, started, both of the control
station, which received the invoice of the screens."""

FIRST_ROW = 2
"""The row of the first line of a tab, under its headings."""

HELD_IMPORT, HELD_IMPORT_TASK = hex_identifier(0xA17), universe(947)


def import_report(nodes: dict[int, Node]) -> JsonObject:
    """Return the report of the remaining to commit of IMPORTED placed in the tab of TAB.

    The subproject of a line is that of the tab that bears it (WF-INTF-0120): a line placed in the
    tab of another changes subproject, and the report presents it as a difference, unless the line
    is held by its own, rejected then, the report naming that subproject, and the line by its tab
    and its row (#1162). The quantities of the file are those of the revision: nothing else
    differs.
    """
    rejected: list[JsonValue] = []
    differences: list[JsonValue] = []
    for row, number in enumerate(IMPORTED, start=FIRST_ROW):
        line = nodes[number]
        refusal = held_refusal(nodes, line, TAB, pasted=False)
        if refusal is not None:
            rejected.append({"sheet": tab_name(TAB), "row": row, **refusal})
        elif line["estimate_line"]["subproject_id"] != TAB:
            differences.append(
                {
                    "change": "updated",
                    "target": "estimate_line",
                    "lineage_id": mockcore.lineage(number),
                    "label": line["estimate_line"]["label"],
                    "fields": ["subproject"],
                }
            )
    return {
        "format_version": "1",
        "read_count": len(IMPORTED),
        "unchanged_count": len(IMPORTED) - len(rejected) - len(differences),
        "rejected": rejected,
        "refusals": [],
        "differences": differences,
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [],
    }


SUBMITTED, ANALYSED, EXPIRES = (
    "2026-06-03T10:20:05Z",
    "2026-06-03T10:21:00Z",
    "2026-06-04T10:21:00Z",
)
"""When the import was opened today, analysed, and until when it applies (WF-ARC-0100)."""


def import_remaining_subproject_held() -> JsonObject:
    """Return what getImport answers of the remaining to commit of IMPORTED, analysed today."""
    return {
        "import_id": HELD_IMPORT,
        "kind": "remaining",
        "filename": "reste-a-engager-essais.xlsx",
        **opened_on(main_structure()),
        "status": "analysed",
        "created_at": SUBMITTED,
        "expires_at": EXPIRES,
        "report": import_report(read()),
        "task": {
            "task_id": HELD_IMPORT_TASK,
            "kind": "import_analysis",
            "status": "succeeded",
            "progress": 100,
            "submitted_at": SUBMITTED,
            "finished_at": ANALYSED,
            "problem": None,
            "result_url": None,
        },
    }


# --- The estimate imported on the main structure of a project in progress ----------------------

ESTIMATE_CORRELATION = universe(1175)


def main_structure() -> Node:
    """Return the main structure of the current revision of the witness, as it is listed."""
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    return cast("Node", main)


def opened_on(
    structure: Node | None, period: tuple[date | None, date | None] = (None, None)
) -> Node:
    """Return what an import says of its opening: its structure, its revision, its period.

    The structure the import writes on, and the current revision that bears it (WF-INTF-0090); an
    extraction of actual costs writes on neither, its lines being the project's, and says the
    period it extracted instead, each bound possibly missing (WF-CRE-0020, WF-CRE-0050).
    """
    start, end = period
    return {
        "structure_id": None if structure is None else structure["structure_id"],
        "revision_id": None if structure is None else structure["revision_id"],
        "period_from": None if start is None else start.isoformat(),
        "period_to": None if end is None else end.isoformat(),
    }


def import_estimate_main_in_progress() -> JsonObject:
    """Return what openImport answers to an estimate imported on the main structure, in progress.

    The estimate of the main structure is entered no more once the project is in progress, its
    grid read only (`StructureCommand.edit_estimate`): its import is refused, the condition named
    as the structure names it (WF-INTF-0100, C-358).
    """
    commands = main_structure()["available_commands"]
    [command] = [each for each in commands if each["command"] == "edit_estimate"]
    [condition] = cast("Sequence[str]", command["missing_conditions"])
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": condition},
        "correlation_id": ESTIMATE_CORRELATION,
    }


# --- The first extraction of April, analysed, and an export of another project ----------------

APRIL_IMPORT, APRIL_TASK = hex_identifier(APRIL.exchange), universe(944)
APRIL_SUBMITTED, APRIL_ANALYSED, APRIL_EXPIRES = (
    "2026-05-04T08:25:00Z",
    "2026-05-04T08:26:00Z",
    "2026-05-05T08:26:00Z",
)
"""When the extraction of April was opened, analysed, and until when it applied, as imports
lists it; it was applied at 8:30, the instant its journal says (``cost_imports``)."""

OUTSIDE_SUBPROJECT = "SP-CAB"
"""The code of subproject the element of the line of another project carries after the slash."""


def other_project() -> str:
    """Return the code of a project of the portfolio other than the witness, as homes lists it."""
    witness = fixture("project")["code"]
    return next(each["code"] for each in fixture("projects")["items"] if each["code"] != witness)


def april_added() -> list[CostLine]:
    """Return the lines the extraction of April created, in the order of their documents."""
    created = [line for line in mockcosts.lines() if line.imports[0] is APRIL]
    return sorted(created, key=lambda line: (line.document, line.item or ""))


def april_report() -> JsonObject:
    """Return the report of the extraction of April, as its analysis presented it.

    Each line whose document and item were not yet imported is added, named by its document and
    its item (WF-INTF-0140, D-4); each line of another project the journal counts is rejected, its
    element named as the file carries it, with the code of project read (WF-CRE-0020), last in the
    file. A code of subproject no subproject of the project carries is kept, and asks for an
    explicit confirmation, as the lines of another project do.
    """
    added = april_added()
    code = other_project()
    rejected: list[JsonValue] = [
        {
            "sheet": None,
            "row": FIRST_ROW + len(added) + offset,
            "code": "WBS_ELEMENT_OUTSIDE_PROJECT",
            "params": {"wbs_element": f"{code}/{OUTSIDE_SUBPROJECT}", "project_code": code},
        }
        for offset in range(APRIL.rejected)
    ]
    differences: list[JsonValue] = [
        {
            "change": "added",
            "target": "actual_cost_line",
            "lineage_id": None,
            "label": line.document,
            "document_item": line.item,
            "predecessor_label": None,
            "fields": [],
        }
        for line in added
    ]
    reasons: list[JsonValue] = ["lines_outside_project"] if rejected else []
    if unknown_codes(added):
        reasons.append("unknown_subproject")
    read = len(added) + len(rejected)
    return {
        "format_version": None,
        "read_count": read,
        "unchanged_count": read - len(rejected) - len(differences),
        "rejected": rejected,
        "refusals": [],
        "differences": differences,
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": reasons,
    }


def unknown_codes(added: Sequence[CostLine]) -> list[str]:
    """Return the codes of subproject of lines no subproject of the project carries, once each."""
    return sorted(
        {line.code for line in added if line.code is not None and mockcosts.imputed(line) is None}
    )


def import_actual_costs_first() -> JsonObject:
    """Return what getImport answered of the extraction of April, analysed on 4 May."""
    return {
        "import_id": APRIL_IMPORT,
        "kind": "actual_costs",
        "filename": "couts-reels-2026-04.xlsx",
        **opened_on(None, APRIL.period),
        "status": "analysed",
        "created_at": APRIL_SUBMITTED,
        "expires_at": APRIL_EXPIRES,
        "report": april_report(),
        "task": {
            "task_id": APRIL_TASK,
            "kind": "import_analysis",
            "status": "succeeded",
            "progress": 100,
            "submitted_at": APRIL_SUBMITTED,
            "finished_at": APRIL_ANALYSED,
            "problem": None,
            "result_url": None,
        },
    }


EXPORT_CORRELATION = universe(1579)


def export_revision_not_found() -> JsonObject:
    """Return what requestExport answers to a revision of another project (WF-ADM-0110)."""
    return {"code": "NOT_FOUND", "status": 404, "correlation_id": EXPORT_CORRELATION}


# --- The examples ------------------------------------------------------------------------------


def _subproject(refusal: JsonValue) -> str:
    return cast("dict[str, dict[str, dict[str, str]]]", refusal)["params"]["subproject"]["label"]


def _april_said() -> str:
    """Say what the analysis of the extraction of April presented, from its report."""
    report = cast("dict[str, Any]", april_report())
    added = april_added()
    named = ", ".join(
        line.document if line.item is None else f"{line.document} poste {line.item}"
        for line in added
    )
    [rejected] = report["rejected"]
    codes = unknown_codes(added)
    confirmed = "des lignes d'un autre projet"
    if codes:
        confirmed += (
            f", et le code de sous-projet {', '.join(codes)}, qu'aucun sous-projet du projet "
            "ne porte"
        )
    return (
        f"L'extraction d'avril, {mockcosts.period_said(APRIL)}, déposée le "
        f"{mocktext.day(date(2026, 5, 4))} à {mocktext.hour(APRIL_SUBMITTED)} et analysée à "
        f"{mocktext.hour(APRIL_ANALYSED)}, telle que son analyse la présenta, avant son "
        f"application à {mocktext.hour(stamp(APRIL.event.instant))} (imports, cost_imports) : "
        f"{report['read_count']} lignes lues ; {len(added)} lignes nouvelles ajoutées, chacune "
        f"désignée par sa pièce et son poste — {named} — ; à la ligne {rejected['row']}, "
        f"l'élément d'OTP « {rejected['params']['wbs_element']} », d'un autre projet, rejeté et "
        f"nommé avec le code projet lu, {rejected['params']['project_code']}, que le journal "
        f"compte parmi les lignes rejetées. L'application demande une confirmation explicite : "
        f"{confirmed} (WF-CRE-0020, WF-CRE-0050, WF-INTF-0140, WF-INTF-0080)."
    )


def examples() -> dict[str, JsonObject]:
    """Return the examples of the refusals of a paste and of an import, by file name."""
    nodes = read()
    labels = {label: key for key, label in subprojects().items()}
    lines = pasted_lines(nodes, len(PASTED))
    plan = paste_plan_subproject_held()
    [pasted_refusal] = cast("list[JsonValue]", plan["rejected"])
    imported = import_remaining_subproject_held()
    report = cast("dict[str, list[JsonValue]]", imported["report"])
    [moved] = cast("list[dict[str, str]]", report["differences"])
    [imported_refusal] = report["rejected"]
    rejected_at = cast("dict[str, Any]", imported_refusal)
    wiring = nodes[N.WIRING]["task"]
    started = mocktext.day(date.fromisoformat(wiring["started_on"]))
    refused = nodes[IMPORTED[1]]["estimate_line"]["label"]
    return {
        "paste_plan_subproject_held.json": mocktext.example(
            f"Un bloc d'une colonne, deux sous-projets, collé sur le sous-projet de la ligne "
            f"{lines[0]['row_number']} de la structure du témoin, « "
            f"{lines[0]['estimate_line']['label']} », du « {wiring['label']} », "
            f"démarré le {started} : la première cellule, « {labels[PASTED[0]]} », est refusée, "
            f"la ligne ne pouvant quitter le « {_subproject(pasted_refusal)} », qui a reçu des "
            f"coûts réels, et le refus le nomme ; la seconde, « {labels[PASTED[1]]} », sur la "
            f"ligne {lines[1]['row_number']}, « {lines[1]['estimate_line']['label']} », est son "
            f"propre sous-projet, qu'elle ne quitte pas : elle sera écrite ; rien n'est encore "
            f"écrit (WF-IHM-0050, WF-PRJ-0050).",
            plan,
        ),
        "import_remaining_subproject_held.json": mocktext.example(
            f"L'import d'un reste à engager lu aujourd'hui à {mocktext.hour(SUBMITTED)} et analysé "
            f"à {mocktext.hour(ANALYSED)}, une variante qu'imports ne reprend pas : deux lignes du "
            f"« {labels[SUBPROJECT_CONTROL]} "
            f"» placées dans l'onglet « {tab_name(TAB)} », nommé par le code du sous-projet « "
            f"{labels[TAB]} ». « {moved['label']} », d'une tâche non "
            f"démarrée, change de sous-projet, un écart au compte rendu ; « {refused} », du « "
            f"{wiring['label']} », démarré le {started}, est rejetée à la ligne "
            f"{rejected_at['row']} de l'onglet « {rejected_at['sheet']} », et le compte rendu "
            f"nomme le « {_subproject(imported_refusal)} », qui a reçu des coûts réels "
            f"(WF-INTF-0120, WF-PRJ-0050, WF-INTF-0080).",
            imported,
        ),
        "import_actual_costs_first.json": mocktext.example(
            _april_said(), import_actual_costs_first()
        ),
        "export_revision_not_found.json": mocktext.example(
            "L'export du devis demandé aujourd'hui sur le projet témoin, nommant une révision du "
            f"projet {other_project()} : refusé comme une révision inconnue, sans dire qu'elle "
            "existe ailleurs ; rien n'est mis en file (WF-ADM-0110, WF-INTF-0110).",
            export_revision_not_found(),
        ),
        "import_estimate_main_in_progress.json": mocktext.example(
            "L'import d'un devis demandé aujourd'hui sur la structure principale du projet "
            "témoin, En cours : refusé, la condition manquante nommée — un projet qui n'a pas "
            "atteint En cours —, comme la principale la nomme à la saisie de son devis "
            "(StructureCommand.edit_estimate) ; rien n'est analysé. Il reste ouvert sur un "
            "différentiel et sur le devis propre d'un risque (WF-INTF-0100).",
            import_estimate_main_in_progress(),
        ),
    }
