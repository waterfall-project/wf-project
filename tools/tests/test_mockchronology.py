# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the chronology of the witness written for the loader of the projects (US-0990/L1)."""

import json
from datetime import datetime
from itertools import pairwise
from typing import Any

from wftools import REPOSITORY, mockchronology, mockdata, mockwitness, paths

FILE = REPOSITORY / "fixtures" / "api" / mockchronology.NAME


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
    assert all(event["occurred_at"].endswith("Z") for event in _events())


def test_the_order_is_that_of_the_events() -> None:
    # WF-QUA-0040-A: the events come in the order of the chronology, numbered from 1.
    events = _events()
    assert [event["what"] for event in events] == [e.what for e in mockwitness.CHRONOLOGY]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert all(a["occurred_at"] < b["occurred_at"] for a, b in pairwise(events))


def _writes() -> list[dict[str, Any]]:
    return [write for event in _events() for write in event["writes"]]


def _written(*kinds: str) -> list[dict[str, Any]]:
    return [write for write in _writes() if write["kind"] in kinds]


def test_the_writes_are_those_of_the_design_in_that_order() -> None:
    # WF-QUA-0040-A: the design of EP-04 lists them: 100 opened (Created to Costing), marked, 101
    # opened, 100 designated and refused, the code entered, 101 marked, 102 opened; no abandon.
    assert [(w["kind"], w.get("revision")) for w in _writes()] == [
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


def test_each_write_has_the_fields_of_its_kind() -> None:
    # WF-QUA-0040-A: the full shape of each write, by kind, and no field beyond it.
    fields = {
        "project_created": {"kind", "project"},
        "revision_opened": {"kind", "project", "revision"},
        "revision_marked": {"kind", "project", "revision", "version_name"},
        "designation_attempted": {"kind", "project", "revision", "refused"},
        "code_entered": {"kind", "project", "code"},
        "state_transition": {"kind", "project", "from", "to"},
    }
    assert all(set(write) == fields[write["kind"]] for write in _writes())
    assert [(w["revision"], w["version_name"]) for w in _written("revision_marked")] == [
        (100, "v1.0"),
        (101, "Référence"),
    ]
    assert [(w["revision"], w["refused"]) for w in _written("designation_attempted")] == [
        (100, "no_task")
    ]
    assert [(w["from"], w["to"]) for w in _written("state_transition")] == [("created", "costing")]
    assert [w["revision"] for w in _written("revision_opened")] == [100, 101, 102]


def test_an_event_writes_the_opening_of_the_offer_before_its_transition() -> None:
    # WF-QUA-0040-A: at the opening of the offer, 100 is opened, then Created to Costing.
    opening = next(
        event
        for event in _events()
        if event["writes"] and event["writes"][0]["kind"] == "revision_opened"
    )
    assert [(w["kind"], w.get("revision")) for w in opening["writes"]] == [
        ("revision_opened", 100),
        ("state_transition", None),
    ]


def test_every_write_names_a_project_of_the_example_of_the_projects() -> None:
    # WF-QUA-0040-A: each write carries its project, a code of projects.json; the code entered is
    # that of the witness project.
    codes = {
        item["code"]
        for item in json.loads((FILE.parent / "projects.json").read_text(encoding="utf-8"))[
            "value"
        ]["items"]
    }
    assert all(write["project"] in codes for write in _writes())
    assert [w["code"] for w in _written("code_entered")] == ["PRJ-001"]


def test_the_file_is_an_example_of_a_summary_a_description_and_a_value() -> None:
    # WF-QUA-0040-A: the file stands alone, a summary, a description and a value, as an example.
    assert set(json.loads(FILE.read_text(encoding="utf-8"))) == {"summary", "description", "value"}
