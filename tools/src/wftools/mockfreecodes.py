# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the WBS element compared whole and of the free subproject code (US-3270/L1).

The specification 1.0.7 compares the WBS element of an actual cost line whole with the code of the
project and those of its subprojects, and frees the code of a subproject, which is never that of
its project (WF-CRE-0020, WF-PRJ-0050; #3966, `docs/api/DECISIONS.md`, « L'élément d'OTP comparé
en entier et le code de sous-projet libre »). The contract precedes the service (US-3270/L2):

- ``import_actual_costs_unknown_elements.json``, the Vérif of WF-CRE-0020-A as an analysed
  extraction, a counterfactual variant of ``import_actual_costs_dotted_code``: on the project of
  code A.ABC.26001, which bears the subproject of code A.ABC.26001/10001, the lines of the two
  codes added, those of the other elements rejected, each element named with its lines;
- ``subproject_code_of_project.json``, a subproject of the witness created or recoded under the
  code of the witness: refused on ``/code``, without a parameter;
- ``project_code_of_subproject.json``, the witness recoded under the code of one of its
  subprojects: refused likewise.

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from typing import TYPE_CHECKING, Any, cast

from wftools import mocktext
from wftools.mockcorrelations import correlation
from wftools.mockexchanges import FIRST_ROW, import_commands
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

type Entry = dict[str, Any]

SUBPROJECT_OF_PROJECT = "subproject_code_of_project"
PROJECT_OF_SUBPROJECT = "project_code_of_subproject"
"""The names of the examples of a refusal, from which their correlation is derived (#1007)."""

PROJECT_CODE = "A.ABC.26001"
SUBPROJECT_CODE = "A.ABC.26001/10001"
"""The codes of the Vérif of WF-CRE-0020-A: the project, and the subproject it bears."""

LINES: tuple[tuple[str, str, str], ...] = (
    (PROJECT_CODE, "FA-2026-0409", "10"),
    (SUBPROJECT_CODE, "FA-2026-0412", "10"),
    ("A.ABC.26001/10002", "FA-2026-0415", "10"),
    ("A.ABC.26001/10002", "FA-2026-0415", "20"),
    ("10001", "FA-2026-0417", "10"),
    ("A.ABC.26002", "FA-2026-0418", "10"),
    ("", "FA-2026-0421", "10"),
)
"""The lines of the file, in its order, each by its WBS element, its document and its item: the
elements of the Vérif, the subproject not declared on two lines, so that the report counts them."""

KNOWN = (PROJECT_CODE, SUBPROJECT_CODE)
"""The elements the project knows: its code, and that of its subproject."""


def unknown_elements(lines: tuple[tuple[str, str, str], ...]) -> list[JsonValue]:
    """Return each element of the lines that is no known code, once, with the number of its lines.

    In the order in which the file first carries it (``ImportReport.unknown_wbs_elements``).
    """
    counted: dict[str, int] = {}
    for element, _document, _item in lines:
        if element not in KNOWN:
            counted[element] = counted.get(element, 0) + 1
    return [{"wbs_element": element, "line_count": count} for element, count in counted.items()]


def unknown_elements_report() -> JsonObject:
    """Return the report of the extraction of the Vérif, as its analysis presents it."""
    added: list[JsonValue] = [
        {
            "change": "added",
            "target": "actual_cost_line",
            "lineage_id": None,
            "label": document,
            "document_item": item,
            "predecessor_label": None,
            "fields": [],
        }
        for element, document, item in LINES
        if element in KNOWN
    ]
    rejected: list[JsonValue] = [
        {
            "sheet": None,
            "row": FIRST_ROW + rank,
            "code": "WBS_ELEMENT_OUTSIDE_PROJECT",
            "params": {"wbs_element": element},
        }
        for rank, (element, _document, _item) in enumerate(LINES)
        if element not in KNOWN
    ]
    return {
        "format_version": None,
        "read_count": len(LINES),
        "unchanged_count": 0,
        "rejected": rejected,
        "refusals": [],
        "differences": added,
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": ["lines_outside_project"],
        "unknown_wbs_elements": unknown_elements(LINES),
        "unit_constants": None,
        "calendar_gap": None,
    }


def import_actual_costs_unknown_elements() -> JsonObject:
    """Return what getImport answers of the extraction of the Vérif of WF-CRE-0020-A, analysed.

    A counterfactual variant of ``import_actual_costs_dotted_code``, whose import, task and
    instants it keeps, as ``import_remaining_amount_rounded`` keeps those of the import it varies:
    only the lines of the file, and so the report, differ.
    """
    dotted = cast("Entry", fixture("import_actual_costs_dotted_code"))
    report = unknown_elements_report()
    return {**dotted, "report": report, "available_commands": import_commands("analysed", report)}


def code_refused(name: str) -> JsonObject:
    """Return the refusal of a code a subproject and its project would share, on ``/code``."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/code", "code": "SUBPROJECT_CODE_INVALID"}],
        "correlation_id": correlation(name),
    }


def _unknown_said() -> str:
    report = unknown_elements_report()
    elements = cast("list[Entry]", report["unknown_wbs_elements"])
    named = ", ".join(
        f"« {each['wbs_element']} »" if each["wbs_element"] else "l'élément vide"
        for each in elements
    )
    counted = sum(cast("int", each["line_count"]) for each in elements)
    return (
        f"Variante contrefactuelle d'import_actual_costs_dotted_code, la Vérif de WF-CRE-0020-A : "
        f"sur le projet de code {PROJECT_CODE}, qui porte le sous-projet de code "
        f"{SUBPROJECT_CODE}, l'élément d'OTP se compare en entier. La ligne d'élément "
        f"{PROJECT_CODE} est ajoutée et imputée au seul projet, celle d'élément {SUBPROJECT_CODE} "
        f"à ce sous-projet ; les {counted} autres sont rejetées, et le compte rendu nomme chaque "
        f"élément inconnu une fois, avec le nombre de ses lignes — {named} —, ce qui dit quels "
        f"sous-projets déclarer avant de réimporter. L'application demande une confirmation "
        f"explicite pour les lignes rejetées pour leur élément (WF-CRE-0020, #3966). L'import et "
        f"les tâches sont ceux d'import_actual_costs_dotted_code, dont la famille des tâches de "
        f"fond 920-959 est pleine : les deux exemples décrivent le même import, avec deux comptes "
        f"rendus que seul le contenu du fichier distingue."
    )


def examples() -> dict[str, JsonObject]:
    """Return the examples of the WBS element compared whole and of the free code, by file name."""
    project = cast("Entry", fixture("project"))
    [subproject, *_others] = cast("list[Entry]", fixture("subprojects"))
    return {
        "import_actual_costs_unknown_elements.json": mocktext.example(
            _unknown_said(), import_actual_costs_unknown_elements()
        ),
        f"{SUBPROJECT_OF_PROJECT}.json": mocktext.example(
            f"Un sous-projet du projet témoin créé ou recodé sous le code du projet, "
            f"{project['code']} : refusé sur le code, sans paramètre — un sous-projet ne porte "
            f"jamais le code de son projet, auquel l'élément d'OTP d'une ligne de coût se compare "
            f"en entier ; rien n'est écrit (WF-PRJ-0050, WF-CRE-0020, #3966).",
            code_refused(SUBPROJECT_OF_PROJECT),
        ),
        f"{PROJECT_OF_SUBPROJECT}.json": mocktext.example(
            f"Le projet témoin recodé sous le code de son sous-projet « {subproject['label']} », "
            f"{subproject['code']} : refusé sur le code, sans paramètre, comme un sous-projet qui "
            f"prendrait le code du projet ; rien n'est écrit (WF-PRJ-0050, WF-CRE-0020, #3966).",
            code_refused(PROJECT_OF_SUBPROJECT),
        ),
    }
