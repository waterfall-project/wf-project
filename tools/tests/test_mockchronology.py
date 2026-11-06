# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the chronology of the witness written for the loader of the projects (US-0990/L1)."""

import json
from datetime import datetime
from itertools import pairwise
from typing import Any

from wftools import REPOSITORY, mockchronology, mockdata, mockwitness, paths

FILE = REPOSITORY / "fixtures" / "api" / mockchronology.NAME
KINDS = {
    "project_created",
    "revision_opened",
    "revision_marked",
    "designation_attempted",
    "code_entered",
    "state_transition",
}


def _events() -> list[dict[str, Any]]:
    return json.loads(FILE.read_text(encoding="utf-8"))["value"]["events"]


def test_the_chronology_is_held_by_the_check_of_make_mock_data_up_to_date() -> None:
    # WF-QUA-0040-A: the engendering yields the data announced; the file is held by the check.
    assert mockchronology.NAME in mockdata.named()
    assert mockchronology.NAME in mockdata.declared_names()
    assert FILE.read_text(encoding="utf-8") == mockdata.render(
        mockdata.named()[mockchronology.NAME]
    )
    problems = mockdata.check(FILE.parent)
    assert not [problem for problem in problems if mockchronology.NAME in problem]


def test_the_chronology_is_declared_generated_by_make_mock_data() -> None:
    # WF-QUA-0040-A: a file written by the generator is declared so, and left out of a lot's size.
    declared = [
        entry
        for entry in paths.read().generated
        if f"fixtures/api/{mockchronology.NAME}" in entry.paths
    ]
    assert [entry.by for entry in declared] == ["make mock-data"]


def test_the_instants_are_those_of_the_chronology() -> None:
    # WF-QUA-0040-A: each event carries the instant of the witness's chronology (WF-CYC-0130).
    instants = [datetime.fromisoformat(event["occurred_at"]) for event in _events()]
    assert instants == [event.instant for event in mockwitness.CHRONOLOGY]
    assert all(text["occurred_at"].endswith("Z") for text in _events())


def test_the_order_is_that_of_the_events() -> None:
    # WF-QUA-0040-A: the events come in the order of the chronology, numbered from 1.
    events = _events()
    assert [event["what"] for event in events] == [e.what for e in mockwitness.CHRONOLOGY]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert all(a["occurred_at"] < b["occurred_at"] for a, b in pairwise(events))


def test_what_an_event_writes_is_a_known_kind_of_the_witness_story() -> None:
    # WF-QUA-0040-A: the offer opened, marked, the reference opened and marked, the current one
    # opened, the designation refused, the code entered, the transition to costing.
    writes = [write for event in _events() for write in event["writes"]]
    assert {write["kind"] for write in writes} <= KINDS
    assert [(w["kind"], w.get("revision")) for w in writes] == [
        ("project_created", None),
        ("revision_opened", 100),
        ("state_transition", None),
        ("revision_marked", 100),
        ("revision_opened", 101),
        ("designation_attempted", 100),
        ("code_entered", None),
        ("revision_marked", 101),
        ("revision_opened", 102),
    ]


def test_the_file_holds_no_import_of_wftools_to_read() -> None:
    # WF-QUA-0040-A: the file stands alone, a summary, a description and a value, as an example.
    assert set(json.loads(FILE.read_text(encoding="utf-8"))) == {"summary", "description", "value"}
