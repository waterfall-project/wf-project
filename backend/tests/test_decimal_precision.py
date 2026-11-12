# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The decimals the service writes without a bound are refused by 422 (US-1980/L2).

#2875: a ``numeric`` column without precision refuses more than 16 383 decimals, one with a
precision (``numeric(14, 2)``) a whole part that crosses it, and PostgreSQL's ``DataError`` would
be a 500. As US-1840 does for the thresholds, each field refuses at its pointer a value of more
than ten decimals, or whose whole part crosses its column: the constants of the units of duration,
the durations and the lags of the planning, the unit disbursement and the quantity of a line. The
scenario of the finding is replayed on the test database.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, costing
from installed_reference import holding
from nodes_support import Tree, faults, opened
from projects_support import Scene
from projects_support import scene as make_scene

from waterfall.core.planning.interface.paste import DURATION
from waterfall.platform.decimals import exceeds_precision

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

UNITS = "/api/v1/reference/duration-units"
PRECISION = "VALIDATION_FAILED"
# Twenty thousand decimals, which PostgreSQL would not keep; eleven decimals, a final zero counted;
# eleven digits before the point.
OVERFLOWING = "8." + "0" * 20_000
ELEVEN_DECIMALS = "8.00000000001"
ELEVEN_DIGITS = "12345678901"
TOO_PRECISE = [OVERFLOWING, ELEVEN_DECIMALS, ELEVEN_DIGITS]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def put_units(api: ContractClient, headers: dict[str, str], **sent: str) -> Any:
    """Set the constants of the units of duration, the ones not named left at 8, 40 and 20."""
    read = api.get(UNITS, headers=headers).json()
    body = {
        "hours_per_day": "8",
        "hours_per_week": "40",
        "days_per_month": "20",
        "lock_version": read["lock_version"],
        **sent,
    }
    return api.put(UNITS, headers=headers, json=body)


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("name", ["hours_per_day", "hours_per_week", "days_per_month"])
@pytest.mark.parametrize("value", TOO_PRECISE)
def test_a_constant_of_more_than_ten_decimals_is_refused_at_its_field_and_nothing_is_written(
    api: ContractClient, stage: Scene, realm: TestRealm, name: str, value: str
) -> None:
    changing = holding(stage.database, realm, "resource_settings.write")
    refused = put_units(api, changing, **{name: value})
    assert faults(refused) == [(f"/{name}", PRECISION, {})]
    kept = api.get(UNITS, headers=changing).json()
    assert (kept["hours_per_day"], kept["hours_per_week"], kept["days_per_month"]) == (
        "8",
        "40",
        "20",
    )
    assert kept["lock_version"] == 1


@pytest.mark.requirement("WF-PLA-0160-A")
def test_constants_of_ten_decimals_are_written(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    changing = holding(stage.database, realm, "resource_settings.write")
    written = put_units(api, changing, hours_per_day="7.1234567891", hours_per_week="1234567890")
    assert written.status_code == 200, written.text


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("value", TOO_PRECISE)
def test_a_duration_of_more_than_ten_decimals_is_refused_at_its_field_by_a_creation_and_a_change(
    tree: Tree, value: str
) -> None:
    sent = {"duration": {"value": value, "unit": "d"}}
    created = tree.create("Études", task=sent)
    assert faults(created) == [("/task/duration/value", PRECISION, {})]
    assert tree.labels() == []
    node = tree.made("Études")
    changed = tree.change(node, duration=sent["duration"])
    assert faults(changed) == [("/duration/value", PRECISION, {})]
    assert tree.node(node["node_id"])["task"]["duration"] == {"value": "1", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_duration_of_ten_decimals_is_kept(tree: Tree) -> None:
    node = tree.made("Études", task={"duration": {"value": "1.1234567891", "unit": "d"}})
    assert node["task"]["duration"]["value"] == "1.1234567891"


@pytest.mark.requirement("WF-PLA-0030-A")
@pytest.mark.parametrize("value", [*TOO_PRECISE, "-" + OVERFLOWING])
def test_a_lag_of_more_than_ten_decimals_is_refused_at_its_rank_and_nothing_is_written(
    tree: Tree, value: str
) -> None:
    first, second = tree.made("Préparation"), tree.made("Reprise")
    link = {"predecessor_node_id": first["node_id"], "link_type": "finish_to_start"}
    sent = {
        "predecessors": [{**link, "lag": {"value": value, "unit": "d"}}],
        "lock_version": second["lock_version"],
    }
    path = f"{tree.path}/nodes/{second['node_id']}/predecessors"
    refused = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert faults(refused) == [("/predecessors/0/lag/value", PRECISION, {})]
    assert tree.node(second["node_id"])["predecessors"] == []


@pytest.mark.requirement("WF-DEV-0020-A")
@pytest.mark.parametrize("value", ["1" + "0" * 13, "1" + "0" * 12, "1.00000000001", OVERFLOWING])
def test_a_unit_disbursement_beyond_its_column_is_refused_at_its_field_and_nothing_is_created(
    tree: Tree, lines: Lines, costs: Costing, value: str
) -> None:
    # Thirteen digits before the point overflow numeric(14, 2): the scenario of #2875.
    task = tree.made("Câblage")
    refused = lines.create(
        task, quantity="1", cost_category_id=str(costs.material), unit_disbursement=value
    )
    assert faults(refused) == [("/estimate_line/unit_disbursement", PRECISION, {})]
    assert tree.items("?kinds=estimate_line") == []


@pytest.mark.requirement("WF-DEV-0020-A")
@pytest.mark.parametrize("value", ["1" + "0" * 10, "1.00000000001", OVERFLOWING])
def test_a_quantity_beyond_its_column_is_refused_at_its_field_at_the_creation_and_the_change(
    tree: Tree, lines: Lines, costs: Costing, value: str
) -> None:
    # Eleven digits before the point overflow numeric(14, 4).
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material), "unit_disbursement": "3.00"}
    refused = lines.create(task, quantity=value, **held)
    assert faults(refused) == [("/estimate_line/quantity", PRECISION, {})]
    line = lines.made(task, quantity="1", **held)["nodes"][0]
    changed = lines.change(line, quantity=value)
    assert faults(changed) == [("/quantity", PRECISION, {})]
    assert len(tree.items("?kinds=estimate_line")) == 1


@pytest.mark.requirement("WF-DEV-0020-A")
def test_figures_at_the_edge_of_their_column_are_kept(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    held = {"cost_category_id": str(costs.material)}
    many = lines.made(task, quantity="9999999999.9999", unit_disbursement="0.00", **held)
    dear = lines.made(task, quantity="1", unit_disbursement="999999999999.99", **held)
    assert many["nodes"][0]["estimate_line"]["quantity"] == "9999999999.9999"
    assert dear["nodes"][0]["estimate_line"]["unit_disbursement"] == "999999999999.99"


@pytest.mark.requirement("WF-IHM-0050-A")
@pytest.mark.parametrize("text", ["\u0663", "\u0663 d", "3,\u0665 d", "3.\u0665"])
def test_a_pasted_duration_written_with_other_digits_than_0_to_9_is_no_duration(
    text: str,
) -> None:
    assert DURATION.fullmatch(text) is None


@pytest.mark.requirement("WF-IHM-0050-A")
@pytest.mark.parametrize(("text", "value"), [("3 d", "3"), ("2,5w", "2,5"), ("1.25", "1.25")])
def test_a_pasted_duration_of_digits_0_to_9_is_read(text: str, value: str) -> None:
    found = DURATION.fullmatch(text)
    assert found is not None
    assert found.group(1) == value


@pytest.mark.requirement("WF-DAT-0100-A")
@pytest.mark.parametrize(
    ("text", "whole_digits", "exceeds"),
    [
        ("999999999999.99", 12, False),
        ("1000000000000", 12, True),
        ("9999999999", 10, False),
        ("10000000000", 10, True),
        ("0.1234567890", 10, False),
        ("0.12345678901", 10, True),
        ("-10000000000", 10, True),
    ],
)
def test_the_whole_digits_of_a_column_bound_a_decimal_beside_its_ten_decimals(
    text: str, whole_digits: int, exceeds: bool
) -> None:
    assert exceeds_precision(Decimal(text), whole_digits) is exceeds
