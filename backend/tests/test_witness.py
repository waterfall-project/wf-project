# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loader of the witness, ``waterfall-api load-witness``: its settings, its order, its refusals.

Each slice is its story's to fill and to try, the witness whole US-0890's; here, the command
around them: one transaction under its lock, the slices in their order, and what it says when it
writes, when it has nothing to write and when a slice fails.
"""

import json
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import insert, select, text
from support import WITNESS

from waterfall import __version__
from waterfall.api.contract.models import DurationUnits
from waterfall.core.cost_settings.tables import CostType
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.settings import WitnessSettings
from waterfall.witness import loader
from waterfall.witness.description import Witness, is_loaded
from waterfall.witness.main import WITNESS_LOCK, load_witness, main

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

ALREADY_EXISTS = "ALREADY_EXISTS"
# The order EP-05 fixes ("Le chargeur du témoin"): each slice after those it names.
ORDER = [
    "reference_settings",
    "duration_units",
    "cost_types",
    "cost_categories",
    "hourly_rates",
    "calendars",
    "org_nodes",
    "resource_roles",
    "actual_cost_mapping",
]


@pytest.fixture
def settings(service_database_url: str, database: Database) -> WitnessSettings:
    """Give the settings of the loader on the database of the test, as the service."""
    del database
    return WitnessSettings(database_url=SecretStr(service_database_url), witness_path=str(WITNESS))


def events(logs: Logs) -> list[str]:
    """Give the events the loader logged, in their order."""
    return [record["event"] for record in logs.records if record["event"].startswith("witness.")]


def test_the_slices_are_loaded_in_the_order_of_their_dependencies(
    settings: WitnessSettings, logs: Logs, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[str] = []

    def slice_of(name: str, *, writes: bool) -> loader.Slice:
        def load(session: Session, witness: Witness) -> bool:
            assert witness.act.author is None
            assert session.execute(text("SELECT 1")).scalar_one() == 1
            called.append(name)
            return writes

        return load

    assert [name for name, _ in loader.SLICES] == ORDER
    slices = tuple((name, slice_of(name, writes=name != "hourly_rates")) for name in ORDER)
    monkeypatch.setattr(loader, "SLICES", slices)
    assert load_witness(settings) == 0
    assert called == ORDER
    loaded = [record["slices"] for record in logs.named("witness.loaded")]
    assert loaded == [[name for name in ORDER if name != "hourly_rates"]]


def test_a_loading_that_writes_nothing_succeeds_and_says_the_witness_is_there(
    settings: WitnessSettings, logs: Logs, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every slice already held: nothing is written, and that is a success.
    def held(session: Session, witness: Witness) -> bool:
        del session, witness
        return False

    monkeypatch.setattr(loader, "SLICES", tuple((name, held) for name in ORDER))
    assert load_witness(settings) == 0
    assert events(logs) == ["witness.already_loaded"]
    assert {record["correlation_id"] for record in logs.records} != {None}


def test_a_slice_refused_writes_nothing_of_the_slices_before_it(
    settings: WitnessSettings, database: Database, logs: Logs, monkeypatch: pytest.MonkeyPatch
) -> None:
    # One transaction: the nature the first slice wrote goes with the refusal of the second.
    def writing(session: Session, witness: Witness) -> bool:
        at = witness.act.at
        columns = {"code": "MO", "label": "Main-d'œuvre", "kind": "labor", "is_active": True}
        session.execute(
            insert(CostType).values(id=uuid4(), created_at=at, updated_at=at, **columns)
        )
        return True

    def refusing(session: Session, witness: Witness) -> bool:
        del session, witness
        raise ConflictError(ALREADY_EXISTS, {"conflicting_object_id": "o-1"})

    monkeypatch.setattr(loader, "SLICES", (("cost_types", writing), ("org_nodes", refusing)))
    assert load_witness(settings) == 1
    with database.transaction() as session:
        assert session.scalars(select(CostType)).all() == []
    assert [(record["code"], record["params"]) for record in logs.named("witness.refused")] == [
        ("ALREADY_EXISTS", {"conflicting_object_id": "o-1"})
    ]


def test_a_slice_that_fails_ends_the_loading_in_failure(
    settings: WitnessSettings, logs: Logs, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(session: Session, witness: Witness) -> bool:
        del session
        witness.read("absent.json", DurationUnits)
        return True

    monkeypatch.setattr(loader, "SLICES", (("duration_units", failing),))
    assert load_witness(settings) == 1
    assert events(logs) == ["witness.failed"]


def test_the_slices_are_loaded_under_the_lock_of_the_loader(
    settings: WitnessSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A lock of the transaction: two loadings wait for each other, the second finding the first's.
    held: list[int] = []

    def locked(session: Session, witness: Witness) -> bool:
        del witness
        count = session.execute(
            text(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted "
                "AND pid = pg_backend_pid() AND classid = 0 AND objid = :key AND objsubid = 1"
            ),
            {"key": WITNESS_LOCK},
        ).scalar_one()
        held.append(count)
        return False

    monkeypatch.setattr(loader, "SLICES", (("org_nodes", locked),))
    assert load_witness(settings) == 0
    assert held == [1]


def test_an_example_is_read_in_the_form_of_the_contract(tmp_path: Path) -> None:
    witness = Witness(WITNESS, Act(None, utc_now()))
    units = witness.read("duration_units.json", DurationUnits)
    assert (units.hours_per_day.root, units.hours_per_week.root) == ("8", "40")
    assert Decimal(units.days_per_month.root) == 20
    stray = {"summary": "…", "value": {"hours_per_day": 8}}
    (tmp_path / "duration_units.json").write_text(json.dumps(stray), encoding="utf-8")
    with pytest.raises(ValidationError):
        Witness(tmp_path, Act(None, utc_now())).read("duration_units.json", DurationUnits)


def test_the_command_loads_the_witness_its_settings_given(
    service_database_url: str,
    database: Database,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del database
    monkeypatch.setenv("WATERFALL_DATABASE_URL", service_database_url)
    monkeypatch.setenv("WATERFALL_WITNESS_PATH", str(WITNESS))
    assert main(["load-witness"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("environment", "fault"),
    [
        ({"WATERFALL_DATABASE_URL": "postgresql://nowhere/waterfall"}, "WATERFALL_WITNESS_PATH"),
        ({"WATERFALL_WITNESS_PATH": str(WITNESS)}, "WATERFALL_DATABASE_URL"),
    ],
)
def test_the_command_without_a_setting_stops_at_start_naming_it(
    environment: dict[str, str],
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in ("WATERFALL_DATABASE_URL", "WATERFALL_WITNESS_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    assert main(["load-witness"]) == 2
    assert f"{fault}: is missing" in capsys.readouterr().err


def test_the_command_refuses_a_witness_that_is_no_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", "postgresql://nowhere/waterfall")
    monkeypatch.setenv("WATERFALL_WITNESS_PATH", str(tmp_path / "absent"))
    assert main(["load-witness"]) == 2
    assert "WATERFALL_WITNESS_PATH: is not a directory" in capsys.readouterr().err


def test_the_command_passes_anything_else_to_the_bootstrap_and_the_api(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-api {__version__}\n"
    assert main(["serve"]) == 2
    assert "usage: waterfall-api [--version | install | load-witness]" in capsys.readouterr().err


def test_the_witness_of_the_tests_is_loaded_by_the_command_as_the_service(
    witness: Database,
) -> None:
    # Nothing to load yet: each slice fills it as its story comes (EP-05, "Les tests du back").
    with witness.transaction() as session:
        assert session.scalars(select(CostType)).all() == []


def test_a_slice_finds_its_objects_all_there_none_there_or_a_platform_half_loaded() -> None:
    first, second = sorted((uuid4(), uuid4()))
    assert is_loaded({first, second}, {first, second, uuid4()}) is True
    assert is_loaded({first, second}, {uuid4()}) is False
    # An empty slice has nothing to write, and nothing that the platform could hold.
    assert is_loaded(set(), {first}) is False
    with pytest.raises(ConflictError) as refused:
        is_loaded({first, second}, {second})
    assert (refused.value.code, dict(refused.value.params)) == (
        ALREADY_EXISTS,
        {"conflicting_object_id": str(second)},
    )
