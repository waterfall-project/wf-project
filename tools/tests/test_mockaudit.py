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


# --- The revision of an object, the sort, the filters and the facets (#550) ----------------------


def test_an_object_that_lives_in_a_revision_names_it_as_it_was(journal: dict[str, Node]) -> None:
    # The risk that occurred lives in the revision in progress, where its occurrence merges its own
    # estimate (WF-RIS-0060), open before it; the amendment in the revision of its structure,
    # which the merge marks. A line of cost is imputed to the project (WF-CRE-0010), and only the
    # imports of a planning, an estimate or a remaining apply to a revision (WF-INTF-0090); a
    # revision is no object of a revision.
    revisions = {each["revision_id"]: each for each in fixture("revisions")["items"]}
    [amendment] = [
        each
        for each in fixture("structures_amendments")
        if each["kind"] == "amendment" and each["is_merged"]
    ]
    named: dict[str, list[Node | None]] = {}
    for event in _events(journal["audit_events"]):
        named.setdefault(event["action"], []).append(event["object"]["revision"])
    current = fixture("project")["current_revision_id"]
    [occurred] = named["risk_occurrence"]
    assert occurred == {"revision_id": current, "label": None}
    [occurrence] = [e for e in _events(journal["audit_events"]) if e["action"] == "risk_occurrence"]
    assert revisions[current]["audit"]["created_at"] <= occurrence["occurred_at"]
    lived = revisions[amendment["revision_id"]]
    assert named["amendment_merge"] == [
        {"revision_id": lived["revision_id"], "label": lived["version_name"]}
    ]
    for action in ("import_apply", "cost_line_exclude", "revision_mark", "reference_designate"):
        assert named[action], action
    others = set(named) - {"risk_occurrence", "amendment_merge"}
    assert all(revision is None for action in others for revision in named[action])


def _inscription(
    number: int,
    actor: str | None = None,
    *,
    label: str | None = "x",
    project: tuple[str, str] | None = None,
    user: str | None = None,
) -> Node:
    """Return a synthetic inscription: its number, its author, its object's label, its project."""
    return {
        "audit_event_id": universe(number),
        "actor": (
            {"kind": "platform"}
            if actor is None
            else {"kind": "user", "user_id": user or universe(300 + number), "display_name": actor}
        ),
        "object": {"label": label},
        "project": (
            None
            if project is None
            else {"project_id": project[0], "code": project[1], "label": f"Projet {project[1]}"}
        ),
        "correlation_id": f"c-{number:02d}",
    }


def _sorted(events: list[Node], column: str, *, descending: bool = False) -> list[int]:
    found = mockaudit.sorted_by(cast("list[Any]", events), column, descending=descending)
    return [int(cast("Node", each)["audit_event_id"][-3:]) for each in found]


def test_a_text_column_sorts_by_code_point_without_value_last_and_ties_in_journal_order() -> None:
    # « Zoé » before « Émile »: É (U+00C9) comes after every unaccented letter by code point, the
    # lower case too — « alix » after « Zoé », before « Émile » (WF-IHM-0060, #292). The platform,
    # with no name, last in the ascending order, first in the descending; two inscriptions of one
    # name keep the order of the journal, whichever the way.
    events = [
        _inscription(1, "Émile"),
        _inscription(2, None),
        _inscription(3, "Zoé"),
        _inscription(4, "Alix"),
        _inscription(5, "alix"),
        _inscription(6, "Zoé"),
    ]
    assert _sorted(events, "actor") == [4, 3, 6, 5, 1, 2]
    assert _sorted(events, "actor", descending=True) == [2, 1, 5, 3, 6, 4]
    labels = [
        _inscription(1, "A", label="Référence"),
        _inscription(2, "A", label=None),
        _inscription(3, "A", label="Retard"),
        _inscription(4, "A", label="couts.xlsx"),
    ]
    assert _sorted(labels, "object_label") == [3, 1, 4, 2]
    projects = [
        _inscription(1, "A", project=(universe(2), "PRJ-010")),
        _inscription(2, "A"),
        _inscription(3, "A", project=(universe(1), "PRJ-002")),
    ]
    assert _sorted(projects, "project") == [3, 1, 2]
    assert _sorted(events, "correlation_id", descending=True) == [6, 5, 4, 3, 2, 1]
    with pytest.raises(ValueError, match="no text column"):
        mockaudit.sorted_by([], "occurred_at")


def test_the_journal_is_sorted_by_author_and_by_label_as_the_examples_read(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    for name, column in (
        ("audit_events_by_actor", "actor"),
        ("audit_events_by_object_label", "object_label"),
    ):
        assert _events(journal[name]) == mockaudit.sorted_by(cast("list[Any]", events), column)
        assert sorted(map(json.dumps, _events(journal[name]))) == sorted(map(json.dumps, events))
    names = [
        event["actor"].get("display_name") for event in _events(journal["audit_events_by_actor"])
    ]
    assert names[-1] is None
    assert names[0] == "Camille Martin"
    labels = [
        event["object"]["label"] for event in _events(journal["audit_events_by_object_label"])
    ]
    assert labels.index("Retard de livraison des armoires") < labels.index("Référence")
    assert labels[-1] is None


def test_a_correlation_retains_the_inscriptions_of_one_request(journal: dict[str, Node]) -> None:
    retained = _events(journal["audit_events_correlation"])
    assert [event["action"] for event in retained] == [
        "reference_designate",
        "revision_mark",
        "amendment_merge",
    ]
    assert len({event["correlation_id"] for event in retained}) == 1
    others = [
        event
        for event in _events(journal["audit_events"])
        if event["correlation_id"] == retained[0]["correlation_id"]
    ]
    assert others == retained


def test_a_search_holds_the_text_whatever_its_case_and_retains_no_object_without_label() -> None:
    events = [
        _inscription(1, "A", label="COUTS-reels-2026-05.xlsx"),
        _inscription(2, "A", label="couts-reels-2026-04.xlsx"),
        _inscription(3, "A", label=None),
        _inscription(4, "A", label="Réception couts-Reels-2026-05"),
    ]
    found = mockaudit.searched(cast("list[Any]", events), "Couts-Reels-2026-05")
    assert [cast("Node", each)["audit_event_id"] for each in found] == [
        universe(1),
        universe(4),
    ]
    assert mockaudit.searched(cast("list[Any]", events), "") == [events[0], events[1], events[3]]


def test_the_search_example_retains_the_labels_that_hold_the_text_in_any_case(
    journal: dict[str, Node],
) -> None:
    def holds(event: Node) -> bool:
        label = event["object"]["label"]
        return label is not None and mockaudit.SEARCHED.casefold() in label.casefold()

    retained = _events(journal["audit_events_search"])
    assert mockaudit.SEARCHED not in "".join(event["object"]["label"] for event in retained)
    assert retained == [event for event in _events(journal["audit_events"]) if holds(event)]
    assert [event["object"]["label"] for event in retained] == [
        "couts-reels-2026-05.xlsx",
        "couts-reels-2026-05-06.xlsx",
    ]


def test_the_facets_order_authors_by_name_then_identifier_and_projects_by_code() -> None:
    # Two accounts of one name, by their identifiers; « Zoé » before « Émile » by code point; the
    # platform no author. Two projects whose codes go the other way of their identifiers, by their
    # codes; each once, under its latest inscription — the journal reads the latest first.
    events = [
        _inscription(1, "Émile", user=universe(305), project=(universe(1), "PRJ-020")),
        _inscription(2, "Zoé", user=universe(309)),
        _inscription(3, "Zoé", user=universe(302), project=(universe(2), "PRJ-003")),
        _inscription(4, None, project=(universe(1), "PRJ-001")),
        _inscription(5, "Alix", user=universe(307)),
        _inscription(6, "Émile, avant", user=universe(305)),
    ]
    found = mockaudit.facets(cast("list[Any]", events))
    assert found["actors"] == [
        {"user_id": universe(307), "display_name": "Alix"},
        {"user_id": universe(302), "display_name": "Zoé"},
        {"user_id": universe(309), "display_name": "Zoé"},
        {"user_id": universe(305), "display_name": "Émile"},
    ]
    assert found["projects"] == [
        {"project_id": universe(2), "code": "PRJ-003", "label": "Projet PRJ-003"},
        {"project_id": universe(1), "code": "PRJ-020", "label": "Projet PRJ-020"},
    ]
    assert mockaudit.facets([]) == {"actors": [], "projects": []}


def test_the_facets_name_each_author_and_project_of_the_journal_once(
    journal: dict[str, Node],
) -> None:
    events = _events(journal["audit_events"])
    users = {user["user_id"]: user for user in fixture("users")["items"]}
    facets = journal["audit_facets"]
    authors = {event["actor"]["user_id"] for event in events if event["actor"]["kind"] == "user"}
    assert {actor["user_id"] for actor in facets["actors"]} == authors
    names = [(actor["display_name"], actor["user_id"]) for actor in facets["actors"]]
    assert names == sorted(names)
    for actor in facets["actors"]:
        # The name of today: the account's, which its latest inscription displays.
        assert actor["display_name"] == mockaudit.display_name(users[actor["user_id"]])
    projects = {event["project"]["project_id"] for event in events if event["project"] is not None}
    assert {project["project_id"] for project in facets["projects"]} == projects
    codes = [(project["code"], project["project_id"]) for project in facets["projects"]]
    assert codes == sorted(codes)
    witness = fixture("project")
    assert facets["projects"] == [
        {"project_id": witness["project_id"], "code": witness["code"], "label": witness["label"]}
    ]


def test_the_estimate_applied_today_heads_the_journal_of_the_witness_with_its_revision(
    journal: dict[str, Node],
) -> None:
    # The import of the estimate analysed this morning, applied by its task, which succeeds just
    # after today: one inscription of its own request, on the import under its file name, in the
    # revision in progress where an estimate applies (WF-INTF-0090), by the account of the
    # session; the rest is the journal of the witness as it was.
    imported = _events(journal["audit_events_import_applied"])
    head, rest = imported[0], imported[1:]
    analysed = fixture("import_analysed")
    task = fixture("task_import_succeeded")
    session = fixture("session")["user"]
    current = fixture("project")["current_revision_id"]
    assert analysed["kind"] == "estimate"
    assert task["kind"] == "import_apply"
    assert head["action"] == "import_apply"
    assert head["occurred_at"] == task["finished_at"]
    assert head["object"] == {
        "kind": "import",
        "object_id": analysed["import_id"],
        "label": analysed["filename"],
        "revision": {"revision_id": current, "label": None},
    }
    assert head["actor"] == {
        "kind": "user",
        "user_id": session["user_id"],
        "display_name": mockaudit.display_name(session),
    }
    assert head["project"] is not None
    assert head["project"]["project_id"] == fixture("project")["project_id"]
    assert head["correlation_id"] not in {event["correlation_id"] for event in rest}
    # A variant of the exit, not its sequel: neither its identifier nor its correlation is the
    # exit's.
    exited = _events(journal["audit_events_exited"])[0]
    assert head["audit_event_id"] != exited["audit_event_id"]
    assert head["correlation_id"] != exited["correlation_id"]
    assert rest == _events(journal["audit_events_project"])
    # The import of actual costs, applied before, lives in no revision (WF-CRE-0010).
    assert all(
        event["object"]["revision"] is None for event in rest if event["action"] == "import_apply"
    )
