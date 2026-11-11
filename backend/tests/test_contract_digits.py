# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
r"""A decimal is read as the contract writes it, in digits of 0 to 9 (US-1840, #2238).

The pattern of ``Decimal`` is one of JSON Schema, where ``\d`` is a digit of 0 to 9; the models
the service engenders read it in Unicode. The base of the models refuses a decimal of the contract
written in other digits, and the bounds a reading takes by hand are read by ``[0-9]``. Every answer
is checked against the contract (``ContractClient``).
"""

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nodes_support import Tree, faults, opened
from projects_support import scene as make_scene
from pydantic import BaseModel
from pydantic_core import PydanticCustomError
from support import CONTRACT

from waterfall.api.contract import models
from waterfall.api.contract.base import (
    DIGIT_FAULT,
    ContractModel,
    is_decimal,
    refuse_other_digits,
)
from waterfall.api.middleware import CorrelationMiddleware
from waterfall.api.problems import install_problem_handlers

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient, ReferenceSessions

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-DAT-0100-A")

# MO-003 of the witness, the first mechanical engineering: it bears no rate before 2016.
MECHANICAL = UUID("01926f3a-7c00-7000-8000-000400000000")
RATES = f"/api/v1/reference/cost-categories/{MECHANICAL}/hourly-rates"
SETTINGS = "/api/v1/reference/settings"
ROLES = "/api/v1/reference/resource-roles"
# The two types of the contract a decimal is written by; every other carries one of them.
ROOTS = frozenset({"Decimal", "Money"})
# The keywords by which a schema carries another one.
NESTING = frozenset({"allOf", "anyOf", "oneOf", "items", "not"})
# The digits of 0 to 9 written as Arabic-Indic ones, which a Unicode digit class matches.
ARABIC_INDIC = str.maketrans({str(digit): chr(0x0660 + digit) for digit in range(10)})


def arabic(text: str) -> str:
    """Write the digits of a text in Arabic-Indic digits: ``12.50`` as the issue sends it."""
    return text.translate(ARABIC_INDIC)


def fields_of(answer: Any) -> tuple[int, str, list[tuple[str, str]]]:
    """Give the status, the code and the fields (pointer, code) of a refusal."""
    body = answer.json()
    return (
        answer.status_code,
        body["code"],
        [(each["pointer"], each["code"]) for each in body.get("fields", [])],
    )


def test_an_amount_in_other_digits_is_refused_at_its_field_and_no_rate_is_written(
    api: ContractClient, witness: Database, reference_sessions: ReferenceSessions
) -> None:
    del witness
    headers = reference_sessions("cost_settings").changing
    refused = api.put(f"{RATES}/2015", headers=headers, json={"amount": arabic("12.50")})
    assert fields_of(refused) == (422, "VALIDATION_FAILED", [("/amount", "VALIDATION_FAILED")])
    assert 2015 not in [rate["year"] for rate in api.get(RATES, headers=headers).json()]
    # The same amount in digits of 0 to 9 is written.
    assert api.put(f"{RATES}/2015", headers=headers, json={"amount": "12.50"}).status_code == 200


@pytest.mark.requirement("WF-REF-0170-A")
def test_a_threshold_in_other_digits_is_refused_at_its_field_and_nothing_is_written(
    api: ContractClient, witness: Database, reference_sessions: ReferenceSessions
) -> None:
    del witness
    headers = reference_sessions("indicator_settings").changing
    read = api.get(SETTINGS, headers=headers).json()
    # A threshold is a text for the base, which does not see it: the form of the threshold does.
    thresholds = {**read["index_thresholds"], "cost_watch": arabic("0.9")}
    sent = {"index_thresholds": thresholds, "lock_version": read["lock_version"]}
    refused = api.patch(SETTINGS, headers=headers, json=sent)
    assert fields_of(refused) == (
        422,
        "VALIDATION_FAILED",
        [("/index_thresholds/cost_watch", "NUMBER_INVALID")],
    )
    assert api.get(SETTINGS, headers=headers).json() == read


def test_a_bound_of_the_matrix_in_other_digits_is_refused_at_its_rank_and_nothing_is_written(
    api: ContractClient, witness: Database, reference_sessions: ReferenceSessions
) -> None:
    del witness
    headers = reference_sessions("risk_settings").changing
    read = api.get(SETTINGS, headers=headers).json()
    matrix = {**read["risk_matrix"], "probability_bounds": [arabic("0.25"), "0.5", "0.75"]}
    sent = {"risk_matrix": matrix, "lock_version": read["lock_version"]}
    refused = api.patch(SETTINGS, headers=headers, json=sent)
    assert fields_of(refused) == (
        422,
        "VALIDATION_FAILED",
        [("/risk_matrix/probability_bounds/0", "VALIDATION_FAILED")],
    )
    assert api.get(SETTINGS, headers=headers).json() == read


@pytest.fixture
def tree(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Tree:
    """Give the main structure of the revision a manager opened on a project of a new platform."""
    stage = make_scene(api, owner, database, realm)
    return Tree(api, stage, opened(api, stage))


def test_a_bound_of_the_nodes_in_other_digits_is_refused_at_its_parameter(tree: Tree) -> None:
    # A bound of each form, a decimal, an amount, a whole number and a date, all named at once;
    # the same bounds in digits of 0 to 9 are read.
    bounds = {
        "duration_min": "5",
        "base_amount_max": "12.50",
        "payment_delay_days_min": "30",
        "start_from": "2026-05-01",
    }
    assert tree.read("?" + "&".join(f"{name}={value}" for name, value in bounds.items())).is_success
    query = "&".join(f"{name}={arabic(value)}" for name, value in bounds.items())
    assert faults(tree.read(f"?{query}")) == [
        ("/query/duration_min", "NUMBER_INVALID", {}),
        ("/query/base_amount_max", "NUMBER_INVALID", {}),
        ("/query/payment_delay_days_min", "NUMBER_INVALID", {}),
        ("/query/start_from", "DATE_INVALID", {}),
    ]


def test_a_bound_of_the_roles_in_other_digits_is_refused_at_its_parameter(
    api: ContractClient, witness: Database, reference_sessions: ReferenceSessions
) -> None:
    del witness
    headers = reference_sessions("resource_settings").changing
    refused = api.get(f"{ROLES}?monthly_hours_min={arabic('120')}&headcount_max=2", headers=headers)
    assert fields_of(refused) == (
        422,
        "VALIDATION_FAILED",
        [("/query/monthly_hours_min", "NUMBER_INVALID")],
    )


def decimal_schemas() -> set[str]:
    """Name the schemas of the contract that are ``Decimal`` or ``Money``, or carry one of them.

    Read from the sources of the contract, apart from the models: a schema carries another by its
    reference, alone or in its ``allOf``, ``anyOf``, ``oneOf``, ``items`` or ``not``, at any depth.
    """
    schemas: dict[str, dict[str, Any]] = {}
    for source in (CONTRACT.parent / "components").rglob("*.yaml"):
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
        for name, schema in cast("dict[str, Any]", document).items():
            if isinstance(schema, dict):
                schemas[name] = cast("dict[str, Any]", schema)
    found = set(ROOTS)
    while True:
        carriers = {name for name, schema in schemas.items() if carried(schema) & found}
        if carriers <= found:
            return found
        found |= carriers


def carried(schema: object) -> set[str]:
    """Name the schemas a schema refers to, by itself or by what it nests, at any depth."""
    if isinstance(schema, list):
        return {name for each in cast("list[object]", schema) for name in carried(each)}
    if not isinstance(schema, dict):
        return set()
    found: set[str] = set()
    for key, each in cast("dict[str, object]", schema).items():
        if key == "$ref":
            found.add(str(each).rpartition("/")[2])
        elif key in NESTING:
            found |= carried(each)
    return found


def engendered() -> dict[str, type[BaseModel]]:
    """Give the models ``models.py`` declares, without the generic ones pydantic adds to it."""
    return {
        name: kind
        for name, kind in vars(models).items()
        if isinstance(kind, type)
        and issubclass(kind, BaseModel)
        and kind.__module__ == models.__name__
        and kind.__pydantic_generic_metadata__["origin"] is None
    }


def test_the_base_recognises_every_engendered_type_that_carries_a_decimal_and_no_other() -> None:
    kinds = engendered()
    recognised = {name for name, kind in kinds.items() if is_decimal(kind)}
    expected = decimal_schemas() & kinds.keys()
    assert recognised == expected
    assert {"Decimal", "Money", "Percent", "Hours", "IndexThreshold", "ProjectRatio"} <= expected


def test_each_type_recognised_refuses_other_digits_at_its_item_and_takes_digits_of_0_to_9() -> None:
    for name, kind in engendered().items():
        if not is_decimal(kind):
            continue
        kept = [kind.model_validate("0.5")]
        assert refuse_other_digits(kept) is kept, name
        # A digit of another script that every pattern admits, where a type asks a 0 or a 1 to 9.
        sent = [*kept, kind.model_validate(f"0.{arabic('5')}5")]
        with pytest.raises(PydanticCustomError) as refused:
            refuse_other_digits({"values": sent})
        assert (refused.value.type, refused.value.context) == (
            DIGIT_FAULT,
            {"path": ("values", 1)},
        ), name


class Inner(ContractModel):
    """An object nested in a field."""

    amount: models.Decimal


class Sheet(ContractModel):
    """A model of the contract whose fields hold a decimal, in a list and in a nested object."""

    amounts: list[models.Decimal]
    nested: Inner


def test_a_decimal_in_a_field_of_the_base_is_refused_at_its_item_by_a_route() -> None:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    install_problem_handlers(app)

    @app.post("/sheet")
    def receive(sheet: Sheet) -> dict[str, int]:
        return {"amounts": len(sheet.amounts)}

    client = TestClient(app)
    kept = {"amounts": ["0.5", "1"], "nested": {"amount": "2"}}
    assert client.post("/sheet", json=kept).json() == {"amounts": 2}
    for sent, pointer in (
        ({**kept, "amounts": ["0.5", arabic("1")]}, "/amounts/1"),
        ({**kept, "nested": {"amount": arabic("2")}}, "/nested/amount"),
    ):
        refused = client.post("/sheet", json=sent)
        assert fields_of(refused) == (
            422,
            "VALIDATION_FAILED",
            [(pointer, "VALIDATION_FAILED")],
        )
