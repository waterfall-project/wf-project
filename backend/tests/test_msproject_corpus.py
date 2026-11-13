# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The corpus of MS Project, its dates against the engine's.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1430/L3
writes its tests here ("Les tests du back"). Without MS Project, a database or a browser
(WF-QUA-0080): each planning of ``fixtures/msproject/`` its manifest dates is read, given to the
engine with its tasks, its links, the calendars of its tasks and its constants, and each start and
each finish the engine computes is compared with the one MS Project computed, read on the calendar
of its task — a file deposited later enters the test by its entry in the manifest, without a
change here. A task is given as the import gives it (WF-INTF-0040): manual in the file, or bearing
a date constraint, at the dates of the file; a summary always automatic. A summary the file
carries in manual mode keeps there the dates entered on it, which Waterfall does not: it is
compared apart, its dates derived from its subordinates (``DERIVED``). The cases the body of
WF-QUA-0080 cites, by the identifiers the README of the corpus gives them, are each declared by a
file of the manifest.
"""

import json
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_OID, UUID, uuid5

import pytest
from lxml import etree

from waterfall.core.exchanges.interface import hardened_parser
from waterfall.core.planning.msproject import (
    DATE_CONSTRAINTS,
    MsProject,
    calendar_of,
    calendars_of,
    constants_of,
    duration_of,
    lag_of,
    read_project,
    write_project,
)
from waterfall.core.planning.scheduling import (
    Link,
    Schedule,
    Structure,
    Task,
    WorkInstant,
    schedule,
)
from waterfall.core.planning.scheduling import engine as dating_engine

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "msproject"
MANIFEST: dict[str, Any] = json.loads((CORPUS / "corpus.json").read_text(encoding="utf-8"))
FILES: list[dict[str, Any]] = MANIFEST["files"]
DATED = [entry for entry in FILES if entry.get("dating", True)]

# The cases of the body of WF-QUA-0080, by the identifiers of the README of the corpus: « les
# quatre types de liaison, des décalages positifs et négatifs dans chaque unité, en temps écoulé
# et en pourcentage, des calendriers dont les journées n'ont pas toutes la même durée, des tâches
# récapitulatives, des jalons et des tâches en mode manuel » — the durations in each unit, the
# critical path, and the cases the README adds for the import (the constraints, what is ignored,
# other constants, the horizon), which the README asks of the corpus as well.
CASES: dict[str, tuple[str, ...]] = {
    "the four types of link": ("link_fs", "link_ss", "link_ff", "link_sf"),
    "lags in each unit, positive and negative": (
        "lag_positive_d",
        "lag_negative_d",
        "lag_min",
        "lag_h",
        "lag_w",
        "lag_mo",
        "lag_negative_w",
    ),
    "lags in elapsed time": (
        "lag_emin",
        "lag_eh",
        "lag_ed",
        "lag_ew",
        "lag_emo",
        "lag_elapsed_over_weekend",
    ),
    "lags in percent": ("lag_percent",),
    "durations in each unit": (
        "duration_min",
        "duration_h",
        "duration_d",
        "duration_w",
        "duration_mo",
        "duration_elapsed",
        "sixteen_hours_standard",
    ),
    "calendars whose days are not all as long": (
        "calendar_uneven",
        "calendar_4x10",
        "calendar_half_day",
        "calendar_four_hours",
        "task_calendar_chain",
    ),
    "summary tasks": ("summary", "summary_nested", "summary_single_milestone"),
    "milestones": ("milestone", "milestone_linked_ff"),
    "tasks in manual mode": (
        "manual",
        "manual_with_auto_successor",
        "manual_conflict_fs",
        "manual_conflict_ss",
        "manual_non_working_day",
        "manual_summary",
    ),
    "the critical path": (
        "two_branches",
        "float_equals_gap",
        "summary_critical",
        "summary_without_float",
    ),
    "date constraints": ("constraint_snet", "constraint_mfo", "constraint_fnlt"),
    "what the import ignores": (
        "resources_ignored",
        "assignments_ignored",
        "resource_calendar_ignored",
        "progress_ignored",
        "costs_ignored",
        "custom_fields_ignored",
    ),
    "other constants": ("constants_7_35_20",),
    "the horizon": ("horizon_exceeded",),
}

# The cases no planning of the corpus declares, each with the issue that says why: the corpus
# lacks a file for it, the text of the specification is not in question.
MISSING: dict[str, str] = {}

# The summaries the corpus carries in manual mode, by file: MS Project keeps the dates entered on
# them, Waterfall always computes a summary from its subordinates, and the import makes it
# automatic and signals it (``SUMMARY_TASK_DERIVED``, WF-INTF-0040). Not compared with the dates of
# the file, they are affirmed apart; no other task is left out of the comparison.
DERIVED: dict[str, tuple[str, ...]] = {"06-manual-tasks.xml": ("Manuelle 4",)}


def _ids(project: MsProject) -> dict[int, UUID]:
    """Give each task of a file an identifier of the engine, drawn from its ``UID``."""
    return {task.uid: uuid5(NAMESPACE_OID, str(task.uid)) for task in project.tasks}


def dated(file: str) -> tuple[MsProject, Schedule]:
    """Date a file of the corpus by the engine, as the import gives it its tasks.

    The engine is given the tasks of the file in its order, their parent, their mode — a summary
    always automatic, a leaf manual when the file says so or when it bears a date constraint —,
    their duration and the calendar of each in the file, the dates of the file for a task in
    manual mode; the links with their type and their lag; the start of the project and the
    constants of the file.
    """
    project = read_project((CORPUS / file).read_bytes()).project
    assert project.start is not None, f"{file} says no start"
    calendars = calendars_of(project)
    constants = constants_of(project)
    parents = project.parents()
    summaries = {uid for uid in parents.values() if uid is not None}
    ids = _ids(project)
    tasks: list[Task] = []
    for each in project.tasks:
        calendar = calendar_of(project, calendars, each)
        assert calendar is not None, f"{file}: {each.name} has no calendar"
        frozen = each.manual or each.constraint in DATE_CONSTRAINTS
        manual = frozen and each.uid not in summaries
        assert not manual or (each.start is not None and each.finish is not None)
        parent = parents[each.uid]
        tasks.append(
            Task(
                ids[each.uid],
                None if parent is None else ids[parent],
                "manual" if manual else "automatic",
                duration_of(each, constants),
                calendar.calendar,
                calendar.instant(each.start) if manual and each.start else None,
                calendar.instant(each.finish) if manual and each.finish else None,
            )
        )
    links = tuple(
        Link(ids[link.predecessor_uid], ids[each.uid], link.link_type, lag_of(link, constants))
        for each in project.tasks
        for link in each.predecessors
    )
    return project, schedule(Structure(tuple(tasks), links, project.start.date(), constants))


def mismatches(file: str) -> list[str]:
    """Date a file of the corpus by the engine; name each date that differs from MS Project's.

    A date of the file is read on the calendar of its task. A summary in manual mode the test
    names (``DERIVED``) is left out, and only it.
    """
    project, dates = dated(file)
    calendars = calendars_of(project)
    ids = _ids(project)
    found: list[str] = []
    for each in project.tasks:
        if each.name in DERIVED.get(file, ()):
            continue
        calendar = calendar_of(project, calendars, each)
        assert calendar is not None
        assert each.start is not None
        assert each.finish is not None
        placed = dates.tasks[ids[each.uid]]
        for end, expected, computed in (
            ("start", calendar.instant(each.start), placed.start),
            ("finish", calendar.instant(each.finish), placed.finish),
        ):
            if expected != computed:
                found.append(
                    f"{each.uid} « {each.name} » {end}: MS Project {expected.day} at "
                    f"{expected.hours} h of work, Waterfall {computed.day} at {computed.hours} h"
                )
    return found


@pytest.mark.requirement("WF-QUA-0080-A")
@pytest.mark.requirement("WF-INTF-0050-A")
@pytest.mark.requirement("WF-INTF-0060-A")
@pytest.mark.parametrize("entry", DATED, ids=[entry["file"] for entry in DATED])
def test_each_planning_of_the_corpus_is_dated_by_the_engine_as_ms_project_dated_it(
    entry: dict[str, Any],
) -> None:
    assert mismatches(entry["file"]) == []


def _manual_summaries(project: MsProject) -> tuple[str, ...]:
    """Name the summaries a file carries in manual mode."""
    parents = project.parents()
    summaries = {uid for uid in parents.values() if uid is not None}
    return tuple(each.name for each in project.tasks if each.manual and each.uid in summaries)


@pytest.mark.requirement("WF-QUA-0080-A")
def test_the_only_tasks_left_out_of_the_comparison_are_the_summaries_in_manual_mode() -> None:
    # Only a summary in manual mode is left out, and each one the corpus carries is named.
    carried: dict[str, tuple[str, ...]] = {}
    for entry in DATED:
        names = _manual_summaries(read_project((CORPUS / entry["file"]).read_bytes()).project)
        if names:
            carried[entry["file"]] = names
    assert carried == DERIVED


@pytest.mark.requirement("WF-QUA-0080-A")
@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_summary_in_manual_mode_is_dated_from_its_subordinates_not_at_the_file_dates() -> None:
    # « Une récapitulative en mode manuel dans le fichier est importée en mode automatique, et le
    # compte rendu la signale avec l'écart de dates. » MS Project keeps the dates entered on
    # « Manuelle 4 », a single day, the 16th of November 2009; Waterfall dates it from its
    # subordinates, from the 10th, where « Manuelle 7 » starts, to the 19th, where « Auto 2 »
    # finishes at 3 h of work.
    file = "06-manual-tasks.xml"
    project, dates = dated(file)
    ids = _ids(project)
    parents = project.parents()
    summary = next(each for each in project.tasks if each.name == "Manuelle 4")
    subordinates = [
        dates.tasks[ids[uid]] for uid, parent in parents.items() if parent == summary.uid
    ]
    placed = dates.tasks[ids[summary.uid]]
    assert placed.start == min(each.start for each in subordinates)
    assert placed.finish == max(each.finish for each in subordinates)
    assert (placed.start, placed.finish) == (
        WorkInstant(date(2009, 11, 10), Decimal(0)),
        WorkInstant(date(2009, 11, 19), Decimal(3)),
    )
    calendar = calendar_of(project, calendars_of(project), summary)
    assert calendar is not None
    assert summary.start is not None
    assert summary.finish is not None
    assert (calendar.instant(summary.start), calendar.instant(summary.finish)) == (
        WorkInstant(date(2009, 11, 16), Decimal(0)),
        WorkInstant(date(2009, 11, 16), Decimal(7)),
    )


@pytest.mark.requirement("WF-QUA-0080-A")
def test_a_change_of_the_rule_that_dates_the_tasks_fails_the_corpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A link finish to finish counted from the start of its predecessor, as a link start to
    # start: a planning of the corpus no longer dates as MS Project did.
    # The file 01 carries such a link and is dated right by the rule as it stands.
    assert mismatches("01-links-and-lags-days.xml") == []
    monkeypatch.setattr(dating_engine, "FROM_FINISH", frozenset({"finish_to_start"}))
    assert mismatches("01-links-and-lags-days.xml") != []


@pytest.mark.requirement("WF-QUA-0080-A")
def test_the_manifest_names_each_file_of_the_corpus_and_each_is_read() -> None:
    named = sorted(entry["file"] for entry in FILES)
    assert named == sorted(path.name for path in CORPUS.glob("*.xml"))
    for entry in FILES:
        read = read_project((CORPUS / entry["file"]).read_bytes())
        assert read.project.tasks, entry["file"]


CITED = [(theme, case) for theme, cases in CASES.items() for case in cases]


@pytest.mark.requirement("WF-QUA-0080-A")
@pytest.mark.parametrize(("theme", "case"), CITED, ids=[case for _, case in CITED])
def test_each_case_the_body_cites_is_declared_by_a_planning_of_the_corpus(
    theme: str, case: str
) -> None:
    # « Chaque cas cité par le corps figure dans au moins un planning du corpus. » A case no file
    # declares is not run only when the test names the issue that says why (``MISSING``, empty
    # since the file 02 carries a negative lag in weeks, #2812); any other fails, and a case a
    # file declares needs that file in the corpus.
    declaring = [entry["file"] for entry in FILES if case in entry["cases"]]
    if not declaring and case in MISSING:
        pytest.skip(f"{case} ({theme}): no planning of the corpus declares it ({MISSING[case]})")
    assert declaring, f"{case} ({theme}): no planning of the corpus declares it"
    assert [file for file in declaring if (CORPUS / file).is_file()] != [], declaring


@pytest.mark.requirement("WF-INTF-0040-A")
@pytest.mark.requirement("WF-QUA-0080-A")
def test_the_manual_tasks_of_the_corpus_are_read_at_the_dates_of_their_start_and_finish() -> None:
    # « Une tâche en mode manuel du fichier est en mode manuel aux mêmes dates » : the reader reads
    # a manual task in its fields ``Manual…`` (US-1990), which MS Project wrote equal to ``Start``
    # and ``Finish`` in each file of the corpus: replayed, the corpus changes no date.
    read: list[str] = []
    lasting: list[str] = []
    for entry in FILES:
        content = (CORPUS / entry["file"]).read_bytes()
        tasks = {each.uid: each for each in read_project(content).project.tasks}
        for element in etree.fromstring(content, hardened_parser()).iterfind("{*}Tasks/{*}Task"):
            uid = int(element.findtext("{*}UID") or "0")
            if element.findtext("{*}Manual") != "1" or element.findtext("{*}ManualStart") is None:
                continue
            start, finish = (element.findtext(f"{{*}}{name}") for name in ("Start", "Finish"))
            assert (start, finish) == tuple(
                element.findtext(f"{{*}}{name}") for name in ("ManualStart", "ManualFinish")
            ), uid
            assert (tasks[uid].start, tasks[uid].finish) == (
                datetime.fromisoformat(start or ""),
                datetime.fromisoformat(finish or ""),
            ), uid
            # The duration read is the ``ManualDuration`` when the file has it, not ``Duration``.
            manual_duration = element.findtext("{*}ManualDuration")
            if manual_duration is not None:
                hours = int(manual_duration.removeprefix("PT").removesuffix("H0M0S"))
                assert tasks[uid].duration == timedelta(hours=hours), uid
                lasting.append(f"{entry['file']} {uid}")
            read.append(f"{entry['file']} {uid}")
    # The file 06, of the tasks in manual mode, carries them: the test does not pass on none.
    assert [each for each in read if each.startswith("06-manual-tasks.xml")], read
    assert [each for each in lasting if each.startswith("06-manual-tasks.xml")], lasting


@pytest.fixture
def schema() -> etree.XMLSchema:
    """Give the schema of MSPDI the variable names, the test skipped without it (WF-QUA-0080)."""
    named = os.environ.get("WATERFALL_MSPDI_SCHEMA_PATH")
    if not named:
        pytest.skip("WATERFALL_MSPDI_SCHEMA_PATH names no schema of MSPDI")
    return etree.XMLSchema(etree.parse(Path(named)))


@pytest.mark.requirement("WF-QUA-0080-A")
@pytest.mark.parametrize("entry", FILES, ids=[entry["file"] for entry in FILES])
def test_each_planning_of_the_corpus_read_then_written_is_valid_against_the_schema(
    entry: dict[str, Any], schema: etree.XMLSchema
) -> None:
    # « Chaque planning du corpus réimporté puis exporté par Waterfall est valide contre le
    # schéma » : without a database (« Leur exécution ne demande ni MS Project, ni base de
    # données »), the planning the reader gives is written by the writer of the export, the
    # working day of its head, ``Estimated`` and the fields ``Manual…`` of its manual tasks
    # included; the order of the schema is the writer's (``test_msproject.py``).
    project = read_project((CORPUS / entry["file"]).read_bytes()).project
    written = write_project(project)

    assert schema.validate(etree.fromstring(written, hardened_parser())), schema.error_log
    assert read_project(written).project == project
