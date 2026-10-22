# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The Kanban of the witness: the gestures of its cards, and what each gesture answers (US-0540).

Each task of the three columns of `listStartableTasks` lists the gestures its card offers, each
available or not with the conditions it misses, and the progress it sends (`KanbanTask`,
WF-IHM-0090): the front deduces none of them from the nature of the task or from its lines. The
answers of the gestures are writes of the core (``wftools.mockwrites``), the difference of two
readings of the whole structure, never written by hand (#287); a gesture on a node another write
renders follows that write, one version further (#421).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockcore import READ_ON
from wftools.mockids import universe
from wftools.mockwitness import CORE, FIRST_ITEM, Link, N
from wftools.mockwrites import SITE_DELAY, amended, core_write, on_task, totals_said

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue
    from wftools.mockwitness import Task

STARTED_TASK, COMPLETED_MILESTONE = N.MOUNTING, N.FACTORY_ACCEPTANCE
REOPENED_TASK, REOPENED_MILESTONE = N.DETAILED_STUDIES, N.STUDIES_RECEIVED
"""The tasks of the core the gestures are made on: the mounting on site, not started, started
today; the factory acceptance, a milestone without a line, completed today; the detailed studies,
completed, reopened; the reception of the studies, a completed milestone, reopened."""

REFUSAL_CORRELATION = universe(1540)


def commands(facet: JsonObject, *, bears_lines: bool) -> list[JsonValue]:
    """Return the gestures of a card, in the order of `KanbanCommand`, for a caller who may all.

    A task not started that is no milestone starts; a milestone never does (WF-PLA-0050). A task
    not completed completes from the Kanban if it is a milestone or started, and bears no line
    but provision lines — otherwise the remaining it is sent to completes it (WF-RAE-0030,
    WF-RAE-0040). A completed task reopens: a milestone to not started, any other to started.
    The witness is in progress and no background task runs: no condition of the entry of the
    remaining misses.
    """
    progress, milestone = facet["progress"], facet["is_milestone"]
    entries: list[tuple[str, list[str], str | None]] = []
    if progress == "not_started" and not milestone:
        entries.append(("start", [], "started"))
    if progress != "completed":
        missing = ["task_is_milestone"] if progress == "not_started" and not milestone else []
        missing += ["task_without_lines"] if bears_lines else []
        entries.append(("complete", missing, "completed"))
    else:
        entries.append(("reopen", [], "not_started" if milestone else "started"))
    if progress != "completed" and bears_lines:
        entries.append(("enter_remaining", [], None))
    return [
        {
            "command": command,
            "is_available": not missing,
            "missing_conditions": cast("list[JsonValue]", missing),
            "progress": sent,
        }
        for command, missing, sent in entries
    ]


def kanban(rows: list[mockcore.Row]) -> JsonObject:
    """Return the answer of listStartableTasks, each task with the gestures of its card.

    A task bears lines when one of its lines is not a provision line, which the server computes
    (`EstimateLine.is_computed`): a provision line holds no task from completing (WF-PLA-0050).
    """
    bearers = {
        row.parent
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
        and not cast("JsonObject", row.node["estimate_line"])["is_computed"]
    }
    numbers = {cast("str", row.node["node_id"]): row.number for row in rows}
    answer = mockcore.startable(rows)
    return {
        column: [
            {
                **node,
                "available_commands": commands(
                    cast("JsonObject", node["task"]),
                    bears_lines=numbers[cast("str", node["node_id"])] in bearers,
                ),
            }
            for node in cast("list[JsonObject]", nodes)
        ]
        for column, nodes in answer.items()
    }


# --- The gestures, made on the core ------------------------------------------------------------


def linked() -> tuple[Task, ...]:
    """Return the core as `predecessor_set` leaves it: the mounting two days after acceptance."""
    links = (Link(COMPLETED_MILESTONE, lag=SITE_DELAY),)
    return amended(CORE, on_task(STARTED_TASK, links=links))


def attached() -> tuple[Task, ...]:
    """Return the core as `task_attached` leaves it: the acceptance bearing the post 1.1."""
    return amended(CORE, on_task(COMPLETED_MILESTONE, bears=FIRST_ITEM))


def task_started() -> JsonObject:
    """Return what setTaskProgress answers when the mounting on site is started today.

    It follows the predecessors set anew (`predecessor_set`), which wrote the mounting: one
    version further (#421). Its dates do not move — the day of the gesture is its date of start
    (`started_on`, WF-PLA-0130) —, and its summary is started with it.
    """
    roots = amended(linked(), on_task(STARTED_TASK, progress="started", declared_on=READ_ON))
    return core_write(roots, [STARTED_TASK], following=linked())


def milestone_completed() -> JsonObject:
    """Return what setTaskProgress answers when the factory acceptance is completed today.

    A milestone without a line goes from not started to completed by a gesture of the Kanban, at
    the date entered (WF-RAE-0030, WF-PLA-0050). It follows the post attached (`task_attached`),
    which wrote the milestone: one version further (#421).
    """
    gesture = on_task(COMPLETED_MILESTONE, progress="completed", declared_on=READ_ON)
    return core_write(amended(attached(), gesture), [COMPLETED_MILESTONE], following=attached())


def task_reopened() -> JsonObject:
    """Return what setTaskProgress answers when the detailed studies, completed, are reopened."""
    return core_write(amended(CORE, on_task(REOPENED_TASK, progress="started")), [REOPENED_TASK])


def milestone_reopened() -> JsonObject:
    """Return what setTaskProgress answers when the reception of the studies is reopened.

    A completed milestone reopened is not started, its date of completion erased: the one case
    a task goes back to that state (WF-RAE-0030).
    """
    roots = amended(CORE, on_task(REOPENED_MILESTONE, progress="not_started"))
    return core_write(roots, [REOPENED_MILESTONE])


def reopen_not_started_refused() -> JsonObject:
    """Return what setTaskProgress answers to the detailed studies sent back to not started.

    No gesture brings a task but a milestone back to not started (WF-RAE-0030): refused, the
    condition named; nothing is written.
    """
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "completed_milestone"},
        "correlation_id": REFUSAL_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def _written(answer: JsonObject) -> JsonObject:
    """Return the facet of the one task a gesture writes."""
    [node] = cast("list[JsonObject]", answer["nodes"])
    return cast("JsonObject", node["task"])


def _ancestor(answer: JsonObject, number: int) -> JsonObject:
    """Return the facet of a summary a gesture renders above the task it writes."""
    [node] = [
        each
        for each in cast("list[JsonObject]", answer["ancestors"])
        if each["node_id"] == universe(number)
    ]
    return cast("JsonObject", node["task"])


def _on(value: JsonValue) -> str:
    """Say the day of an instant of work, or of a date, as French does."""
    text = value if isinstance(value, str) else cast("dict[str, str]", value)["date"]
    return mocktext.day(date.fromisoformat(text))


def _lines(rows: dict[int, mockcore.Row], number: int) -> list[mockcore.Row]:
    """Return the lines of a task of the core, in the order of the plan."""
    return [
        row for row in rows.values() if row.parent == number and row.kind == mockcore.ESTIMATE_LINE
    ]


def _labels(lines: list[mockcore.Row]) -> str:
    """Say lines by their labels: « A » et « B »."""
    return mocktext.listed([f"« {row.label} »" for row in lines])


def _subproject(lines: list[mockcore.Row]) -> str:
    """Say the subproject some lines all bear."""
    [label] = {
        cast("str", cast("JsonObject", row.node["estimate_line"])["subproject_label"])
        for row in lines
    }
    return label


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the gestures of the Kanban, by file name."""
    rows = {row.number: row for row in mockcore.current()}
    facets = {
        number: cast("JsonObject", row.node["task"])
        for number, row in rows.items()
        if row.kind == mockcore.TASK
    }
    started, completed = task_started(), milestone_completed()
    reopened, back = task_reopened(), milestone_reopened()
    day = mocktext.day(READ_ON)
    mounting, studies = _written(started), _written(reopened)
    mounted = _lines(rows, STARTED_TASK)
    was = cast("JsonObject", facets[N.STUDIES]["physical_progress"])["value"]
    now = cast("JsonObject", _ancestor(reopened, N.STUDIES)["physical_progress"])["value"]
    return {
        "task_started.json": mocktext.example(
            f"Le « {rows[STARTED_TASK].label} », non démarré, démarré depuis le Kanban le {day}, "
            f"date du geste (started_on) : ses dates ne bougent pas, du {_on(mounting['start'])} "
            f"au {_on(mounting['finish'])} ; une version de plus que celle que la saisie de ses "
            f"prédécesseurs (predecessor_set) lui laissait. Avec lui, sa récapitulative "
            f"« {rows[N.INSTALLATION].label} », démarrée à son tour, et {totals_said(started)}, "
            f"inchangés. Ses lignes, {_labels(mounted)}, ne sont ni écrites ni rendues ; portées "
            f"au sous-projet « {_subproject(mounted)} », qui a reçu des coûts réels, elles ne "
            f"nomment plus `estimate_line.subproject_id` parmi les champs qu'elles acceptent : la "
            f"grille relit les lignes de la tâche (WF-RAE-0030, WF-PLA-0130, WF-PRJ-0050, "
            f"#1154).",
            started,
        ),
        "milestone_completed.json": mocktext.example(
            f"Le jalon « {rows[COMPLETED_MILESTONE].label} », sans ligne de devis, terminé "
            f"depuis le Kanban le {day}, à la date saisie (completed_on), sans avoir démarré ; sa "
            f"date prévue reste au {_on(facets[COMPLETED_MILESTONE]['finish'])}. Son "
            f"prédécesseur, le « {rows[N.WIRING].label} », est encore démarré : rien ne termine "
            f"un jalon seul, et le Kanban, qui signale ceux dont les prédécesseurs sont terminés, "
            f"n'en fait pas une condition. Une version de plus que celle que le rattachement au "
            f"poste (task_attached) lui laissait ; avec lui, sa récapitulative "
            f"« {rows[N.CONTROL_STATION].label} », et {totals_said(completed)} (WF-RAE-0030, "
            f"WF-PLA-0050, WF-PLA-0130).",
            completed,
        ),
        "task_reopened.json": mocktext.example(
            f"Les « {rows[REOPENED_TASK].label} », terminées le "
            f"{_on(facets[REOPENED_TASK]['completed_on'])}, rouvertes depuis le Kanban : "
            f"démarrées de nouveau, depuis le {_on(studies['started_on'])} (started_on), leur "
            f"date de terminaison effacée, leur fin passée (finish_overdue) ; une version de "
            f"plus. Avec elles, la récapitulative « {rows[N.STUDIES].label} », son avancement "
            f"physique à {now} au lieu de {was}, et {totals_said(reopened)}. Leur ligne, "
            f"{_labels(_lines(rows, REOPENED_TASK))}, accepte de nouveau la réestimation "
            f"(remaining_entry) : la grille la relit (WF-RAE-0030, WF-IND-0060, #1154).",
            reopened,
        ),
        "milestone_reopened.json": mocktext.example(
            f"Le jalon « {rows[REOPENED_MILESTONE].label} », terminé le "
            f"{_on(facets[REOPENED_MILESTONE]['completed_on'])}, rouvert depuis le Kanban : il "
            f"redevient non démarré, seul cas où une tâche revient à cet état, sa date de "
            f"terminaison effacée ; une version de plus. Avec lui, sa récapitulative "
            f"« {rows[N.STUDIES].label} », et {totals_said(back)} (WF-RAE-0030).",
            back,
        ),
        "task_reopen_not_started_refused.json": mocktext.example(
            f"Les « {rows[REOPENED_TASK].label} », terminées, envoyées à l'état non démarré : "
            f"seul un jalon terminé y revient, et aucune commande ne fait passer une autre tâche "
            f"à cet état — leur carte ne rouvre que vers l'état démarré (available_commands). Le "
            f"geste est refusé, la condition nommée ; rien n'est écrit (WF-RAE-0030).",
            reopen_not_started_refused(),
        ),
    }
