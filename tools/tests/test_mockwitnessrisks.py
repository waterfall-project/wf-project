# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the risks of the witness read through its history: register, matrix, reviews, coverage.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from decimal import Decimal
from typing import Any

import pytest

from wftools import mockcore, mockdata, mockhistory, mockwitness, mockwitnessrisks
from wftools.mockids import universe
from wftools.mockwitness import AMENDMENT_MERGED, TODAY
from wftools.mockwitnessrisks import REGISTER

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def history() -> dict[str, Any]:
    """Read the named examples of the history back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mockhistory.examples().items()
    }


def test_the_register_totals_its_provisions_and_sets_the_reserve_beside(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0040: the identified risks for their provision today, those that occurred and those
    # dismissed for the provision the reference bore; the reserve of the reference beside.
    register = history["risks"]
    assert register["totals"] == {
        "identified": "500000.00",
        "occurred": "60.00",
        "dismissed": "600000.00",
        "total": "1100060.00",
        "reserve": "850060.00",
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
    # The severity is read on the reference budget of the whole structure, 65,430,697.64:
    # 1,250,000 is 1.91 % of it, level 2; 200, level 1; 12,000,000, 18.34 %, level 4 — 751 and
    # 753 at the scale of the structure (EP-14/L45b). The matrix counts the identified risks alone
    # (#1395, WF-RIS-0040): 751, the other two sit in their cells without being counted.
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
        universe(753): (1, 4, "watch"),
    }
    counted = {
        (cell["probability_level"], cell["severity_level"]): cell
        for cell in history["risk_matrix"]["cells"]
        if cell["count"]
    }
    assert {key: cell["count"] for key, cell in counted.items()} == {
        (3, 2): 1,
    }
    assert {(p, s, cell["zone"]) for (p, s), cell in counted.items()} == {(3, 2, "watch")}
    assert mockhistory.level(Decimal("0.3"), ["0.1", "0.3", "0.6"]) == 3
    assert mockhistory.level(Decimal("0.6"), ["0.1", "0.3", "0.6"]) == 4


def test_a_risk_offers_its_commands_by_its_state_and_its_citation(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0020: a risk that occurred is neither updated, reviewed nor deleted; only an
    # identified one occurs, or changes the category or the subproject of its provision
    # (WF-RIS-0010, EP-14/L42p); one a marked revision cites — all three, identified before the
    # reference was marked — is not deleted.
    available = {
        item["risk_id"]: {
            entry["command"]: entry["missing_conditions"] for entry in item["available_commands"]
        }
        for item in history["risks"]["items"]
    }
    assert available[universe(751)] == {
        "update": [],
        "update_provision": [],
        "review": [],
        "declare_occurrence": [],
        "delete": ["risk_not_cited"],
    }
    assert available[universe(752)] == {
        "update": ["risk_not_occurred"],
        "update_provision": ["risk_identified"],
        "review": ["risk_not_occurred"],
        "declare_occurrence": ["risk_identified"],
        "delete": ["risk_not_occurred", "risk_not_cited"],
    }
    assert available[universe(753)]["declare_occurrence"] == ["risk_identified"]
    assert available[universe(753)]["update_provision"] == ["risk_identified"]
    assert available[universe(753)]["update"] == []
    assert all(mockhistory.is_cited(risk) for risk in REGISTER)
    late = mockwitnessrisks.Risk(
        799,
        "Risque identifié aujourd'hui",
        "",
        None,
        217,
        (mockwitnessrisks.Review(TODAY, Decimal("0.1"), Decimal("100.00")),),
    )
    assert not mockhistory.is_cited(late)
    assert mockhistory.commands(late)[4] == {
        "command": "delete",
        "is_available": True,
        "missing_conditions": [],
    }


def test_each_risk_names_the_category_and_the_subproject_its_line_of_provision_bears(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0010: the line of provision bears the category the risk designates and belongs to
    # the subproject it designates, if any. The one line of provision of the current revision, that
    # of 751, bears PRV-001 and no subproject; 752 and 753 keep the category they designated.
    lines = {
        node["node_id"]: node["estimate_line"]
        for node in mockwitness.fixture("nodes_estimate")["items"]
        if node["kind"] == "estimate_line"
    }
    categories = {
        each["cost_category_id"]: each
        for each in mockwitness.fixture("volume/cost_categories")["items"]
    }
    kinds = {
        each["cost_type_id"]: each["kind"] for each in mockwitness.fixture("cost_types")["items"]
    }
    items = history["risks"]["items"]
    for item in items:
        category = categories[item["provision_cost_category_id"]]
        assert kinds[category["cost_type_id"]] == "provision", item["label"]
        assert item["provision_cost_category_label"] == category["label"]
        assert item["provision_subproject_id"] is None
        assert item["provision_subproject_label"] is None
    assert all(item["provision_cost_category_is_active"] is True for item in items)
    [identified] = [item for item in items if item["provision_node_id"] is not None]
    line = lines[identified["provision_node_id"]]
    assert line["is_computed"] is True
    # The subproject of a line of provision is the one its risk designates, computed: the grid and
    # the paste do not write it (revue 1 of EP-14/L42p).
    nodes = {node["node_id"]: node for node in mockwitness.fixture("nodes_estimate")["items"]}
    for node in nodes.values():
        if node["kind"] == "estimate_line" and node["estimate_line"]["is_computed"]:
            assert "estimate_line.subproject_id" not in node["editable_fields"]
            assert "estimate_line.subproject_id" in node["computed_fields"]
    assert line["cost_category_id"] == identified["provision_cost_category_id"]
    assert line["subproject_id"] == identified["provision_subproject_id"]
    assert history["risk"] == items[0]
    summary = json.loads((mockwitness.FIXTURES / "risk.json").read_text(encoding="utf-8"))
    assert "« Provisions pour risques », hors sous-projet" in summary["summary"]


def test_the_reviews_of_a_risk_and_its_audit_follow_the_chronology(
    history: dict[str, Any],
) -> None:
    # The reviews of 751, the latest first: identified on 12 January at 25 % of 1,000,000 — the
    # 250,000 the reference knew on 1 February —, raised to 1,250,000 on 2 February, to 40 % on
    # 2 March.
    reviews = history["risk_reviews"]
    assert [(r["reviewed_on"], r["probability"], r["severity"]) for r in reviews] == [
        ("2026-03-02", "0.4", "1250000.00"),
        ("2026-02-02", "0.25", "1250000.00"),
        ("2026-01-12", "0.25", "1000000.00"),
    ]
    known = mockwitnessrisks.REWORK.known_on(AMENDMENT_MERGED.on)
    assert known is not None
    assert known.severity * known.probability == Decimal("250000.00")
    for item, risk in zip(history["risks"]["items"], REGISTER, strict=True):
        assert item["audit"]["created_at"] == mockhistory.stamp(risk.reviews[0].at)
        assert item["last_review_on"] == risk.last.at.date().isoformat()


def test_the_coverage_sets_the_reserve_against_what_the_risks_cost_today(
    history: dict[str, Any],
) -> None:
    # WF-RIS-0050: the reserve of 850,060 against the 500,000 of the provision still identified
    # and the 200 reestimated of the lines merged by the occurrence: +349,860, read today.
    covered = history["risk_coverage"]
    assert covered["context"]["computed_at"] == mockhistory.stamp(TODAY)
    assert covered["context"]["revision_id"] == mockhistory.CURRENT
    assert (
        covered["reserve"],
        covered["remaining_provisions"],
        covered["occurred_cost"],
        covered["coverage_variance"],
    ) == ("850060.00", "500000.00", "200.00", "349860.00")
