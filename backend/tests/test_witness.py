# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loader of the witness, ``waterfall-api load-witness``: its settings, its order, its refusals.

Each slice is its story's to fill and to try, the witness whole US-0890's; here, the command
around them: one transaction under its lock, the slices in their order, and what it says when it
writes, when it has nothing to write and when a slice fails.
"""

import json
import shutil
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from cost_settings_examples import LABOUR, NON_LABOUR, PROVISION, UNSHARED
from installed_reference import install
from project_rows import (
    drop_partitions,
    insert_project,
    partition_of,
    projects_with_partitions,
    unguarded,
)
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, func, insert, select, text
from support import WITNESS

from waterfall import __version__
from waterfall.api.contract.models import DurationUnits
from waterfall.core.access_roles.tables import WRITTEN_BY_MIGRATION
from waterfall.core.cost_settings.interface import (
    read_actual_cost_mapping,
    read_reference_settings,
)
from waterfall.core.cost_settings.tables import (
    CostCategory,
    CostType,
    HourlyRate,
    ReferenceSetting,
)
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.core.resource_settings.tables import (
    Calendar,
    DurationUnit,
    OrgNode,
    ResourceRole,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import Base, utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import WitnessSettings
from waterfall.witness import chronology, loader, projects
from waterfall.witness.description import Witness, is_loaded
from waterfall.witness.main import WITNESS_LOCK, load_witness, main

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient, Logs, ReferenceSessions

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
    # The slices of the projects, after the reference, by their entry (EP-04).
    "chronology",
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


def test_the_slices_of_the_projects_are_loaded_in_their_order_after_the_reference(
    session: Session, owner: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    # One entry for the slices of the projects, last of the loader (EP-04): each slice called, in
    # the order of their dependencies, and the entry tells whether one of them wrote.
    called: list[str] = []
    # The tasks of the revisions are dated by the engine, which reads the units of the installation.
    install(owner)

    def slice_of(name: str, *, writes: bool) -> loader.Slice:
        def load(_: Session, witness: Witness) -> bool:
            assert witness.act.author is None
            called.append(name)
            return writes

        return load

    order = ["projects", "contributors", "subprojects", "work_breakdown", "timelines", "revisions"]
    assert [name for name, _ in chronology.SLICES] == order
    witness = Witness(WITNESS, Act(None, utc_now()))
    # The slices of the projects are filled: on a platform that holds none they write, and the
    # entry tells so; on a platform that holds them it writes nothing.
    with logging_context(correlation_id="witness-slices"):
        # The projects ask the reference of the witness, which the slices before them load (#2155);
        # their partitions are created first, as the loader does (#2937).
        projects.partition(session, witness)
        for _, load in loader.SLICES[:-1]:
            load(session, witness)
        assert chronology.load(session, witness) is True
        assert chronology.load(session, witness) is False
    nothing: set[str] = set()
    for writing in (nothing, {"subprojects"}):
        slices = tuple((name, slice_of(name, writes=name in writing)) for name in order)
        monkeypatch.setattr(chronology, "SLICES", slices)
        assert chronology.load(session, witness) is bool(writing)
    assert called == order * 2


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


# The tables the transaction of the loader holds ``SHARE ROW EXCLUSIVE``: those the creation of the
# partitions of a project locks so, the tables their keys bind.
HELD_SHARE_ROW_EXCLUSIVE = text(
    "SELECT relation::regclass::text FROM pg_locks WHERE locktype = 'relation' AND granted "
    "AND pid = pg_backend_pid() AND mode = 'ShareRowExclusiveLock'"
)
# The tables of the catalogue among those named.
NAMED_TABLES = text("SELECT relname FROM pg_class WHERE relname = ANY (:names)")


def test_the_partitions_of_the_projects_are_created_before_any_slice_writes(
    settings: WitnessSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #2937: created with each project, after the reference and the accounts, the partitions asked
    # their locks of a transaction that held some of their tables already; an autovacuum of one of
    # them, whose truncation waited for that transaction, held its own five seconds by table, and
    # the creation, which never waits, gave up after ten (``LockNotAvailable``). Created first,
    # before the first slice writes: the transaction holds their locks, and they are there.
    seen: list[tuple[set[str], set[str]]] = []

    def first(session: Session, witness: Witness) -> bool:
        imposed = witness.read(projects.PROJECTS_FILE, projects.Projects).items
        expected = [partition_of(each.project_id.root) for each in imposed]
        missing = set(expected) - set(session.scalars(NAMED_TABLES, {"names": expected}))
        seen.append((missing, set(session.scalars(HELD_SHARE_ROW_EXCLUSIVE))))
        return False

    monkeypatch.setattr(loader, "SLICES", (("reference_settings", first),))
    assert load_witness(settings) == 0
    [(missing, held)] = seen
    assert missing == set()
    assert {"user_account", "cost_category", "resource_role", "revision"} <= held


def test_the_partitions_are_not_created_on_a_platform_that_holds_a_project_of_the_witness(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A platform that holds the witness, or half of it: nothing to create first, the slice writes
    # nothing or refuses the platform (ALREADY_EXISTS), as before the partitions came first.
    created: list[UUID] = []

    def record(_session: Session, project_id: UUID) -> None:
        created.append(project_id)

    monkeypatch.setattr(projects, "create_project_partitions", record)
    description = Witness(WITNESS, Act(None, utc_now()))
    with witness.transaction() as session:
        projects.partition(session, description)
        projects.partition(session, description)
    assert created == []


def test_a_platform_half_loaded_is_refused_as_already_existing_not_by_the_partitions(
    database: Database, owner: Engine, service_database_url: str, logs: Logs
) -> None:
    # #2937: one project of the witness is there, with its partitions. The creation of the
    # partitions skips (``projects_present``), else it would fail on those already there; the slice
    # of the projects then refuses the platform half loaded: ALREADY_EXISTS, naming that project,
    # and nothing stays of the slices before it.
    install(owner)
    description = Witness(WITNESS, Act(None, utc_now()))
    listed = description.read(projects.PROJECTS_FILE, projects.Projects).items
    held = min(each.project_id.root for each in listed)
    with owner.begin() as connection:
        connection.execute(insert_project(id=held))
        connection.execute(select(func.create_project_partitions(held)))
    try:
        assert load(service_database_url) == 1
    finally:
        with owner.begin() as connection:
            drop_partitions(connection, held)
    refusals = [(record["code"], record["params"]) for record in logs.named("witness.refused")]
    assert refusals == [(ALREADY_EXISTS, {"conflicting_object_id": str(held)})]
    with database.transaction() as session:
        for model, column in OBJECTS:
            assert rows_of(session, model, column) == [], model


def test_the_partitions_are_created_for_each_project_of_the_witness_on_a_new_platform(
    database: Database, owner: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(owner)
    created: list[UUID] = []

    def record(_session: Session, project_id: UUID) -> None:
        created.append(project_id)

    monkeypatch.setattr(projects, "create_project_partitions", record)
    description = Witness(WITNESS, Act(None, utc_now()))
    listed = description.read(projects.PROJECTS_FILE, projects.Projects).items
    imposed = sorted(each.project_id.root for each in listed)
    with database.transaction() as session:
        projects.partition(session, description)
    assert created == imposed


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
    owner: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del database
    # The command runs on an installed platform: the tasks are dated with its units.
    install(owner)
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


def test_the_witness_of_the_tests_is_installed_as_the_bootstrap_does_then_loaded(
    witness: Database,
) -> None:
    # #2143: the settings, the units and the mapping the slices set are the bootstrap's to give
    # (``install_reference``): the witness of the tests is whole, the provision of the bootstrap
    # beside the three natures of the witness.
    with witness.transaction() as session:
        natures = set(session.scalars(select(CostType.id)))
        units = get_duration_units(session).units
        settings = read_reference_settings(session)
        mapping = read_actual_cost_mapping(session)
    assert {LABOUR, NON_LABOUR, PROVISION} < natures
    assert len(natures) == 4
    assert units.hours_per_week == 40
    assert (settings.company_name, settings.max_weeks_between_reviews) == (
        "Delmas Automatismes",
        8,
    )
    assert mapping.is_complete


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


# The witness whole (US-0890): the slices each story wrote, tried together on a platform.

# The examples whose objects bear the identifiers the witness imposes, and the key of their id.
EXAMPLES = (
    ("org_nodes_with_inactive", "org_node_id"),
    ("resource_roles", "resource_role_id"),
    ("calendars_with_inactive", "calendar_id"),
    ("cost_types", "cost_type_id"),
    ("volume/cost_categories", "cost_category_id"),
)
# The columns a loading dates and signs as the platform (WF-DAT-0070), and the counter of writes.
AUDIT = frozenset({"lock_version", "created_at", "created_by", "updated_at", "updated_by"})
# The tables the witness fills, and the column that holds the identifier the witness imposes.
OBJECTS = (
    (OrgNode, "id"),
    (ResourceRole, "id"),
    (Calendar, "id"),
    (CostType, "id"),
    (CostCategory, "id"),
    (HourlyRate, "cost_category_id"),
)


def example(name: str) -> Any:
    """Read the value of an example of the contract the witness is made of."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def items_of(name: str) -> list[dict[str, Any]]:
    """Give the objects of an example: a list of nodes, or the items of a page."""
    value = example(name)
    if isinstance(value, list):
        return cast("list[dict[str, Any]]", value)
    return cast("list[dict[str, Any]]", value["items"])


def imposed() -> set[UUID]:
    """Give the identifiers the witness imposes on its nodes, roles, calendars and categories."""
    return {UUID(item[key]) for name, key in EXAMPLES for item in items_of(name)}


def rows_of(session: Session, model: type[Base], column: str) -> list[Any]:
    """Read the rows of a table that bear an identifier of the witness, in the order of the key."""
    held = getattr(model, column)
    return list(session.scalars(select(model).where(held.in_(imposed())).order_by(held)))


def identifying(database: Database) -> dict[str, list[tuple[str, ...]]]:
    """Give what identifies the objects of the witness: every column but those the platform fills.

    The audit and the identifier of a rate are the platform's; the rest is the witness's, and the
    same on two platforms.
    """
    held: dict[str, list[tuple[str, ...]]] = {}
    with database.transaction() as session:
        for model, column in OBJECTS:
            names = [
                each.key
                for each in model.__table__.columns
                if each.key not in AUDIT and not (model is HourlyRate and each.key == "id")
            ]
            held[model.__tablename__] = sorted(
                tuple(str(getattr(row, name)) for name in names)
                for row in rows_of(session, model, column)
            )
        for model in (DurationUnit, ReferenceSetting):
            held[model.__tablename__] = [
                tuple(
                    str(getattr(row, each.key))
                    for each in model.__table__.columns
                    if each.key not in AUDIT
                )
                for row in session.scalars(select(model))
            ]
        mapping = read_actual_cost_mapping(session)
        held["actual_cost_mapping"] = [(str(mapping.columns), str(mapping.kept_columns))]
    return held


def load(url: str, directory: Path = WITNESS) -> int:
    """Run the command on the database of the test, the description at ``directory``."""
    return load_witness(WitnessSettings(database_url=SecretStr(url), witness_path=str(directory)))


def wipe(owner: Engine) -> None:
    """Empty the database of every row, as the owner does after a test: a platform neuve again.

    The partitions of the projects go with their rows: a project loaded again creates them again.
    """
    with owner.begin() as connection:
        unguarded(connection)
        drop_partitions(connection)
        for table in reversed(Base.metadata.sorted_tables):
            if not table.info.get(WRITTEN_BY_MIGRATION):
                connection.execute(delete(table))


def test_the_witness_holds_the_volumes_of_the_tranche_of_the_reference(witness: Database) -> None:
    # Six nodes (two deactivated), five roles (two deactivated), three calendars (one deactivated),
    # three natures, two hundred categories, the grid of a hundred and fifty on fifteen years, the
    # units, the settings and the mapping.
    grid = example("volume/hourly_rate_grid")
    cells = [cell for row in grid["rows"] for cell in row["cells"] if cell is not None]
    with witness.transaction() as session:
        held = [
            rows_of(session, model, column) for model, column in OBJECTS if model is not HourlyRate
        ]
        rates = rows_of(session, HourlyRate, "cost_category_id")
        units = get_duration_units(session).units
        mapping = read_actual_cost_mapping(session)
    nodes, roles, calendars, types, _ = held
    assert [len(each) for each in held] == [6, 5, 3, 3, 200]
    assert [sum(not each.is_active for each in rows) for rows in (nodes, roles, calendars)] == [
        2,
        2,
        1,
    ]
    assert (len(grid["rows"]), len(grid["years"]), len(cells)) == (150, 15, 1938)
    assert len(rates) == len(cells)
    assert {each.year for each in rates} == set(grid["years"])
    assert [each.label for each in calendars if each.is_default] == ["Semaine standard"]
    assert [each.kind for each in types if each.is_active] == ["labor", "non_labor", "provision"]
    assert (units.hours_per_day, units.hours_per_week, units.days_per_month) == (8, 40, 20)
    assert [column.column for column in mapping.columns] == [
        column["column"] for column in example("actual_cost_mapping")["columns"]
    ]


def without_audit(value: Any) -> Any:
    """Give a value of the contract without what a loading does not write as the example says.

    The audit, the counter of writes and the commands (``UNSHARED``), at any depth.
    """
    if isinstance(value, list):
        return [without_audit(each) for each in cast("list[object]", value)]
    if isinstance(value, dict):
        mapped = cast("dict[str, object]", value)
        return {key: without_audit(each) for key, each in mapped.items() if key not in UNSHARED}
    return value


def item_id(item: dict[str, Any]) -> UUID:
    """Give the identifier of an object read, whatever its kind: its key that ends in ``_id``."""
    return UUID(next(value for key, value in item.items() if key.endswith("_id")))


@pytest.mark.parametrize(
    "case",
    [
        ("org-nodes?include_inactive=true", "resource_settings", "org_nodes_with_inactive"),
        ("resource-roles?include_inactive=true", "resource_settings", "resource_roles"),
        ("calendars?include_inactive=true", "resource_settings", "calendars_with_inactive"),
        ("cost-types", "cost_settings", "cost_types"),
        ("cost-categories?limit=500", "cost_settings", "volume/cost_categories"),
        ("hourly-rates?limit=500", "cost_settings", "volume/hourly_rate_grid"),
        ("duration-units", "resource_settings", "duration_units"),
        ("settings", "cost_settings", "reference_settings"),
        ("actual-cost-mapping", "cost_settings", "actual_cost_mapping"),
    ],
)
def test_the_lists_of_the_service_loaded_with_the_witness_are_the_examples_the_faux_back_serves(
    api: ContractClient,
    witness: Database,
    reference_sessions: ReferenceSessions,
    case: tuple[str, str, str],
) -> None:
    # The calculated becomes the expected: what the service reads of the witness is what the
    # fixtures say, to the audit columns, the counter of writes and the commands near, as the
    # tests of each list.
    del witness
    path, part, example_name = case
    response = api.get(f"/api/v1/reference/{path}", headers=reference_sessions(part).changing)
    assert response.status_code == 200, response.text
    expected = example(example_name)
    read = response.json()
    if "items" in expected:
        # What the bootstrap wrote beside (its default calendar, its provision) is not the witness.
        read = {
            "items": [item for item in read["items"] if item_id(item) in imposed()],
        }
        expected = {"items": expected["items"]}
    assert without_audit(read) == without_audit(expected)


def test_two_new_platforms_loaded_with_the_witness_hold_the_same_identifying_data(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # Two loadings, each on a platform neuve (the rows emptied, the bootstrap done again): the
    # identifiers, the codes and the labels are the same; only what the platform engenders differs.
    first = identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying(witness) == first
    assert len(first["cost_category"]) == 200


def test_a_second_loading_on_the_same_platform_writes_nothing_and_says_the_witness_is_there(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    def audited() -> list[tuple[object, ...]]:
        with witness.transaction() as session:
            return [
                tuple(getattr(row, name) for name in sorted(AUDIT))
                for model, column in OBJECTS
                for row in rows_of(session, model, column)
            ]

    before, held = audited(), identifying(witness)
    logs.clear()
    assert load(service_database_url) == 0
    assert events(logs) == ["witness.already_loaded"]
    assert audited() == before
    assert identifying(witness) == held


def test_the_loading_dates_and_signs_every_object_as_the_platform_not_as_the_witness(
    database: Database, owner: Engine, service_database_url: str
) -> None:
    # WF-DAT-0070: created at the moment of the loading, by no account (the platform); the dates
    # and the authors the examples say (September 2025, an account) are not kept.
    said = items_of("org_nodes_with_inactive")[0]["audit"]
    assert (said["created_at"][:4], said["created_by"]["kind"]) == ("2025", "user")
    install(owner)
    started = utc_now()
    assert load(service_database_url) == 0
    ended = utc_now()
    with database.transaction() as session:
        for model, column in OBJECTS:
            rows = rows_of(session, model, column)
            assert rows, model
            for row in rows:
                assert started <= row.created_at <= row.updated_at <= ended, model
                assert (row.created_by, row.updated_by) == (None, None), model


def test_the_witness_holds_no_address_and_only_the_fictitious_labels_of_its_description(
    witness: Database,
) -> None:
    # No electronic address in any text the tranche writes, and the labels of the objects are those
    # of the examples, which `test_mockuniverse.py` holds fictitious.
    said = {item["label"] for name, _ in EXAMPLES for item in items_of(name)}
    texts: set[str] = set()
    labels: set[str] = set()
    with witness.transaction() as session:
        for model, column in OBJECTS:
            for row in rows_of(session, model, column):
                texts.update(
                    value
                    for each in model.__table__.columns
                    if isinstance(value := getattr(row, each.key), str)
                )
                if model is not HourlyRate:
                    labels.add(row.label)
    assert not any("@" in text for text in texts)
    assert labels == said


def test_the_command_stops_saying_so_on_a_witness_the_rules_refuse_and_writes_nothing(
    tmp_path: Path, database: Database, owner: Engine, service_database_url: str, logs: Logs
) -> None:
    # A role of the description bears the code of another: the rule of the roles refuses it, after
    # the slices before it have written; one transaction, none of them stays.
    install(owner)
    refused = tmp_path / "witness"
    shutil.copytree(WITNESS, refused)
    path = refused / "resource_roles.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document["value"]["items"]
    items[1]["code"] = items[0]["code"]
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load(service_database_url, refused) == 1
    assert [record["code"] for record in logs.named("witness.refused")] == [ALREADY_EXISTS]
    assert events(logs) == ["witness.refused"]
    with database.transaction() as session:
        for model, column in OBJECTS:
            assert rows_of(session, model, column) == [], model


def test_the_witness_is_refused_on_an_installation_that_holds_a_project_without_its_calendars(
    database: Database, owner: Engine, service_database_url: str, logs: Logs
) -> None:
    # Its default calendar, designated, would judge the tasks of a project already there, and
    # redate them: the loader refuses such an installation, naming the project, and writes nothing
    # of the slices before the calendars (#2556).
    install(owner)
    with projects_with_partitions(owner) as [project_id]:
        assert load(service_database_url) == 1
        refusals = [(record["code"], record["params"]) for record in logs.named("witness.refused")]
        assert refusals == [(ALREADY_EXISTS, {"conflicting_object_id": str(project_id)})]
        with database.transaction() as session:
            for model, column in OBJECTS:
                assert rows_of(session, model, column) == [], model
