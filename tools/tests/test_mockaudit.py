# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the journal of audit of the universe, engendered from its chronology (#516).

Each inscription is an action another example already says — when, by whom, on what —, and the
answers of ``listAuditEvents`` are readings of one journal. They try the generator against the
examples written by hand, not the Vérif of a requirement: none cites one (WF-QUA-0010).
"""

import json
from typing import Any, cast

import pytest

from wftools import mockaudit, mockcosts, mockdata, mockhistory, mockwitness
from wftools.mockids import hex_identifier, universe
from wftools.mocktext import PAGE
from wftools.mockwitness import INSTALLED, TODAY, fixture

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def journal() -> dict[str, Node]:
    """Read the answers of the journal back from the text the generator writes, by name."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mockaudit.examples().items()
    }


def _events(answer: Node) -> list[Node]:
    return cast("list[Node]", answer["items"])


def test_the_journal_reads_the_latest_first_each_inscription_once_since_the_installation(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    assert journal["audit_events"]["meta"] == {"limit": PAGE, "offset": 0, "total": len(events)}
    instants = [event["occurred_at"] for event in events]
    assert instants == sorted(instants, reverse=True)
    assert mockhistory.stamp(INSTALLED.instant) == instants[-1]
    assert instants[0] <= mockhistory.stamp(TODAY)
    assert len({event["audit_event_id"] for event in events}) == len(events)
    # Inscribed in order, numbered so: two of one instant come in that order, reversed.
    numbers = [int(event["audit_event_id"][-8:]) for event in events]
    assert numbers == sorted(numbers, reverse=True)
    # One correlation by request: shared only by the inscriptions of one request, at one instant.
    by_request: dict[str, set[str]] = {}
    for event in events:
        by_request.setdefault(event["correlation_id"], set()).add(event["occurred_at"])
    assert all(len(instants) == 1 for instants in by_request.values())


def test_a_merge_inscribes_the_amendment_then_the_marking_and_the_designation_it_makes(
    journal: dict[str, Node],
) -> None:
    # Decision of the review of EP-02/L42b: one request, three inscriptions, one correlation.
    merged = mockhistory.stamp(mockwitness.AMENDMENT_MERGED.instant)
    at_merge = [e for e in _events(journal["audit_events"])[::-1] if e["occurred_at"] == merged]
    assert [(e["action"], e["object"]["kind"]) for e in at_merge] == [
        ("amendment_merge", "cost_structure"),
        ("revision_mark", "revision"),
        ("reference_designate", "revision"),
    ]
    assert len({e["correlation_id"] for e in at_merge}) == 1
    reference = next(each for each in fixture("revisions")["items"] if each["is_reference"])
    assert {e["object"]["object_id"] for e in at_merge[1:]} == {reference["revision_id"]}


def test_every_marked_revision_and_the_reference_have_their_inscriptions(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    said = {(e["action"], e["object"]["object_id"], e["occurred_at"]) for e in events}
    designated = {e["object"]["object_id"] for e in events if e["action"] == "reference_designate"}
    revisions = fixture("revisions")["items"]
    for revision in revisions:
        if revision["status"] == "marked":
            mark = ("revision_mark", revision["revision_id"], revision["marked_at"])
            assert mark in said, revision["version_name"]
    [reference] = [each for each in revisions if each["is_reference"]]
    assert reference["revision_id"] in designated


def test_each_action_on_the_witness_is_one_the_chronology_says(journal: dict[str, Node]) -> None:
    project = fixture("project")
    witness = _events(journal["audit_events_project"])
    assert {event["project"]["project_id"] for event in witness} == {project["project_id"]}
    said = {(event["action"], event["occurred_at"]) for event in witness}
    offer = next(
        each for each in fixture("revisions")["items"] if each["revision_id"].endswith("100")
    )
    assert ("revision_mark", offer["marked_at"]) in said
    assert ("reference_designate", mockhistory.stamp(mockwitness.ORDER_RECEIVED.instant)) in said
    assert ("amendment_merge", mockhistory.stamp(mockwitness.AMENDMENT_MERGED.instant)) in said
    assert ("risk_occurrence", mockhistory.stamp(mockwitness.RISK_752_OCCURRED.instant)) in said
    # Each import of actual costs applied is an inscription, at the instant its journal says.
    applied = {mockhistory.stamp(each.event.instant) for each in mockwitness.JOURNAL}
    imported = {entry["imported_at"] for entry in fixture("cost_imports")["items"]}
    assert applied == imported
    assert {at for action, at in said if action == "import_apply"} == imported
    # The line excluded is named by its document, as the consultation names it.
    lines = {line["cost_line_id"]: line for line in fixture("actual_costs")["items"]}
    [excluded] = [event for event in witness if event["action"] == "cost_line_exclude"]
    line = lines[excluded["object"]["object_id"]]
    assert excluded["object"]["label"] == line["document_number"]
    assert line["is_in_tracked_scope"] is False
    assert _events(journal["audit_events_project"]) == [
        event for event in _events(journal["audit_events"]) if event["project"] is not None
    ]


def test_each_account_role_and_backup_is_inscribed_as_its_example_says(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    by_object: dict[str, list[Node]] = {}
    for event in events:
        by_object.setdefault(event["object"]["object_id"], []).append(event)
    for user in fixture("users")["items"]:
        created = by_object[user["user_id"]][-1]
        assert created["action"] == "user_create"
        assert created["occurred_at"] == user["audit"]["created_at"]
        assert created["actor"] == user["audit"]["created_by"]
        assert created["object"]["label"] == f"{user['first_name']} {user['last_name']}"
        deactivated = [e for e in by_object[user["user_id"]] if e["action"] == "user_deactivate"]
        assert len(deactivated) == (0 if user["is_active"] else 1), user["last_name"]
    for role in fixture("access_roles"):
        [created] = by_object[role["access_role_id"]]
        assert (created["action"], created["object"]["label"]) == (
            "access_role_create",
            role["label"],
        )
        assert created["occurred_at"] == role["audit"]["created_at"]
    for backup in fixture("backups")["items"]:
        [taken] = by_object[backup["backup_id"]]
        assert (taken["action"], taken["occurred_at"]) == ("backup", backup["taken_at"])
        assert (taken["actor"]["kind"] == "platform") is (backup["origin"] == "scheduled")
        assert taken["project"] is None
    # Every actor is the platform or an account of the installation, under its name.
    names = {
        user["user_id"]: f"{user['first_name']} {user['last_name']}"
        for user in fixture("users")["items"]
    }
    for event in events:
        actor = event["actor"]
        assert actor["kind"] == "platform" or names[actor["user_id"]] == actor["display_name"]


def test_an_account_is_given_the_roles_created_after_it_once_they_exist(
    journal: dict[str, Node],
) -> None:
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    given = [e for e in _events(journal["audit_events"]) if e["action"] == "user_access_roles_set"]
    for event in given:
        user = next(
            each
            for each in fixture("users")["items"]
            if each["user_id"] == event["object"]["object_id"]
        )
        created = max(roles[role]["audit"]["created_at"] for role in user["access_role_ids"])
        assert event["occurred_at"] == created > user["audit"]["created_at"]
    assert [event["object"]["label"] for event in given] == ["Camille Martin"]


def test_the_other_readings_are_pages_and_filters_of_the_one_journal(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    page = journal["audit_events_page"]
    assert page["meta"] == {"limit": 10, "offset": 10, "total": len(events)}
    assert _events(page) == events[10:20]
    assert journal["audit_events_empty"] == {
        "items": [],
        "meta": {"limit": 50, "offset": 0, "total": 0},
    }
    # The exit confirmed today heads the journal of the witness, which is otherwise the same.
    exited = _events(journal["audit_events_exited"])
    completed = fixture("project_completed")
    assert exited[0]["action"] == "project_exit"
    assert exited[0]["occurred_at"] == completed["audit"]["updated_at"] == mockhistory.stamp(TODAY)
    assert exited[0]["object"]["object_id"] == completed["project_id"]
    assert exited[1:] == _events(journal["audit_events_project"])


def test_each_actor_is_the_one_who_did_the_action(journal: dict[str, Node]) -> None:
    # An actor read from an audit is the one of the action only where that audit was last updated
    # by it: the instant of the audit is the instant of the inscription. Elsewhere — the
    # designation of the offer, the exclusion of a line, which an audit updated since does not
    # date — it is the actor of the witness; an import is by the actor of its journal.
    revisions = {each["revision_id"]: each for each in fixture("revisions")["items"]}
    risks = {each["risk_id"]: each for each in fixture("risks")["items"]}
    reference = next(each for each in revisions.values() if each["is_reference"])
    imports = {
        hex_identifier(each.exchange): hex_identifier(each.number) for each in mockwitness.JOURNAL
    }
    journal_of_costs = {each["cost_import_id"]: each for each in fixture("cost_imports")["items"]}
    witness = fixture("project")["audit"]["created_by"]
    offer_designated = mockhistory.stamp(mockwitness.ORDER_RECEIVED.instant)
    for event in _events(journal["audit_events"]):
        kind, identifier = event["object"]["kind"], event["object"]["object_id"]
        audit: Node | None = None
        if kind == "revision" and event["occurred_at"] != offer_designated:
            audit = revisions[identifier]["audit"]
        elif kind == "cost_structure":
            audit = reference["audit"]
        elif kind == "risk":
            audit = risks[identifier]["audit"]
        if audit is not None:
            assert audit["updated_at"] == event["occurred_at"], event["action"]
            assert event["actor"] == audit["updated_by"], event["action"]
        elif kind in {"revision", "cost_line"}:
            assert event["actor"] == witness, event["action"]
        elif kind == "import":
            assert event["actor"] == journal_of_costs[imports[identifier]]["actor"]


def test_the_designation_and_the_exclusion_stay_with_the_witness_whoever_updated_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # In the universe, Camille Martin did everything, so the test above cannot tell the actor of
    # an action from the one who last updated its object (#543). Here someone else last updated
    # the offer and the excluded line — Lucas Petit re-extracting the line on 11 May —: the marking
    # of the offer, whose audit its marking dates, follows its audit; the designation and the
    # exclusion, which their audits do not date, stay with the actor of the witness. The line is
    # changed where the generator could read it, on the disk and in memory, as `mockcosts` writes
    # it: whichever it read, the exclusion would follow it.
    witness = fixture("project")["audit"]["created_by"]
    users = {user["last_name"]: user for user in fixture("users")["items"]}
    other = {"kind": "user", "user_id": users["Petit"]["user_id"], "display_name": "Lucas Petit"}
    assert other != witness
    offer, excluded = universe(100), hex_identifier(0xC04)
    real = mockwitness.fixture

    def updated_by_another(name: str) -> Any:
        value = real(name)
        if name == "revisions":
            objects, key = value["items"], ("revision_id", offer)
        elif name == "actual_costs":
            objects, key = value["items"], ("cost_line_id", excluded)
        else:
            return value
        [changed] = [each for each in objects if each[key[0]] == key[1]]
        changed["audit"]["updated_by"] = other
        return value

    written = mockcosts.cost_line

    def line_updated_by_another(line: mockwitness.CostLine) -> Any:
        value = cast("Node", written(line))
        if value["cost_line_id"] == excluded:
            value["audit"]["updated_by"] = other
        return value

    monkeypatch.setattr(mockaudit, "fixture", updated_by_another)
    monkeypatch.setattr(mockcosts, "cost_line", line_updated_by_another)
    events = {
        (event["action"], event["object"]["object_id"]): event["actor"]
        for event in cast("list[Node]", mockaudit.journal())
    }
    assert events["revision_mark", offer] == other
    assert events["reference_designate", offer] == witness
    assert events["cost_line_exclude", excluded] == witness


def test_the_journal_reads_no_example_the_same_command_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # One run of `make mock-data` reaches its fixed point only if nothing it writes is read back
    # from the disk: what mockaudit reads by `fixture` is written by hand.
    read: list[str] = []
    real = mockwitness.fixture

    def recording(name: str) -> Any:
        read.append(name)
        return real(name)

    monkeypatch.setattr(mockaudit, "fixture", recording)
    mockaudit.examples()
    generated = {name.removesuffix(".json") for name in mockdata.declared_names()}
    assert read
    assert set(read) & generated == set()


def test_an_actor_exists_and_is_active_when_it_acts(journal: dict[str, Node]) -> None:
    users = {user["user_id"]: user for user in fixture("users")["items"]}
    for event in _events(journal["audit_events_exited"]) + _events(journal["audit_events"]):
        actor = event["actor"]
        if actor["kind"] == "platform":
            continue
        user = users[actor["user_id"]]
        assert user["audit"]["created_at"] <= event["occurred_at"], event["action"]
        if not user["is_active"]:
            assert event["occurred_at"] < user["audit"]["updated_at"], event["action"]


def test_the_roles_are_inscribed_before_the_accounts_that_hold_them(
    journal: dict[str, Node],
) -> None:
    # A role an account holds from its creation is created before it, at the same instant or
    # earlier; a role created later is given afterwards (`user_access_roles_set`).
    inscribed = [event["object"]["object_id"] for event in _events(journal["audit_events"])[::-1]]
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    for user in fixture("users")["items"]:
        for role in user["access_role_ids"]:
            if roles[role]["audit"]["created_at"] <= user["audit"]["created_at"]:
                assert inscribed.index(role) < inscribed.index(user["user_id"]), user["last_name"]


def test_an_account_updated_by_its_holder_alone_is_no_inscription(
    journal: dict[str, Node],
) -> None:
    # The session's own account was last updated today by its holder, its preferences of display:
    # no administrator modified it, and the journal says nothing of it (WF-SEC-0030).
    session = fixture("session")["user"]
    audit = session["audit"]
    assert audit["updated_at"] == mockhistory.stamp(TODAY)
    assert audit["updated_by"]["user_id"] == session["user_id"]
    about = [
        e
        for e in _events(journal["audit_events"])
        if e["object"]["object_id"] == session["user_id"]
        and e["occurred_at"] == audit["updated_at"]
    ]
    assert about == []
