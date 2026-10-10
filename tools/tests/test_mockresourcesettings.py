# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the writes of the resource settings: their refusals and their commands (EP-14/L42j).

And the code of a role, unique, and the projects that the refusal of a calendar names (EP-14/L42r).

They try the examples of the nodes, the roles and the calendars against the universe they
illustrate and against the contract, not the Vérif of a requirement: none cites one (WF-QUA-0010,
« un test qui ne couvre aucune exigence »).
"""

import json
import re
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockportfolio
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"

PATHS = API / "paths" / "reference.yaml"

ROLE_WRITES = (
    "resource_role_created",
    "resource_role_updated",
    "resource_role_reactivated",
    "resource_role_deactivated",
)
"""The roles written today, each answered whole, its code with it."""

PROJECTS_NAMED = ("updateResourceRole", "updateCalendar", "setDefaultCalendar")
"""The writes of the reference whose refusal `TASK_WITHOUT_WORKING_HOURS` names the projects in
cause by their label and code alone (WF-PLA-0010)."""

STRUCTURES = ("nodes", "volume/nodes_thousand")
"""The main structure of the witness project, its core and its whole, whose tasks bear the lines of
the roles: the main structure alone, the own estimates of the risks 204 and 206 have no example."""

REFUSED = {
    "org_node_move_cycle_refused": (("updateOrgNode",), [("/parent_id", "ORG_NODE_CYCLE")]),
    "resource_role_attachments_refused": (
        ("createResourceRole",),
        [
            ("/org_node_id", "UNKNOWN_ORG_NODE"),
            ("/cost_category_id", "LABOUR_CATEGORY_REQUIRED"),
            ("/calendar_id", "INACTIVE_REFERENCE_OBJECT"),
        ],
    ),
    "resource_role_update_refused": (
        ("updateResourceRole",),
        [
            ("/calendar_id", "INACTIVE_REFERENCE_OBJECT"),
            ("/capacity/headcount", "VALUE_OUT_OF_RANGE"),
        ],
    ),
    "calendar_hours_refused": (
        ("createCalendar", "updateCalendar"),
        [
            ("/weekly_hours/monday", "VALUE_OUT_OF_RANGE"),
            ("/weekly_hours/saturday", "VALUE_OUT_OF_RANGE"),
        ],
    ),
}
"""Each refusal by field of the resource settings: the operations that cite it, its fields."""

STALE = {
    "org_node_update_stale": ("updateOrgNode", "org_node_updated"),
    "resource_role_update_stale": ("updateResourceRole", "resource_role_updated"),
    "calendar_update_stale": ("updateCalendar", "calendar_updated"),
    "calendar_default_stale": ("setDefaultCalendar", "calendar_updated"),
}
"""Each stale write, its operation, and the write of another session whose version it names."""


def _cited(operation: str) -> set[str]:
    """Return the fixtures the contract cites under an operation of the reference."""
    text = PATHS.read_text(encoding="utf-8")
    block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
    return set(re.findall(r"fixtures/api/([a-z_]+)\.json", block))


def _calendars() -> dict[str, Entry]:
    return {c["calendar_id"]: c for c in fixture("calendars_with_inactive")["items"]}


def _block(operation: str) -> str:
    """Return the text of an operation of the reference, up to the next one."""
    text = PATHS.read_text(encoding="utf-8")
    return text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]


def _summary(name: str) -> str:
    text = (REPOSITORY / "fixtures" / "api" / f"{name}.json").read_text(encoding="utf-8")
    return json.loads(text)["summary"].lower()


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_each_refusal_by_field_names_its_fields_and_is_cited_by_its_operation(name: str) -> None:
    operations, fields = REFUSED[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in refused["fields"]] == fields
    for operation in operations:
        assert name in _cited(operation), operation


def test_a_node_under_its_descendant_and_a_role_given_deactivated_objects_are_refused() -> None:
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    # The technical direction (470), a root, is an ancestor of the wiring workshop (472).
    workshop = nodes[universe(472)]
    assert nodes[workshop["parent_id"]]["parent_id"] == universe(470)
    assert nodes[universe(470)]["parent_id"] is None
    # The category the summary names is outside labour; the calendar, deactivated, is not the one
    # the technician has, which a role keeps without refusal.
    categories = fixture("volume/cost_categories")["items"]
    summary = _summary("resource_role_attachments_refused")
    [named] = [c for c in categories if f"à la {c['label'].lower()}," in summary]
    assert named["cost_type_kind"] == "non_labor"
    [week] = [c for c in _calendars().values() if not c["is_active"]]
    assert week["label"].lower() in summary
    assert week["label"].lower() in _summary("resource_role_update_refused")
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    assert roles[universe(452)]["calendar_id"] != week["calendar_id"]


def test_each_bound_crossed_is_the_one_its_refusal_names_and_the_universe_holds() -> None:
    _, headcount = fixture("resource_role_update_refused")["fields"]
    assert headcount["params"] == {"minimum": "0"}
    assert "effectif de -1" in _summary("resource_role_update_refused")
    monday, saturday = fixture("calendar_hours_refused")["fields"]
    assert (monday["params"], saturday["params"]) == ({"maximum": "24"}, {"minimum": "0"})
    assert "25 heures le lundi et -7 le samedi" in _summary("calendar_hours_refused")
    for calendar in _calendars().values():
        assert all(0 <= Decimal(v) <= 24 for v in calendar["weekly_hours"].values())
    for role in fixture("resource_roles")["items"]:
        assert all(Decimal(v) >= 0 for v in role["capacity"].values())


@pytest.mark.parametrize(
    ("name", "listed", "key"),
    [
        ("org_node_code_taken", "org_nodes_with_inactive", "org_node_id"),
        ("resource_role_code_taken", "resource_roles", "resource_role_id"),
    ],
)
def test_a_node_or_a_role_taken_names_its_bearer_by_its_label(
    name: str, listed: str, key: str
) -> None:
    read = fixture(listed)
    entries = cast("list[Entry]", read["items"] if isinstance(read, dict) else read)
    objects = {entry[key]: entry for entry in entries}
    [code] = fixture(name)["fields"]
    bearer = objects[code["params"]["conflicting_object_id"]]
    # The list read without the deactivated objects does not show the bearer: its label names it.
    assert bearer["is_active"] is False
    assert code["params"]["conflicting_object_label"] == bearer["label"]


def test_a_calendar_taken_names_its_bearer_by_its_identifier_and_each_refusal_is_cited() -> None:
    [label] = fixture("calendar_label_taken")["fields"]
    assert list(label["params"]) == ["conflicting_object_id"]
    for operation, expected in (
        ("createOrgNode", "org_node_code_taken"),
        ("updateOrgNode", "org_node_code_taken"),
        ("createResourceRole", "resource_role_code_taken"),
        ("updateResourceRole", "resource_role_code_taken"),
        ("createCalendar", "calendar_label_taken"),
        ("updateCalendar", "calendar_label_taken"),
    ):
        assert expected in _cited(operation), operation


def test_each_role_bears_a_code_of_its_own_that_its_writes_keep() -> None:
    # WF-REF-0090: « Un rôle de ressource porte un code unique et un libellé ».
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    codes = [role["code"] for role in roles.values()]
    assert len(set(codes)) == len(codes)
    assert all(1 <= len(code) <= 20 for code in codes)
    cascaded = fixture("org_node_deactivated")["resource_roles"]
    for role in [*(fixture(name) for name in ROLE_WRITES), *cascaded]:
        read = roles.get(role["resource_role_id"])
        if read is None:
            # The role created today, under a code no other role bears.
            assert role["code"] not in codes, role["label"]
            assert role["code"] in _summary("resource_role_created").upper()
        else:
            assert role["code"] == read["code"], role["label"]
    # The code taken is that of a role of the list, deactivated.
    [taken] = fixture("resource_role_code_taken")["fields"]
    assert roles[taken["params"]["conflicting_object_id"]]["code"].lower() in _summary(
        "resource_role_code_taken"
    )


def test_the_roles_are_searched_filtered_and_sorted_by_their_code() -> None:
    listing = _block("listResourceRoles")
    flat = " ".join(listing.split())
    assert "porte sur le libellé et sur le code du rôle" in flat
    assert "\n      - name: code\n        in: query\n" in listing
    sort = listing.split("- name: sort_by", 1)[1]
    assert "\n            - code\n" in sort


def test_the_refusal_of_a_calendar_names_each_project_by_its_label_and_its_code_alone() -> None:
    # WF-PLA-0010: the refusal names « pour chaque projet en cause, son libellé et, lorsqu'il est
    # renseigné, son code, sans autre détail » — a project the manager may not read included: no
    # task, no identifier (#762, option (a)). A seizure in a revision names its tasks still.
    common = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    problem = " ".join(common.split("\nProblem:\n", 1)[1].split("\n\n", 1)[0].split())
    tasks = problem.split("`tasks` pour une saisie d'une révision", 1)[1].split("`projects`", 1)[0]
    assert tasks.startswith(
        " — `createNode`, `updateEstimateLine`, `moveNodes`, `mergeCostStructure`, et le motif"
        " d'une ligne collée ou importée — "
    )
    assert "(`project_id`, `node_id`, `label`)" in tasks
    assert "project_label" not in tasks
    exchanges = (API / "components" / "schemas" / "exchanges.yaml").read_text(encoding="utf-8")
    rejection = " ".join(
        exchanges.split("\nImportRejection:\n", 1)[1].split("properties:", 1)[0].split()
    )
    assert (
        "(`resource_role_ids`, `tasks`, chaque tâche par `project_id`, `node_id` et `label`)"
        in (rejection)
    )
    projects = problem.split("`projects` pour une modification du référentiel", 1)[1]
    assert projects.startswith(
        " qui produirait le même effet (`updateCalendar`, `setDefaultCalendar`,"
        " `updateResourceRole`), un élément par projet en cause, par son libellé et son code"
        " (`project_label`, `project_code`, nul pour un projet sans code), sans identifiant ni"
        " tâche"
    )
    for operation in PROJECTS_NAMED:
        refusals = " ".join(_block(operation).split("'422':", 1)[1].split("content:", 1)[0].split())
        assert "`TASK_WITHOUT_WORKING_HOURS`" in refusals, operation
        assert "`params.projects`" in refusals, operation
        assert "(`project_label`, `project_code`), sans identifiant ni tâche" in refusals, operation
        assert "params.tasks" not in refusals, operation


def _roles_by_task(structure: str) -> dict[str, set[str]]:
    """Return the roles of the labour lines of each task of a structure of the witness."""
    found: dict[str, set[str]] = {}
    for node in cast("list[Entry]", fixture(structure)["items"]):
        line = cast("Entry | None", node.get("estimate_line"))
        if line is not None and line.get("resource_role_id"):
            found.setdefault(node["parent_id"], set()).add(line["resource_role_id"])
    return found


def test_the_refusal_of_a_calendar_names_its_roles_by_their_identifiers_alone() -> None:
    # The session of the three writes may read every role, deactivated ones included, and a seizure
    # in a revision knows the label of its roles by its lines: identifiers suffice, unlike the
    # refusals of the cost settings, whose screen does not read the deactivated roles (revue 3).
    common = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    problem = " ".join(common.split("\nProblem:\n", 1)[1].split("\n\n", 1)[0].split())
    assert (
        "par leurs seuls identifiants, que la session d'une modification du référentiel peut"
        " nommer, lisant tous les rôles (`listResourceRoles`, `include_inactive`), et une saisie"
        " d'une révision d'après ses lignes (`resource_role_label`)"
    ) in problem
    for operation in PROJECTS_NAMED:
        refusals = " ".join(_block(operation).split("'422':", 1)[1].split("content:", 1)[0].split())
        assert "`params.resource_role_ids`" in refusals, operation
        assert "resource_roles" not in refusals, operation


def test_a_calendar_emptied_of_its_hours_is_refused_naming_its_roles_and_its_projects() -> None:
    # The week of four days (482), emptied, leaves without an hour the tasks whose roles never work
    # together on another day: every role of the tasks that bear one on it, and each project of the
    # installation in cause by its label and code, nothing else — no task, no identifier
    # (WF-PLA-0010; option (b) of the revue 3, the standard week naming the thirty offers too).
    refused = fixture("calendar_update_without_hours")
    assert (refused["status"], refused["code"]) == (422, "TASK_WITHOUT_WORKING_HOURS")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert list(refused["params"]) == ["resource_role_ids", "projects"]
    emptied = universe(482)
    assert _calendars()[emptied]["is_default"] is False
    calendar = {r["resource_role_id"]: r["calendar_id"] for r in fixture("resource_roles")["items"]}
    # Task by task: every role of a task that bears at least one role of the week emptied.
    tasks = [roles for structure in STRUCTURES for roles in _roles_by_task(structure).values()]
    in_cause = {
        role
        for roles in tasks
        if any(calendar[role] == emptied for role in roles)
        for role in roles
    }
    assert refused["params"]["resource_role_ids"] == sorted(in_cause) == [universe(454)]
    # The projects of the installation in cause: the witness, whose current revision bears these
    # tasks, and the generated projects that employ one of these roles. The universe does not say
    # which projects in progress among the generated ones have a revision in progress; supposed:
    # those whose list shows a current estimate, the thirty offers in pricing. Either way none is in
    # cause, `role_shares` parting the labour of every generated project between 451 and 452 alone.
    projects = fixture("projects")["items"]
    known = {p["project_id"] for p in projects}
    witness = [p for p in projects if p["current_revision_id"] is not None]
    generated = [
        row
        for row in fixture("volume/portfolio_projects")["items"]
        if row["project_id"] not in known
    ]
    offers = [row for row in generated if row["current_estimate"] is not None]
    assert len(offers) == 30
    employing = [
        row for row in generated if set(mockportfolio.role_shares(row["project_id"])) & in_cause
    ]
    assert employing == []
    in_cause_projects = [*witness, *(row for row in offers if row in employing)]
    assert refused["params"]["projects"] == [
        {"project_label": p["label"], "project_code": p["code"]} for p in in_cause_projects
    ]
    assert all(
        set(each) == {"project_label", "project_code"} for each in refused["params"]["projects"]
    )
    assert "semaine de quatre jours" in _summary("calendar_update_without_hours")
    # Cited after the hours out of range, which stays the first, the fake back's.
    said = _block("updateCalendar").split("'422':", 1)[1].split("\n      '", 1)[0]
    cited = re.findall(r"fixtures/api/([a-z_]+)\.json", said)
    assert cited == ["calendar_hours_refused", "calendar_update_without_hours"]


def test_only_a_move_is_refused_under_a_deactivated_node() -> None:
    # WF-REF-0070 bounds the move: the body takes the parent read, and a deactivated node that keeps
    # its deactivated parent is modified; the move refused gives another parent than the one read.
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    renamed = fixture("org_node_renamed_under_inactive")
    read = nodes[renamed["org_node_id"]]
    assert (read["is_active"], nodes[read["parent_id"]]["is_active"]) == (False, False)
    assert renamed["label"] != read["label"]
    assert renamed["lock_version"] == read["lock_version"] + 1
    # Nothing else changes but who wrote it and when (#691).
    audit, written = dict(renamed["audit"]), dict(read["audit"])
    for key in ("updated_at", "updated_by"):
        audit.pop(key)
        written.pop(key)
    assert audit == written
    kept = ("label", "lock_version", "audit")
    assert {k: v for k, v in renamed.items() if k not in kept} == {
        k: v for k, v in read.items() if k not in kept
    }
    # Cited after the move, which stays the first example of the 200, the one the fake back serves.
    ok = _block("updateOrgNode").split("'200':", 1)[1].split("\n      '", 1)[0]
    cited = re.findall(r"fixtures/api/([a-z_]+)\.json", ok)
    assert cited == ["org_node_updated", "org_node_renamed_under_inactive"]
    # The workshop (472), refused under the office of automation studies (474), leaves its own.
    assert nodes[universe(472)]["parent_id"] != universe(474)
    assert not nodes[universe(474)]["is_active"]
    assert "bureau d'études automatismes" in _summary("org_node_move_refused")


def test_a_designation_already_made_answers_without_change_after_the_version() -> None:
    # The default calendar lists no designation; sent anyway, the version is checked first, and the
    # answer changes nothing: the contract says it where the commands and the operation are.
    schema = (REPOSITORY / "docs" / "api" / "components" / "schemas" / "reference.yaml").read_text(
        encoding="utf-8"
    )
    commands = schema.split("\nCalendarCommands:\n", 1)[1].split("\n\n", 1)[0]
    text = PATHS.read_text(encoding="utf-8")
    operation = text.split("operationId: setDefaultCalendar\n", 1)[1].split("parameters:", 1)[0]
    for said in (commands, operation):
        flat = " ".join(said.split())
        assert "répond 200 sans rien changer" in flat
        assert "412 si elle est périmée" in flat


@pytest.mark.parametrize("name", sorted(STALE))
def test_each_stale_write_names_the_version_another_session_wrote(name: str) -> None:
    operation, written = STALE[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (412, "STALE_LOCK_VERSION")
    assert refused["params"] == {"expected_lock_version": fixture(written)["lock_version"]}
    assert name in _cited(operation)


def test_each_calendar_but_the_default_lists_its_designation_available_when_active() -> None:
    calendars = [
        *_calendars().values(),
        *fixture("calendars")["items"],
        *(fixture(n) for n in ("calendar_created", "calendar_updated", "calendar_deactivated")),
        fixture("calendar_default"),
    ]
    for calendar in calendars:
        listed = [c for c in calendar["available_commands"] if c["command"] == "set_default"]
        missing = [] if calendar["is_active"] else ["calendar_active"]
        expected = [
            {"command": "set_default", "is_available": not missing, "missing_conditions": missing}
        ]
        assert listed == ([] if calendar["is_default"] else expected), calendar["label"]
    # The designation refused is that of the deactivated calendar, by the condition it misses.
    refused = fixture("calendar_default_refused")
    [week] = [c for c in _calendars().values() if not c["is_active"]]
    assert week["label"].lower() in _summary("calendar_default_refused")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "calendar_active"}
    assert "calendar_default_refused" in _cited("setDefaultCalendar")


def test_each_category_says_the_kind_of_its_nature_and_a_role_bears_one_of_labour() -> None:
    kinds = {n["cost_type_id"]: n["kind"] for n in fixture("cost_types_with_inactive")["items"]}
    categories = [
        *fixture("volume/cost_categories")["items"],
        *(fixture(n) for n in ("cost_category_created", "cost_category_updated")),
        fixture("cost_category_deactivated"),
    ]
    for category in categories:
        assert category["cost_type_kind"] == kinds[category["cost_type_id"]], category["code"]
    labour = {c["cost_category_id"] for c in categories if c["cost_type_kind"] == "labor"}
    assert {role["cost_category_id"] for role in fixture("resource_roles")["items"]} <= labour


def test_each_category_says_whether_its_nature_is_active_as_the_universe_reads_it() -> None:
    # `cost_type_is_active`, resolved at the reading (EP-14/L42p, revue 2): the natures of the
    # universe, never those of `cost_types_with_inactive`, where the disbursements are deactivated.
    natures = {n["cost_type_id"]: n for n in fixture("cost_types")["items"]}
    categories = [
        *fixture("volume/cost_categories")["items"],
        *(fixture(n) for n in ("cost_category_created", "cost_category_updated")),
        fixture("cost_category_deactivated"),
    ]
    for category in categories:
        nature = natures[category["cost_type_id"]]
        assert category["cost_type_is_active"] == nature["is_active"], category["code"]


def test_the_parent_is_required_to_modify_a_node() -> None:
    # An absent parent would read neither as the root nor as the parent read: the body is whole, a
    # root sends `null`, and « keeps its parent » is judged on the value sent (revue 2 of L42j).
    schema = (REPOSITORY / "docs" / "api" / "components" / "schemas" / "reference.yaml").read_text(
        encoding="utf-8"
    )
    block = re.split(r"\n(?=\S)", schema.split("\nOrgNodeUpdate:\n", 1)[1], maxsplit=1)[0]
    required = [
        {name.strip() for name in found.split(",")}
        for found in re.findall(r"required: \[([^\]]*)\]", block)
    ]
    assert {"lock_version", "parent_id"} in required
    # Redeclared in the branch, without which the generated client leaves it optional (revue 3).
    branch = block.split("required: [lock_version, parent_id]", 1)[1]
    assert "\n        parent_id:\n" in branch
    text = PATHS.read_text(encoding="utf-8")
    operation = text.split("operationId: updateOrgNode\n", 1)[1].split("operationId:", 1)[0]
    refusals = operation.split("'422':", 1)[1].split("content:", 1)[0]
    assert "`/parent_id` absent, par `VALUE_REQUIRED`" in " ".join(refusals.split())
