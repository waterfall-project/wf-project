# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of one form each: a state refused by its condition, a catalogue without dead codes.

The review of the contract before the freeze (`docs/api/2026-10-28-contrat-avant-gel.md`, D-05,
J-01, J-02) and the decision of the author of the 2026-10-28: a terminal project and a marked
revision are refused everywhere by 409 ``STATE_FORBIDS_OPERATION`` and their missing condition,
never by a 403 (US-0702/L1):

- ``timeline_create_terminal.json``, a timeline created on the witness completed today
  (``project_completed``), refused by ``project_not_terminal``, as ``manage_timelines`` says it
  beforehand — and ``timeline_delete_terminal``, written by hand (#803), refused alike;
- ``node_create_marked_refused.json`` and ``skeleton_marked_refused.json``, a task created and the
  skeleton generated on the reference, the marked revision 101, refused by ``revision_draft``,
  the condition the revision names for its entries (``revision_marked``).

And a catalogue in which every code and every condition is rendered by an operation, with an
example (J-03, J-06, J-11, E-07, F-05, J-04):

- ``project_update_not_manager.json``, the witness updated by its participant, who holds every
  permission of its project manager and not her quality: ``NOT_PROJECT_MANAGER``
  (WF-PRJ-0060); ``next_state_pricing_without_code.json``, the offer whose reference would be
  designated before its code: ``project_code_set`` alone remains (WF-CYC-0030, WF-PRJ-0010);
- ``undo_history_empty.json`` and ``redo_history_empty.json``, an undo and a redo with nothing
  to undo or to redo; the undo and the redo of a change another contributor took up since,
  refused by naming the object (``undo_later_change``, ``redo_later_change``), stay written by
  hand, as counterfactual variants (#1531);
- ``task_progress_summary_refused.json`` and ``task_summary_date_refused.json``, the state and the
  finish of a summary entered, refused by naming its direct subordinates (WF-PLA-0040,
  WF-IHM-0030);
- ``estimate_line_rate_missing.json`` and ``estimate_line_role_required.json``, the hours of the
  wiring of the terminal blocks entered while the electrical engineering would have no rate for
  the reference year, as ``missing_rates`` supposes it, and its role withdrawn (WF-DEV-0010,
  WF-DEV-0020).

And the answers every operation may give (J-07, J-10): ``internal_error.json``, the unexpected
error any operation declares by the shared ``InternalError``, its correlation the reference the
front shows (WF-OBS-0020); ``nodes_fields_unknown.json``, a reading of the nodes asked for a
property ``Node`` does not have, refused as any parameter of a query, by 422 on ``/query/fields``.

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext, mockwitness
from wftools.mockids import universe
from wftools.mockproject import PARTICIPANT
from wftools.mockstructure import REFERENCE_YEAR, labels
from wftools.mockwitness import CREATED_TIMELINE, ELECTRICAL_ENGINEERING, N, fixture

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

TIMELINE_CORRELATION, NODE_CORRELATION, SKELETON_CORRELATION = (
    universe(1610),
    universe(1611),
    universe(1612),
)
"""The correlations of the refusals of a state."""

MANAGER_CORRELATION, UNDO_CORRELATION, REDO_CORRELATION = (
    universe(1613),
    universe(1614),
    universe(1615),
)
PROGRESS_CORRELATION, DATE_CORRELATION = universe(1616), universe(1617)
RATE_CORRELATION, ROLE_CORRELATION = universe(1618), universe(1619)
"""The correlations of the refusals of the catalogue."""

INTERNAL_CORRELATION, FIELDS_CORRELATION = universe(1620), universe(1621)
"""The correlations of the answers every operation, or every reading of the nodes, may give."""

UNKNOWN_FIELD = "task.duration_days"
"""A property a grid would ask for that ``Node`` does not have: the duration is ``task.duration``."""

REFERENCE = universe(101)
"""The reference of the witness, its marked revision 101."""

PROGRESS_SUMMARY, DATE_SUMMARY = N.STUDIES, N.CONTROL_STATION
"""The summaries whose state, and whose finish, are entered: the studies, the control station."""


def state_refused(condition: str, correlation: str) -> JsonObject:
    """Return the refusal of a command a state makes unavailable: its missing condition named."""
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": condition},
        "correlation_id": correlation,
    }


def quality_refused(code: str, quality: str, correlation: str) -> JsonObject:
    """Return the refusal of a write the quality of the caller on the project does not permit."""
    return {
        "code": code,
        "status": 403,
        "params": {"missing_condition": quality},
        "correlation_id": correlation,
    }


def subordinates(number: int) -> list[JsonValue]:
    """Return the direct subordinates of a summary of the witness, in the order of the plan."""
    return [
        mockwitness.node_id(row.number)
        for row in mockcore.current()
        if row.parent == number and row.kind == "task"
    ]


def summary_refused(number: int, correlation: str) -> JsonObject:
    """Return the refusal of the state of a summary entered: its direct subordinates named."""
    return {
        "code": "SUMMARY_TASK_DERIVED",
        "status": 422,
        "params": {"subordinate_node_ids": subordinates(number)},
        "correlation_id": correlation,
    }


def summary_date_refused(number: int, correlation: str) -> JsonObject:
    """Return the refusal of the finish of a summary entered, its subordinates named on its field."""
    field: JsonObject = {
        "pointer": "/finish",
        "code": "SUMMARY_TASK_DERIVED",
        "params": {"subordinate_node_ids": subordinates(number)},
    }
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [field],
        "correlation_id": correlation,
    }


def rate_missing() -> JsonObject:
    """Return the refusal of an entry of a line whose category has no rate for the reference year.

    The electrical engineering without a rate for 2026, as ``missing_rates`` supposes it: named
    without a field, the calculation of the line refused, not one of its cells (WF-DEV-0010).
    """
    missing: JsonObject = {
        "cost_category_id": ELECTRICAL_ENGINEERING,
        "label": labels()[ELECTRICAL_ENGINEERING],
        "year": REFERENCE_YEAR,
    }
    return {
        "code": "HOURLY_RATE_MISSING",
        "status": 422,
        "params": {"missing_rates": [missing]},
        "correlation_id": RATE_CORRELATION,
    }


def role_required() -> JsonObject:
    """Return the refusal of the role withdrawn from a line of labour, named on its field."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/resource_role_id", "code": "RESOURCE_ROLE_REQUIRED"}],
        "correlation_id": ROLE_CORRELATION,
    }


def next_state_without_code() -> JsonObject:
    """Return the next state of the offer, its reference designated before its code."""
    return {
        **cast("JsonObject", fixture("next_state_pricing")),
        "missing_conditions": ["project_code_set"],
    }


def _participant() -> str:
    """Return the name of the participant of the witness, from its contributors."""
    contributors = cast("list[JsonObject]", fixture("contributors")["items"])
    [row] = [each for each in contributors if each["user_id"] == PARTICIPANT]
    return str(row["display_name"])


def _reference() -> str:
    """Return the version name of the marked revision 101, from the revisions written by hand."""
    revisions = cast("list[JsonObject]", fixture("revisions")["items"])
    [revision] = [each for each in revisions if each["revision_id"] == REFERENCE]
    return str(revision["version_name"])


def examples() -> dict[str, JsonObject]:
    """Return the refusals of a state, those of the catalogue and the shared answers, by file."""
    return {**_state_examples(), **_catalogue_examples(), **_shared_examples()}


def _shared_examples() -> dict[str, JsonObject]:
    return {
        "internal_error.json": mocktext.example(
            "Une erreur inattendue du service, sur n'importe quelle opération : rien de ce qui a "
            "échoué n'est rendu, la cause est écrite au seul journal, avec sa trace, sous "
            "l'identifiant de corrélation que la réponse porte et que le front affiche comme sa "
            "référence (WF-OBS-0020, WF-ARC-0060).",
            {"code": "INTERNAL_ERROR", "status": 500, "correlation_id": INTERNAL_CORRELATION},
        ),
        "nodes_fields_unknown.json": mocktext.example(
            f"La structure principale du témoin lue avec fields={UNKNOWN_FIELD}, une propriété que "
            f"le nœud n'a pas — sa durée est task.duration : refusée comme tout paramètre de "
            f"requête, le paramètre désigné ; rien n'est lu (WF-ARC-0110, WF-IHM-0130).",
            {
                "code": "VALIDATION_FAILED",
                "status": 422,
                "fields": [{"pointer": "/query/fields", "code": "FIELD_NOT_ACCEPTED"}],
                "correlation_id": FIELDS_CORRELATION,
            },
        ),
    }


def _state_examples() -> dict[str, JsonObject]:
    project = cast("JsonObject", fixture("project_completed"))
    reference = _reference()
    _, timeline = CREATED_TIMELINE
    return {
        "timeline_create_terminal.json": mocktext.example(
            f"Une chronologie « {timeline} » créée sur le projet témoin, « {project['label']} », "
            f"terminé aujourd'hui (project_completed) : refusée par la condition que sa commande "
            f"manage_timelines dit manquer, project_not_terminal, comme toute écriture d'un "
            f"projet terminal ; rien n'est créé (WF-CYC-0100, WF-PLA-0140, WF-IHM-0090).",
            state_refused("project_not_terminal", TIMELINE_CORRELATION),
        ),
        "node_create_marked_refused.json": mocktext.example(
            f"Une tâche créée sur la structure principale de la révision « {reference} », "
            f"marquée (revision_marked) : refusée par la condition que la révision dit manquer à "
            f"ses saisies, revision_draft, une révision marquée ne se modifiant plus ; rien n'est "
            f"créé (WF-DAT-0020, WF-IHM-0090).",
            state_refused("revision_draft", NODE_CORRELATION),
        ),
        "skeleton_marked_refused.json": mocktext.example(
            f"La génération du squelette de planning demandée sur la révision « {reference} », "
            f"marquée (revision_marked) : refusée par la seule condition que sa commande "
            f"generate_skeleton dit manquer, revision_draft ; rien n'est écrit (WF-DAT-0020, "
            f"WF-PRJ-0030, WF-IHM-0090).",
            state_refused("revision_draft", SKELETON_CORRELATION),
        ),
    }


def _catalogue_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    witness, offer = fixture("project"), fixture("project_pricing")
    wiring = rows[N.LABOUR].label
    return {
        "project_update_not_manager.json": mocktext.example(
            f"Le libellé du projet témoin, « {witness['label']} », modifié par {_participant()}, "
            f"participante pour le pilotage, qui porte toutes les permissions de sa cheffe de "
            f"projet mais n'en a pas la qualité : refusé, la qualité nommée, comme la commande "
            f"update le lui disait d'avance (project_participant) ; rien n'est écrit "
            f"(WF-PRJ-0060, WF-ADM-0110, WF-IHM-0090).",
            quality_refused("NOT_PROJECT_MANAGER", "is_project_manager", MANAGER_CORRELATION),
        ),
        "next_state_pricing_without_code.json": mocktext.example(
            f"Variante contrefactuelle de l'offre en chiffrage, « {offer['label']} » : sa révision "
            f"de référence désignée avant la saisie de son code projet. Il ne lui reste qu'une "
            f"condition, le code projet, nommée ; elle passera à En cours à sa saisie "
            f"(WF-CYC-0030, WF-CYC-0050, WF-PRJ-0010).",
            next_state_without_code(),
        ),
        "undo_history_empty.json": mocktext.example(
            "Une annulation demandée sur la révision courante du témoin par un contributeur dont "
            "l'historique y est vide — il n'y a rien saisi pendant sa session, ou a tout annulé : "
            "refusée par la condition qui manque, rien n'est défait (WF-IHM-0110).",
            state_refused("undo_history_not_empty", UNDO_CORRELATION),
        ),
        "redo_history_empty.json": mocktext.example(
            "Un rétablissement demandé sur la révision courante du témoin quand aucune annulation "
            "n'est à rétablir : refusé par la condition qui manque, rien n'est rétabli "
            "(WF-IHM-0110).",
            state_refused("redo_history_not_empty", REDO_CORRELATION),
        ),
        "task_progress_summary_refused.json": mocktext.example(
            f"Les « {rows[PROGRESS_SUMMARY].label} », récapitulative, envoyées à l'état terminé : "
            f"son état est dérivé de ses subordonnées et n'est pas saisissable ; refusé en nommant "
            f"ses {mocktext.count(len(subordinates(PROGRESS_SUMMARY)))} subordonnées directes, "
            f"dans l'ordre du plan ; rien n'est écrit (WF-PLA-0040, WF-IHM-0030).",
            summary_refused(PROGRESS_SUMMARY, PROGRESS_CORRELATION),
        ),
        "task_summary_date_refused.json": mocktext.example(
            f"La date de fin du « {rows[DATE_SUMMARY].label} », récapitulative, saisie : elle "
            f"tire ses dates de ses subordonnées. « La tentative de modifier la date de fin d'une "
            f"tâche récapitulative est refusée en nommant ses subordonnées » : ses "
            f"{mocktext.count(len(subordinates(DATE_SUMMARY)))} subordonnées directes, sur son "
            f"champ ; rien n'est écrit (WF-PLA-0040, WF-IHM-0030).",
            summary_date_refused(DATE_SUMMARY, DATE_CORRELATION),
        ),
        "estimate_line_rate_missing.json": mocktext.example(
            f"La charge du « {wiring} » saisie si l'ingénierie électrique, la catégorie de son "
            f"rôle, n'avait pas de taux horaire pour {REFERENCE_YEAR}, l'année de référence de sa "
            f"révision, comme missing_rates le suppose : le calcul de la ligne est refusé et la "
            f"catégorie nommée, sans champ ; rien n'est écrit (WF-DEV-0010).",
            rate_missing(),
        ),
        "estimate_line_role_required.json": mocktext.example(
            f"Le rôle du « {wiring} », ligne de main-d'œuvre, retiré : une ligne de main-d'œuvre "
            f"porte un rôle, refusé sur son champ ; rien n'est écrit (WF-DEV-0020).",
            role_required(),
        ),
    }
