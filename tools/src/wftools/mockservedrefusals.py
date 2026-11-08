# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals the service served and the contract did not declare (US-1380/L4, #2519).

The local reviews of EP-06 found refusals the service gave that no operation declared, and three
rules to settle; the user decided on the 2026-11-08 to declare each one, with its example drawn
from the witness — the gestures of the structure and the entries of a task (as ``mockgestures``
writes their successes), the application of an import, an export, the reference, a project:

- ``node_create_parent_unknown``, ``node_create_dates_required``,
  ``node_create_finish_before_start``, ``node_create_kind_not_accepted`` and
  ``node_create_facet_missing``, a task created under a line, in manual mode without its dates,
  with its finish before its start, a line created while the service creates none, a task sent
  with the facet of a line (``createNode``, #2490, #2500);
- ``task_dates_required``, ``task_finish_before_start`` and ``task_update_empty``, the start of a
  manual task cleared, its finish entered before its start, a modification of the counter alone
  (``updateTaskFacet``, #2490);
- ``nodes_move_parent_unknown`` and ``nodes_move_node_cycle``, a task moved under a line, and a
  summary under its own subordinate (``moveNodes``, #2500);
- ``predecessors_unknown_task``, a line given as a predecessor (``setPredecessors``, #2506);
- ``task_completed_before_start``, the wiring of the cabinets completed before it started
  (``setTaskProgress``, WF-PLA-0130, #2495);
- ``import_apply_background_running`` and ``import_apply_may_create_revision``, two refusals that
  pass and leave the import awaiting its decision (``applyImport``, WF-ARC-0100, #2475);
- ``export_permission_missing``, the planning exported without the permission to consult it
  (``requestExport``, #2483);
- ``duration_units_horizon_exceeded``, ``calendar_update_horizon_exceeded``,
  ``calendar_default_horizon_exceeded`` and ``revision_create_horizon_exceeded``, the reference
  and an opening that would carry the witness beyond fifteen years (WF-PLA-0150, #2505);
- ``project_rate_precision``, an inflation rate of five decimals (``updateProject``, #2305).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockids import universe
from wftools.mockrefusals import field_refused, problem, state_refused
from wftools.mockwitness import N, fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

(
    PARENT_CORRELATION,
    DATES_CORRELATION,
    ORDER_CORRELATION,
    KIND_CORRELATION,
    FACET_CORRELATION,
    START_CORRELATION,
    FINISH_CORRELATION,
    EMPTY_CORRELATION,
    MOVE_PARENT_CORRELATION,
    CYCLE_CORRELATION,
    PREDECESSOR_CORRELATION,
    COMPLETED_CORRELATION,
    RUNNING_CORRELATION,
    REVISION_RIGHT_CORRELATION,
    EXPORT_CORRELATION,
    UNITS_CORRELATION,
    CALENDAR_CORRELATION,
    DEFAULT_CORRELATION,
    OPENING_CORRELATION,
    RATE_CORRELATION,
) = (universe(number) for number in range(1686, 1706))
"""The correlations of the refusals of US-1380/L4, the first free of the third range."""

CREATED_ORDER = (date(2026, 6, 1), date(2026, 5, 28))
"""A Monday and the Thursday before it, both worked: the start and the finish sent for a task."""

DESKS_FINISH = date(2026, 2, 26)
"""The finish entered for the operator desks, in manual mode: a Thursday before their start."""

COMPLETED_ON = date(2026, 4, 30)
"""The day the completion of the wiring of the cabinets is dated: before it started."""

RATE_SENT = "0.03125"
"""An inflation rate of five decimals: within its bounds, beyond the precision kept (#2305)."""

PLANNING_READ = "planning.read"
"""The permission to consult the planning, which guards its export (WF-ADM-0100)."""


def _rows() -> dict[int, mockcore.Row]:
    return {row.number: row for row in mockcore.current()}


def _task(number: int) -> JsonObject:
    return cast("JsonObject", _rows()[number].node["task"])


def _day(instant: JsonValue) -> date:
    return date.fromisoformat(cast("str", cast("JsonObject", instant)["date"]))


def _out_of_range(pointer: str, minimum: date, correlation: str) -> JsonObject:
    """Return a 422 that names one field below its least value, a day."""
    field: JsonObject = {
        "pointer": pointer,
        "code": "VALUE_OUT_OF_RANGE",
        "params": {"minimum": minimum.isoformat()},
    }
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [field],
        "correlation_id": correlation,
    }


def _fields(faults: list[tuple[str, str]], correlation: str) -> JsonObject:
    """Return a 422 that names several fields by their motive, without a parameter."""
    fields: list[JsonValue] = [{"pointer": pointer, "code": code} for pointer, code in faults]
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": fields,
        "correlation_id": correlation,
    }


def _witness() -> JsonObject:
    """Return the witness as a refusal of the reference names it: its label and its code."""
    project = fixture("project")
    return {"project_label": project["label"], "project_code": project["code"]}


def _beyond(correlation: str, named: JsonObject) -> JsonObject:
    return {
        "code": "PROJECT_HORIZON_EXCEEDED",
        "status": 422,
        "params": named,
        "correlation_id": correlation,
    }


def last_task() -> mockcore.Row:
    """Return the task of the witness that finishes last, no summary, the first in plan order.

    The one a replay of the whole structure names beyond the horizon when no task is written
    (WF-PLA-0150).
    """
    leaves = [
        row
        for row in mockcore.current()
        if row.kind == "task" and not cast("JsonObject", row.node["task"])["is_summary"]
    ]

    def finish(row: mockcore.Row) -> tuple[str, Decimal]:
        end = cast("JsonObject", cast("JsonObject", row.node["task"])["finish"])
        return cast("str", end["date"]), Decimal(cast("str", end["hours"]))

    latest = max(finish(row) for row in leaves)
    return next(row for row in leaves if finish(row) == latest)


def gestures() -> dict[str, JsonObject]:
    """Return the refusals of the gestures of the structure and of the entries of a task."""
    return {
        "node_create_parent_unknown.json": field_refused(
            "/parent_id", "UNKNOWN_TASK", PARENT_CORRELATION
        ),
        "node_create_dates_required.json": _fields(
            [("/task/start", "VALUE_REQUIRED"), ("/task/finish", "VALUE_REQUIRED")],
            DATES_CORRELATION,
        ),
        "node_create_finish_before_start.json": _out_of_range(
            "/task/finish/date", CREATED_ORDER[0], ORDER_CORRELATION
        ),
        "node_create_kind_not_accepted.json": field_refused(
            "/kind", "FIELD_NOT_ACCEPTED", KIND_CORRELATION
        ),
        "node_create_facet_missing.json": _fields(
            [("/task", "VALUE_REQUIRED"), ("/estimate_line", "FIELD_NOT_ACCEPTED")],
            FACET_CORRELATION,
        ),
        "task_dates_required.json": field_refused("/start", "VALUE_REQUIRED", START_CORRELATION),
        "task_finish_before_start.json": _out_of_range(
            "/finish/date", _day(_task(N.DESKS)["start"]), FINISH_CORRELATION
        ),
        "task_update_empty.json": problem("VALIDATION_FAILED", 422, EMPTY_CORRELATION),
        "nodes_move_parent_unknown.json": field_refused(
            "/parent_id", "UNKNOWN_TASK", MOVE_PARENT_CORRELATION
        ),
        "nodes_move_node_cycle.json": field_refused("/parent_id", "NODE_CYCLE", CYCLE_CORRELATION),
        "predecessors_unknown_task.json": field_refused(
            "/predecessors/1/predecessor_node_id", "UNKNOWN_TASK", PREDECESSOR_CORRELATION
        ),
        "task_completed_before_start.json": _out_of_range(
            "/occurred_on",
            date.fromisoformat(cast("str", _task(N.WIRING)["started_on"])),
            COMPLETED_CORRELATION,
        ),
    }


def others() -> dict[str, JsonObject]:
    """Return the refusals of an import applied, an export, the reference and a project."""
    beyond = last_task()
    named: JsonObject = {"node_id": beyond.node["node_id"], "label": beyond.label}
    return {
        "import_apply_background_running.json": state_refused(
            "no_background_task_running", RUNNING_CORRELATION
        ),
        "import_apply_may_create_revision.json": state_refused(
            "may_create_revision", REVISION_RIGHT_CORRELATION
        ),
        "export_permission_missing.json": {
            "code": "PERMISSION_MISSING",
            "status": 403,
            "params": {"missing_permission": PLANNING_READ},
            "correlation_id": EXPORT_CORRELATION,
        },
        "duration_units_horizon_exceeded.json": _beyond(
            UNITS_CORRELATION, {"projects": [_witness()]}
        ),
        "calendar_update_horizon_exceeded.json": _beyond(
            CALENDAR_CORRELATION, {"projects": [_witness()]}
        ),
        "calendar_default_horizon_exceeded.json": _beyond(
            DEFAULT_CORRELATION, {"projects": [_witness()]}
        ),
        "revision_create_horizon_exceeded.json": _beyond(OPENING_CORRELATION, {"task": named}),
        "project_rate_precision.json": field_refused(
            "/inflation_rate", "VALIDATION_FAILED", RATE_CORRELATION
        ),
    }


def examples() -> dict[str, JsonObject]:
    """Return the examples of the refusals served and not declared, by file name."""
    values, said = {**gestures(), **others()}, _said()
    return {name: mocktext.example(said[name], value) for name, value in values.items()}


def _said() -> dict[str, str]:
    """Say each refusal, from what the witness reads."""
    rows = _rows()
    wiring, desks = rows[N.WIRING], rows[N.DESKS]
    started = date.fromisoformat(cast("str", _task(N.WIRING)["started_on"]))
    desks_start = _day(_task(N.DESKS)["start"])
    project = _witness()
    witness = f"« {project['project_label']} », {project['project_code']}"
    beyond = last_task()
    first, last = CREATED_ORDER
    return {
        "node_create_parent_unknown.json": (
            f"Une tâche créée sous les « {rows[N.BLOCKS].label} », une ligne du "
            f"« {wiring.label} » : le parent n'est pas une tâche de la structure, comme un nœud "
            f"inconnu ; refusée sur son champ, sans paramètre, et rien n'est créé (#2490, #2500)."
        ),
        "node_create_dates_required.json": (
            "Une tâche créée en mode manuel sans son début ni sa fin : une tâche manuelle porte "
            "les dates qu'on lui saisit, et chacune manque à son champ ; rien n'est créé "
            "(WF-PLA-0020, #2490)."
        ),
        "node_create_finish_before_start.json": (
            f"Une tâche créée en mode manuel, du {mocktext.day(first)} au {mocktext.day(last)} : "
            f"sa fin précède son début, refusée sur sa date, le début nommé comme le plus petit "
            f"jour admis ; rien n'est créé (WF-PLA-0020, #2490)."
        ),
        "node_create_kind_not_accepted.json": (
            "Une ligne de devis créée sur un service qui ne crée pas encore les lignes, avant "
            "EP-07 : la nature du nœud est refusée sur son champ, sans paramètre ; rien n'est "
            "créé (#2490)."
        ),
        "node_create_facet_missing.json": (
            "Une tâche envoyée sans sa facette de tâche, avec celle d'une ligne : la première "
            "manque, la seconde n'est pas reçue, chacune à son champ ; rien n'est créé (#2490)."
        ),
        "task_dates_required.json": (
            f"Le début de la « {rows[N.COMMISSIONING].label} », en mode manuel "
            f"(task_mode_changed), envoyé nul : une tâche manuelle garde ses dates, que l'on "
            f"modifie sans les effacer ; refusé sur son champ, rien n'est écrit (WF-PLA-0020, "
            f"#2490)."
        ),
        "task_finish_before_start.json": (
            f"La fin des « {desks.label} », en mode manuel, saisie au "
            f"{mocktext.day(DESKS_FINISH)}, avant leur début, le {mocktext.day(desks_start)} : "
            f"refusée sur sa date, le début nommé comme le plus petit jour admis ; rien n'est "
            f"écrit (WF-PLA-0020, #2490)."
        ),
        "task_update_empty.json": (
            "Une modification qui n'envoie que le compteur lu : elle ne dit rien à écrire "
            "(minProperties), refusée sans champ ni paramètre ; rien n'est écrit (#2490)."
        ),
        "nodes_move_parent_unknown.json": (
            f"La « {rows[N.FACTORY_ACCEPTANCE].label} » déplacée sous les "
            f"« {rows[N.BLOCKS].label} », une ligne : le parent visé n'est pas une tâche de la "
            f"structure ; refusé sur son champ, sans paramètre, rien ne bouge (#2500)."
        ),
        "nodes_move_node_cycle.json": (
            f"Le « {rows[N.CONTROL_STATION].label} » déplacé sous le « {wiring.label} », l'une de "
            f"ses propres subordonnées : la hiérarchie bouclerait, et le refus le dit sur le "
            f"parent visé, sans paramètre ; rien ne bouge (WF-PLA-0040, #2500)."
        ),
        "predecessors_unknown_task.json": (
            f"La « {rows[N.COMMISSIONING].label} » donnée à suivre le "
            f"« {rows[N.MOUNTING].label} » et le « {rows[N.WIRING_ON_SITE].label} », une ligne de "
            f"celui-ci, au second rang envoyé : un prédécesseur est une tâche de la structure ; "
            f"refusé à son rang, rien n'est écrit (WF-PLA-0030, #2506)."
        ),
        "task_completed_before_start.json": (
            f"Le « {wiring.label} », démarré le {mocktext.day(started)}, terminé depuis le Kanban "
            f"à la date du {mocktext.day(COMPLETED_ON)} : une terminaison ne se date pas avant le "
            f"démarrage ; refusée sur la date, le démarrage nommé comme le plus petit jour admis, "
            f"rien n'est écrit (WF-PLA-0130, #2495)."
        ),
        "import_apply_background_running.json": (
            "L'application d'un import analysé du projet témoin demandée pendant le marquage de "
            "sa révision en cours : refusée, la condition manquante nommée ; le refus est "
            "passager, l'import reste analysé et son fichier en place, et l'application se "
            "redemande après le marquage, sans nouveau dépôt (WF-ARC-0100, #2475)."
        ),
        "import_apply_may_create_revision.json": (
            "Variante contrefactuelle : l'application d'un import analysé sur un projet sans "
            "révision en cours, qu'elle créerait, demandée par un contributeur qui ne peut pas "
            "créer de révision : refusée, la condition manquante nommée ; l'import reste analysé "
            "et son fichier en place, la permission pouvant lui être donnée (WF-INTF-0090, "
            "WF-ARC-0100, #2475)."
        ),
        "export_permission_missing.json": (
            f"L'export du planning du projet témoin demandé par un compte qui ne peut pas le "
            f"consulter : la commande export_planning est absente de sa révision, et le refus "
            f"nomme la permission de consultation qui manque, {PLANNING_READ} ; rien n'est mis en "
            f"file (WF-ADM-0100, WF-CYC-0110, #2483)."
        ),
        "duration_units_horizon_exceeded.json": (
            f"Variante contrefactuelle : une constante des unités de durée changée, qui porterait "
            f"au-delà de quinze ans le projet {witness}, dont la révision en cours est recalculée "
            f"(WF-PLA-0160) : refusée, le projet nommé par son libellé et son code, sans tâche ni "
            f"identifiant, l'auteur pouvant ne pas le consulter ; rien n'est écrit (WF-PLA-0150, "
            f"WF-ADM-0110, #2505)."
        ),
        "calendar_update_horizon_exceeded.json": (
            f"Variante contrefactuelle : les heures d'un calendrier réduites au point de porter "
            f"au-delà de quinze ans le projet {witness}, dont la révision en cours est recalculée "
            f"(WF-PLA-0160) : refusées, le projet nommé par son libellé et son code, sans tâche ni "
            f"identifiant ; rien n'est écrit (WF-PLA-0150, WF-ADM-0110, #2505)."
        ),
        "calendar_default_horizon_exceeded.json": (
            f"Variante contrefactuelle : un calendrier désigné par défaut dont les heures "
            f"porteraient au-delà de quinze ans le projet {witness}, ses tâches sans ligne de "
            f"main-d'œuvre en relevant : refusé, le projet nommé par son libellé et son code, sans "
            f"tâche ni identifiant ; rien n'est écrit (WF-PLA-0150, WF-ADM-0110, #2505)."
        ),
        "revision_create_horizon_exceeded.json": (
            f"Variante contrefactuelle : la révision en cours 102 ouverte de la référence 101, ses "
            f"tâches datées avec les unités de durée et les calendriers d'aujourd'hui au point de "
            f"porter le projet au-delà de quinze ans : refusée, la tâche qui finit la dernière, "
            f"« {beyond.label} », nommée par son nœud et son libellé ; rien n'est créé "
            f"(WF-PLA-0150, WF-PLA-0160, #2505)."
        ),
        "project_rate_precision.json": (
            f"Le taux d'inflation du projet témoin saisi à {RATE_SENT}, cinq décimales : dans ses "
            f"bornes, mais au-delà des quatre que le taux garde, un centième de pour cent ; refusé "
            f"sur son champ, sans paramètre, plutôt qu'arrondi ; rien n'est écrit (WF-PRJ-0040, "
            f"WF-DAT-0100, #2305)."
        ),
    }
