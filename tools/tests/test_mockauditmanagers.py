# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the project managers in the journal of audit of the universe (US-2980, #4127).

The registration, the removal and the change of capacity of a project manager, read from the lists
of contributors the examples write, as the service inscribes them, at the head of the journal of
the witness. They try the generator against the examples, not the Vérif of a requirement: none
cites one (WF-QUA-0010).
"""

import json
from typing import Any, cast

import pytest

from wftools import mockaudit, mockauditmanagers, mockdata, mockhistory, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import TODAY, fixture

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def journal() -> dict[str, Node]:
    """Read the answers back from the text the generator writes, by name, the witness's included."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in {
            **mockaudit.examples(),
            **mockauditmanagers.examples(),
        }.items()
    }


def _events(answer: Node) -> list[Node]:
    return cast("list[Node]", answer["items"])


def _line(user: int, kind: str) -> Node:
    return {"user_id": universe(user), "kind": kind}


def test_a_list_written_inscribes_its_project_managers_alone_as_the_service_does() -> None:
    # Registered as project manager, changed in capacity either way, removed as project manager:
    # one inscription each, in the order of the list written, then the lines removed; a
    # participant registered or removed is none (WF-SEC-0030, #4127).
    before = [_line(301, "project_manager"), _line(302, "contributor"), _line(303, "contributor")]
    before += [_line(304, "project_manager"), _line(305, "project_manager")]
    after = [
        _line(306, "project_manager"),
        _line(307, "contributor"),
        _line(302, "project_manager"),
    ]
    after += [_line(301, "contributor"), _line(305, "project_manager")]
    assert mockauditmanagers.changes(before, after) == [
        ("project_manager_add", universe(306)),
        ("project_manager_change", universe(302)),
        ("project_manager_change", universe(301)),
        ("project_manager_remove", universe(304)),
    ]
    assert mockauditmanagers.changes(before, before) == []


def _manager_head(journal: dict[str, Node], name: str, count: int) -> tuple[list[Node], list[Node]]:
    """Split a reading of the project managers into its inscriptions of today and the rest."""
    events = _events(journal[name])
    return events[:count], events[count:]


def test_the_list_written_today_heads_the_journal_of_the_witness_with_its_manager(
    journal: dict[str, Node],
) -> None:
    # contributors_set makes Inès Roux project manager, and registers Sacha Lefèvre participant:
    # the change alone is inscribed, on the contributor, by the creator of the witness, today;
    # the rest is the journal of the witness as it was.
    [head], rest = _manager_head(journal, "audit_events_manager_changed", 1)
    read = {each["user_id"]: each for each in fixture("contributors")["items"]}
    written = {each["user_id"]: each for each in fixture("contributors_set")["items"]}
    ines = head["object"]["object_id"]
    assert (read[ines]["kind"], written[ines]["kind"]) == ("contributor", "project_manager")
    assert head["action"] == "project_manager_change"
    assert head["object"]["kind"] == "contributor"
    assert head["object"]["label"] == written[ines]["display_name"]
    assert head["object"]["revision"] is None
    assert head["actor"] == fixture("project")["audit"]["created_by"]
    assert head["occurred_at"] == mockhistory.stamp(TODAY)
    assert head["project"]["project_id"] == fixture("project")["project_id"]
    assert head["params"] == {}
    assert rest == _events(journal["audit_events_project"])


def test_the_rescue_inscribes_the_manager_a_non_contributor_registers(
    journal: dict[str, Node],
) -> None:
    # The rescuer is no contributor of the list it reads, none of whose project managers is
    # active; it registers a project manager who was not in it — a liberty of the variant: the
    # rescue of the contract promotes Inès Roux (contributors_set_by_rescuer).
    [head], rest = _manager_head(journal, "audit_events_manager_added", 1)
    read = fixture("contributors_without_active_manager")["items"]
    assert head["action"] == "project_manager_add"
    assert head["actor"]["user_id"] not in {each["user_id"] for each in read}
    assert not [each for each in read if each["kind"] == "project_manager" and each["is_active"]]
    assert head["object"]["object_id"] not in {each["user_id"] for each in read}
    assert head["object"]["label"] == mockauditmanagers.RESCUED
    rescued = fixture("contributors_set_by_rescuer")["items"]
    assert head["object"]["object_id"] not in {each["user_id"] for each in rescued}
    assert rest == _events(journal["audit_events_project"])


def test_the_removal_follows_the_change_that_made_the_manager(journal: dict[str, Node]) -> None:
    # The list written after the one of today removes Inès Roux: its inscription heads the
    # reading, after the very inscription of the change, which keeps its identifier and its
    # correlation.
    [removal, change], rest = _manager_head(journal, "audit_events_manager_removed", 2)
    [changed] = _events(journal["audit_events_manager_changed"])[:1]
    assert change == changed
    assert removal["action"] == "project_manager_remove"
    assert removal["object"] == changed["object"]
    assert removal["occurred_at"] > changed["occurred_at"]
    assert removal["correlation_id"] != changed["correlation_id"]
    assert rest == _events(journal["audit_events_project"])


def test_the_project_managers_are_numbered_apart_from_every_other_example(
    journal: dict[str, Node],
) -> None:
    # No identifier nor correlation of theirs is given by an example of another reading.
    names = {
        "audit_events_manager_changed.json",
        "audit_events_manager_added.json",
        "audit_events_manager_removed.json",
    }
    written = {
        path.name: path.read_text(encoding="utf-8")
        for path in mockwitness.FIXTURES.rglob("*.json")
        if path.name not in names
    }
    for name in names:
        head = [
            event
            for event in _events(journal[name.removesuffix(".json")])
            if event["action"].startswith("project_manager_")
        ]
        assert head
        for event in head:
            for other, text in written.items():
                assert event["audit_event_id"] not in text, other
                assert event["correlation_id"] not in text, other
