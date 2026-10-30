# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the examples of the platform, aligned on the specification 1.0.0 (US-0701/L8).

The schedule of the reading of the accounts, the parameters of operation on the screen of status,
the predefined « Manager » of the witness, the journal read by one who may open no project, and
the reading of the currency by any session.
"""

from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockaudit, mockwitness

_PATHS = REPOSITORY / "docs/api/paths"
_STATUSES = (
    "system_status",
    "system_status_backup_failed",
    "system_status_storage_full",
    "system_status_copy_failed",
)
_MANAGER = "01926f3a-7c00-7000-8000-000000000702"
_SETTINGS = ("risk_settings.write", "indicator_settings.write")


def _operation(file: str, path: str, method: str) -> dict[str, Any]:
    """Return an operation of the contract, as its file of paths declares it."""
    paths = yaml.safe_load((_PATHS / file).read_text(encoding="utf-8"))
    operation: dict[str, Any] = paths[path][method]
    return operation


def _projects(events: list[Any]) -> list[dict[str, Any]]:
    """Return the projects the inscriptions name, in their order, those without one left out."""
    return [each["project"] for each in cast("list[dict[str, Any]]", events) if each["project"]]


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_reading_of_the_accounts_is_scheduled_daily_by_default_and_set_by_a_user() -> None:
    # « au terme de la périodicité choisie, sans intervention » : the schedule as delivered is
    # daily and enabled; the one a user sets is read back as he chose it.
    delivered = mockwitness.fixture("identity_sync_schedule")
    assert (delivered["is_enabled"], delivered["frequency"], delivered["weekday"]) == (
        True,
        "daily",
        None,
    )
    chosen = mockwitness.fixture("identity_sync_schedule_set")
    assert (chosen["frequency"], chosen["weekday"]) == ("weekly", 1)
    assert chosen["lock_version"] == delivered["lock_version"] + 1
    writing = _operation("access.yaml", "/identity-sync-schedule", "put")
    assert writing["operationId"] == "setIdentitySyncSchedule"
    assert "users.write" in writing["description"]


@pytest.mark.requirement("WF-ADM-0130-A")
@pytest.mark.parametrize("name", _STATUSES)
def test_the_screen_of_status_presents_the_validity_of_the_cache_in_force(name: str) -> None:
    # « L'écran présente la durée de validité du cache en vigueur » : each reading of the screen
    # carries the parameters of operation, the same in force on every one of them.
    parameters = mockwitness.fixture(name)["operating_parameters"]
    assert parameters["cache_validity_seconds"] == 600
    assert parameters == mockwitness.fixture("system_status")["operating_parameters"]
    assert parameters["avatar_max_bytes"] == mockwitness.fixture("installation")["avatar_max_bytes"]


@pytest.mark.requirement("WF-INTF-0020-A")
def test_the_predefined_manager_completes_the_settings_of_fbs_3_whole() -> None:
    # « mène à leur terme le paramétrage de chacune des fonctions FBS-3.1 à FBS-3.4 » : the
    # predefined manager writes the settings of risks and of indicators, and so does its holder.
    [manager] = [
        each for each in mockwitness.fixture("access_roles") if each["access_role_id"] == _MANAGER
    ]
    assert manager["is_predefined"]
    assert set(_SETTINGS) <= set(manager["permissions"])
    assert set(_SETTINGS) <= set(mockwitness.fixture("me_manager")["permissions"])
    assert mockwitness.fixture("access_role") == manager


@pytest.mark.requirement("WF-ADM-0190-A")
def test_an_inscription_on_a_project_the_reader_cannot_consult_names_it_without_opening_it() -> (
    None
):
    # « Une inscription sur un projet que le lecteur ne peut pas consulter nomme ce projet sans
    # l'ouvrir » : the auditor reads the code and the label of the witness, and no link.
    witness = [each for each in mockaudit.journal() if each["project"] is not None]
    named, read = _projects(witness), _projects(mockaudit.unopenable(witness))
    assert all(project["can_open"] for project in named)
    assert [project["code"] for project in read] == [project["code"] for project in named]
    assert not any(project["can_open"] for project in read)


def test_the_exit_and_the_imports_say_their_parameters() -> None:
    # B-02: the exit says the state it reached, an import its nature.
    exited = mockaudit.exit_today().params
    assert exited == {"to_state": "completed", "reason": None}
    events = cast("list[dict[str, Any]]", mockaudit.journal())
    kinds = {each["params"]["import_kind"] for each in events if each["action"] == "import_apply"}
    assert kinds == {"actual_costs"}


@pytest.mark.requirement("WF-REF-0140-A")
def test_the_currency_is_read_by_any_session() -> None:
    # « La devise apparaît partout où un montant est affiché » : the settings that bear it are
    # read by any open session, without a permission that would hide them.
    reading = _operation("reference.yaml", "/reference/settings", "get")
    assert "404" not in reading["responses"]
    assert set(reading["responses"]) == {"200", "401", "503"}
    assert mockwitness.fixture("reference_settings")["currency_code"] == "EUR"
