# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the invariants that hold the examples of the universe together, across their files.

The examples written by hand — sessions, accounts, roles, imports and their reports, background
tasks, the state of the system and the backups — and those the generator writes must tell one
witness at one instant (#287; C3, C5, C6 and #421). They try the simplifications of the fake back
against one another, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui
ne couvre aucune exigence »).
"""

import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any, cast

import pytest

from wftools import (
    REPOSITORY,
    mockcore,
    mockcosts,
    mockcurves,
    mockhistory,
    mockids,
    mockindicators,
    mockwitness,
)
from wftools.mockids import PREFIX, universe
from wftools.mockwitness import (
    COSTS,
    JOURNAL,
    PAYMENT_DELAY,
    STUDIES_LINE,
    TODAY,
    fixture,
)

type Node = dict[str, Any]

_SEQUEL = timedelta(minutes=10)
"""How long after today the sequel of a write made today may run: a background task."""

BLOCKS = mockwitness.N.BLOCKS
"""The terminal blocks of the core, paid a month after their work, as the detailed studies."""


def _instant(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _every_example() -> dict[str, Any]:
    """Return the value of every example under the fixtures, the volumes included, by its path."""
    return {
        path.relative_to(mockwitness.FIXTURES).as_posix(): json.loads(
            path.read_text(encoding="utf-8")
        )["value"]
        for path in sorted(mockwitness.FIXTURES.rglob("*.json"))
    }


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read every example of the universe once."""
    return _every_example()


# --- The payment delays: the nodes render those the curve applies -------------------------------


def test_the_nodes_render_the_payment_delays_the_curve_of_the_disbursements_applies() -> None:
    reading = mockindicators.today()
    rendered = {
        int(node["node_id"].removeprefix(PREFIX)): node["estimate_line"]["payment_delay_days"]
        for node in mockwitness.fixture("nodes_core")["items"]
        if node["kind"] == mockcore.ESTIMATE_LINE
    }
    # Every line has its delay (WF-DEV-0020): in the core, a month for the subcontracting and the
    # terminal blocks, nought for the others, labour and provision included; drawn about it, a
    # month for every disbursement, nought for the labour.
    expected = {
        number: PAYMENT_DELAY if number in {STUDIES_LINE, BLOCKS} else 0 for number in rendered
    }
    assert rendered == expected
    for row in reading.lines:
        if row.number >= mockwitness.GENERATED:
            expected[row.number] = 0 if row.hours else PAYMENT_DELAY
    assert reading.delays == expected
    lines = [row.number for row in mockindicators.budgeted(reading)]
    flows = dict(zip(lines, mockcurves.budget_flows(reading, delays=True), strict=True))
    assert {number: flow.delay for number, flow in flows.items()} == {
        number: expected[number] for number in flows
    }


# --- The milestones tracked: one source, the inscriptions of the nodes -------------------------


def test_the_milestones_tracked_are_those_the_nodes_inscribe_to_the_time_time_tracking(
    examples: dict[str, Any],
) -> None:
    # One source for the milestones tracked (`mockwitness.TRACKED`, revue d'EP-02/L24): the chart
    # follows the very lineages whose nodes carry the inscription `milestone_tracking`, in the
    # order of the plan (WF-PLA-0060, WF-IND-0090).
    inscribed = [
        node["lineage_id"]
        for node in examples["volume/nodes_thousand.json"]["items"]
        if node["kind"] == mockcore.TASK
        and any(entry["kind"] == "milestone_tracking" for entry in node["task"].get("tracking", []))
    ]
    followed = [entry["lineage_id"] for entry in examples["milestone_tracking.json"]["milestones"]]
    assert followed == inscribed
    assert inscribed == [mockcore.lineage(number) for number in mockwitness.TRACKED]


# --- The structures a risk cites: those of the revision it is read in (#461) ---------------------


def test_a_risk_read_in_a_revision_cites_the_structures_of_that_revision(
    examples: dict[str, Any],
) -> None:
    # A structure has an identifier of its own revision (WF-DAT-0030): the risks read in the
    # current revision cite its own structures, never those the reference bore.
    current = {entry["structure_id"]: entry for entry in examples["structures.json"]}
    reference = {entry["structure_id"] for entry in examples["structures_amendments.json"]}
    assert not current.keys() & reference
    cited = [
        examples["risk.json"],
        examples["risk_occurred_detail.json"],
        *examples["risks.json"]["items"],
    ]
    for risk in cited:
        structure = current[risk["structure_id"]]
        assert structure["revision_id"] == mockhistory.CURRENT
        assert (structure["kind"], structure["risk_id"]) == ("risk", risk["risk_id"])
        # The own estimate of a risk occurred is merged into the main structure (WF-RIS-0060).
        assert structure["is_merged"] is (risk["state"] == "occurred")


# --- The answers of the writes (#421) ----------------------------------------------------------


def test_two_answers_never_render_one_node_at_one_version_with_two_contents(
    examples: dict[str, Any],
) -> None:
    rendered: dict[tuple[str, int], tuple[str, Node]] = {}
    clashes: list[tuple[str, str, str]] = []
    for name, value in examples.items():
        if not (isinstance(value, dict) and "structure_lock_version" in value):
            continue
        for node in cast("list[Node]", cast("Node", value).get("nodes", [])):
            key = (node["node_id"], node["lock_version"])
            if key in rendered and rendered[key][1] != node:
                clashes.append((node["node_id"], rendered[key][0], name))
            rendered.setdefault(key, (name, node))
    assert clashes == []


def test_the_paste_follows_the_label_entered_and_the_reestimate_the_hours_entered() -> None:
    entered, applied = (
        mockwitness.fixture(name) for name in ("estimate_line_entered", "paste_applied")
    )
    updated, reestimated = (
        mockwitness.fixture(name) for name in ("estimate_line_updated", "remaining_reestimated")
    )
    for first, then in ((entered, applied), (updated, reestimated)):
        line = first["nodes"][0]
        follow = next(node for node in then["nodes"] if node["node_id"] == line["node_id"])
        assert follow["lock_version"] == line["lock_version"] + 1
        assert then["structure_lock_version"] == first["structure_lock_version"] + 1


# --- The accounts and the sessions (C6) ---------------------------------------------------------


def test_each_session_is_of_a_user_the_accounts_list_with_the_roles_it_holds(
    examples: dict[str, Any],
) -> None:
    users = {user["user_id"]: user for user in fixture("users")["items"]}
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}
    contributors = {each["user_id"] for each in fixture("contributors")["items"]}
    for name, value in examples.items():
        if not (name.startswith("session") and isinstance(value, dict) and "user" in value):
            continue
        session = cast("Node", value)
        user = session["user"]
        listed = users[user["user_id"]]
        assert listed["access_role_ids"] == user["access_role_ids"], name
        assert (listed["last_name"], listed["first_name"]) == (
            user["last_name"],
            user["first_name"],
        ), name
        granted = {
            permission
            for role in user["access_role_ids"]
            for permission in roles[role]["permissions"]
        }
        assert set(session["permissions"]) == granted, name
        # A session that reads the witness without reading every project is a contributor's
        # (WF-PRJ-0060, WF-ADM-0110).
        if "revisions.read" in granted and "all_projects_read" not in granted:
            assert user["user_id"] in contributors, name
    for role_id, role in roles.items():
        held = [user for user in users.values() if role_id in user["access_role_ids"]]
        assert role["holder_count"] == len(held), role["label"]


def test_the_last_administrator_has_its_deactivation_alone_unavailable() -> None:
    # The accounts are read by Camille Martin, who may modify them: each carries the command that
    # changes its state and the attribution of its roles. The one active account that holds the
    # permissions to modify the accounts and the access roles has its deactivation unavailable,
    # the condition `last_administrator` missing (WF-ADM-0120); giving it more roles stays
    # possible, and every other command listed is available.
    roles = {role["access_role_id"]: role for role in fixture("access_roles")}

    def administers(user: Node) -> bool:
        held = {p for role in user["access_role_ids"] for p in roles[role]["permissions"]}
        return user["is_active"] and {"users.write", "access_roles.write"} <= held

    users = fixture("users")["items"]
    administrators = [user["user_id"] for user in users if administers(user)]
    assert administrators == [universe(301)]
    listed = {user["user_id"]: user for user in users}
    for user in [*users, *fixture("users_page")["items"]]:
        assert user["available_commands"] == listed[user["user_id"]]["available_commands"]
        last = user["user_id"] in administrators
        unmet = ["last_administrator"] if last else []
        assert user["available_commands"] == [
            {
                "command": "deactivate" if user["is_active"] else "reactivate",
                "is_available": not last,
                "missing_conditions": unmet,
            },
            {"command": "set_access_roles", "is_available": True, "missing_conditions": []},
        ], user["last_name"]


def test_the_refusals_of_the_last_administrator_say_what_its_commands_say() -> None:
    # The deactivation of Camille Martin, which her command says unavailable beforehand, is
    # refused by the condition the command misses; the attribution of her roles, offered because
    # giving her more stays possible, is refused by `LAST_ADMINISTRATOR` alone when the roles sent
    # would take a permission away, as is the modification of the role she holds (WF-ADM-0120).
    [camille] = [user for user in fixture("users")["items"] if user["user_id"] == universe(301)]
    commands = {each["command"]: each for each in camille["available_commands"]}
    deactivate, attribute = commands["deactivate"], commands["set_access_roles"]
    deactivation = fixture("user_deactivation_refused")
    assert not deactivate["is_available"]
    assert deactivation["code"] == "STATE_FORBIDS_OPERATION"
    assert deactivation["status"] == 409
    assert [deactivation["params"]["missing_condition"]] == deactivate["missing_conditions"]
    assert attribute["is_available"]
    assert attribute["missing_conditions"] == []
    for name in ("user_access_roles_refused", "access_role_update_refused"):
        refusal = fixture(name)
        assert (refusal["code"], refusal["status"]) == ("LAST_ADMINISTRATOR", 409), name
        assert "params" not in refusal, name


def test_an_active_object_is_refused_under_a_deactivated_node_by_its_field() -> None:
    # WF-REF-0080: the office of automation studies (474) is deactivated, the wiring workshop
    # (472) active; creating a node or a role under the first, or moving the second under it, is
    # refused on the field that names it, by `INACTIVE_REFERENCE_OBJECT` (#293, #547).
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    assert nodes[universe(474)]["is_active"] is False
    assert nodes[universe(472)]["is_active"] is True
    for name, pointer in (
        ("org_node_creation_refused", "/parent_id"),
        ("org_node_move_refused", "/parent_id"),
        ("resource_role_creation_refused", "/org_node_id"),
    ):
        refusal = fixture(name)
        assert (refusal["code"], refusal["status"]) == ("VALIDATION_FAILED", 422), name
        assert refusal["fields"] == [{"pointer": pointer, "code": "INACTIVE_REFERENCE_OBJECT"}]


def test_the_account_of_the_session_is_written_alike_wherever_it_is_read() -> None:
    audits: list[tuple[Node, int]] = []
    for name in ("session", "me", "users"):
        value = fixture(name)
        accounts = value["items"] if "items" in value else [value.get("user", value)]
        mine = next(each for each in accounts if each["user_id"] == universe(301))
        audits.append((mine["audit"], mine["lock_version"]))
        assert _instant(mine["audit"]["updated_at"]) <= TODAY, name
    assert all(each == audits[0] for each in audits)


# --- The actual costs (C3) ----------------------------------------------------------------------


CHARGED = (
    "subprojects",
    "subprojects_by_label",
    "subproject_updated",
    "subprojects_with_actual_costs",
    "subproject_created",
)
"""The examples that render a subproject, each confronted to the lines imputed to it: the lists
read today, the one a rename answers, and the subproject created today under a code lines already
bore (#625). Otherwise the row read anew would become deletable in the mockup."""


def test_both_subprojects_of_the_witness_are_charged() -> None:
    # The screens of the control station, and the invoices of the drawn tasks of the lots « Ligne
    # d'essais » completed: both subprojects are charged (EP-14/L45a).
    imputed = {mockcosts.imputed(line) for line in mockcosts.lines()}
    assert imputed == {None, universe(801), universe(802)}


@pytest.mark.parametrize("name", CHARGED)
def test_a_subproject_has_actual_costs_when_a_line_is_imputed_to_it(name: str) -> None:
    # A line is imputed to the subproject of its code the day it is created (WF-CRE-0020).
    lines = mockcosts.lines()
    codes = {line.code for line in lines}
    imputed = {mockcosts.imputed(line) for line in lines}
    value = fixture(name)
    subprojects = cast("list[Node]", value if isinstance(value, list) else [value])
    for subproject in subprojects:
        charged = subproject["code"] in codes
        assert subproject["has_actual_costs"] is charged, (name, subproject["code"])
        if name != "subproject_created":
            assert (subproject["subproject_id"] in imputed) is charged, (name, subproject["code"])


def test_each_line_is_dated_in_the_period_of_each_import_that_brought_it_and_before_it() -> None:
    for line in mockcosts.lines():
        creating = line.imports[0]
        for each in line.imports:
            start, end = each.period
            assert line.on <= each.event.on, line.document
            assert start is None or start <= line.on, line.document
            assert end is None or line.on <= end, line.document
        assert [each.event.instant for each in line.imports] == sorted(
            each.event.instant for each in line.imports
        )
        if line.excluded is not None:
            assert creating.event.instant < line.excluded[0] < TODAY


def test_each_import_of_the_journal_is_an_import_of_the_exchanges_applied_before_it() -> None:
    imports = {item["import_id"]: item for item in fixture("imports")["items"]}
    for entry in JOURNAL:
        applied = imports[mockids.hex_identifier(entry.exchange)]
        assert (applied["kind"], applied["status"]) == ("actual_costs", "applied")
        assert _instant(applied["created_at"]) < entry.event.instant
    assert [item["status"] for item in imports.values() if item["kind"] == "actual_costs"].count(
        "applied"
    ) == len(JOURNAL)


def test_an_import_expires_a_day_after_its_analysis_and_is_said_expired_once_past(
    examples: dict[str, Any],
) -> None:
    for item in fixture("imports")["items"]:
        lasted = _instant(item["expires_at"]) - _instant(item["created_at"])
        assert timedelta(hours=24) <= lasted <= timedelta(hours=24, minutes=5), item["filename"]
        if item["status"] == "expired":
            assert _instant(item["expires_at"]) <= TODAY, item["filename"]
        if item["status"] == "analysed":
            assert _instant(item["expires_at"]) > TODAY, item["filename"]
    expiries: dict[str, set[str]] = defaultdict(set)
    for item in fixture("imports")["items"]:
        expiries[item["import_id"]].add(item["expires_at"])
    for name, value in examples.items():
        if not (isinstance(value, dict) and "import_id" in value and "task" in value):
            continue
        item = cast("Node", value)
        expiries[item["import_id"]].add(item["expires_at"])
        finished = item["task"]["finished_at"]
        if item["task"]["kind"] == "import_analysis" and finished is not None:
            expected = mockhistory.stamp(_instant(finished) + timedelta(hours=24))
            assert item["expires_at"] == expected, name
    # An import has one expiry, whichever reading tells it.
    assert {key: found for key, found in expiries.items() if len(found) > 1} == {}


# --- The reports of the imports aim at the tree -------------------------------------------------


def test_each_report_names_the_lineages_of_the_core_by_their_labels(
    examples: dict[str, Any],
) -> None:
    labels = {
        cast("Node", row.node)["lineage_id"]: row.label for row in mockcore.core(mockwitness.CORE)
    }
    documents = {line.document for line in COSTS}
    reports = [
        (name, cast("Node", value)["report"])
        for name, value in examples.items()
        if isinstance(value, dict) and isinstance(cast("Node", value).get("report"), dict)
    ]
    assert reports
    for name, report in reports:
        named = [*report["differences"], *report["date_mismatches"], *report["completed_tasks"]]
        for each in named:
            if each.get("target") == "actual_cost_line":
                assert each["label"] in documents, name
            elif each["lineage_id"] is not None:
                assert labels[each["lineage_id"]] == each["label"], name


# --- The background tasks (C5) ------------------------------------------------------------------


def test_the_background_tasks_run_each_at_its_own_instant_within_minutes_after_the_write_of_today(
    examples: dict[str, Any],
) -> None:
    submitted: dict[str, set[str]] = defaultdict(set)
    for value in examples.values():
        for task in _tasks(value):
            submitted[task["submitted_at"]].add(task["task_id"])
            # A task follows the write that launches it: an analysis this morning or before, the
            # sequel of a write made at 14:05 within minutes after (#287).
            assert _instant(task["submitted_at"]) <= TODAY + _SEQUEL
            if task["finished_at"] is not None:
                assert task["submitted_at"] < task["finished_at"]
                assert _instant(task["finished_at"]) <= TODAY + _SEQUEL
    assert {instant: ids for instant, ids in submitted.items() if len(ids) > 1} == {}


def _tasks(value: Any) -> list[Node]:
    """Return each background task a value read from JSON carries."""
    if isinstance(value, list):
        return [task for item in cast("list[Any]", value) for task in _tasks(item)]
    if not isinstance(value, dict):
        return []
    fields = cast("Node", value)
    own = [fields] if {"task_id", "submitted_at"} <= fields.keys() else []
    return own + [task for item in fields.values() for task in _tasks(item)]


# --- The state of the system and the backups, today ---------------------------------------------


def test_the_state_of_the_system_is_read_now_and_names_the_last_backup_of_the_list() -> None:
    backups = fixture("backups")["items"]
    scheduled = max(each["taken_at"] for each in backups if each["origin"] == "scheduled")
    days = sorted(
        date.fromisoformat(each["taken_at"][:10])
        for each in backups
        if each["origin"] == "scheduled"
    )
    assert days[-1] == TODAY.date()
    assert all((later - earlier).days == 1 for earlier, later in pairwise(days))
    for name in ("system_status", "system_status_backup_failed", "system_status_storage_full"):
        status = fixture(name)
        checked = {_instant(each["checked_at"]) for each in status["components"]}
        assert all(at.date() == TODAY.date() and at <= TODAY for at in checked), name
        assert status["last_backup"]["at"] == scheduled, name


def test_the_external_copy_names_a_location_the_installation_declares() -> None:
    # #488: the schedule, the test of a location and the alert of a copy failed each name a
    # location of `external_backup_locations`, never one of their own; an installation without a
    # location has none to name.
    declared = {each["name"] for each in fixture("external_backup_locations")}
    assert fixture("external_backup_locations_none") == []
    for name in ("backup_schedule", "backup_schedule_disabled"):
        assert fixture(name)["external_copy"]["location"] in declared, name
    assert "external_copy" not in fixture("backup_schedule_weekly")
    for name in ("external_backup_location_tested", "external_backup_location_test_failed"):
        tested = fixture(name)
        assert tested["location"] in declared, name
        assert _instant(tested["tested_at"]) == TODAY, name
    assert fixture("external_backup_location_tested")["failure"] is None
    refused = fixture("backup_schedule_unknown_location")["fields"][0]
    assert refused["params"]["location"] not in declared
    # The copy that failed is that of the last scheduled backup, which succeeded: the alert says
    # the copy, not the backup, and comes after it.
    status = fixture("system_status_copy_failed")
    [alert] = status["alerts"]
    backups = {each["backup_id"]: each for each in fixture("backups")["items"]}
    copied = backups[alert["params"]["backup_id"]]
    assert alert["code"] == "scheduled_backup_copy_failed"
    assert alert["params"]["location"] == fixture("backup_schedule")["external_copy"]["location"]
    assert copied["taken_at"] == status["last_backup"]["at"]
    assert status["last_backup"]["succeeded"] is True
    assert copied["taken_at"] < alert["since"] <= mockhistory.stamp(TODAY)
    assert status["last_backup_copy"] == {"at": alert["since"], "succeeded": False, "problem": None}


def test_the_copies_outside_the_platform_keep_at_least_its_retention() -> None:
    # WF-EXP-0050: « une rétention au moins égale à celle configurée sur la plateforme ». Every
    # schedule that copies keeps as many copies; the refusal names the retention of the platform.
    for name in (
        "backup_schedule",
        "backup_schedule_disabled",
        "backup_schedule_weekly",
        "backup_schedule_set",
    ):
        schedule = fixture(name)
        copy = schedule.get("external_copy")
        assert copy is None or copy["retained_count"] >= schedule["retained_count"], name
    [refused] = fixture("backup_schedule_retention_too_short")["fields"]
    assert refused["params"]["minimum"] == fixture("backup_schedule")["retained_count"]


def _retention_bounds(schema: str) -> tuple[int, int]:
    text = (REPOSITORY / "docs" / "api" / "components" / "schemas" / "platform.yaml").read_text(
        encoding="utf-8"
    )
    block = text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
    found = re.search(
        r"\n    retained_count:\n      type: integer\n      minimum: (\d+)\n"
        r"      maximum: (\d+)\n",
        block,
    )
    assert found is not None, schema
    return int(found[1]), int(found[2])


def test_a_retention_out_of_its_range_is_refused_with_the_one_bound_it_crosses() -> None:
    # EP-14/L42m: the twin of #659 for the backups. Each retention the schedule publishes, on the
    # platform and on the location, is refused out of its bounds by VALUE_OUT_OF_RANGE, the bound
    # crossed that of the schema; every schedule of the examples keeps within them.
    platform, copy = _retention_bounds("BackupSchedule"), _retention_bounds("BackupExternalCopy")
    assert platform == copy == (1, 365)
    refused = fixture("backup_schedule_retention_out_of_range")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert [(f["pointer"], f["code"], f["params"]) for f in refused["fields"]] == [
        ("/retained_count", "VALUE_OUT_OF_RANGE", {"minimum": platform[0]}),
        ("/external_copy/retained_count", "VALUE_OUT_OF_RANGE", {"maximum": copy[1]}),
    ]
    for name in (
        "backup_schedule",
        "backup_schedule_disabled",
        "backup_schedule_weekly",
        "backup_schedule_set",
    ):
        schedule = fixture(name)
        assert platform[0] <= schedule["retained_count"] <= platform[1], name
        if "external_copy" in schedule:
            assert copy[0] <= schedule["external_copy"]["retained_count"] <= copy[1], name
    # Cited under the 422 of the operation, after the refusal the fake back serves first.
    text = (REPOSITORY / "docs" / "api" / "paths" / "platform.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: setBackupSchedule\n", 1)[1].split("operationId:", 1)[0]
    cited = re.findall(r"fixtures/api/(\w+)\.json", block.split("'422':", 1)[1])
    assert cited[0] == "backup_schedule_unknown_location"
    assert cited[-1] == "backup_schedule_retention_out_of_range"


def test_the_last_copy_follows_the_last_backup_it_copies() -> None:
    # The copy of a scheduled backup is made after it; a night without a backup has no copy, and
    # the last one is the day before's.
    backups = sorted(each["taken_at"] for each in fixture("backups")["items"])
    for name in ("system_status", "system_status_storage_full", "system_status_backup_failed"):
        status = fixture(name)
        copy = status["last_backup_copy"]
        assert copy["succeeded"] is True, name
        copied = max(at for at in backups if at < copy["at"])
        assert copied[:10] == copy["at"][:10], name
        if status["last_backup"]["succeeded"]:
            assert copied == status["last_backup"]["at"], name
        else:
            assert copied < status["last_backup"]["at"], name


def test_a_deposited_backup_is_a_copy_the_external_location_keeps_and_names_its_instant() -> None:
    # EP-14/L42m (#628): the deposit reads in the archive the instant it bears, the date the
    # confirmation of the restore states (WF-ADM-0160). The copy deposited is one the location of
    # Lyon keeps and the platform no longer does: a scheduled night, older than the list, within
    # the thirty copies of the schedule; named and sized as the platform writes its backups.
    deposited = fixture("file_upload_external_backup")
    taken = _instant(deposited["backup_taken_at"])
    assert deposited["purpose"] == "external_backup"
    assert deposited["filename"] == f"waterfall-backup-{taken:%Y%m%dT%H%M%SZ}.tar"
    assert deposited["size_bytes"] <= fixture("installation")["external_backup_max_bytes"]
    schedule = fixture("backup_schedule")
    scheduled = sorted(
        _instant(each["taken_at"])
        for each in fixture("backups")["items"]
        if each["origin"] == "scheduled"
    )
    assert taken < scheduled[0]
    assert TODAY - taken <= timedelta(days=schedule["external_copy"]["retained_count"])
    assert taken.time() == scheduled[0].time()
    # The nights of the list grow by one step a day; the copy of an older night is on that line.
    sizes = [
        each["size_bytes"]
        for each in sorted(fixture("backups")["items"], key=lambda each: each["taken_at"])
        if each["origin"] == "scheduled"
    ]
    [daily] = {later - earlier for earlier, later in pairwise(sizes)}
    assert deposited["size_bytes"] == sizes[0] - daily * (scheduled[0] - taken).days
    assert _instant(deposited["uploaded_at"]) <= TODAY
    # The file of an import has no date of backup.
    assert fixture("file_upload")["backup_taken_at"] is None


def _block_of(operation: str, file: str) -> str:
    text = (REPOSITORY / "docs" / "api" / "paths" / file).read_text(encoding="utf-8")
    return text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]


def test_a_confirmation_that_is_not_the_instant_of_the_deposit_is_refused_at_its_field() -> None:
    # The refusal of a backup of the list (`restore_date_mismatch`, EP-14/L42h), for a deposit:
    # the date confirmed is the one of a backup of the list, not the instant the archive bears.
    refused = fixture("restore_external_date_mismatch")
    assert set(refused) == {"code", "status", "fields", "correlation_id"}
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [
        {"pointer": "/acknowledged_backup_taken_at", "code": "BACKUP_DATE_MISMATCH"}
    ]
    assert fixture("restore_date_mismatch")["fields"] == refused["fields"]
    listed = {each["taken_at"] for each in fixture("backups")["items"]}
    assert fixture("file_upload_external_backup")["backup_taken_at"] not in listed
    assert "fixtures/api/restore_external_date_mismatch.json" in _block_of(
        "startRestore", "platform.yaml"
    )


def test_a_restore_on_the_deposit_of_an_import_is_refused_by_its_purpose_alone() -> None:
    # The date compares only to the deposit of a backup: the deposit of an import has none
    # (`backup_taken_at` null), and its refusal names the deposit, never the date confirmed.
    assert fixture("file_upload")["purpose"] == "import"
    assert fixture("file_upload")["backup_taken_at"] is None
    refused = fixture("restore_upload_purpose_mismatch")
    assert refused["fields"] == [
        {"pointer": "/external_backup_upload_id", "code": "UPLOAD_PURPOSE_MISMATCH"}
    ]


def test_a_deposited_archive_whose_instant_does_not_read_is_refused_without_parameter() -> None:
    # No kind of exchange names the format of the backups: `expected_format` stays absent.
    unreadable = fixture("file_upload_backup_unreadable")
    assert set(unreadable) == {"code", "status", "correlation_id"}
    assert (unreadable["status"], unreadable["code"]) == (422, "FILE_FORMAT_UNREADABLE")
    upload = _block_of("uploadFile", "exchanges.yaml")
    for name in ("file_upload", "file_upload_external_backup", "file_upload_backup_unreadable"):
        assert f"fixtures/api/{name}.json" in upload, name


def test_the_costs_on_disk_are_the_actual_cost_the_indicators_on_disk_count() -> None:
    assert (
        fixture("actual_costs")["totals"]["tracked"] == fixture("project_indicators")["actual_cost"]
    )
    # The consultation holds every line retained, the drawn invoices among them, in one page.
    consulted = fixture("actual_costs")
    assert consulted["meta"]["total"] == len(consulted["items"]) == len(mockcosts.lines()) == 27


def test_the_indicators_of_the_estimate_of_the_volume_are_the_witness_s_own() -> None:
    # The witness sums its whole structure since EP-14/L45a: the estimate of the volume of §4.6.2
    # and the estimate of the witness are one reading, and the total is that of the grid.
    volume, witness = fixture("volume/estimate_indicators_volume"), fixture("estimate_indicators")
    assert volume == witness
    totals = fixture("volume/nodes_thousand")["totals"]
    assert volume["total"]["value"] == totals["base_amount"]
    # The reference budget is the budgeted amounts of the grid, but the provision's (WF-RIS-0050).
    provisions = sum(
        Decimal(node["estimate_line"]["budgeted_amount"])
        for node in fixture("volume/nodes_thousand")["items"]
        if node["kind"] == mockcore.ESTIMATE_LINE and node["estimate_line"]["is_computed"]
    )
    assert provisions == Decimal("250000.00")
    assert Decimal(fixture("project_indicators")["reference_budget"]) == (
        Decimal(totals["budgeted_amount"]) - provisions
    )


def test_the_columns_kept_are_those_of_every_line_retained_in_the_order_declared() -> None:
    def kept(items: list[Node]) -> list[str]:
        found = {column for item in items for column in cast("Node", item["passthrough"])}
        return [column for column in mockwitness.PASSTHROUGH if column in found]

    whole = fixture("actual_costs")
    # The whole consultation is one page: its lines are every line retained.
    assert whole["meta"]["total"] == len(whole["items"])
    assert whole["meta"]["passthrough_columns"] == kept(whole["items"])
    # A page says the columns of every line retained, not of its own.
    assert fixture("actual_costs_page")["meta"]["passthrough_columns"] == kept(whole["items"])
    filtered = fixture("actual_costs_subproject")
    assert filtered["meta"]["passthrough_columns"] == kept(filtered["items"])
    journal = max(entry["imported_at"] for entry in fixture("cost_imports")["items"])
    for name in ("actual_costs", "actual_costs_page", "actual_costs_subproject"):
        assert fixture(name)["last_import_at"] == journal, name


def test_an_exclusion_and_a_reinstatement_answer_a_line_of_the_consultation_written_today() -> None:
    consulted = {line["cost_line_id"]: line for line in fixture("actual_costs")["items"]}
    for name, tracked in (("actual_cost_excluded", False), ("actual_cost_reinstated", True)):
        line = fixture(name)
        before = consulted[line["cost_line_id"]]
        # The write turns the line over, and changes nothing else of it but its audit.
        assert before["is_in_tracked_scope"] is not tracked, name
        assert line["is_in_tracked_scope"] is tracked, name
        assert (line["excluded_reason"] is None) is tracked, name
        assert _instant(line["audit"]["updated_at"]) == TODAY, name
        unchanged = {"is_in_tracked_scope", "excluded_reason", "audit"}
        assert {key: value for key, value in line.items() if key not in unchanged} == {
            key: value for key, value in before.items() if key not in unchanged
        }, name


def test_the_consultation_read_anew_after_the_exclusion_moves_the_line_between_the_totals() -> None:
    before = fixture("actual_costs")
    after = fixture("actual_costs_after_exclusion")
    excluded = fixture("actual_cost_excluded")
    amount = Decimal(excluded["amount"])
    totals = {key: Decimal(value) for key, value in before["totals"].items()}
    assert {key: Decimal(value) for key, value in after["totals"].items()} == {
        "tracked": totals["tracked"] - amount,
        "excluded": totals["excluded"] + amount,
        "overall": totals["overall"],
    }
    [line] = [item for item in after["items"] if item["cost_line_id"] == excluded["cost_line_id"]]
    assert line == excluded


def test_each_correlation_is_told_by_one_example_alone(examples: dict[str, Any]) -> None:
    told: dict[str, list[str]] = defaultdict(list)
    for name, value in examples.items():
        if isinstance(value, dict) and "correlation_id" in value:
            told[cast("Node", value)["correlation_id"]].append(name)
    assert {key: names for key, names in told.items() if len(names) > 1} == {}


# --- The roles and the portfolio (EP-02/L26) ----------------------------------------------------


def test_the_hours_of_a_role_are_its_headcount_by_its_weekly_hours_by_fifty_two_over_twelve() -> (
    None
):
    weeks: dict[str, Decimal] = {
        entry["calendar_id"]: sum(
            (Decimal(hours) for hours in entry["weekly_hours"].values()), Decimal(0)
        )
        for entry in fixture("calendars")["items"]
    }
    # The semaine de trente-neuf heures, deactivated, is not listed: its hours are its label's.
    weeks.setdefault(universe(483), Decimal(39))
    for role in fixture("resource_roles")["items"]:
        # The monthly hours are the role's, all its people counted (WF-REF-0100).
        each = (weeks[role["calendar_id"]] * 52 / 12).quantize(Decimal("0.01"))
        capacity = role["capacity"]
        hours, headcount = Decimal(capacity["monthly_hours"]), Decimal(capacity["headcount"])
        assert hours / headcount == each, role["label"]
        assert role["audit"]["created_at"] == mockhistory.stamp(mockwitness.INSTALLED.instant)


def test_the_witness_of_the_portfolio_is_the_project_its_examples_describe() -> None:
    rows = fixture("volume/portfolio_projects")["items"]
    witness = next(row for row in rows if row["project_id"] == universe(1))
    project, indicators = fixture("project"), fixture("project_indicators")
    for field in ("label", "code", "state", "win_probability"):
        assert witness[field] == project[field], field
    assert witness["reference_budget"] == indicators["reference_budget"]
    assert witness["project_manager_projection"] == indicators["projections"]["project_manager"]
    assert witness["delta_to_reference"] == indicators["projections"]["variance_project_manager"]
    assert witness["cost_index"] == indicators["cost_index"]
    assert witness["schedule_index"] == indicators["schedule_index"]
    reference = next(
        each
        for each in fixture("revisions")["items"]
        if each["revision_id"] == project["reference_revision_id"]
    )
    assert witness["last_marked_at"] == reference["marked_at"]


def test_the_portfolio_is_read_at_the_instant_of_the_indicators_it_sums(
    examples: dict[str, Any],
) -> None:
    day = fixture("project_indicators")["context"]["computed_at"][:10]
    views: dict[str, Node] = {}
    for name, value in examples.items():
        if isinstance(value, dict) and "as_of" in cast("Node", value).get("scope", {}):
            views[name] = cast("Node", value)
    assert len(views) >= 11
    for name, value in views.items():
        if name == "portfolio_cost_curve_credit.json":
            # An earlier instant of the same chronology, the witness still in pricing.
            assert value["scope"]["as_of"] < day, name
            continue
        assert value["scope"]["as_of"] == day, name


def test_the_coverage_of_the_portfolio_counts_that_of_the_witness() -> None:
    portfolio = fixture("volume/portfolio_risks")["coverage"]
    witness = fixture("risk_coverage")
    assert Decimal(portfolio["reserve"]) > Decimal(witness["reserve"])
    assert Decimal(portfolio["remaining_provisions"]) == Decimal(
        fixture("volume/portfolio_risks")["identified_total"]
    )


def test_every_inverted_period_is_refused_by_one_rule() -> None:
    # One rule for every period of the contract (docs/api/README.md): 422, `/query/to` by
    # VALUE_OUT_OF_RANGE, `params.minimum` the start given — a date or an instant, as `from` is.
    # A bound of the portfolio sent alone is completed by the default period, and the refusal
    # names the bound sent, `params` the bound completed (#560).
    found = sorted(mockwitness.FIXTURES.glob("*_period_inverted.json"))
    expected = {
        "actual_costs": ("/query/to", "minimum", date),
        "audit_events": ("/query/to", "minimum", datetime),
        "backups": ("/query/to", "minimum", datetime),
        "portfolio": ("/query/to", "minimum", date),
        "portfolio_open": ("/query/from", "maximum", date),
        "projects": ("/query/to", "minimum", datetime),
    }
    assert {path.name.removesuffix("_period_inverted.json") for path in found} == set(expected)
    for path in found:
        pointer, bound, kind = expected[path.name.removesuffix("_period_inverted.json")]
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        assert (value["code"], value["status"]) == ("VALIDATION_FAILED", 422), path.name
        [field] = value["fields"]
        assert {key: field[key] for key in ("pointer", "code")} == {
            "pointer": pointer,
            "code": "VALUE_OUT_OF_RANGE",
        }, path.name
        assert list(field["params"]) == [bound], path.name
        # The other bound in the type of the period: a date of planning for the actual costs and
        # the portfolio, an instant for the journal and the home.
        given = field["params"][bound]
        if kind is date:
            assert date.fromisoformat(given).isoformat() == given, path.name
        else:
            assert datetime.fromisoformat(given).tzinfo == UTC, path.name
    # The end the server completes is the date of calculation, today in the universe.
    opened = json.loads(
        (mockwitness.FIXTURES / "portfolio_open_period_inverted.json").read_text(encoding="utf-8")
    )
    assert opened["value"]["fields"][0]["params"]["maximum"] == TODAY.date().isoformat()


_CONTRACT = REPOSITORY / "docs/api"
_PERIOD_REFUSED = "responses.yaml#/PortfolioPeriodRefused"
"""The refusal the views of the portfolio share, which carries their example (#560)."""


def _operations() -> dict[str, str]:
    """Return the text of each operation of the contract, by its identifier."""
    found: dict[str, str] = {}
    for path in sorted((_CONTRACT / "paths").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        parts = re.split(r"^    operationId: (\w+)$", text, flags=re.MULTILINE)
        found.update(zip(parts[1::2], parts[2::2], strict=True))
    return found


def test_every_operation_that_takes_a_period_declares_its_refusal_with_an_example() -> None:
    # Each operation that takes `to` declares the 422 of the rule, with an inverted period as
    # its example — its own, or that of the views of the portfolio, which share one (#560).
    shared = (_CONTRACT / "components/responses.yaml").read_text(encoding="utf-8")
    refusal = shared.split("PortfolioPeriodRefused:", 1)[1].split("\n\n", 1)[0]
    assert "fixtures/api/portfolio_period_inverted.json" in refusal
    assert "fixtures/api/portfolio_open_period_inverted.json" in refusal
    assert "/query/to" in refusal
    assert "params.minimum" in refusal
    taking = {
        name: text
        for name, text in _operations().items()
        if "- name: to\n" in text or re.search(r"parameters\.yaml#/\w*To\b", text)
    }
    assert sorted(taking) == [
        "getPortfolioPerformance",
        "getPortfolioProjects",
        "getPortfolioRisks",
        "getPortfolioValue",
        "listActualCosts",
        "listAuditEvents",
        "listBackups",
        "listProjects",
    ]
    for name, text in taking.items():
        refused = text.split("\n      '422':", 1)
        assert len(refused) == 2, name
        declared = refused[1].split("\n      '", 1)[0]
        assert _PERIOD_REFUSED in declared or "_period_inverted.json" in declared, name
