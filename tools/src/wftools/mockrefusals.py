# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The refusals of one form each: a state refused by its condition, a catalogue without dead codes.

The review of the contract before the freeze (`docs/api/2026-10-28-contrat-avant-gel.md`, D-05,
J-01, J-02) and the decision of the author of the 2026-10-28: a terminal project and a marked
revision are refused everywhere by 409 ``STATE_FORBIDS_OPERATION`` and their missing condition,
never by a 403 (US-0702/L1):

- ``timeline_create_terminal.json``, a timeline created on the witness completed today
  (``project_completed``), which lists no command any more (US-0702/L3), refused by
  ``project_not_terminal`` — and ``timeline_delete_terminal``, written by hand (#803), refused
  alike;
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

And the refusals of the common tree its operations declared without an example (F-17, #1648):
a line of labour that would leave its task without any hour of work, created, changed of role,
moved under it or pasted on its cell of role (#779), the calendars supposed otherwise, those of the
witness all meeting from Monday to Thursday (``*_without_hours``); a field a node does not accept
(``*_field_not_accepted``, ``task_milestone_duration_refused``); a category of provision given to
a line entered; a line of a completed task re-estimated (``remaining_completed_refused``).

And the refusals the catalogue named without an example, each carried by an operation that says it
(US-0702/L1, J-17): the 401 of a request without a token, of a deactivated account and of an
account not admitted (``session_required``, ``account_deactivated``, ``account_not_admitted``); the
avatar sent empty or too large (``avatar_malformed``, ``avatar_too_large``); the project updated by
who is not even a contributor (``project_update_not_contributor``); a bound of a reading that is
no number, an instant that is no date, a calendar the reference lacks
(``access_roles_number_invalid``, ``access_roles_date_invalid``,
``resource_role_calendar_unknown``); and two motives of a line imported, its element of the work
breakdown structure malformed and its task named by a label several tasks bear
(``import_actual_costs_wbs_invalid``, ``import_remaining_ambiguous_label``).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

from wftools import mockcore, mockexchanges, mocktext, mockwitness, mockwrites
from wftools.mockids import hex_identifier, universe
from wftools.mockproject import PARTICIPANT
from wftools.mockstructure import REFERENCE_YEAR, labels
from wftools.mockwitness import (
    CABLE_FITTER,
    COMMISSIONING_TECHNICIAN,
    CREATED_TIMELINE,
    ELECTRICAL_ENGINEERING,
    ENGINEER,
    PROVISIONS,
    N,
    fixture,
)

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

CREATE_HOURS_CORRELATION, ROLE_HOURS_CORRELATION = universe(1622), universe(1623)
CREATE_FIELD_CORRELATION, MILESTONE_CORRELATION = universe(1624), universe(1625)
LINE_FIELD_CORRELATION, PROVISION_CORRELATION = universe(1626), universe(1627)
REMAINING_CORRELATION = universe(1628)
"""The correlations of the refusals of the common tree (#1648)."""

MOVE_HOURS_CORRELATION = universe(1658)
"""The correlation of a line of labour moved under a task it would leave without hours (#779)."""

ABANDON_STALE_CORRELATION, EXIT_STALE_CORRELATION = universe(1659), universe(1660)
DESIGNATE_STALE_CORRELATION, RISK_STALE_CORRELATION = universe(1661), universe(1662)
SUBPROJECT_STALE_CORRELATION = universe(1663)
"""The correlations of the five writes that carry their counter since US-0702/L2 (US-0703/L8)."""

WITHOUT_HOURS_BLOCK = (
    mockwrites.BLOCK[0],
    (mockwrites.ENTERED, mockwrites.BLOCK[0][1], "Monteur câbleur", "1"),
    mockwrites.BLOCK[2],
)
"""The block of the journeys, its second row giving its line to the cable fitter: the task would
bear him with the electrical engineer, whose calendars, supposed otherwise, never meet (#779)."""

WITHOUT_HOURS_PASTE = universe(997)
"""The plan of WITHOUT_HOURS_BLOCK (``paste_plan_without_hours``)."""

SESSION_CORRELATION, DEACTIVATED_CORRELATION, NOT_ADMITTED_CORRELATION = (
    universe(1629),
    universe(1630),
    universe(1631),
)
MALFORMED_CORRELATION, TOO_LARGE_CORRELATION = universe(1632), universe(1633)
CONTRIBUTOR_CORRELATION = universe(1634)
NUMBER_CORRELATION, INSTANT_CORRELATION, CALENDAR_CORRELATION = (
    universe(1635),
    universe(1636),
    universe(1637),
)
"""The correlations of the refusals the catalogue named without an example."""

WBS_IMPORT, WBS_IMPORT_TASK = hex_identifier(0xA30), universe(956)
WBS_INSTANTS = ("2026-05-04T09:25:00Z", "2026-05-04T09:26:00Z", "2026-05-05T09:26:00Z")
LABEL_IMPORT, LABEL_IMPORT_TASK = hex_identifier(0xA31), universe(957)
LABEL_INSTANTS = ("2026-06-03T10:40:05Z", "2026-06-03T10:41:00Z", "2026-06-04T10:41:00Z")
"""The imports whose line is rejected for its element of the work breakdown structure and for an
ambiguous label, the tasks that analysed them, and the instants of their opening, their analysis
and their expiry: each import has its own, an instant naming one task."""

MALFORMED_ELEMENT = "/SP-CAB"
"""An element of the work breakdown structure with nothing before the slash (WF-CRE-0020)."""

AMBIGUOUS_LABEL = "Mise en service"
"""A label two tasks of the witness bear: the commissioning of the installation, and a task of the
volume of the portfolio."""

UNKNOWN_FIELD = "task.duration_days"
"""A property a grid would ask for that ``Node`` lacks: its duration is ``task.duration``."""

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
    """Return the refusal of the finish of a summary entered: its subordinates, on its field."""
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


def field_refused(pointer: str, code: str, correlation: str) -> JsonObject:
    """Return a 422 that names one field by its motive, without a parameter."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": pointer, "code": code}],
        "correlation_id": correlation,
    }


def without_hours(roles: list[str], correlation: str) -> JsonObject:
    """Return the refusal of a line of labour that would leave the wiring without hours of work.

    Created, its role changed or moved under it (`createNode`, `updateEstimateLine`, `moveNodes`).

    The roles whose calendars never meet, by their identifiers, and the task by its project, its
    node and its label (WF-PLA-0010).
    """
    task: JsonObject = {
        "project_id": fixture("project")["project_id"],
        "node_id": mockwitness.node_id(N.WIRING),
        "label": {row.number: row for row in mockcore.current()}[N.WIRING].label,
    }
    return {
        "code": "TASK_WITHOUT_WORKING_HOURS",
        "status": 422,
        "params": {"resource_role_ids": cast("list[JsonValue]", roles), "tasks": [task]},
        "correlation_id": correlation,
    }


def paste_plan_without_hours() -> JsonObject:
    """Return what previewPaste answers for WITHOUT_HOURS_BLOCK, the calendars supposed otherwise.

    Pasted on the line of the journeys (`mockwrites.LINE`), its second row would leave the task of
    that line without any hour of work in the week: the calendar of the cable fitter it gives to
    its line never meets that of the electrical engineer, whom the first row and another line of
    the task keep. The row is refused on its cell of role, the two roles and the task named as for
    a line of labour entered (`TASK_WITHOUT_WORKING_HOURS`, `PasteRejection`, WF-PLA-0010); the
    others are accepted.
    """
    plan = mockwrites.paste_plan(WITHOUT_HOURS_BLOCK, WITHOUT_HOURS_PASTE)
    if plan["rejected"]:
        message = "WITHOUT_HOURS_BLOCK names a category or a role the reference does not know"
        raise ValueError(message)
    task = mockwrites.pasted_task()
    _, roles = mockwrites.known()
    refusal: JsonObject = {
        "row": 1,
        "column": "resource_role",
        "code": "TASK_WITHOUT_WORKING_HOURS",
        "params": {
            "resource_role_ids": [roles[row[2]] for row in WITHOUT_HOURS_BLOCK[:2]],
            "tasks": [
                {
                    "project_id": fixture("project")["project_id"],
                    "node_id": mockwitness.node_id(task.number),
                    "label": task.label,
                }
            ],
        },
    }
    return {
        "paste_id": WITHOUT_HOURS_PASTE,
        "accepted": len(WITHOUT_HOURS_BLOCK) - 1,
        "rejected": [refusal],
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


def problem(code: str, status: int, correlation: str) -> JsonObject:
    """Return a refusal that says its code alone, without a parameter nor a field.

    Public, as ``state_refused`` and ``field_refused``: the refusals of US-0702/L2
    (``mockdeclared``) are written by the same helpers.
    """
    return {"code": code, "status": status, "correlation_id": correlation}


class _ImportReport(TypedDict):
    """The parts of the report of an import read that its variants rewrite (``ImportReport``)."""

    rejected: list[JsonObject]
    differences: list[JsonValue]
    read_count: int
    unchanged_count: int
    requires_confirmation_reasons: list[JsonValue]


def _report(imported: JsonObject) -> _ImportReport:
    """Return the report of an import read, typed by the parts its variants rewrite."""
    return cast("_ImportReport", imported["report"])


def _rejecting(
    imported: JsonObject,
    identifiers: tuple[str, str],
    instants: tuple[str, str, str],
    rejected: JsonObject,
) -> None:
    """Rewrite an import read of the witness: its own identifiers and instants, one line rejected.

    The lines read are those it differs by, and the one rejected.
    """
    task = cast("JsonObject", imported["task"])
    report = _report(imported)
    imported["import_id"], task["task_id"] = identifiers
    opened, analysed, expires = instants
    imported["created_at"], task["submitted_at"] = opened, opened
    task["finished_at"], imported["expires_at"] = analysed, expires
    report["rejected"] = [rejected]
    report["read_count"] = len(report["differences"]) + 1
    report["unchanged_count"] = 0


def import_wbs_invalid() -> JsonObject:
    """Return the extraction of April whose line of another project is a malformed element."""
    imported = mockexchanges.import_actual_costs_first()
    report = _report(imported)
    [outside] = report["rejected"]
    rejected: JsonObject = {
        "sheet": None,
        "row": outside["row"],
        "code": "WBS_ELEMENT_INVALID",
        "params": {"wbs_element": MALFORMED_ELEMENT},
    }
    _rejecting(imported, (WBS_IMPORT, WBS_IMPORT_TASK), WBS_INSTANTS, rejected)
    report["requires_confirmation_reasons"] = [
        each for each in report["requires_confirmation_reasons"] if each != "lines_outside_project"
    ]
    return imported


def import_ambiguous_label() -> JsonObject:
    """Return a remaining to commit whose second line cites a task by a label two tasks bear."""
    imported = mockexchanges.import_remaining_subproject_held()
    tasks: list[JsonValue] = [
        {"lineage_id": mockcore.lineage(row.number), "label": row.label}
        for row in mockcore.current()
        if row.label == AMBIGUOUS_LABEL
    ]
    rejected: JsonObject = {
        "sheet": mockexchanges.tab_name(mockexchanges.TAB),
        "row": mockexchanges.FIRST_ROW + 1,
        "code": "AMBIGUOUS_TASK_LABEL",
        "params": {"label": AMBIGUOUS_LABEL, "tasks": tasks},
    }
    _rejecting(imported, (LABEL_IMPORT, LABEL_IMPORT_TASK), LABEL_INSTANTS, rejected)
    return imported


def examples() -> dict[str, JsonObject]:
    """Return the refusals of a state, those of the catalogue and the shared answers, by file."""
    return {
        **_state_examples(),
        **_catalogue_examples(),
        **_shared_examples(),
        **_tree_examples(),
        **_named_examples(),
        **_stale_examples(),
    }


def stale(current: JsonValue, correlation: str) -> JsonObject:
    """Return the refusal of a write sent with a counter older than the object's (WF-IHM-0110).

    The object was written since the screen read it: nothing is written, and the refusal names the
    counter the object bears now (``expected_lock_version``).
    """
    return {
        "code": "STALE_LOCK_VERSION",
        "status": 412,
        "params": {"expected_lock_version": current},
        "correlation_id": correlation,
    }


def _stale_examples() -> dict[str, JsonObject]:
    """Return the 412 of the five writes that carry their counter since US-0702/L2 (E-13, E-24).

    Each is sent with the counter before the one its object bears in the witness — another session
    wrote it since the screen read it —, and is refused with the counter the object bears now.
    """
    revision, project, risk = fixture("revision"), fixture("project"), fixture("risk")
    subproject = cast("list[JsonObject]", fixture("subprojects"))[0]

    def told(what: str, who: str, now: JsonValue, *, feminine: bool = False) -> str:
        # The counter sent is the one before: the object of the witness was written once at least.
        if not isinstance(now, int) or now < 1:
            message = f"{what}: a counter of 1 at least is needed to send the one before, not {now}"
            raise ValueError(message)
        e = "e" if feminine else ""
        return (
            f"{what} envoyé{e} avec le compteur {cast('int', now) - 1}, quand {who} porte {now} — "
            f"une autre session l'a écrit depuis la lecture de l'écran — : refusé{e}, le compteur "
            f"courant rendu, et rien n'est écrit ; l'écran propose de relire (WF-IHM-0110, "
            f"US-0702/L2)."
        )

    return {
        "revision_abandon_stale.json": mocktext.example(
            told(
                f"L'abandon de la révision en cours de « {project['label']} »",
                "la révision",
                revision["lock_version"],
            ),
            stale(revision["lock_version"], ABANDON_STALE_CORRELATION),
        ),
        "project_exit_stale.json": mocktext.example(
            told(
                f"La sortie de « {project['label']} »",
                "le projet",
                project["lock_version"],
                feminine=True,
            ),
            stale(project["lock_version"], EXIT_STALE_CORRELATION),
        ),
        "reference_designate_stale.json": mocktext.example(
            told(
                f"La désignation de la référence de « {project['label']} »",
                "le projet, dont elle écrit la référence,",
                project["lock_version"],
                feminine=True,
            ),
            stale(project["lock_version"], DESIGNATE_STALE_CORRELATION),
        ),
        "risk_delete_stale.json": mocktext.example(
            told(
                f"La suppression du risque « {risk['label']} »",
                "le risque",
                risk["lock_version"],
                feminine=True,
            ),
            stale(risk["lock_version"], RISK_STALE_CORRELATION),
        ),
        "subproject_delete_stale.json": mocktext.example(
            told(
                f"La suppression du sous-projet « {subproject['label']} »",
                "le sous-projet",
                subproject["lock_version"],
                feminine=True,
            ),
            stale(subproject["lock_version"], SUBPROJECT_STALE_CORRELATION),
        ),
    }


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
            f"terminé aujourd'hui (project_completed) : le projet clos ne liste plus "
            f"manage_timelines, et l'appel direct est refusé par la condition qui manque, "
            f"project_not_terminal, comme toute écriture d'un projet terminal ; rien n'est créé "
            f"(WF-CYC-0100, WF-PLA-0140, WF-IHM-0090).",
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


def _tree_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    wiring, line, blocks = rows[N.WIRING].label, rows[N.LABOUR].label, rows[N.BLOCKS].label
    supposed = (
        "Aucune situation du témoin ne le produit, ses calendriers se recoupant tous du lundi au "
        "jeudi : les calendriers sont supposés ici autres"
    )
    return {
        "node_create_without_hours.json": mocktext.example(
            f"Une ligne du monteur câbleur créée sous le « {wiring} », qui porte une ligne de "
            f"l'ingénieur : leurs calendriers n'auraient aucun jour en commun, et la tâche aucune "
            f"heure travaillée. Refusée, les deux rôles et la tâche nommés ; rien n'est créé "
            f"(WF-PLA-0010). {supposed}.",
            without_hours([ENGINEER, CABLE_FITTER], CREATE_HOURS_CORRELATION),
        ),
        "estimate_line_without_hours.json": mocktext.example(
            f"Le rôle du « {line} », seule ligne de main-d'œuvre du « {wiring} », passé au "
            f"monteur câbleur, dont le calendrier n'aurait aucune heure dans la semaine : refusé, "
            f"le rôle et la tâche nommés ; rien n'est écrit (WF-PLA-0010). {supposed}.",
            without_hours([CABLE_FITTER], ROLE_HOURS_CORRELATION),
        ),
        "nodes_move_without_hours.json": mocktext.example(
            f"La « {rows[N.COMMISSIONING_LINE].label} », ligne du technicien de mise en service "
            f"sous la « {rows[N.COMMISSIONING].label} », déplacée sous le « {wiring} », qui porte "
            f"une ligne de l'ingénieur : leurs calendriers n'auraient aucun jour en commun, et la "
            f"tâche qui la reçoit aucune heure travaillée. Refusé, les deux rôles et la tâche "
            f"nommés ; rien ne bouge (WF-PLA-0010). {supposed}.",
            without_hours([ENGINEER, COMMISSIONING_TECHNICIAN], MOVE_HOURS_CORRELATION),
        ),
        "paste_plan_without_hours.json": mocktext.example(
            f"Variante contrefactuelle déclarée : le bloc de paste_plan, dont la deuxième ligne "
            f"donne la ligne {mockwrites.ROW + 1} au monteur câbleur, « "
            f"{WITHOUT_HOURS_BLOCK[1][0]} » ; sa tâche, « {mockwrites.pasted_task().label} », le "
            f"porterait avec l'ingénieur électricien, que la première ligne et la ligne de "
            f"supervision gardent, et leurs calendriers n'auraient aucun jour en commun : cette "
            f"ligne est refusée sur sa cellule de rôle, les deux rôles et la tâche nommés, et les "
            f"deux autres seraient écrites ; confirmé, le collage écrira les deux autres et non "
            f"celle-ci, abandonné, il n'écrira rien (WF-IHM-0050, WF-PLA-0010). {supposed}.",
            paste_plan_without_hours(),
        ),
        "node_create_field_not_accepted.json": mocktext.example(
            f"Une ligne de l'ingénieur créée sous le « {wiring} » avec un débours unitaire : une "
            f"ligne de main-d'œuvre n'en porte pas, refusée sur ce champ ; rien n'est créé "
            f"(WF-DEV-0020).",
            field_refused(
                "/estimate_line/unit_disbursement", "FIELD_NOT_ACCEPTED", CREATE_FIELD_CORRELATION
            ),
        ),
        "task_milestone_duration_refused.json": mocktext.example(
            f"Une durée envoyée pour la « {rows[N.FACTORY_ACCEPTANCE].label} », un jalon, qui "
            f"n'en a pas à saisir : refusée sur son champ, que le nœud n'accepte pas ; rien n'est "
            f"écrit (WF-PLA-0050).",
            field_refused("/duration", "FIELD_NOT_ACCEPTED", MILESTONE_CORRELATION),
        ),
        "estimate_line_field_not_accepted.json": mocktext.example(
            f"Un débours unitaire envoyé pour le « {line} », ligne de main-d'œuvre, qui n'en "
            f"porte pas : refusé sur son champ, que la ligne n'accepte pas (editable_fields) ; "
            f"rien n'est écrit (WF-DEV-0020).",
            field_refused("/unit_disbursement", "FIELD_NOT_ACCEPTED", LINE_FIELD_CORRELATION),
        ),
        "estimate_line_provision_reserved.json": mocktext.example(
            f"Les « {blocks} » passés dans la catégorie « {labels()[PROVISIONS]} », de type "
            f"provision pour risques : seule la déclaration d'un risque crée une ligne de "
            f"provision ; refusé sur son champ, rien n'est écrit (WF-DEV-0020, WF-RIS-0010).",
            field_refused(
                "/cost_category_id", "PROVISION_CATEGORY_RESERVED", PROVISION_CORRELATION
            ),
        ),
        "remaining_completed_refused.json": mocktext.example(
            f"L'« {rows[N.STUDIES_LINE].label} », ligne des « {rows[N.DETAILED_STUDIES].label} », "
            f"terminées, réestimée : les lignes d'une tâche terminée ne se modifient pas ; refusé "
            f"par la condition que sa remaining_entry dit manquer, rien n'est écrit (WF-RAE-0040, "
            f"WF-IHM-0090).",
            state_refused("task_not_completed", REMAINING_CORRELATION),
        ),
    }


def _april_row() -> int:
    """Return the row of the line of the extraction of April the analysis rejected."""
    [rejected] = _report(mockexchanges.import_actual_costs_first())["rejected"]
    return int(cast("int", rejected["row"]))


def _named_examples() -> dict[str, JsonObject]:
    avatar_mio = int(cast("int", fixture("installation")["avatar_max_bytes"])) // 2**20
    tab = mockexchanges.tab_name(mockexchanges.TAB)
    return {
        "session_required.json": mocktext.example(
            "Une requête de la liste des projets envoyée sans jeton d'accès : refusée avant toute "
            "lecture, sans rien dire de ce qu'elle demandait ; le front mène à la connexion "
            "(WF-SEC-0020).",
            problem("SESSION_REQUIRED", 401, SESSION_CORRELATION),
        ),
        "account_deactivated.json": mocktext.example(
            "Le compte d'un contributeur désactivé lit son compte avec un jeton encore valable : "
            "refusé à chaque requête, ses sessions étant fermées ; le front ne le renvoie pas à "
            "une connexion qui bouclerait (WF-ADM-0060, WF-SEC-0020).",
            problem("ACCOUNT_DEACTIVATED", 401, DEACTIVATED_CORRELATION),
        ),
        "account_not_admitted.json": mocktext.example(
            "Un compte local du fournisseur d'identité que Waterfall n'a pas créé, sans adresse, "
            "lit son compte : il n'est pas admis, et ne l'est pas davantage à la requête "
            "suivante ; le front ne le renvoie pas à une connexion qui bouclerait "
            "(WF-ADM-0180, WF-SEC-0020).",
            problem("ACCOUNT_NOT_ADMITTED", 401, NOT_ADMITTED_CORRELATION),
        ),
        "avatar_malformed.json": mocktext.example(
            "Un avatar déposé avec un corps vide : refusé comme une requête mal formée, l'avatar "
            "du compte reste celui qu'il était (WF-ADM-0080).",
            problem("MALFORMED_REQUEST", 400, MALFORMED_CORRELATION),
        ),
        "avatar_too_large.json": mocktext.example(
            f"Un avatar de plus de {avatar_mio} Mio déposé alors que l'installation borne les "
            f"siens à {avatar_mio} Mio (avatar_max_bytes) : refusé avant d'être lu, l'avatar du "
            f"compte reste celui qu'il était (WF-ADM-0080, WF-CMP-0020).",
            problem("FILE_TOO_LARGE", 413, TOO_LARGE_CORRELATION),
        ),
        "project_update_not_contributor.json": mocktext.example(
            "Le libellé du projet témoin modifié par un compte qui peut le consulter — il lit "
            "tous les projets — sans en être contributeur : refusé, la qualité nommée, "
            "is_contributor ; rien n'est écrit (WF-PRJ-0060, WF-ADM-0110).",
            quality_refused("NOT_CONTRIBUTOR", "is_contributor", CONTRIBUTOR_CORRELATION),
        ),
        "access_roles_number_invalid.json": mocktext.example(
            "Les rôles d'habilitation demandés avec holder_count_min=beaucoup : la borne n'est "
            "pas un entier, désignée par /query/holder_count_min ; rien n'est lu (WF-IHM-0130).",
            field_refused("/query/holder_count_min", "NUMBER_INVALID", NUMBER_CORRELATION),
        ),
        "access_roles_date_invalid.json": mocktext.example(
            "Les rôles d'habilitation demandés avec created_at_from=hier : l'instant n'est pas "
            "une date, désigné par /query/created_at_from ; rien n'est lu (WF-IHM-0130).",
            field_refused("/query/created_at_from", "DATE_INVALID", INSTANT_CORRELATION),
        ),
        "resource_role_calendar_unknown.json": mocktext.example(
            "Un rôle créé rattaché à un calendrier que le référentiel n'a pas : refusé sur "
            "/calendar_id ; rien n'est écrit (WF-REF-0090).",
            field_refused("/calendar_id", "UNKNOWN_CALENDAR", CALENDAR_CORRELATION),
        ),
        "import_actual_costs_wbs_invalid.json": mocktext.example(
            f"Une variante de l'extraction d'avril : la ligne {_april_row()} porte l'élément "
            f"d'OTP « {MALFORMED_ELEMENT} », sans rien avant la barre oblique, qui n'a pas la "
            f"forme d'un code projet suivi d'un code de sous-projet : rejetée, l'élément nommé "
            f"tel que le fichier le porte ; les lignes lues avant elle sont ajoutées "
            f"(WF-CRE-0020, WF-INTF-0140, WF-INTF-0080).",
            import_wbs_invalid(),
        ),
        "import_remaining_ambiguous_label.json": mocktext.example(
            f"Une variante du reste à engager importé aujourd'hui : la ligne "
            f"{mockexchanges.FIRST_ROW + 1} de l'onglet « {tab} » désigne sa tâche par « "
            f"{AMBIGUOUS_LABEL} », que portent deux tâches — celle de l'installation et celle du "
            f"volume du portefeuille — alors que l'onglet « Tâches » ne la connaît pas : rejetée, "
            f"le libellé et les deux tâches nommés par leur lignée ; l'autre ligne change de "
            f"sous-projet (WF-INTF-0080, WF-INTF-0120).",
            import_ambiguous_label(),
        ),
    }
