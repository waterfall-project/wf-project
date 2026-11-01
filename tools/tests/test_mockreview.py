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
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

from wftools import REPOSITORY, mockreview, mockwitness
from wftools.mockids import universe
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
    # The complement of the author of 2026-11-01: the rates of a category follow the grid.
    assert _cited("listHourlyRates", "404") == ["hourly_rates_not_readable"]
    assert fixture("hourly_rates_not_readable")["code"] == "NOT_FOUND"
    [auditor] = [role for role in fixture("access_roles") if role["label"] == "Auditeur"]
    assert "cost_settings.read" not in auditor["permissions"]
    said = _flat(_schemas("access.yaml")["PermissionCode"]["description"])
    for code in ("cost_settings.read", "resource_settings.read", "risk_settings.read"):
        assert f"`{code}`" in said, code
    assert "`listHourlyRates`" in said


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
    assert refused["fields"] == [
        {"pointer": "/cost_category_ids/1", "code": "UNKNOWN_COST_CATEGORY"}
    ]
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
    received = universe(mockreview.CREATED_UNDER_MILESTONE[1])
    assert fixture("node_create_under_milestone")["fields"][0]["params"]["node_id"] == received
    for schema, file in (
        ("ImportRejection", "exchanges.yaml"),
        ("PasteRejection", "revisions.yaml"),
    ):
        assert "`MILESTONE_HAS_NO_SUBTASK`" in _flat(_schemas(file)[schema]["description"]), schema


def test_a_summary_awaiting_its_own_lines_says_it_by_its_facet() -> None:
    # F-05, #1774: computed, always rendered, required; the ancestors a write renders and the
    # cards of the Kanban carry it by the facet. The variant reads the Vérif of WF-PLA-0040 — « une
    # récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre porte
    # un reste à engager de 500 est démarrée et signalée ».
    facet = _schemas("revisions.yaml")["TaskFacet"]
    assert "awaiting_own_lines" in facet["required"]
    assert facet["properties"]["awaiting_own_lines"]["type"] == "boolean"
    assert "nodes_awaiting_own_lines" in _cited("listNodes", "200")
    read = fixture("nodes_awaiting_own_lines")["items"]
    summary, own = read[0], read[1]
    assert (summary["task"]["progress"], summary["task"]["awaiting_own_lines"]) == (
        "started",
        True,
    )
    assert own["estimate_line"]["reestimated_amount"] == "500.00"
    below = [node["task"] for node in read[2:] if node["kind"] == "task"]
    assert below
    assert {(each["progress"], each["awaiting_own_lines"]) for each in below} == {
        ("completed", False)
    }
    # Every task of the witness renders it, false: no summary of the witness bears own lines.
    for name in ("nodes", "startable_tasks"):
        tasks = [each for each in _walk(fixture(name)) if "is_summary" in each]
        assert tasks, name
        assert {each["awaiting_own_lines"] for each in tasks} == {False}, name


COMPLETED_REFUSED = {
    "createNode": "estimate_line_completed_refused",
    "updateEstimateLine": "estimate_line_completed_update_refused",
    "deleteNode": "node_delete_line_completed_refused",
    "moveNodes": "nodes_move_completed_refused",
}


def test_a_line_of_a_completed_task_of_the_main_structure_is_refused_by_its_task() -> None:
    # F-01, #1766: on the main structure, a line is neither created under a task completed, nor
    # modified, deleted, or moved to it or from it — the task is reopened from the Kanban first
    # (WF-DEV-0050, WF-RAE-0040, WF-RAE-0030). The phase of the project refuses no write (C-358):
    # no operation names `project_before_in_progress`.
    nodes = {each["node_id"]: each for each in fixture("nodes_core")["items"]}
    under = nodes[universe(mockreview.COMPLETED_UNDER)]
    assert under["task"]["progress"] == "completed"
    correlations: set[str] = set()
    for operation, name in COMPLETED_REFUSED.items():
        assert name in _cited(operation, "409"), operation
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": "task_not_completed"}, name
        correlations.add(refused["correlation_id"])
        said = _flat(_operations()[operation]["responses"]["409"]["description"])
        assert "`task_not_completed`" in said, operation
        assert "`project_before_in_progress`" not in said, operation
        assert "différentiel" in said, operation
    assert len(correlations) == len(COMPLETED_REFUSED)
    moved = nodes[universe(mockreview.COMPLETED_MOVED)]
    assert nodes[moved["parent_id"]]["task"]["progress"] != "completed"


def test_the_line_of_a_completed_task_names_no_field_on_the_main_structure_alone() -> None:
    # F-01, #1766: no field, its label included, its remaining to commit said apart; the
    # differential names them, for the amendment to rebudget the line (WF-REV-0050, #1765).
    nodes = fixture("nodes_core")["items"]
    tasks = {each["node_id"]: each["task"] for each in nodes if each["kind"] == "task"}
    lines = [each for each in nodes if each["kind"] == "estimate_line"]
    for line in lines:
        closed = tasks[line["parent_id"]]["progress"] == "completed"
        assert (line["editable_fields"] == []) == closed, line["node_id"]
    [line] = [each for each in lines if each["node_id"] == universe(mockreview.COMPLETED_LINE)]
    assert line["estimate_line"]["remaining_entry"]["missing_conditions"] == ["task_not_completed"]
    rebudgeted = fixture("estimate_line_rebudgeted_amendment")
    [written] = rebudgeted["nodes"]
    assert written["lineage_id"] == line["lineage_id"]
    assert "estimate_line.unit_disbursement" in written["editable_fields"]
    assert "estimate_line_rebudgeted_amendment" in _cited("updateEstimateLine", "200")
    said = _flat(_schemas("revisions.yaml")["PasteRejection"]["description"])
    assert "`task_not_completed`" in said


def test_the_nodes_an_occurrence_merges_bear_their_risk_and_are_filtered_by_it() -> None:
    # #1761: `origin_risk_id`, read-only, required; the two filters shared by the two readings
    # of the tree; a risk that has not occurred is refused by its rank in the list.
    node = _schemas("revisions.yaml")["Node"]
    assert "origin_risk_id" in node["required"]
    assert node["properties"]["origin_risk_id"]["readOnly"] is True
    for operation in ("listNodes", "compareRevisions"):
        refs = {each.get("$ref", "") for each in _parameters(operation)}
        assert "../components/parameters.yaml#/NodeIsFromRiskFilter" in refs, operation
        assert "../components/parameters.yaml#/NodeOriginRiskFilter" in refs, operation
        assert "nodes_origin_risk_unknown" in _cited(operation, "422"), operation
    occurred = universe(mockwitness.DELIVERY_DELAY_RISK)
    merged = {each["node_id"] for each in fixture("nodes_risk_occurred")["items"]}
    found = fixture("nodes_from_risk")["items"]
    assert {each["node_id"] for each in found if each["origin_risk_id"] == occurred} == merged
    [ancestor] = [each for each in found if each["origin_risk_id"] is None]
    assert ancestor["node_id"] == universe(mockwitness.N.CONTROL_STATION)
    assert all(each["origin_risk_id"] is None for each in fixture("nodes_core")["items"][:3])
    refused = fixture("nodes_origin_risk_unknown")
    assert refused["fields"][0]["code"] == "UNKNOWN_RISK"


def test_an_occurred_risk_shows_the_reestimate_of_its_lines_beside_its_cost() -> None:
    # #1761: the re-estimate of the lines it merged, and its sum to the coverage, outside the
    # variance, which stays reserve minus (remaining + occurred cost).
    risks = {each["risk_id"]: each for each in fixture("risks")["items"]}
    lines = [each for each in fixture("nodes_from_risk")["items"] if each["kind"] != "task"]
    total = sum(Decimal(each["estimate_line"]["reestimated_amount"]) for each in lines)
    for risk in risks.values():
        assert (risk["occurred_reestimated_amount"] is None) == (risk["state"] != "occurred")
    [occurred] = [each for each in risks.values() if each["state"] == "occurred"]
    assert Decimal(occurred["occurred_reestimated_amount"]) == total
    coverage = fixture("risk_coverage")
    assert coverage["occurred_reestimated"] == occurred["occurred_reestimated_amount"]
    variance = Decimal(coverage["reserve"]) - Decimal(coverage["remaining_provisions"])
    assert Decimal(coverage["coverage_variance"]) == variance - Decimal(coverage["occurred_cost"])


def test_the_own_estimate_of_the_occurred_risk_has_one_root_placed_last_under_its_bearer() -> None:
    # H-03, #1788: 541 is the one root of the own estimate of 752, not an envelope.
    estimate = fixture("nodes_risk_estimate_occurred")["items"]
    roots = [each for each in estimate if each["parent_id"] is None]
    occurred = fixture("nodes_risk_occurred")["items"]
    assert [each["task"]["label"] for each in roots] == [occurred[0]["task"]["label"]]
    assert not occurred[0]["task"]["label"].startswith("Risque survenu")
    labels = [(each.get("task") or each["estimate_line"])["label"] for each in estimate]
    assert labels == [(each.get("task") or each["estimate_line"])["label"] for each in occurred]
    assert all(each["origin_risk_id"] is None for each in estimate)
    assert "nodes_risk_estimate_occurred" in _cited("listNodes", "200")


def test_the_identity_of_a_risk_and_its_provision_are_written_apart_on_one_counter() -> None:
    # H-02, #1782: the identity, a data of the project; the provision, an entry of the revision.
    update = _schemas("risks.yaml")["RiskUpdate"]["properties"]
    assert set(update) == {"label", "description", "mitigation_notes", "lock_version"}
    provision = _schemas("risks.yaml")["RiskProvisionUpdate"]
    assert set(provision["properties"]) == {
        "provision_cost_category_id",
        "provision_subproject_id",
        "provision_task_id",
        "lock_version",
    }
    said = _flat(_operations()["updateRisk"]["description"])
    assert "ne crée aucune révision" in said
    assert "`edit_risks`" in said
    assert "risk_provision_frozen" in _cited("updateRiskProvision", "409")
    assert "risk_provision_moved" in _cited("updateRiskProvision", "200")
    refusal = _flat(_operations()["updateRiskProvision"]["responses"]["409"]["description"])
    assert refusal.index("`risk_identified`") < refusal.index("`may_create_revision`")
    updated, moved = fixture("risk_updated"), fixture("risk_provision_moved")
    assert moved["lock_version"] == updated["lock_version"] + 1
    edit = _flat(_schemas("revisions.yaml")["RevisionCommand"]["description"])
    assert "`updateRiskProvision`" in edit


def test_the_register_filters_each_of_its_columns_and_totals_the_risks_retained() -> None:
    # H-01, #1785: bounds of each column of numbers, the period of the last review.
    names = {each.get("$ref", "").rsplit("/", 1)[-1] for each in _parameters("listRisks")}
    for column in ("Probability", "Severity", "ProvisionAmount", "OccurrenceCost"):
        assert {f"Risk{column}Min", f"Risk{column}Max"} <= names, column
    assert {"RiskLastReviewOnFrom", "RiskLastReviewOnTo"} <= names
    read = fixture("risks_filtered")
    bound = mockreview.FILTERED_PROVISION_MIN
    assert all(Decimal(each["provision_amount"]) >= bound for each in read["items"])
    assert read["meta"]["total"] == len(read["items"]) < len(fixture("risks")["items"])
    total = sum(Decimal(each["provision_amount"]) for each in read["items"])
    assert Decimal(read["totals"]["total"]) == total
    assert "risks_period_inverted" in _cited("listRisks", "422")


def test_an_import_says_its_commands_and_refuses_what_its_state_forbids() -> None:
    # I-01 to I-04, #1789, #1792: the state `refused`, the commands of an import and their
    # conditions, the refusals of the opening, the application and the abandonment.
    status = _schemas("exchanges.yaml")["Import"]["properties"]["status"]["enum"]
    assert status[-1] == "refused"
    detail = _schemas("exchanges.yaml")["ImportDetail"]
    assert {"report", "task", "available_commands"} <= set(detail["required"])
    assert "report" not in _schemas("exchanges.yaml")["Import"]["required"]
    for name, operation, condition in (
        ("import_open_terminal", "openImport", "project_not_terminal"),
        ("import_open_background_running", "openImport", "no_background_task_running"),
        ("import_open_may_create_revision", "openImport", "may_create_revision"),
        ("import_apply_expired", "applyImport", "import_awaiting_decision"),
        ("import_abandon_applied", "abandonImport", "import_not_applied"),
    ):
        assert name in _cited(operation, "409"), name
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == STATE, name
        assert refused["params"] == {"missing_condition": condition}, name
    said = _flat(_operations()["openImport"]["responses"]["409"]["description"])
    assert "déjà consommé" not in said
    assert said.index("`no_background_task_running`") < said.index("`may_create_revision`")
    refused = fixture("import_apply_refused_permission")
    assert (refused["status"], refused["expires_at"]) == ("refused", None)
    [apply, abandon] = refused["available_commands"]
    assert apply["missing_conditions"] == ["import_awaiting_decision"]
    assert abandon["is_available"] is True


def test_a_new_line_imported_under_a_completed_task_is_rejected_naming_the_task() -> None:
    # I-05, #1793: as its entry, by the condition, the task named by its lineage and its label.
    nodes = {each["node_id"]: each for each in fixture("nodes_core")["items"]}
    under = nodes[universe(mockreview.COMPLETED_UNDER)]
    [rejected] = fixture("import_remaining_completed_task")["report"]["rejected"]
    assert rejected["code"] == "STATE_FORBIDS_OPERATION"
    assert rejected["params"] == {
        "missing_condition": "task_not_completed",
        "tasks": [{"lineage_id": under["lineage_id"], "label": under["task"]["label"]}],
    }
    assert "remaining_completed_task" in str(_cited("getImport", "200"))


def test_the_fields_always_rendered_are_required() -> None:
    # G-03, #1780, with D-11, E-10, A-05 and I-06: required, nullable where they may be null.
    required = {
        ("portfolio.yaml", "PortfolioScope"): {"from", "to", "org_node_id"},
        ("portfolio.yaml", "PortfolioProjectRow"): {"code", "cost_index", "schedule_index"},
        ("indicators.yaml", "RemainingIndicators"): {"delta_to_previous_revision"},
        ("indicators.yaml", "EstimateIndicators"): {"provisions_identified"},
        ("indicators.yaml", "CurveSeries"): {"steps"},
        ("indicators.yaml", "Computable"): {"value", "reason"},
        ("indicators.yaml", "ComputableMoney"): {"value", "reason"},
        ("indicators.yaml", "AmountByKey"): {"label"},
        ("projects.yaml", "Project"): {"description", "code", "current_revision_id"},
        ("revisions.yaml", "Revision"): {"version_name", "description", "marked_at"},
        ("access.yaml", "Permission"): {"fbs_code"},
        ("platform.yaml", "OperationOutcome"): {"problem"},
        ("platform.yaml", "ComponentHealth"): {"version"},
    }
    for (file, name), fields in required.items():
        assert fields <= set(_schemas(file)[name]["required"]), name
    by_subproject = fixture("estimate_indicators")["by_subproject"]
    [unassigned] = [each for each in by_subproject if each["key"] == "unassigned"]
    assert unassigned["label"] is None
