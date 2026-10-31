# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the findings of contract the lots of EP-15 raised, settled point by point (US-0640/L6).

Each point the recadrage of EP-16 decided (#1445), or the author on 2026-10-28, is written in the
contract with its examples (`docs/api/DECISIONS.md`, « Les constats de contrat des lots d'EP-15 »):
these tests hold each example to the contract that cites it and to the readings it derives from.
They try the examples of the fake back, not the Vérif of a requirement: none cites one
(WF-QUA-0010, « un test qui ne couvre aucune exigence »); the criterion they bear is the US's own,
« chaque constat de contrat reçu soldé, point par point ».
"""

import json
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

from wftools import REPOSITORY, mocknonworking
from wftools.mockwitness import default_calendar, fixture

API = REPOSITORY / "docs" / "api"
RATE_UPDATE = "apply_rate_update"


@cache
def _operations() -> dict[str, dict[str, Any]]:
    """Return every operation of the contract, by its identifier."""
    found: dict[str, dict[str, Any]] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        for item in cast(
            "dict[str, Any]", yaml.safe_load(path.read_text(encoding="utf-8"))
        ).values():
            for operation in cast("dict[str, Any]", item).values():
                if isinstance(operation, dict) and "operationId" in operation:
                    found[cast("str", operation["operationId"])] = operation
    return found


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples an answer of an operation cites, by the name of their file."""
    answer = _operations()[operation]["responses"][status]
    [content] = cast("dict[str, Any]", answer["content"]).values()
    return [
        Path(cast("str", each["$ref"])).stem
        for each in cast("dict[str, Any]", content["examples"]).values()
    ]


def _schema(file: str, name: str) -> dict[str, Any]:
    text = (API / "components" / file).read_text(encoding="utf-8")
    return cast("dict[str, Any]", yaml.safe_load(text)[name])


def _command(revision: dict[str, Any], name: str) -> dict[str, Any] | None:
    found = [each for each in revision["available_commands"] if each["command"] == name]
    return found[0] if found else None


def _revisions(value: Any) -> list[dict[str, Any]]:
    """Return every revision an example renders with its commands, however deep it lies."""
    if isinstance(value, list):
        return [found for each in cast("list[Any]", value) for found in _revisions(each)]
    if not isinstance(value, dict):
        return []
    fields = cast("dict[str, Any]", value)
    here = [fields] if {"revision_id", "status", "available_commands"} <= fields.keys() else []
    return here + [found for each in fields.values() for found in _revisions(each)]


# --- #1351: the update of the rates, a command of the revision ----------------------------------


def test_the_update_of_the_rates_is_a_command_of_each_revision_its_conditions_in_order() -> None:
    commands = _schema("schemas/revisions.yaml", "RevisionCommand")["enum"]
    assert commands[commands.index("merge_structure") + 1] == RATE_UPDATE
    conditions = _schema("schemas/projects.yaml", "CommandCondition")["enum"]
    assert "rate_update_available" in conditions
    listed = 0
    for path in sorted((REPOSITORY / "fixtures" / "api").glob("*.json")):
        example = json.loads(path.read_text(encoding="utf-8"))
        for revision in _revisions(example["value"]):
            names = [each["command"] for each in revision["available_commands"]]
            # Hypothesis, not read from the fixtures: `apply_rate_update` is guarded by
            # `revisions.write` alone, but in the roles of the examples whoever holds it also
            # holds `revision_mark`, so `mark` present means the update of the rates is offered.
            if "mark" not in names:
                assert RATE_UPDATE not in names, path.name
                continue
            assert names[names.index("merge_structure") + 1] == RATE_UPDATE, path.name
            offer = cast("dict[str, Any]", _command(revision, RATE_UPDATE))
            listed += 1
            if revision["status"] == "marked":
                assert offer["missing_conditions"] == ["revision_draft"], path.name
            elif path.stem == "revision_rate_update_offered":
                assert (offer["is_available"], offer["missing_conditions"]) == (True, []), path.stem
            else:
                missing = offer["missing_conditions"]
                assert missing[0] == "rate_update_available", path.name
                busy = cast("dict[str, Any]", _command(revision, "mark"))["missing_conditions"]
                assert missing[1:] == busy, path.name
    assert listed > 10


def test_the_update_is_offered_on_the_101_at_its_opening_and_its_refusal_names_the_condition() -> (
    None
):
    offered, applied = fixture("revision_rate_update_offered"), fixture("rate_update_applied")
    assert offered["revision_id"] == applied["revision_id"]
    assert offered["lock_version"] == applied["lock_version"] - 1 == 1
    assert offered["audit"]["updated_at"] == offered["audit"]["created_at"]
    assert offered["audit"]["updated_by"] == offered["audit"]["created_by"]
    assert fixture("rate_update")["categories"] != []
    unchanged = ("available_commands", "audit", "lock_version")
    assert {k: v for k, v in offered.items() if k not in unchanged} == {
        k: v for k, v in applied.items() if k not in unchanged
    }
    assert [each for each in offered["available_commands"] if each["command"] != RATE_UPDATE] == [
        each for each in applied["available_commands"] if each["command"] != RATE_UPDATE
    ]
    assert "revision_rate_update_offered" in _cited("getRevision", "200")
    # The 409 of applyRateUpdate names the first condition the command of the revision misses.
    refused = fixture("rate_update_not_available")
    current = cast("dict[str, Any]", _command(fixture("revision"), RATE_UPDATE))
    assert fixture("rate_update_none")["categories"] == []
    assert refused["params"] == {"missing_condition": current["missing_conditions"][0]}
    assert {"rate_update_not_available", "rate_update_revision_marked"} <= set(
        _cited("applyRateUpdate", "409")
    )


# --- #1367: the register of the risks, paged ----------------------------------------------------


def test_the_register_of_the_risks_is_paged_its_totals_on_every_risk_retained() -> None:
    operation = _operations()["listRisks"]
    references = {each.get("$ref", "") for each in operation["parameters"]}
    assert {"../components/parameters.yaml#/Limit", "../components/parameters.yaml#/Offset"} <= (
        references
    )
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert "meta" in schema["required"]
    whole = fixture("risks")
    for name in _cited("listRisks", "200"):
        register = fixture(name)
        if name == "risks_page":
            # A page shorter than the register: its count and its totals of the whole (US-0660/L3).
            assert register["meta"] == {"limit": 2, "offset": 0, "total": len(whole["items"])}
            assert register["items"] == whole["items"][:2]
            assert register["totals"] == whole["totals"]
            continue
        assert register["meta"] == {"limit": 50, "offset": 0, "total": len(register["items"])}
    assert "risks_page" in _cited("listRisks", "200")


# --- #1345: a date on a day without hours, refused at the creation ------------------------------


def test_a_task_created_with_a_date_on_a_day_without_hours_is_refused_naming_the_next() -> None:
    refused = fixture("node_create_non_working_day")
    [field] = refused["fields"]
    assert (refused["status"], field["pointer"], field["code"]) == (
        422,
        "/task/start/date",
        "NON_WORKING_DAY",
    )
    # Judged on the default calendar, that of a task without labour line (WF-PLA-0010).
    assert field["params"] == mocknonworking.judged(mocknonworking.SATURDAY, default_calendar())
    assert "node_create_non_working_day" in _cited("createNode", "422")


# --- #1361: a paste aimed at a node withdrawn -------------------------------------------------


def test_a_paste_aimed_at_a_node_withdrawn_is_refused_whole_on_its_anchor() -> None:
    plan = fixture("paste_plan_amendment_target_removed")
    assert plan["accepted"] == 0
    assert plan["rejected"] == [{"row": 0, "column": "label", "code": "PASTE_TARGET_REMOVED"}]
    assert "PASTE_TARGET_REMOVED" in _schema("common.yaml", "ErrorCode")["enum"]
    rejection = _schema("schemas/revisions.yaml", "PasteRejection")
    assert "`PASTE_TARGET_REMOVED`" in rejection["description"]
    assert "paste_plan_amendment_target_removed" in _cited("previewPaste", "200")
    removed = [
        each for each in fixture("nodes_amendment")["items"] if each["difference"] == "removed"
    ]
    assert len(removed) == 1
    assert removed[0]["editable_fields"] == []


# --- #1379: the revisions of the project created today, the analysis failed ---------------------


def test_the_revision_103_is_listed_and_the_analysis_of_the_import_has_its_failure() -> None:
    listed = fixture("revisions_project_created")
    assert listed["items"] == [fixture("revision_without_tasks")]
    assert listed["meta"] == {"limit": 50, "offset": 0, "total": 1}
    assert (
        fixture("project_revision_opened")["current_revision_id"]
        == (listed["items"][0]["revision_id"])
    )
    assert "revisions_project_created" in _cited("listRevisions", "200")
    failed, running = fixture("task_import_analysis_failed"), fixture("import_analysing")["task"]
    assert (failed["task_id"], failed["kind"], failed["submitted_at"]) == (
        running["task_id"],
        running["kind"],
        running["submitted_at"],
    )
    assert (failed["status"], failed["problem"]["code"]) == ("failed", "INTERNAL_ERROR")
    assert "task_import_analysis_failed" in _cited("getBackgroundTask", "200")


# --- #1384, point 1: two risks the tests of the front derived ---------------------------------


def test_the_two_risks_are_risks_of_the_register_one_value_changed() -> None:
    items = {each["state"]: each for each in fixture("risks")["items"]}
    deactivated, uncited = fixture("risk_dismissed_category_deactivated"), fixture("risk_uncited")
    assert deactivated == {**items["dismissed"], "provision_cost_category_is_active": False}
    assert items["dismissed"]["provision_cost_category_is_active"] is True
    identified = items["identified"]
    assert {k: v for k, v in uncited.items() if k != "available_commands"} == {
        k: v for k, v in identified.items() if k != "available_commands"
    }
    delete = {each["command"]: each for each in uncited["available_commands"]}["delete"]
    assert (delete["is_available"], delete["missing_conditions"]) == (True, [])
    assert {"risk_dismissed_category_deactivated", "risk_uncited"} <= set(_cited("getRisk", "200"))


# --- #1401: the states of the list of the home, a preference ------------------------------------


def test_the_states_of_the_home_are_kept_in_the_filters_of_the_grid_of_its_list() -> None:
    grids = fixture("preferences_project_states")["grids"]
    assert list(grids) == ["projects"]
    states = grids["projects"]["filters"]["states"].split(",")
    known = _schema("schemas/projects.yaml", "ProjectState")["enum"]
    assert set(states) <= set(known)
    assert set(states) != {"pricing", "in_progress"}
    assert "preferences_project_states" in _cited("updateMyPreferences", "200")


# --- #870: the name of a contributor anonymised -----------------------------------------------


def test_a_contributor_anonymised_has_no_name_and_comes_after_the_others_of_its_kind() -> None:
    for name in ("Contributor", "ContributorSuggestion"):
        named = _schema("schemas/projects.yaml", name)["properties"]["display_name"]
        assert {"type": "null"} in named["anyOf"], name
    gone = {
        each["user_id"]
        for each in fixture("users_anonymized")["items"]
        if each["anonymized_at"] is not None
    }
    before, after = fixture("contributors"), fixture("contributors_anonymized")
    assert after["lock_version"] == before["lock_version"]
    rows = {each["user_id"]: each for each in before["items"]}
    assert len(after["items"]) == len(rows)
    for row in after["items"]:
        expected = (
            {**rows[row["user_id"]], "display_name": None}
            if row["user_id"] in gone
            else (rows[row["user_id"]])
        )
        assert row == expected
    last = after["items"][-1]
    assert (last["user_id"] in gone, last["display_name"]) == (True, None)
    assert "contributors_anonymized" in _cited("listContributors", "200")


# --- #1577: the creation of a project and the abandon of a revision in the journal --------------


def test_the_journal_inscribes_the_creation_of_the_witness_and_the_abandon_of_its_revision() -> (
    None
):
    actions = _schema("schemas/audit.yaml", "AuditAction")["enum"]
    order = ["project_create", "revision_mark", "revision_abandon"]
    assert all(name in actions for name in order)
    assert [actions.index(name) for name in order] == sorted(actions.index(name) for name in order)
    project = fixture("project")
    [created] = [
        each for each in fixture("audit_events")["items"] if each["action"] == "project_create"
    ]
    assert (created["occurred_at"], created["actor"]) == (
        project["audit"]["created_at"],
        project["audit"]["created_by"],
    )
    assert created["object"] == {
        "kind": "project",
        "object_id": project["project_id"],
        "label": project["label"],
        "revision": None,
    }
    assert created["params"] == {}
    abandoned = fixture("audit_events_revision_abandoned")["items"]
    head, rest = abandoned[0], abandoned[1:]
    after = fixture("project_without_current_revision")
    assert head["action"] == "revision_abandon"
    assert (head["occurred_at"], head["actor"]) == (
        after["audit"]["updated_at"],
        after["audit"]["updated_by"],
    )
    assert head["object"] == {
        "kind": "revision",
        "object_id": project["current_revision_id"],
        "label": None,
        "revision": None,
    }
    assert head["params"] == {}
    assert rest == fixture("audit_events_project")["items"]
    # A sequel of its own: neither its identifier nor its correlation is another sequel's.
    others = [
        fixture(name)["items"][0] for name in ("audit_events_exited", "audit_events_import_applied")
    ]
    assert head["audit_event_id"] not in {each["audit_event_id"] for each in others}
    assert head["correlation_id"] not in {each["correlation_id"] for each in others}
    assert "audit_events_revision_abandoned" in _cited("listAuditEvents", "200")


# --- #1566: the delay of payment, a change of a differential ------------------------------------


def test_a_line_whose_delay_of_payment_alone_changes_is_modified_by_it() -> None:
    changes = _schema("schemas/revisions.yaml", "NodeChange")["enum"]
    assert (
        changes.index("reestimated_amount")
        < changes.index("payment_delay_days")
        < (changes.index("parent"))
    )
    written = fixture("estimate_line_payment_delay_amendment")
    [line] = written["nodes"]
    assert (line["difference"], line["changes"]) == ("modified", ["payment_delay_days"])
    assert {(each["difference"], tuple(each["changes"])) for each in written["ancestors"]} == {
        ("modified", ())
    }


# --- #1531: the refusals of the undo and the redo ---------------------------------------------


def test_the_undo_and_the_redo_have_the_examples_of_their_refusals() -> None:
    later, again = fixture("undo_later_change"), fixture("redo_later_change")
    for refused in (later, again):
        assert (refused["code"], refused["status"]) == ("UNDO_CONFLICT", 409)
        # The object in conflict is named since US-0702/L1 (E-07, WF-IHM-0110).
        assert set(refused["params"]) == {"conflicting_object_id", "conflicting_object_label"}
    deleted = fixture("undo_restored_subproject_deleted")
    assert deleted["params"] == {"missing_condition": "restored_subproject_exists"}
    assert {"undo_later_change", "undo_restored_subproject_deleted"} <= set(
        _cited("undoLastChange", "409")
    )
    assert "redo_later_change" in _cited("redoLastUndo", "409")
