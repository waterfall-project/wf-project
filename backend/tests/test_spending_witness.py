# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spending projection of the witness, compared with the examples of the contract (US-2050/L1).

The witness loaded as the platform loads it, read on 3 June 2026 as the examples are: the service
gives the amounts of the examples, to the cent, but for the two lines of the occurrence of a risk
(EP-08), which no line of the witness bears yet, and which the projection leaves out as the
provisions (#3614).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from projects_support import PROJECTS
from witness_support import PRJ_001, READ_AT, example, read

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
# The two lines of the occurrence of a risk (EP-08), 200 of disbursements in June, in the example.
OCCURRENCE = D("200.00")
SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801"


def projection(
    api: ContractClient, witness: Database, realm: TestRealm, query: str
) -> dict[str, Any]:
    """Read the projection of the witness project, the query said."""
    return read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/spending?{query}")


def gaps(found: dict[str, Any], expected: dict[str, Any]) -> dict[str, D]:
    """Give, by month, what the example holds that the service does not; none for an equal month."""
    held = {each["month"]: D(each["amount"]) for each in found["monthly_totals"]}
    wanted = {each["month"]: D(each["amount"]) for each in expected["monthly_totals"]}
    assert set(held) <= set(wanted)
    return {month: gap for month in wanted if (gap := wanted[month] - held.get(month, D(0))) != 0}


def natures_of(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Give the natures of a projection by label."""
    return {each["label"]: each for each in body["cost_types"]}


@pytest.mark.requirement("WF-DEV-0100-A")
@pytest.mark.parametrize(
    "asked",
    [
        ("spending", "basis=current_remaining"),
        ("spending_payment_delays", "basis=current_remaining&payment_delays=true"),
    ],
)
def test_the_remaining_of_the_witness_is_the_example_but_for_the_occurrence_of_a_risk(
    api: ContractClient,
    witness: Database,
    realm: TestRealm,
    monkeypatch: pytest.MonkeyPatch,
    asked: tuple[str, str],
) -> None:
    # The remaining to commit of the witness, spread from 3 June: every month, nature and
    # category of the example to the cent, consumed or paid out, but for the 200 of June, in
    # disbursements, of the two lines of the occurrence of a risk the witness does not bear yet.
    monkeypatch.setattr("waterfall.api.spending.utc_now", lambda: READ_AT)
    name, query = asked
    found = projection(api, witness, realm, query)
    expected = example(name)
    assert gaps(found, expected) == {"2026-06": OCCURRENCE}
    assert D(expected["total"]) - D(found["total"]) == OCCURRENCE
    held, wanted = natures_of(found), natures_of(expected)
    assert held["Main-d'œuvre"] == wanted["Main-d'œuvre"]
    assert D(wanted["Débours"]["total"]) - D(held["Débours"]["total"]) == OCCURRENCE
    assert [each["cost_type_id"] for each in found["cost_types"]] == [
        each["cost_type_id"] for each in expected["cost_types"]
    ]
    assert found["context"] == expected["context"]


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_remaining_of_a_subproject_of_the_witness_is_the_example_to_the_cent(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The subproject of the example holds no line of the occurrence: the whole projection is its.
    monkeypatch.setattr("waterfall.api.spending.utc_now", lambda: READ_AT)
    expected = example("spending_subproject")
    found = projection(api, witness, realm, f"basis=current_remaining&subproject_id={SUBPROJECT}")
    assert found["monthly_totals"] == expected["monthly_totals"]
    assert found["cost_types"] == expected["cost_types"]
    assert (found["total"], found["context"]["scope"]) == (expected["total"], SUBPROJECT)
