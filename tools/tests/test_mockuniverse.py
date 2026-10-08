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
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any, cast

import pytest

from wftools import (
    mockcore,
    mockcosts,
    mockcurves,
    mockhistory,
    mockindicators,
    mockwitness,
)
from wftools.mockwitness import (
    COSTS,
    JOURNAL,
    PAYMENT_DELAY,
    PREFIX,
    STUDIES_LINE,
    TODAY,
    fixture,
    universe,
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
    # Every line has its delay (WF-DEV-0020): a month for the subcontracting and the terminal
    # blocks, nought for the others, labour and provision included.
    expected = {
        number: PAYMENT_DELAY if number in {STUDIES_LINE, BLOCKS} else 0 for number in rendered
    }
    assert rendered == expected
    assert {number: reading.delays[number] for number in rendered} == expected
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


def test_a_subproject_has_actual_costs_when_a_line_is_imputed_to_it() -> None:
    imputed = {mockcosts.imputed(line) for line in COSTS}
    for subproject in fixture("subprojects"):
        assert subproject["has_actual_costs"] == (subproject["subproject_id"] in imputed)


def test_each_line_is_dated_in_the_period_of_each_import_that_brought_it_and_before_it() -> None:
    for line in COSTS:
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
        applied = imports[mockwitness.hex_identifier(entry.exchange)]
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


def test_the_costs_on_disk_are_the_actual_cost_the_indicators_on_disk_count() -> None:
    assert (
        fixture("actual_costs")["totals"]["tracked"] == fixture("project_indicators")["actual_cost"]
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
        for entry in fixture("calendars")
    }
    # The semaine de trente-neuf heures, deactivated, is not listed: its hours are its label's.
    weeks.setdefault(universe(483), Decimal(39))
    for role in fixture("resource_roles"):
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
