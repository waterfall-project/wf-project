# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the import of a planning of MS Project (US-2780/L1), without a base.

What the pure reader and the pure writer of ``planning.msproject`` keep of a file of the corpus
(``fixtures/msproject``) — the links of the four types with their lag, the tasks in manual mode,
the constraint « Pas avant le » — read, written, then read again, from the fixture
``msproject_round_trip.json`` (WF-INTF-0040). The import that applies the reading — the tasks
created, the manual mode and the report of what a date constraint made manual, the resources and
the calendars not created, the user informed — takes a database: ``test_msproject_import.py`` and
``test_msproject_corpus.py`` replay it.
"""

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.planning.msproject import MsProject, read_project, write_project

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
CORPUS = Path(__file__).resolve().parents[3] / "fixtures" / "msproject"


def _read(data: Example, name: str) -> tuple[MsProject, MsProject]:
    """Read a file of the corpus, then the file written from what was read, read again."""
    held = cast("dict[str, str]", data["files"])
    first = read_project((CORPUS / held[name]).read_bytes())
    return first.project, read_project(write_project(first.project)).project


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_file_saved_by_ms_project_is_read_without_error(
    example: Callable[[str], Example],
) -> None:
    # « Un fichier XML produit par MS Project 2013 est importé sans erreur. » The reading of the
    # file only (the tasks it holds are all read); the import that creates them takes a database.
    data = example("WF-INTF-0040-A#90a413b0721b")
    for name in cast("dict[str, str]", data["files"]):
        first, _ = _read(data, name)
        assert first.tasks


@pytest.mark.requirement("WF-INTF-0040-A")
def test_the_links_of_the_four_types_and_their_lag_are_the_same_after_a_write_and_a_read(
    example: Callable[[str], Example],
) -> None:
    # « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et
    # décalage — sont identiques à celles du fichier source ; [...] » The links as the reader keeps
    # them are the same once written and read again; the file holds the four types and the lags.
    data = example("WF-INTF-0040-A#144393ff59c5")
    first, again = _read(data, "links")
    links = [link for task in first.tasks for link in task.predecessors]
    assert {link.link_type for link in links} == set(cast("list[str]", data["link_types"]))
    assert {link.lag for link in links} >= set(
        cast("list[int]", data["lags_in_tenths_of_a_minute"])
    )
    assert [task.predecessors for task in again.tasks] == [
        task.predecessors for task in first.tasks
    ]
    assert [task.name for task in again.tasks] == [task.name for task in first.tasks]


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_task_in_manual_mode_keeps_its_mode_and_its_dates_after_a_write_and_a_read(
    example: Callable[[str], Example],
) -> None:
    # « [...] une tâche en mode manuel du fichier est en mode manuel aux mêmes dates ; [...] »
    data = example("WF-INTF-0040-A#144393ff59c5")
    first, again = _read(data, "manual")
    assert any(task.manual for task in first.tasks)
    assert [(task.manual, task.start, task.finish) for task in again.tasks] == [
        (task.manual, task.start, task.finish) for task in first.tasks
    ]


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_task_with_a_constraint_not_before_keeps_it_and_the_reading_names_it_ignored(
    example: Callable[[str], Example],
) -> None:
    # « [...] une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; »
    # The constraint and its date are kept by the reader, which counts it among what an import
    # does not read (``date_constraints``); the task made manual by the import takes a database.
    data = example("WF-INTF-0040-A#144393ff59c5")
    held = cast("dict[str, str]", data["constraint"])
    first, again = _read(data, "constraints")
    task = next(each for each in again.tasks if each.name == held["task"])
    assert (
        task.constraint,
        task.constraint_date.isoformat() if task.constraint_date else None,
    ) == (
        held["type"],
        held["date"],
    )
    assert [(each.constraint, each.constraint_date) for each in again.tasks] == [
        (each.constraint, each.constraint_date) for each in first.tasks
    ]
    report = read_project(
        (CORPUS / cast("dict[str, str]", data["files"])["constraints"]).read_bytes()
    )
    named = {each.kind: each.labels for each in report.ignored}
    assert held["task"] in named["date_constraints"]
