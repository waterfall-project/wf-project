# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the majors of the review of the contract of the 2026-10-31, as the contract follows.

The author decided each point (`docs/api/DECISIONS.md`, the sections « (US-0704, #1735, …) »), and
its issue « contrat » carries it to the contract, to its examples and to their generators
(``wftools.mockreview`` among them): these tests hold each example to the contract that cites it
and to the readings it derives from. They try the examples of the fake back, not the Vérif of a
requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »); the
criterion they bear is the US's own, « chaque majeur de la revue du 2026-10-31 […] porté au
contrat, à ses fixtures et à ses générateurs ».
"""

import json
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

from wftools import REPOSITORY, mockreview, mockwitness
from wftools.mocklists import PROJECT_STATES
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
STATE = (409, "STATE_FORBIDS_OPERATION")


@cache
def _operations() -> dict[str, Entry]:
    """Return every operation of the contract, by its identifier."""
    found: dict[str, Entry] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for item in cast("dict[str, Entry]", yaml.safe_load(text)).values():
            for operation in item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    found[cast("str", operation["operationId"])] = cast("Entry", operation)
    return found


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples an answer of an operation cites, by the name of their file."""
    answer = _operations()[operation]["responses"][status]
    [content] = cast("dict[str, Entry]", answer["content"]).values()
    return [Path(each["$ref"]).stem for each in content["examples"].values()]


def _schemas(file: str) -> Entry:
    text = (API / "components" / "schemas" / file).read_text(encoding="utf-8")
    return cast("Entry", yaml.safe_load(text))


def _parameters(operation: str) -> list[Entry]:
    return cast("list[Entry]", _operations()[operation].get("parameters", []))


def _flat(text: str) -> str:
    return " ".join(text.split())


def _walk(value: Any) -> list[Entry]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if isinstance(value, dict):
        entry = cast("Entry", value)
        return [entry, *(found for item in entry.values() for found in _walk(item))]
    return []


def test_an_account_is_created_without_a_role_and_given_its_roles_apart() -> None:
    # A-01, #1731: the creation carries no role; its 422 no longer names one.
    assert "access_role_ids" not in _schemas("access.yaml")["UserCreate"]["properties"]
    refused = fixture("user_creation_refused")
    assert [field["pointer"] for field in refused["fields"]] == ["/org_node_id"]
    refusal = _operations()["createUser"]["responses"]["422"]["description"]
    assert "access_role_ids" not in _flat(refusal)


def test_the_deletion_of_an_access_role_carries_its_counter_and_a_timeline_none() -> None:
    # A-02, #1733: the counter of the role, required, its 412 and its 422; the timeline, which has
    # no counter, by exception written in the README, in both languages.
    parameters = _parameters("deleteAccessRole")
    [counter] = [each for each in parameters if each.get("name") == "lock_version"]
    assert counter["required"] is True
    assert counter["schema"] == {"$ref": "../components/common.yaml#/LockVersion"}
    responses = _operations()["deleteAccessRole"]["responses"]
    assert responses["422"] == {"$ref": "../components/responses.yaml#/LockVersionInvalid"}
    assert _cited("deleteAccessRole", "412") == ["access_role_delete_stale"]
    assert all(each.get("name") != "lock_version" for each in _parameters("deleteTimeline"))
    for readme in ("README-fr.md", "README.md"):
        assert "(`deleteTimeline`)" in (API / readme).read_text(encoding="utf-8"), readme


def test_the_accounts_deactivated_are_read_under_the_permission_of_the_active_ones() -> None:
    # A-03, #1736: a parameter of its own, without the 403 of the reference's.
    parameters = _parameters("listUsers")
    assert {"$ref": "../components/parameters.yaml#/IncludeInactive"} not in parameters
    [own] = [each for each in parameters if each.get("name") == "include_inactive"]
    assert own["schema"] == {"type": "boolean", "default": False}
    assert "`users.read`" in _flat(own["description"])
    assert "403" not in _operations()["listUsers"]["responses"]


def test_a_local_account_lists_its_link_and_invitation_and_an_anonymised_one_refuses_them() -> None:
    # A-04, #1737: the two commands listed for a local account not anonymised, unavailable while
    # it is deactivated; an anonymised one lists neither, and is refused by `is_not_anonymized`.
    enum = _schemas("access.yaml")["UserCommand"]["enum"]
    assert enum[-2:] == ["create_password_link", "resend_invitation"]
    links = {"create_password_link", "resend_invitation"}
    for name in ("user_anonymized", "users_anonymized"):
        for account in [each for each in _walk(fixture(name)) if "available_commands" in each]:
            assert not links & {each["command"] for each in account["available_commands"]}, name
    for operation, name in (
        ("createPasswordSetupLink", "password_link_anonymized"),
        ("resendInvitation", "invitation_anonymized"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": "is_not_anonymized"}, name
        cited = _cited(operation, "409")
        assert cited.index(name) == 1, operation


def test_the_attachment_of_an_account_is_named_last_by_the_journal() -> None:
    # B-01, #1739: the field of the account a modification of its attachment changes.
    assert _schemas("audit.yaml")["AuditUserField"]["enum"][-1] == "org_node_id"
    administration = fixture("audit_events_administration")["items"]
    assert any(each["params"].get("fields") == ["org_node_id"] for each in administration)


def test_the_schedule_of_the_backups_is_refused_while_a_restoration_runs() -> None:
    # B-02, #1742: refused as the marking is, and kept through the restoration.
    refused = fixture("backup_schedule_refused_during_restore")
    assert (refused["status"], refused["code"]) == STATE
    assert refused["params"] == {"missing_condition": "no_restore_running"}
    assert _cited("setBackupSchedule", "409") == ["backup_schedule_refused_during_restore"]
    assert "`setBackupSchedule`" in _flat(_operations()["startRestore"]["description"])


def test_the_active_objects_of_the_reference_are_read_by_any_session_but_the_rates() -> None:
    # C-01, #1745: no 404 for the five lists of vocabulary; the grid of the rates under
    # `cost_settings.read`, which the auditor does not hold.
    for operation in (
        "listOrgNodes",
        "listResourceRoles",
        "listCalendars",
        "listCostTypes",
        "listCostCategories",
    ):
        assert "404" not in _operations()[operation]["responses"], operation
    assert _cited("getHourlyRateGrid", "404") == ["hourly_rate_grid_not_readable"]
    [auditor] = [role for role in fixture("access_roles") if role["label"] == "Auditeur"]
    assert "cost_settings.read" not in auditor["permissions"]
    said = _flat(_schemas("access.yaml")["PermissionCode"]["description"])
    for code in ("cost_settings.read", "resource_settings.read", "risk_settings.read"):
        assert f"`{code}`" in said, code


def test_the_list_of_the_projects_retains_every_state_it_names() -> None:
    # D-01, #1747: a parameter of its own; the project created today read under the six states.
    parameters = _parameters("listProjects")
    assert {"$ref": "../components/parameters.yaml#/ProjectStates"} in parameters
    assert {"$ref": "../components/parameters.yaml#/PortfolioStates"} not in parameters
    read = fixture("projects_with_created")
    created = fixture("project_created")
    assert read["meta"]["states"] == list(PROJECT_STATES)
    assert read["items"][0] == created
    assert read["items"][1:] == fixture("projects")["items"]
    assert "projects_with_created" in _cited("listProjects", "200")


def test_the_indicators_of_a_project_before_in_progress_are_refused_by_every_reading() -> None:
    # G-01, G-02, #1777, #1778: the 409 of the three other readings of the indicators.
    for operation in ("getIndexHistory", "getMilestoneTracking"):
        assert _cited(operation, "409") == ["project_indicators_not_in_progress"], operation
    said = _flat(_operations()["getIndexHistory"]["description"])
    assert "elle ne donne aucun point" in said
    assert "marquée avant l'état En cours — est un point non calculable" not in said


def test_a_refusal_of_a_state_names_the_condition_the_command_says() -> None:
    # J-01, #1795: no code of its own; the two codes leave the catalogue.
    catalogue = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    for code in ("CURRENT_REVISION_EXISTS", "REFERENCE_NOT_CORRECTABLE"):
        assert code not in catalogue, code
    for name, condition in (
        ("current_revision_exists", "no_current_revision"),
        ("reference_not_correctable", "reference_correctable"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": condition}, name


def test_every_value_too_long_bears_the_bound_of_its_field() -> None:
    # J-02, #1796: `max_length` beside every `VALUE_TOO_LONG`, the code of a subproject among them.
    bound = _schemas("projects.yaml")["DeclaredSubprojectCode"]["maxLength"]
    assert bound == mockreview.SUBPROJECT_CODE_BOUND
    assert fixture("subproject_code_too_long")["fields"] == [mockreview.too_long("/code", bound)]
    assert "subproject_code_too_long" in _cited("createSubproject", "422")
    found = 0
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        for entry in _walk(value):
            if entry.get("code") == "VALUE_TOO_LONG" and "pointer" in entry:
                found += 1
                params = cast("Entry", entry.get("params", {}))
                assert isinstance(params.get("max_length"), int), path.name
    assert found >= 6


def test_the_reestimate_after_a_merge_follows_the_reference_year() -> None:
    # E-02, #1754: the rule of the merge holds between two revisions of the same reference year;
    # between two years, the rates projected or updated move the re-estimate, not the budget.
    deltas = _schemas("revisions.yaml")["RevisionComparison"]["properties"]["amount_deltas"]
    properties = deltas["items"]["properties"]
    reestimated = _flat(properties["reestimated_delta"]["description"])
    assert "Entre deux révisions de même année de référence" in reestimated
    assert "Entre deux révisions d'années de référence différentes" in reestimated
    assert "(`comparison`, #1754)" in reestimated
    assert "quelle que soit l'année de référence" in _flat(
        properties["budgeted_delta"]["description"]
    )


def test_the_rate_update_carries_its_counter_and_categories_the_proposal_presents() -> None:
    # E-03, #1755: a body of its own, the counter required, the list never empty; a category the
    # proposal does not present refused by its rank in the list sent.
    body = _operations()["applyRateUpdate"]["requestBody"]["content"]["application/json"]
    assert body["schema"] == {"$ref": "../components/schemas/revisions.yaml#/RateUpdateApply"}
    schema = _schemas("revisions.yaml")["RateUpdateApply"]
    assert schema["required"] == ["cost_category_ids", "lock_version"]
    assert schema["properties"]["cost_category_ids"]["minItems"] == 1
    assert _cited("applyRateUpdate", "422") == ["rate_update_category_not_proposed"]
    refused = fixture("rate_update_category_not_proposed")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [{"pointer": "/cost_category_ids/1", "code": "UNKNOWN_COST_CATEGORY"}]
    proposed = {entry["cost_category_id"] for entry in fixture("rate_update")["categories"]}
    assert mockreview.NOT_PROPOSED_CATEGORY not in proposed


def test_a_merged_structure_is_not_taken_up_by_the_next_revision() -> None:
    # E-04, #1758: the creation of a revision says it, and a revision in progress never reads a
    # structure merged.
    said = _flat(_operations()["createRevision"]["description"])
    assert "Elle ne reprend pas les structures fusionnées" in said
    assert "Le devis propre d'un risque écarté, qui peut redevenir identifié, est repris" in said
    merged = _flat(
        _schemas("revisions.yaml")["CostStructure"]["properties"]["is_merged"]["description"]
    )
    assert "Une révision en cours ne porte donc jamais une structure fusionnée" in merged
    # The current revision bears no amendment merged; the one merged structure it reads is the
    # estimate of the risk that occurred since it was opened.
    current = [each for each in fixture("structures") if each["is_merged"]]
    assert [each["kind"] for each in current] == ["risk"]
    merged_before = [each for each in fixture("structures_amendments") if each["is_merged"]]
    assert [each["kind"] for each in merged_before] == ["amendment"]
    assert merged_before[0]["label"] not in {each["label"] for each in fixture("structures")}


def test_the_rates_of_a_new_revision_are_projected_by_default() -> None:
    # E-05, #1764: false or absent, the rates of the source projected to the new reference year.
    said = _flat(
        _schemas("revisions.yaml")["RevisionCreate"]["properties"]["apply_rate_update"][
            "description"
        ]
    )
    assert "projetés par le taux d'inflation du projet" in said
    assert "les autres gardent leur taux projeté" in said
    assert "projetés par le taux d'inflation du projet" in _flat(
        _operations()["createRevision"]["description"]
    )


def test_a_task_is_refused_under_a_milestone_on_its_parent() -> None:
    # F-04, #1771: a refusal of placement, a new motive, the milestone named; the import and the
    # paste refuse the line by the same motive.
    catalogue = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    assert "    - MILESTONE_HAS_NO_SUBTASK\n" in catalogue
    for operation, name in (
        ("createNode", "node_create_under_milestone"),
        ("moveNodes", "nodes_move_under_milestone"),
    ):
        assert name in _cited(operation, "422"), operation
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED"), name
        [field] = refused["fields"]
        assert (field["pointer"], field["code"]) == ("/parent_id", "MILESTONE_HAS_NO_SUBTASK")
        assert set(field["params"]) == {"node_id", "label"}, name
    received = mockwitness.universe(mockreview.CREATED_UNDER_MILESTONE[1])
    assert fixture("node_create_under_milestone")["fields"][0]["params"]["node_id"] == received
    for schema, file in (("ImportRejection", "exchanges.yaml"), ("PasteRejection", "revisions.yaml")):
        assert "`MILESTONE_HAS_NO_SUBTASK`" in _flat(_schemas(file)[schema]["description"]), schema
