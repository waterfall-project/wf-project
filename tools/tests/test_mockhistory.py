# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the witness read through its history: its chronology, its revisions, its risks.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import (
    mockcore,
    mockdata,
    mockhistory,
    mockstructure,
    mocktext,
    mockwitness,
    mockwrites,
)
from wftools.mockids import universe
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CREATED,
    GENERATED,
    INSTALLED,
    OFFER_OPENED,
    ORDER_RECEIVED,
    REGISTER,
    TODAY,
    N,
)

type Node = dict[str, Any]

WITNESS = universe(1)
_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
_DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
_PLANNED = {"date", "forecast_date", "from", "to", "as_of"}
"""The keys of the days of planning or of a period, which may run before the installation or past
today: the dates of a task, a point of a curve or of a milestone tracking, the bounds of a period.
Every other day an example carries — a review, an order received, a task started or completed, a
document, a period of costs — is of the chronology, between the installation and today."""

_LATER = (
    ("password_setup_link.json", "expires_at", timedelta(hours=1)),
    ("import", "expires_at", timedelta(hours=24)),
    ("file_upload.json", "expires_at", timedelta(hours=24)),
    ("session", "expires_at", timedelta(hours=24)),
    ("session", "idle_expires_at", timedelta(hours=2)),
)
"""The instants after today the examples may carry, by the start of the name of their file and
their key, and how far after: the link to set a password, valid an hour (WF-ADM-0140); an import
or a deposit, a day after its analysis or its deposit (WF-ARC-0100, WF-DAT-0120); a session,
within the day, and its idleness, two hours after its last request."""


def _later(name: str, key: str) -> timedelta:
    """Return how far after today an instant of a file, under a key, may lie."""
    spans = [span for start, field, span in _LATER if name.startswith(start) and key == field]
    return spans[0] if spans else timedelta(0)


_SEQUELS = {
    "task_mark_queued.json",
    "task_running.json",
    "task_succeeded.json",
    "task_failed.json",
    "task_mark_relaunched.json",
    "task_import_queued.json",
    "task_import_succeeded.json",
    "task_export_queued.json",
    "task_export_succeeded.json",
    "tasks_running.json",
    "audit_events_import_applied.json",
}
_SEQUEL_KEYS = {"submitted_at", "finished_at", "occurred_at"}
_SEQUEL_SPAN = timedelta(minutes=10)
"""The background tasks that follow a write made today, and their instants: the sequel of the
write, at its own instant, within minutes after today (#287, EP-02/L25); and the journal that
inscribes the application of an import, at the instant its task succeeds (EP-02/L42d)."""


@pytest.fixture(scope="module")
def history() -> dict[str, Any]:
    """Read the named examples of the history back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mockhistory.examples().items()
    }


def _stamps(value: Any, key: str = "") -> list[tuple[str, str]]:
    """Return each instant and each day of the chronology of a value, with the key carrying it."""
    if isinstance(value, str):
        day = _DAY.match(value) is not None and key not in _PLANNED
        return [(key, value)] if _STAMP.match(value) or day else []
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _stamps(item, key)]
    if isinstance(value, dict):
        fields = cast("dict[str, Any]", value)
        return [found for name, item in fields.items() for found in _stamps(item, name)]
    return []


def _audits(value: Any) -> list[Node]:
    """Return each object of a value read from JSON that bears an audit."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _audits(item)]
    if not isinstance(value, dict):
        return []
    fields = cast("Node", value)
    found = [fields] if isinstance(fields.get("audit"), dict) else []
    return found + [each for item in fields.values() for each in _audits(item)]


def _instant(text: str) -> datetime:
    """Return an instant, or a day at its first instant, in universal time."""
    if "T" not in text:
        return datetime.combine(date.fromisoformat(text), datetime.min.time(), UTC)
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def test_every_instant_of_the_universe_lies_between_the_installation_and_today() -> None:
    # C11 (#287): nothing is created before the installation, nothing has happened after today
    # — no review, no order received —; an audit is never updated before it is created.
    strays: list[tuple[str, str, str]] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        for key, text in _stamps(value):
            span = _later(path.name, key)
            if path.name in _SEQUELS and key in _SEQUEL_KEYS:
                span = _SEQUEL_SPAN
            if not INSTALLED.instant <= _instant(text) <= TODAY + span:
                strays.append((path.name, key, text))
        for each in _audits(value):
            audit = each["audit"]
            assert audit["created_at"] <= audit["updated_at"], path.name
    assert strays == []


def test_the_project_its_revisions_and_its_transitions_say_the_instants_of_the_chronology() -> None:
    # The project is created before its offer is opened, passes to pricing with it, and is in
    # progress from the reception of the order (C11, #287); every example of its revisions says
    # when each was created and marked, and none is updated after today or before it is created.
    for path in sorted(mockwitness.FIXTURES.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        for each in _audits(value):
            audit = each["audit"]
            if each.get("project_id") == WITNESS and "code" in each:
                assert audit["created_at"] == mockhistory.stamp(CREATED.instant), path.name
            if each.get("revision_id") in mockhistory.REVISIONS and "status" in each:
                created, marked = mockhistory.REVISIONS[each["revision_id"]]
                assert audit["created_at"] == mockhistory.stamp(created.instant), path.name
                if marked is None:
                    assert (each["status"], each["marked_at"]) == ("draft", None), path.name
                else:
                    assert each["marked_at"] == mockhistory.stamp(marked.instant), path.name
                    assert audit["updated_at"] == each["marked_at"], path.name
    transitions = mockwitness.fixture("state_transitions")
    assert [(each["to_state"], each["occurred_at"]) for each in transitions] == [
        ("created", mockhistory.stamp(CREATED.instant)),
        ("pricing", mockhistory.stamp(OFFER_OPENED.instant)),
        ("in_progress", mockhistory.stamp(ORDER_RECEIVED.instant)),
    ]
    assert mockwitness.fixture("project")["order_received_on"] == ORDER_RECEIVED.on.isoformat()


def test_the_current_revision_is_opened_before_the_occurrence_merges_into_it() -> None:
    # WF-RIS-0060 revised: the occurrence of 752 marks nothing and merges into the revision in
    # progress, which the review of 751 the day after the reference opened (WF-RIS-0020): the
    # reference stays 101, the occurrence does not create a revision.
    opened, marked = mockhistory.REVISIONS[mockhistory.CURRENT]
    assert marked is None
    occurred = mockwitness.DELIVERY_DELAY.last
    assert opened.instant < occurred.at
    assert occurred.state == mockwitness.OCCURRED
    references = [
        revision
        for revision in mockwitness.fixture("revisions")["items"]
        if revision["is_reference"]
    ]
    assert [revision["revision_id"] for revision in references] == [mockhistory.REFERENCE]
    assert mockwitness.fixture("project")["reference_revision_id"] == mockhistory.REFERENCE


def test_the_reference_bears_a_reserve_of_its_provisions_and_a_budget_the_occurrence_keeps() -> (
    None
):
    # The reserve of the reference 101: the provisions it bore on 1 February, 751 at 1,000 at
    # 25 %, 752 at 60, 753 at 600 — 910 (#287, amendment of 2026-10-06). Its reference budget, the
    # budgeted amounts but the provisions', is the one the current revision still bears: the lines
    # the occurrence merged are budgeted nothing (WF-RIS-0050, WF-RIS-0060). Both are read on the
    # whole structure of a thousand tasks (EP-14/L45a): the reserve is the core's, which bears the
    # three provisions; the budget sums every line of the structure.
    rows = mockhistory.reference_rows()
    # Without the subtree the occurrence merged, five rows; with the two provisions it bore.
    assert len(rows) == len(mockcore.current()) - 5 + 2
    assert [mockwitness.reference_provision(risk) for risk in REGISTER] == [
        Decimal("250.00"),
        Decimal("60.00"),
        Decimal("600.00"),
    ]
    assert mockhistory.reserve(rows) == Decimal("910.00")
    assert mockwitness.reference_provision(mockwitness.REWORK) == (
        mockwitness.REFERENCE_PROVISION_751
    )
    budget = mockhistory.reference_budget(rows)
    assert budget == mockhistory.reference_budget(mockcore.current())
    # The lines the amendment 1 did not designate keep the rates of the offer (#467): the core's
    # alone are budgeted 120,534.56, the whole structure 65,430,697.64.
    assert mockhistory.reference_budget(mockcore.core(mockwitness.reference())) == Decimal(
        "120534.56"
    )
    assert budget == Decimal("65430697.64")
    numbers = {row.number for row in rows}
    assert mockwitness.MERGED not in numbers
    assert {557, 567} <= numbers


def test_the_register_reads_its_severities_on_the_budget_of_the_core_until_l45b(
    history: dict[str, Any],
) -> None:
    # The register, the matrix and the coverage are left on the core by EP-14/L45a, which sums the
    # whole structure everywhere else: 751 and 753 are scaled to the structure by L45b (#528,
    # decision 4 of the frame of #287), and their summaries still say so (`mocktext.CORE_ONLY`).
    assert mockhistory.register_budget() == Decimal("120534.56")
    assert mockhistory.register_budget() != mockhistory.reference_budget(
        mockhistory.reference_rows()
    )
    examples = mockhistory.examples()
    for name in ("risks", "risk_matrix", "risk_coverage"):
        assert str(examples[f"{name}.json"]["summary"]).endswith(mocktext.CORE_ONLY), name
    assert mocktext.amount(Decimal("120534.56")) in str(examples["risks.json"]["summary"])
    # The coverage does not read the budget: it is the same on the core and on the structure.
    assert history["risk_coverage"]["reserve"] == "910.00"


def test_the_comparison_is_the_difference_of_the_offer_and_the_reference_by_lineage(
    history: dict[str, Any],
) -> None:
    # C12 and C13 (#287): the comparison names the nodes of the core by their lineages and
    # labels — the factory acceptance is the core's, 656 —, and the provision of 751 the
    # reference added is the 250 it then had, not the 500 of today.
    compared = history["comparison"]
    assert (compared["from_revision_id"], compared["to_revision_id"]) == (
        mockhistory.OFFER,
        mockhistory.REFERENCE,
    )
    added = {entry["lineage_id"]: entry for entry in compared["added"]}
    assert added[mockcore.lineage(556)] == {
        "lineage_id": mockcore.lineage(556),
        "label": "Réception usine",
        "kind": "task",
    }
    reference = {row.number: row for row in mockhistory.reference_rows()}
    reference_ids = {mockcore.lineage(number) for number in reference if number < GENERATED}
    assert mockcore.lineage(555) in added
    assert reference[555].amounts.base == Decimal("250.00")
    assert [entry["label"] for entry in compared["removed"]] == [
        "Essais préliminaires sur site",
        "Location du banc d'essais",
    ]
    changed = {entry["lineage_id"]: entry["changes"] for entry in compared["changed"]}
    core = {lineage: changes for lineage, changes in changed.items() if lineage in reference_ids}
    assert core == {
        mockcore.lineage(526): ["dates", "duration"],
        mockcore.lineage(553): ["budgeted_amount", "reestimated_amount"],
        # Not designated by the amendment: their budget is the offer's, their amount at the one
        # rate of 2026 of their category (#467, WF-DEV-0020).
        mockcore.lineage(563): ["reestimated_amount"],
        mockcore.lineage(566): ["reestimated_amount"],
    }
    # Every labour line drawn about the core is re-estimated at the rate of 2026 the same way, and
    # nothing else of the drawn tasks changes: the offer dated them as the reference does.
    drawn = {lineage: changes for lineage, changes in changed.items() if lineage not in core}
    assert len(drawn) == 2_766
    assert {tuple(cast("list[str]", changes)) for changes in drawn.values()} == {
        ("reestimated_amount",)
    }
    # The deltas by nature, as by subproject, sum to the difference of the two estimates: the
    # 4,075 of the core, and the rates of 2026 on the labour drawn.
    offer = mockhistory.offer_rows()
    difference = sum(
        (row.amounts.base for row in reference.values() if row.kind == "estimate_line"),
        Decimal(0),
    ) - sum((row.amounts.base for row in offer if row.kind == "estimate_line"), Decimal(0))
    for dimension in ("cost_type", "subproject"):
        deltas = [
            Decimal(entry["delta"])
            for entry in compared["amount_deltas"]
            if entry["dimension"] == dimension
        ]
        assert sum(deltas, Decimal(0)) == difference == Decimal("178101.25")
    summary = str(mockhistory.examples()["comparison.json"]["summary"])
    rerated = mocktext.count(2_768)
    assert f"les {rerated} lignes de main-d'œuvre que l'avenant ne désigne pas" in summary
    assert "« Câblage sur site » et « Mise en service sur site »" in summary
    assert f"{mocktext.count(2_770)} nœuds modifiés, 5 ajoutés, 2 retirés" in summary


def test_the_offer_dates_what_follows_the_factory_acceptance_after_the_wiring() -> None:
    # The amendment 1 added the factory acceptance: in the offer, what follows it today — the
    # mounting on site, the lots of the control station drawn about the core — followed the wiring
    # it ends, and is dated the same (EP-14/L45a). The whole structure is dated, none of its tasks
    # left without a predecessor; and the step of the amendment on the reference budget of the
    # whole structure is the core's alone, 2,865, no drawn line being designated (#467).
    offer = {row.number: row for row in mockhistory.offer_rows()}
    reference = {row.number: row for row in mockhistory.reference_rows()}
    assert mockwitness.FACTORY_ACCEPTANCE not in offer
    followers = [
        task
        for task in mockcore.tasks_in_order(mockhistory.offer())
        if any(link.predecessor == mockwitness.WIRING for link in task.links)
    ]
    assert [task.number for task in followers if task.number < GENERATED] == [N.MOUNTING]
    assert len(followers) == 1 + 3
    assert all(task.number >= GENERATED for task in followers[1:])
    for task in followers:
        dated = (cast("Node", offer[task.number].node["task"])["start"],)
        assert dated == (cast("Node", reference[task.number].node["task"])["start"],)
    assert len(offer) == len(reference) - 3 - 2 + 2
    assert mockhistory.reference_budget(reference.values()) - mockhistory.reference_budget(
        offer.values()
    ) == Decimal("2865.00")


def test_a_revision_compared_with_itself_has_no_difference() -> None:
    rows = mockhistory.reference_rows()
    same = mockhistory.comparison(rows, rows, mockhistory.REFERENCE, mockhistory.REFERENCE)
    assert (same["added"], same["removed"], same["changed"], same["amount_deltas"]) == (
        [],
        [],
        [],
        [],
    )


def test_a_node_moved_under_another_parent_is_changed_by_its_parent() -> None:
    rows = mockhistory.reference_rows()
    # The design file under the control station instead of the studies.
    moved = [replace(row, parent=551) if row.number == 526 else row for row in rows]
    compared = mockhistory.comparison(rows, moved, mockhistory.REFERENCE, mockhistory.REFERENCE)
    assert compared["changed"] == [
        {
            "lineage_id": mockcore.lineage(526),
            "label": "Dossier de conception",
            "kind": "task",
            "changes": ["parent"],
        }
    ]


def test_the_register_totals_its_provisions_and_sets_the_reserve_beside(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0040: the identified risks for their provision today, those that occurred and those
    # dismissed for the provision the reference bore; the reserve of the reference beside.
    register = history["risks"]
    assert register["totals"] == {
        "identified": "500.00",
        "occurred": "60.00",
        "dismissed": "600.00",
        "total": "1160.00",
        "reserve": "910.00",
    }
    assert history["risk_matrix"]["totals"] == register["totals"]
    items = {item["risk_id"]: item for item in register["items"]}
    assert history["risk"] == items[universe(751)]
    assert history["risk_occurred_detail"] == items[universe(752)]
    # The provision of the identified risk is its line in the core; the others bear none.
    core = {row.number: row for row in mockcore.core()}
    rework = items[universe(751)]
    assert rework["provision_node_id"] == universe(555)
    assert Decimal(rework["provision_amount"]) == core[555].amounts.base
    assert [items[universe(n)]["provision_node_id"] for n in (752, 753)] == [None, None]
    # The severity of the occurred risk is its own estimate, merged under 541: 120 and 80.
    merged = mockwitness.fixture("nodes_risk_occurred")["totals"]
    assert items[universe(752)]["severity"] == merged["reestimated_amount"] == "200.00"


def test_each_risk_sits_in_the_cell_its_probability_and_its_share_of_the_budget_give(
    history: dict[str, Any],
) -> None:
    # The severity is read on the reference budget of the witness, 120,834.56: 1,250 is 1.03 %
    # of it, level 2; 200, level 1; 12,000, 9.93 %, level 3 — the matrix at the scale of the
    # witness (#287). The matrix counts the risks of the register in their cells.
    cells = {
        item["risk_id"]: (
            item["matrix_cell"]["probability_level"],
            item["matrix_cell"]["severity_level"],
            item["matrix_cell"]["zone"],
        )
        for item in history["risks"]["items"]
    }
    assert cells == {
        universe(751): (3, 2, "watch"),
        universe(752): (3, 1, "nominal"),
        universe(753): (1, 3, "nominal"),
    }
    counted = {
        (cell["probability_level"], cell["severity_level"]): cell
        for cell in history["risk_matrix"]["cells"]
        if cell["count"]
    }
    assert {key: cell["count"] for key, cell in counted.items()} == {
        (3, 2): 1,
        (3, 1): 1,
        (1, 3): 1,
    }
    assert {(p, s, cell["zone"]) for (p, s), cell in counted.items()} == set(cells.values())
    assert mockhistory.level(Decimal("0.3"), ["0.1", "0.3", "0.6"]) == 3
    assert mockhistory.level(Decimal("0.6"), ["0.1", "0.3", "0.6"]) == 4


def test_a_risk_offers_its_commands_by_its_state_and_its_citation(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0020: a risk that occurred is neither updated, reviewed nor deleted; only an
    # identified one occurs; one a marked revision cites — all three, identified before the
    # reference was marked — is not deleted.
    available = {
        item["risk_id"]: {
            entry["command"]: entry["missing_conditions"] for entry in item["available_commands"]
        }
        for item in history["risks"]["items"]
    }
    assert available[universe(751)] == {
        "update": [],
        "review": [],
        "declare_occurrence": [],
        "delete": ["risk_not_cited"],
    }
    assert available[universe(752)] == {
        "update": ["risk_not_occurred"],
        "review": ["risk_not_occurred"],
        "declare_occurrence": ["risk_identified"],
        "delete": ["risk_not_occurred", "risk_not_cited"],
    }
    assert available[universe(753)]["declare_occurrence"] == ["risk_identified"]
    assert all(mockhistory.is_cited(risk) for risk in REGISTER)
    late = mockwitness.Risk(
        799,
        "Risque identifié aujourd'hui",
        "",
        None,
        217,
        (mockwitness.Review(TODAY, Decimal("0.1"), Decimal("100.00")),),
    )
    assert not mockhistory.is_cited(late)
    assert mockhistory.commands(late)[3] == {
        "command": "delete",
        "is_available": True,
        "missing_conditions": [],
    }


def test_the_reviews_of_a_risk_and_its_audit_follow_the_chronology(
    history: dict[str, Any],
) -> None:
    # The reviews of 751, the latest first: identified on 12 January at 25 % of 1,000 — the
    # 250 the reference knew on 1 February —, raised to 1,250 on 2 February, to 40 % on 2 March.
    reviews = history["risk_reviews"]
    assert [(r["reviewed_on"], r["probability"], r["severity"]) for r in reviews] == [
        ("2026-03-02", "0.4", "1250.00"),
        ("2026-02-02", "0.25", "1250.00"),
        ("2026-01-12", "0.25", "1000.00"),
    ]
    known = mockwitness.REWORK.known_on(AMENDMENT_MERGED.on)
    assert known is not None
    assert known.severity * known.probability == Decimal("250.00")
    for item, risk in zip(history["risks"]["items"], REGISTER, strict=True):
        assert item["audit"]["created_at"] == mockhistory.stamp(risk.reviews[0].at)
        assert item["last_review_on"] == risk.last.at.date().isoformat()


def test_the_coverage_sets_the_reserve_against_what_the_risks_cost_today(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0050: the reserve of 910 against the 500 of the provision still identified and the
    # 200 reestimated of the lines merged by the occurrence: +210, read today.
    covered = history["risk_coverage"]
    assert covered["context"]["computed_at"] == mockhistory.stamp(TODAY)
    assert covered["context"]["revision_id"] == mockhistory.CURRENT
    assert (
        covered["reserve"],
        covered["remaining_provisions"],
        covered["occurred_cost"],
        covered["coverage_variance"],
    ) == ("910.00", "500.00", "200.00", "210.00")


def test_the_history_is_the_fixtures_the_front_reads(history: dict[str, Any]) -> None:
    for name, value in history.items():
        assert mockwitness.fixture(name) == value, name


def test_the_offer_is_priced_at_the_rates_of_its_reference_year() -> None:
    # The offer, of the reference year 2025, is at the rates of 2025 of the volume of rates, as
    # #232 proposes (WF-REV-0030): 78.50 for the electrical engineering, 73.50 for the
    # commissioning; the reference at those of 2026, one rate a category, the lines the amendment 1
    # did not designate keeping the budget of the offer (WF-REV-0050, #467).
    offer = {row.number: row for row in mockhistory.offer_rows()}
    reference = {row.number: row for row in mockhistory.reference_rows()}
    for number, hours, rate in ((553, 10, "78.50"), (563, 120, "78.50"), (566, 80, "73.50")):
        assert offer[number].amounts.base == hours * Decimal(rate), number
    assert [reference[n].amounts.base for n in (553, 563, 566)] == [
        Decimal("1000.0"),
        Decimal(9600),
        Decimal(6000),
    ]
    assert [reference[n].amounts.budgeted for n in (563, 566)] == [Decimal(9420), Decimal(5880)]
    labour = next(
        entry
        for entry in mockwitness.fixture("comparison")["amount_deltas"]
        if entry["key"] == mockstructure.LABOR
    )
    # The 3,515 of the core, and the step of 1.50 an hour on the labour drawn about it.
    assert Decimal(labour["delta"]) == Decimal("3515.00") + Decimal("174026.25")
    drawn_hours = sum(
        (row.hours for row in reference.values() if row.number >= GENERATED), Decimal(0)
    )
    assert drawn_hours * mockstructure.RATE_STEP == Decimal("174026.25")
    grid = {
        row["cost_category_id"]: {cell["year"]: cell["amount"] for cell in row["cells"] if cell}
        for row in mockwitness.fixture("volume/hourly_rate_grid")["rows"]
    }
    assert {key: str(rate) for key, rate in mockhistory.offer_rates().items()} == {
        key: grid[key][2025] for key in mockhistory.offer_rates()
    }


def test_a_risk_identified_after_the_reference_has_no_share_in_it() -> None:
    # Identified and dismissed today: no review before the reference was marked, no provision
    # it bore — it counts nothing among the dismissed, and the reserve does not move.
    late = mockwitness.Risk(
        798,
        "Risque identifié puis écarté aujourd'hui",
        "",
        None,
        217,
        (
            mockwitness.Review(TODAY, Decimal("0.1"), Decimal("100.00")),
            mockwitness.Review(TODAY, Decimal("0.1"), Decimal("100.00"), mockwitness.DISMISSED),
        ),
    )
    assert late.known_on(AMENDMENT_MERGED.on) is None
    assert mockwitness.reference_provision(late) == 0
    rows = mockhistory.reference_rows()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mockhistory, "REGISTER", (*REGISTER, late))
        counted = mockhistory.totals(rows)
    assert (counted["dismissed"], counted["reserve"]) == ("600.00", "910.00")


def test_one_run_of_the_generator_reaches_its_fixed_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The portfolio sums the register, the matrix and the coverage of the witness: it reads them
    # in memory, not from the files the same command writes (defect no. 7 of the rules), so that
    # a register changed is written whole by one run.
    rework = replace(
        mockwitness.REWORK,
        reviews=(
            *mockwitness.REWORK.reviews,
            mockwitness.Review(TODAY, Decimal("0.6"), Decimal("1250.00")),
        ),
    )
    monkeypatch.setattr(mockhistory, "REGISTER", (rework, *REGISTER[1:]))
    mockdata.write(tmp_path)
    assert mockdata.check(tmp_path) == []
    written = json.loads((tmp_path / "volume" / "portfolio_risks.json").read_text("utf-8"))
    versioned = mockwitness.fixture("volume/portfolio_risks")
    assert written["value"]["identified_total"] != versioned["identified_total"]
    risks = json.loads((tmp_path / "risks.json").read_text("utf-8"))["value"]
    assert risks["totals"]["identified"] == "750.00"


def test_a_line_of_provision_of_a_risk_identified_later_is_not_in_the_reference() -> None:
    # The same late risk, bearing a line of provision in the current revision: the reference,
    # marked before it was identified, does not bear it, nor does the comparison count it.
    late = mockwitness.Risk(
        797,
        "Risque identifié aujourd'hui",
        "",
        None,
        217,
        (mockwitness.Review(TODAY, Decimal("0.1"), Decimal("100.00")),),
        provision_line=599,
    )
    line = mockwitness.Line(
        599,
        "Provision — risque tardif",
        mockwitness.PROVISIONS,
        unit=Decimal("10.00"),
        is_provision=True,
    )
    core = mockwrites.amended(
        mockwitness.CORE,
        lambda task: replace(task, lines=(*task.lines, line)) if task.number == 552 else task,
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(mockhistory, "REGISTER", (*REGISTER, late))
        patch.setattr(mockwitness, "REGISTER", (*REGISTER, late))
        rows = mockcore.core(mockwitness.reference(core), AMENDMENT_MERGED.on)
        offered = mockcore.core(
            mockhistory.offer(core), mockwitness.OFFER_MARKED.on, mockhistory.offer_rates()
        )
        compared = mockhistory.comparison(offered, rows, mockhistory.OFFER, mockhistory.REFERENCE)
    assert 599 not in {row.number for row in rows}
    added = cast("list[Node]", compared["added"])
    assert mockcore.lineage(599) not in {entry["lineage_id"] for entry in added}
    assert mockhistory.reserve(rows) == Decimal("910.00")


def test_the_summary_of_the_matrix_says_the_bounds_of_the_installation() -> None:
    summary = str(mockhistory.examples()["risk_matrix.json"]["summary"])
    settings = mockwitness.fixture("reference_settings")["risk_matrix"]
    for bounds in (settings["probability_bounds"], settings["severity_bounds"]):
        said = [str(int(Decimal(bound) * 100)) for bound in bounds]
        assert f"{len(bounds) + 1} niveaux" in summary or f"{len(bounds) + 1} de" in summary
        assert f"{', '.join(said[:-1])} et {said[-1]} %" in summary


def test_a_line_the_amendment_does_not_designate_keeps_in_the_reference_its_offer_budget() -> None:
    # WF-REV-0050: the merge changes only the budgeted amounts of the lines its differential
    # designates (#467). A line borne by both, its quantities unchanged, keeps in 101 the budget
    # the offer gave it, at the rate of 2025; the update of the rates stays a proposal.
    offer = {row.number: row for row in mockhistory.offer_rows() if row.kind == "estimate_line"}
    reference = {
        row.number: row for row in mockhistory.reference_rows() if row.kind == "estimate_line"
    }

    def quantities(row: mockcore.Row) -> tuple[Any, ...]:
        line = cast("dict[str, Any]", row.node["estimate_line"])
        return tuple(line[key] for key in ("quantity", "hours", "unit_disbursement"))

    kept = [
        number
        for number in offer.keys() & reference.keys()
        if quantities(offer[number]) == quantities(reference[number])
    ]
    assert sorted(number for number in kept if number < GENERATED) == [527, 554, 563, 566]
    # Every line drawn about the core is kept as it was: none was designated (EP-14/L45a).
    assert sum(1 for number in kept if number >= GENERATED) == 4_991
    for number in kept:
        assert reference[number].amounts.budgeted == offer[number].amounts.budgeted, number


def test_a_labour_line_is_priced_at_the_one_rate_of_its_category_in_each_revision() -> None:
    # WF-DEV-0020, WF-REV-0060: one rate for a category and a revision, that of its reference year;
    # the amendment 1 fixes the budgets of the lines it designates alone (#467), so that the wiring
    # on site and the commissioning are budgeted at the offer's and re-estimated at the rate of
    # 2026, in the reference as in the current revision that copies it.
    revisions = {
        "offer": mockhistory.offer_rows(),
        "reference": mockhistory.reference_rows(),
        "current": mockcore.current(),
    }
    for name, rows in revisions.items():
        rates: dict[str, set[Decimal]] = {}
        for row in rows:
            line = (
                cast("dict[str, Any]", row.node["estimate_line"])
                if row.kind == "estimate_line"
                else None
            )
            if line is None or line["hours"] is None:
                continue
            quantity, hours = Decimal(line["quantity"]), Decimal(line["hours"])
            rates.setdefault(line["cost_category_id"], set()).add(
                Decimal(line["base_amount"]) / (quantity * hours)
            )
        assert all(len(found) == 1 for found in rates.values()), (name, rates)
    for name in ("reference", "current"):
        lines = {row.number: row.amounts for row in revisions[name]}
        for number in (563, 566):
            assert lines[number].budgeted != lines[number].reestimated, (name, number)
