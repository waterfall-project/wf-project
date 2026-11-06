# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares (US-0810/L2), through the service.

The installation is as its bootstrap leaves it (``installed_reference``); the settings are read by
any session, and written field by field by sessions that hold the permission of each field, or
not. Every answer is checked against the contract (``ContractClient``); the examples of the
contract (``fixtures/api/reference_settings*.json``) are the oracle, but for the audit and the
counter, which a loading and a writing date and count as themselves.
"""

import json
from typing import TYPE_CHECKING, Any

import pytest
from installed_reference import holding, install
from sqlalchemy import insert
from support import WITNESS

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.witness import duration_units as units_slice
from waterfall.witness import reference_settings as witness_slice
from waterfall.witness.description import Witness

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

SETTINGS = "/api/v1/reference/settings"
COSTS, RISKS, INDICATORS = "cost_settings.write", "risk_settings.write", "indicator_settings.write"
# What a loading and a writing date and count as themselves.
UNSHARED = {"audit", "lock_version"}


def example(name: str) -> dict[str, Any]:
    """Read the value of an example of the contract."""
    document = json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))
    return document["value"]


def shared(body: dict[str, Any]) -> dict[str, Any]:
    """Give the settings without what a loading or a writing dates and counts."""
    return {name: value for name, value in body.items() if name not in UNSHARED}


def refusal(response: Any) -> tuple[int, str, dict[str, Any], list[dict[str, Any]]]:
    """Give the status, the code, the parameters and the fields of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {}), body.get("fields", [])


@pytest.fixture
def installed(owner: Engine, database: Database) -> Database:
    """Give the database of an installation as its bootstrap leaves it."""
    install(owner)
    return database


@pytest.fixture
def witnessed(installed: Database) -> Database:
    """Give the installation with the settings of the witness, at their version 2."""
    with installed.transaction() as session:
        assert witness_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
    return installed


@pytest.fixture
def session_of(installed: Database, realm: TestRealm) -> Any:
    """Give a maker of sessions holding the permissions asked for."""

    def make(*permissions: str) -> dict[str, str]:
        return holding(installed, realm, *permissions)

    return make


def version(database: Database) -> int:
    """Read the counter of the settings, as they are kept."""
    with database.transaction() as session:
        return read_reference_settings(session).lock_version


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.requirement("WF-REF-0140-A")
def test_the_settings_of_a_new_installation_are_read_by_any_session(
    api: ContractClient, session_of: Any
) -> None:
    # The currency and the name of the bootstrap, the language of the installation, the matrix,
    # the thresholds and the delay delivered; the platform their author, at their first version.
    read = api.get(SETTINGS, headers=session_of())
    assert read.status_code == 200
    body = read.json()
    assert (body["currency_code"], body["company_name"], body["default_language"]) == (
        "EUR",
        "Delmas Automatismes",
        "fr",
    )
    assert body["risk_matrix"] == {
        "probability_bounds": ["0.25", "0.5", "0.75"],
        "severity_bounds": ["0.01", "0.05", "0.1"],
        "zones": example("reference_settings")["risk_matrix"]["zones"],
    }
    assert body["index_thresholds"] == {
        "cost_watch": "0.9",
        "cost_alert": "0.8",
        "schedule_watch": "0.9",
        "schedule_alert": "0.8",
    }
    assert body["max_weeks_between_reviews"] == 6
    assert body["lock_version"] == 1
    assert body["audit"]["created_by"] == body["audit"]["updated_by"] == {"kind": "platform"}
    assert api.get(SETTINGS).status_code == 401


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_sets_its_matrix_thresholds_and_delay_and_keeps_the_currency_and_the_name(
    api: ContractClient, installed: Database, session_of: Any
) -> None:
    with installed.transaction() as session:
        assert witness_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
        assert not witness_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
    body = api.get(SETTINGS, headers=session_of()).json()
    assert shared(body) == shared(example("reference_settings"))
    assert body["lock_version"] == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_settings_written_since_the_bootstrap_are_held_and_the_witness_does_not_overwrite_them(
    api: ContractClient, installed: Database, session_of: Any
) -> None:
    sent = {"company_name": "Autre", "lock_version": 1}
    assert api.patch(SETTINGS, headers=session_of(COSTS), json=sent).status_code == 200
    with installed.transaction() as session:
        assert not witness_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
    body = api.get(SETTINGS, headers=session_of()).json()
    assert body["risk_matrix"]["probability_bounds"] == ["0.25", "0.5", "0.75"]
    assert body["lock_version"] == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_finds_no_settings_on_a_database_the_bootstrap_has_not_installed(
    database: Database,
) -> None:
    with database.transaction() as session:
        assert not witness_slice.load(session, Witness(WITNESS, Act(None, utc_now())))


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.requirement("WF-REF-0140-A")
@pytest.mark.usefixtures("witnessed")
def test_the_name_is_written_under_the_permission_of_the_cost_settings_the_currency_never(
    api: ContractClient, session_of: Any
) -> None:
    # « Le nom de l'entreprise saisi à l'installation … ; modifié, il figure sur le suivant » : the
    # name is kept, the export is EP-07's. A currency sent is no field of the writing: it stays.
    sent = {"company_name": "Delmas Automatismes Industriels", "currency_code": "USD"}
    written = api.patch(SETTINGS, headers=session_of(COSTS), json={**sent, "lock_version": 2})
    assert written.status_code == 200
    body = written.json()
    assert shared(body) == shared(example("reference_settings_company_updated"))
    assert body["lock_version"] == 3
    assert body["audit"]["updated_by"]["kind"] == "user"
    assert body["audit"]["created_by"] == {"kind": "platform"}
    assert api.get(SETTINGS, headers=session_of()).json() == body


@pytest.mark.requirement("WF-REF-0160-A")
@pytest.mark.usefixtures("witnessed")
def test_the_six_bounds_and_the_zones_are_written_under_the_permission_of_the_risk_settings(
    api: ContractClient, session_of: Any
) -> None:
    matrix = example("reference_settings_matrix_updated")
    sent = {"risk_matrix": matrix["risk_matrix"], "lock_version": 2}
    written = api.patch(SETTINGS, headers=session_of(RISKS), json=sent)
    assert written.status_code == 200
    assert shared(written.json()) == shared(matrix)


@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.requirement("WF-REF-0180-A")
@pytest.mark.usefixtures("witnessed")
def test_the_thresholds_and_the_delay_are_written_under_the_permission_of_the_indicators(
    api: ContractClient, session_of: Any
) -> None:
    updated = example("reference_settings_thresholds_updated")
    sent = {
        "index_thresholds": updated["index_thresholds"],
        "max_weeks_between_reviews": updated["max_weeks_between_reviews"],
        "lock_version": 2,
    }
    written = api.patch(SETTINGS, headers=session_of(INDICATORS), json=sent)
    assert written.status_code == 200
    assert shared(written.json()) == shared(updated)


MATRIX = example("reference_settings")["risk_matrix"]
THRESHOLDS = example("reference_settings")["index_thresholds"]


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-ADM-0110-A")
@pytest.mark.parametrize(
    ("held", "sent", "missing"),
    [
        # The example of the contract: the matrix by a session of the indicators alone.
        ((INDICATORS,), {"risk_matrix": MATRIX, "index_thresholds": THRESHOLDS}, RISKS),
        ((RISKS, INDICATORS), {"company_name": "Autre", "risk_matrix": MATRIX}, COSTS),
        ((COSTS, RISKS), {"company_name": "Autre", "max_weeks_between_reviews": 4}, INDICATORS),
        ((COSTS,), {"index_thresholds": THRESHOLDS}, INDICATORS),
        # Without any permission, the first field of the contract's order is named.
        ((), {"max_weeks_between_reviews": 4, "company_name": "Autre"}, COSTS),
        # The permission is judged before the body: a malformed field is refused 403 all the same.
        ((COSTS,), {"risk_matrix": {"zones": []}}, RISKS),
        ((COSTS,), {"company_name": "", "max_weeks_between_reviews": 0}, INDICATORS),
        # A field sent null is carried: it asks for its permission, its validation comes after.
        ((COSTS, INDICATORS), {"company_name": "Autre", "risk_matrix": None}, RISKS),
    ],
)
def test_a_field_whose_permission_the_session_lacks_is_refused_and_nothing_is_written(
    api: ContractClient,
    session_of: Any,
    held: tuple[str, ...],
    sent: dict[str, Any],
    missing: str,
) -> None:
    before = api.get(SETTINGS, headers=session_of()).json()
    refused = api.patch(SETTINGS, headers=session_of(*held), json={**sent, "lock_version": 1})
    assert refusal(refused)[:3] == (403, "PERMISSION_MISSING", {"missing_permission": missing})
    assert api.get(SETTINGS, headers=session_of()).json() == before


NULL_FAULT = "VALIDATION_FAILED"


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.parametrize(
    ("sent", "fields"),
    [
        (
            {
                "company_name": None,
                "risk_matrix": None,
                "index_thresholds": None,
                "max_weeks_between_reviews": None,
            },
            [
                {"pointer": f"/{name}", "code": NULL_FAULT}
                for name in (
                    "company_name",
                    "risk_matrix",
                    "index_thresholds",
                    "max_weeks_between_reviews",
                )
            ],
        ),
        # Judged with the other values, in the order of the contract.
        (
            {"max_weeks_between_reviews": 0, "risk_matrix": None, "company_name": ""},
            [
                {"pointer": "/company_name", "code": "VALUE_REQUIRED"},
                {"pointer": "/risk_matrix", "code": NULL_FAULT},
                {
                    "pointer": "/max_weeks_between_reviews",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": 1},
                },
            ],
        ),
        (
            {"index_thresholds": {**THRESHOLDS, "cost_watch": None}},
            [{"pointer": "/index_thresholds/cost_watch", "code": NULL_FAULT}],
        ),
    ],
)
def test_a_field_sent_null_is_refused_as_the_contract_types_none_nullable(
    api: ContractClient,
    installed: Database,
    session_of: Any,
    sent: dict[str, Any],
    fields: list[dict[str, Any]],
) -> None:
    # Only a field absent stays as it is (``ReferenceSettingsWrite``): a null is a value in default.
    everything = session_of(COSTS, RISKS, INDICATORS)
    refused = api.patch(SETTINGS, headers=everything, json={**sent, "lock_version": 1})
    assert refusal(refused) == (422, "VALIDATION_FAILED", {}, fields)
    assert version(installed) == 1


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.parametrize("held", [(), (INDICATORS,)])
def test_a_writing_that_carries_no_field_writes_nothing(
    api: ContractClient, installed: Database, session_of: Any, held: tuple[str, ...]
) -> None:
    # It asks for no permission: were it written, a session that may write nothing would make
    # stale the counter every other one read. The settings are given as they are.
    before = api.get(SETTINGS, headers=session_of()).json()
    written = api.patch(SETTINGS, headers=session_of(*held), json={"lock_version": 1})
    assert written.status_code == 200
    assert written.json() == before
    assert api.get(SETTINGS, headers=session_of()).json() == before
    assert version(installed) == 1
    # A stale counter is refused all the same.
    stale = api.patch(SETTINGS, headers=session_of(*held), json={"lock_version": 9})
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    assert version(installed) == 1


@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_body_that_is_no_object_is_refused_as_unreadable(
    api: ContractClient, session_of: Any
) -> None:
    unreadable: list[object] = [[], "settings"]
    for sent in unreadable:
        refused = api.patch(SETTINGS, headers=session_of(COSTS), json=sent)
        assert refusal(refused)[:2] == (400, "MALFORMED_REQUEST")


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_stale_counter_is_refused_whatever_screen_wrote_since_and_nothing_is_written(
    api: ContractClient, installed: Database, session_of: Any
) -> None:
    # The example of the contract: the thresholds sent with the version 1, when the screen of the
    # risks has written the matrix in version 2 — both share the counter of the settings.
    everything = session_of(COSTS, RISKS, INDICATORS)
    matrix = {"risk_matrix": MATRIX, "lock_version": 1}
    assert api.patch(SETTINGS, headers=everything, json=matrix).status_code == 200
    thresholds = {"index_thresholds": THRESHOLDS, "lock_version": 1}
    stale = api.patch(SETTINGS, headers=everything, json=thresholds)
    assert refusal(stale)[:3] == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    assert version(installed) == 2


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("", {"pointer": "/company_name", "code": "VALUE_REQUIRED"}),
        (
            "x" * 201,
            {"pointer": "/company_name", "code": "VALUE_TOO_LONG", "params": {"max_length": 200}},
        ),
        (" \t ", {"pointer": "/company_name", "code": "VALIDATION_FAILED"}),
    ],
)
def test_a_name_empty_too_long_or_blank_is_refused_and_nothing_is_written(
    api: ContractClient, installed: Database, session_of: Any, name: str, field: dict[str, Any]
) -> None:
    sent = {"company_name": name, "lock_version": 1}
    refused = api.patch(SETTINGS, headers=session_of(COSTS), json=sent)
    assert refusal(refused) == (422, "VALIDATION_FAILED", {}, [field])
    assert version(installed) == 1


@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_name_of_two_hundred_characters_is_written(api: ContractClient, session_of: Any) -> None:
    sent = {"company_name": "x" * 200, "lock_version": 1}
    assert api.patch(SETTINGS, headers=session_of(COSTS), json=sent).status_code == 200


def matrix_with(probability: list[str], severity: list[str]) -> dict[str, Any]:
    """Give the matrix of the witness with the bounds given."""
    return {**MATRIX, "probability_bounds": probability, "severity_bounds": severity}


@pytest.mark.requirement("WF-REF-0160-A")
@pytest.mark.parametrize(
    ("bounds", "pointers"),
    [
        # The example of the contract: the severities bounded at 5, 1 and 10 %.
        (
            (["0.1", "0.3", "0.6"], ["0.05", "0.01", "0.1"]),
            ["/risk_matrix/severity_bounds/1"],
        ),
        (
            (["0.3", "0.3", "0.2"], ["0.01", "0.1", "0.1"]),
            [
                "/risk_matrix/probability_bounds/1",
                "/risk_matrix/probability_bounds/2",
                "/risk_matrix/severity_bounds/2",
            ],
        ),
    ],
)
def test_a_bound_not_above_the_one_before_is_refused_at_its_rank_and_nothing_is_written(
    api: ContractClient,
    installed: Database,
    session_of: Any,
    bounds: tuple[list[str], list[str]],
    pointers: list[str],
) -> None:
    sent = {"risk_matrix": matrix_with(*bounds), "lock_version": 1}
    refused = api.patch(SETTINGS, headers=session_of(RISKS), json=sent)
    status, code, _, fields = refusal(refused)
    assert (status, code) == (422, "VALIDATION_FAILED")
    assert fields == [{"pointer": pointer, "code": "BOUNDS_NOT_ORDERED"} for pointer in pointers]
    assert version(installed) == 1


def threshold(name: str, code: str) -> dict[str, str]:
    """Give the refusal of a threshold at its pointer."""
    return {"pointer": f"/index_thresholds/{name}", "code": code}


BELOW = "THRESHOLD_NOT_BELOW_WATCH"
BETWEEN = "THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE"
NUMBER = "NUMBER_INVALID"


@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.requirement("WF-REF-0180-A")
@pytest.mark.parametrize(
    ("sent", "fields"),
    [
        # The example of the contract: an alert equal to its watch, an alert above its watch.
        (
            ({"cost_alert": "0.9", "schedule_alert": "0.95"}, 8),
            [threshold("cost_alert", BELOW), threshold("schedule_alert", BELOW)],
        ),
        # The example of the contract: a watch at 1, and no week between two reviews.
        (
            ({"cost_watch": "1"}, 0),
            [
                threshold("cost_watch", BETWEEN),
                {
                    "pointer": "/max_weeks_between_reviews",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"minimum": 1},
                },
            ],
        ),
        (
            (dict[str, str](), 105),
            [
                {
                    "pointer": "/max_weeks_between_reviews",
                    "code": "VALUE_OUT_OF_RANGE",
                    "params": {"maximum": 104},
                }
            ],
        ),
        # The form before the range: what is no decimal is said so, whatever its value.
        (
            (
                {
                    "cost_watch": "0,9",
                    "cost_alert": ".5",
                    "schedule_watch": "abc",
                    "schedule_alert": "0",
                },
                8,
            ),
            [
                threshold("cost_watch", NUMBER),
                threshold("cost_alert", NUMBER),
                threshold("schedule_watch", NUMBER),
                threshold("schedule_alert", BETWEEN),
            ],
        ),
        # The order only between thresholds in range: an alert above a watch out of it is no fault.
        (
            ({"cost_watch": "1.5", "cost_alert": "0.95", "schedule_alert": "-0.5"}, 8),
            [threshold("cost_watch", BETWEEN), threshold("schedule_alert", BETWEEN)],
        ),
    ],
)
def test_thresholds_out_of_order_or_range_and_a_delay_out_of_range_are_refused_all_at_once(
    api: ContractClient,
    installed: Database,
    session_of: Any,
    sent: tuple[dict[str, str], int],
    fields: list[dict[str, Any]],
) -> None:
    thresholds, weeks = sent
    body = {
        "index_thresholds": {**THRESHOLDS, **thresholds},
        "max_weeks_between_reviews": weeks,
        "lock_version": 1,
    }
    refused = api.patch(SETTINGS, headers=session_of(INDICATORS), json=body)
    assert refusal(refused) == (422, "VALIDATION_FAILED", {}, fields)
    assert version(installed) == 1


@pytest.mark.requirement("WF-REF-0170-A")
def test_values_in_default_are_refused_before_a_stale_counter(
    api: ContractClient, installed: Database, session_of: Any
) -> None:
    # The values are judged before the counter, an order the contract does not fix.
    sent = {"index_thresholds": {**THRESHOLDS, "cost_alert": "0.95"}, "lock_version": 9}
    refused = api.patch(SETTINGS, headers=session_of(INDICATORS), json=sent)
    assert refusal(refused)[:2] == (422, "VALIDATION_FAILED")
    assert version(installed) == 1


@pytest.mark.requirement("WF-EXP-0020-A")
def test_settings_the_bootstrap_has_not_written_are_unavailable(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # An installation without its reference — made before it existed, until its bootstrap is run
    # again — is not served values nobody chose, nor written.
    with owner.begin() as connection:
        connection.execute(
            insert(Installation).values(
                id=THE_ROW,
                default_language="fr",
                avatar_max_bytes=1024,
                external_backup_max_bytes=1024,
                installed_at=utc_now(),
            )
        )
    headers = holding(database, realm, COSTS)
    assert refusal(api.get(SETTINGS, headers=headers))[:2] == (503, "COMPONENT_UNAVAILABLE")
    sent = {"company_name": "Autre", "lock_version": 1}
    refused = api.patch(SETTINGS, headers=headers, json=sent)
    assert refusal(refused)[:2] == (503, "COMPONENT_UNAVAILABLE")


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_sets_its_units_of_duration_once(installed: Database) -> None:
    # ``duration_units.json``: 8, 40 and 20, written over the constants of the bootstrap; held
    # once written.
    with installed.transaction() as session:
        assert units_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
        assert not units_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
        units = get_duration_units(session)
    declared = example("duration_units")
    written = (units.units.hours_per_day, units.units.hours_per_week, units.units.days_per_month)
    assert [str(value) for value in written] == [
        declared["hours_per_day"],
        declared["hours_per_week"],
        declared["days_per_month"],
    ]
    assert units.lock_version == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_finds_no_units_on_a_database_the_bootstrap_has_not_installed(
    database: Database,
) -> None:
    with database.transaction() as session:
        assert not units_slice.load(session, Witness(WITNESS, Act(None, utc_now())))
