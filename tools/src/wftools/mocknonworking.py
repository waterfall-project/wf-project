# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A date of a manual task on a day without hours of work: refused entered, kept imported.

« Une date saisie sur un jour sans aucune heure travaillée au calendrier applicable est refusée,
et le refus nomme le jour travaillé suivant ; rien n'est écrit. L'import d'un fichier MS Project
garde une telle date telle quelle, et le compte rendu la signale » (WF-PLA-0020; the decision of
the author of 2026-10-22, #1271, #1289, which replaces the day kept at no hour of #1244). Both
say one motive, `NON_WORKING_DAY`, with the same parameters — the date, and the next working day
on the calendar of the task —, so that the front says the entry refused and the line of the
report by one sentence. The day is judged on the applicable calendar of the commissioning, as
``mockdating`` dates it, never written by hand: the entry on the Saturday before its start, and
the same date in a planning exported today and imported back, the commissioning made manual in
it, which the report keeps and signals. A task created in manual mode with the same start is
refused alike (#1345): « une date saisie » is not bound to the modification, and a task created
without any labour line is judged on the default calendar (WF-PLA-0010). Sent on the days of work
that follow, without their hours, it is created, the server completing the hours on that calendar
(``node_created_manual``; the decision of the author of 2026-11-01, F-03, #1769).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mockdating, mocktext
from wftools.mockexchanges import main_structure, opened_on
from wftools.mockids import hex_identifier, universe
from wftools.mockstructure import described
from wftools.mockwitness import CORE, N, Task, default_calendar, fixture
from wftools.mockwrites import amended, core_write

if TYPE_CHECKING:
    from wftools.mockcalendar import Calendar
    from wftools.mockstructure import JsonObject, JsonValue

CODE = "NON_WORKING_DAY"

SATURDAY = date(2026, 12, 19)
"""The start entered on the commissioning, manual, and imported: the Saturday before the Monday
it starts on today."""

REFUSED_CORRELATION = universe(1542)
CREATED_CORRELATION = universe(1563)
PLANNING_START_CORRELATION = universe(1593)

CREATED_LABEL = "Réception provisoire sur site"
"""The task created in manual mode with its start on SATURDAY, under the installation on site."""

CREATED_MANUAL = 594
"""The node of the task created in manual mode on the days of work after SATURDAY (#1769)."""

_WEEKDAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def said(value: date) -> str:
    """Write a day with its name, as the front says the refusal: le samedi 19 décembre 2026."""
    return f"le {_WEEKDAYS[value.weekday()]} {mocktext.day(value)}"


def calendar() -> Calendar:
    """Return the applicable calendar of the commissioning, that of the role of its labour."""
    return mockdating.schedule(described())[N.COMMISSIONING].calendar


def judged(day: date, on: Calendar | None = None) -> JsonObject | None:
    """Return the parameters of the motive a date carries, or None on a day of work.

    A day the calendar of the task grants no hour of work names the next one that grants some:
    the day the entry may take (WF-PLA-0020, WF-PLA-0010). The calendar is the commissioning's
    unless another is given.
    """
    on = calendar() if on is None else on
    if on.hours_on(day) > 0:
        return None
    return {"date": day.isoformat(), "next_working_day": on.next_working_day(day).isoformat()}


def _judged(day: date, on: Calendar | None = None) -> JsonObject:
    params = judged(day, on)
    if params is None:
        message = f"{day} is a day of work on the calendar of the commissioning"
        raise ValueError(message)
    return params


def task_date_non_working_day() -> JsonObject:
    """Return what updateTaskFacet answers to the start of the commissioning sent on SATURDAY.

    Refused on its field, the next working day named; nothing is written, and the hours, none
    sent, are not judged (#1271).
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/start/date", "code": CODE, "params": _judged(SATURDAY)}],
        "correlation_id": REFUSED_CORRELATION,
    }


def node_create_non_working_day() -> JsonObject:
    """Return what createNode answers to a task created in manual mode with its start on SATURDAY.

    The task has no labour line yet: its applicable calendar is the default one (WF-PLA-0010),
    which grants no hour on a Saturday either. Refused on the field of the facet sent, the next
    working day named; nothing is created (#1345).
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/task/start/date",
                "code": CODE,
                "params": _judged(SATURDAY, default_calendar()),
            }
        ],
        "correlation_id": CREATED_CORRELATION,
    }


def created_manual_dates() -> tuple[date, date]:
    """Return the dates the task created in manual mode is sent with, without their hours.

    The day of work that follows SATURDAY on the default calendar, the one the refusal names, and
    the second day of work after it: three days of work.
    """
    on = default_calendar()
    start = on.next_working_day(SATURDAY)
    finish = on.next_working_day(on.next_working_day(start))
    return start, finish


def created_manual() -> Task:
    """Return the task created in manual mode at the dates sent, not started (WF-RAE-0030)."""
    return Task(
        CREATED_MANUAL, CREATED_LABEL, manual=created_manual_dates(), progress="not_started"
    )


def node_created_manual() -> JsonObject:
    """Return what createNode answers to that task created on days of work, without hours.

    Its start and finish are sent by their date alone (`WorkInstantWrite`): the server completes
    their hours on its calendar, the default one, the task bearing no line (WF-PLA-0010), and
    the answer renders them completed (#1769).
    """

    def add(each: Task) -> Task:
        if each.number != N.INSTALLATION:
            return each
        return replace(each, children=(*each.children, created_manual()))

    return core_write(amended(CORE, add), [CREATED_MANUAL])


# --- The same date imported from MS Project ----------------------------------------------------

IMPORTED_IMPORT, IMPORTED_TASK = hex_identifier(0xA18), universe(950)

SUBMITTED, ANALYSED, EXPIRES = (
    "2026-06-03T11:02:05Z",
    "2026-06-03T11:03:00Z",
    "2026-06-04T11:03:00Z",
)
"""When the import was opened today, analysed, and until when it applies (WF-ARC-0100)."""


def structure_start_non_working_day() -> JsonObject:
    """Return what updateCostStructure answers to the planning start sent on SATURDAY.

    The structure has no calendar of its own: its planning start is judged on the default one,
    that of a task without a labour line (WF-PLA-0010), as a date entered is. Refused on its
    field, the next working day named; nothing is written (WF-PLA-0020).
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/planning_start_on",
                "code": CODE,
                "params": _judged(SATURDAY, default_calendar()),
            }
        ],
        "correlation_id": PLANNING_START_CORRELATION,
    }


def imported_dates() -> tuple[date, date]:
    """Return the dates of the commissioning in the file: SATURDAY, and the finish it has today."""
    finish = mockdating.schedule(described())[N.COMMISSIONING].finish.day
    return SATURDAY, finish


def calendars_ignored() -> JsonObject:
    """Return the calendars the file carries, ignored: those the export wrote of each task.

    The export writes its applicable calendar as the calendar of each task (WF-INTF-0050); the
    import never reads one (WF-INTF-0040). They are named in the order the reference reads them.
    """
    used = {dated.calendar.calendar_id for dated in mockdating.schedule(described()).values()}
    labels = [
        entry["label"]
        for entry in cast("list[dict[str, str]]", fixture("calendars")["items"])
        if entry["calendar_id"] in used
    ]
    if len(labels) != len(used):
        message = "a task of the witness is dated on a calendar the reference does not list"
        raise ValueError(message)
    return {"kind": "calendars", "count": len(labels), "labels": cast("list[JsonValue]", labels)}


def signals(lineage: str, label: str, dates: tuple[date, date]) -> list[JsonValue]:
    """Return the signals of the start and finish of a task in the file, one per column.

    A column whose day has no hour of work is signalled by the motive and the parameters of the
    refusal of the entry. The signal follows the cell, not the day, as the refusal follows the
    field: a milestone whose start and finish fall on the same such day is signalled twice, like
    a task whose two dates do (#1271).
    """
    found: list[JsonValue] = []
    for column, day in zip(("start", "finish"), dates, strict=True):
        params = judged(day)
        if params is not None:
            found.append(
                {
                    "lineage_id": lineage,
                    "label": label,
                    "column": column,
                    "code": CODE,
                    "params": params,
                }
            )
    return found


def import_report() -> JsonObject:
    """Return the report of the planning exported today, the commissioning made manual in it.

    A round trip on the identifiers the export wrote (WF-INTF-0060): nothing differs but the
    commissioning, its mode and its start, which the file puts on SATURDAY. The date is kept as
    the file carries it, and the report signals it, the next working day named (WF-PLA-0020).
    """
    rows = {row.number: row for row in mockcore.current()}
    node = cast("dict[str, Any]", rows[N.COMMISSIONING].node)["task"]
    first, last = imported_dates()
    fields: list[JsonValue] = []
    if node["scheduling_mode"] != "manual":
        fields.append("scheduling_mode")
    fields += [
        column
        for column, day in (("start", first), ("finish", last))
        if node[column]["date"] != day.isoformat()
    ]
    lineage, label = mockcore.lineage(N.COMMISSIONING), rows[N.COMMISSIONING].label
    read = len(mockdating.tasks_in_order(described()))
    return {
        "format_version": None,
        "read_count": read,
        "unchanged_count": read - 1,
        "rejected": [],
        "refusals": [],
        "differences": [
            {
                "change": "updated",
                "target": "task",
                "lineage_id": lineage,
                "label": label,
                "predecessor_label": None,
                "fields": fields,
            }
        ],
        "ignored": [calendars_ignored()],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": signals(lineage, label, (first, last)),
        "requires_confirmation_reasons": [],
    }


def import_planning_non_working_day() -> JsonObject:
    """Return what getImport answers of that planning, analysed today, on the main structure."""
    return {
        "import_id": IMPORTED_IMPORT,
        "kind": "ms_project_schedule",
        "filename": "planning-poste-de-commande.xml",
        **opened_on(main_structure()),
        "status": "analysed",
        "created_at": SUBMITTED,
        "expires_at": EXPIRES,
        "report": import_report(),
        "task": {
            "task_id": IMPORTED_TASK,
            "kind": "import_analysis",
            "status": "succeeded",
            "progress": 100,
            "submitted_at": SUBMITTED,
            "finished_at": ANALYSED,
            "problem": None,
            "result_url": None,
        },
    }


# --- The examples ------------------------------------------------------------------------------


def examples() -> dict[str, JsonObject]:
    """Return the refusals of a date entered and of a task created, and the import, by name."""
    refused = task_date_non_working_day()
    [field] = cast("list[dict[str, dict[str, str]]]", refused["fields"])
    following = date.fromisoformat(field["params"]["next_working_day"])
    commissioning = {row.number: row.label for row in mockcore.current()}[N.COMMISSIONING]
    created = node_create_non_working_day()
    [creation] = cast("list[dict[str, dict[str, str]]]", created["fields"])
    created_following = date.fromisoformat(creation["params"]["next_working_day"])
    imported = import_planning_non_working_day()
    planning = structure_start_non_working_day()
    [start] = cast("list[dict[str, dict[str, str]]]", planning["fields"])
    start_following = date.fromisoformat(start["params"]["next_working_day"])
    report = cast("dict[str, list[dict[str, Any]]]", imported["report"])
    [ignored] = report["ignored"]
    start, finish = created_manual_dates()
    written = node_created_manual()
    [task] = [
        node
        for node in cast("list[dict[str, Any]]", written["nodes"])
        if node["node_id"] == universe(CREATED_MANUAL)
    ]
    return {
        "node_created_manual.json": mocktext.example(
            f"La même tâche « {CREATED_LABEL} » créée en mode manuel sous l'« Installation sur "
            f"site », son début envoyé {said(start)} et sa fin {said(finish)}, par leur seule "
            f"date, sans heures (WorkInstantWrite) : le serveur les complète sur le calendrier de "
            f"la tâche, le calendrier par défaut, la tâche ne portant aucune ligne — le début à "
            f"{task['task']['start']['hours']} h, au début de son jour, la fin à "
            f"{task['task']['finish']['hours']} h, au bout des heures du jour. Non démarrée, à sa "
            f"première version ; avec elle, ses ancêtres et les totaux de la structure "
            f"(WF-PLA-0020, WF-PLA-0010, #1769).",
            written,
        ),
        "task_date_non_working_day.json": mocktext.example(
            f"Le début de la « {commissioning} », en mode manuel (task_mode_changed), envoyé "
            f"{said(SATURDAY)}, un jour sans heure travaillée au calendrier de la tâche : la date "
            f"est refusée sur son champ, et le refus nomme le jour travaillé suivant, "
            f"{said(following)} ; rien n'est écrit (WF-PLA-0020, WF-PLA-0010, #1271).",
            refused,
        ),
        "node_create_non_working_day.json": mocktext.example(
            f"Une tâche « {CREATED_LABEL} » créée en mode manuel sous l'« Installation sur "
            f"site », son début envoyé {said(SATURDAY)} : sans ligne de main-d'œuvre, la tâche "
            f"est sur le calendrier par défaut, qui n'accorde aucune heure ce jour-là. La date "
            f"est refusée sur son champ, comme à la modification (task_date_non_working_day), et "
            f"le refus nomme le jour travaillé suivant, {said(created_following)} ; rien n'est "
            f"créé (WF-PLA-0020, WF-PLA-0010, #1345).",
            created,
        ),
        "structure_start_non_working_day.json": mocktext.example(
            f"La date de début de planning de la structure principale du projet témoin envoyée "
            f"{said(SATURDAY)} : la structure n'a pas de calendrier propre, et le calendrier par "
            f"défaut, celui d'une tâche sans ligne de main-d'œuvre, n'accorde aucune heure ce "
            f"jour-là. La date est refusée sur son champ, comme une date saisie "
            f"(task_date_non_working_day), et le refus nomme le jour travaillé suivant, "
            f"{said(start_following)} ; rien n'est écrit (WF-PLA-0020, WF-PLA-0010).",
            planning,
        ),
        "import_planning_non_working_day.json": mocktext.example(
            f"L'import d'un planning MS Project lu aujourd'hui à {mocktext.hour(SUBMITTED)} et "
            f"analysé à {mocktext.hour(ANALYSED)}, une variante qu'imports ne reprend pas : le "
            f"planning de la structure principale du projet témoin exporté aujourd'hui, la « "
            f"{commissioning} » passée en mode "
            f"manuel et commencée {said(SATURDAY)}, un jour sans heure travaillée à son "
            f"calendrier. Un aller-retour sur les identifiants que l'export a écrits : seule la "
            f"tâche diffère ; sa date est gardée telle que le fichier la porte, et le compte rendu "
            f"la signale, nommant {said(following)} ; les {ignored['count']} calendriers du "
            f"fichier sont ignorés et dits (WF-PLA-0020, WF-INTF-0040, WF-INTF-0080, #1271).",
            imported,
        ),
    }
