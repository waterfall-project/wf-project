# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The registries of the extensions, filled in every process that needs them (#2180; EP-06).

A registry is filled at the import of the interface of the module that registers: a process that
never imports it holds a registry without its part, and copies a revision without its tasks, or
designates a reference without asking for them, in silence. Each entry point — the API
(``create_app``), the worker (``handlers``), the loader of the witness (``load_witness``) — is
imported in a process of its own, and its registries compared with those of a process that imports
every module of the core and of the witness: none lacks an extension that a module registers. What
the socle of EP-06 registers is named, so that the comparison is never between two empty lists.

Then how each registry acts, details of the realization which reprise no Vérif: the closing of a
revision, the guard and the recalculation of the reference, the attachments of the work breakdown,
the facets, the formats and the exporters, the fillers of the witness.
"""

import json
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.core.exchanges.interface import (
    exporters,
    formats,
    register_exporter,
    register_format,
)
from waterfall.core.history.interface import close_history
from waterfall.core.planning.interface import (
    MS_PROJECT_EXPORTER,
    MS_PROJECT_FORMAT,
    TASK_TREE_EXPORTER,
    FacetHooks,
    delete_nodes,
    facets,
    register_facet,
)
from waterfall.core.projects.interface import (
    Attachments,
    detach_item,
    item_cited,
    register_attachments,
)
from waterfall.core.resource_settings.interface import (
    DEFAULT_UNITS,
    CalendarChange,
    CalendarContent,
    IdleProject,
    WeeklyHours,
    create_calendar,
    get_duration_units,
    install_duration_units,
    register_idle_task_guard,
    register_recalculation,
    set_default_calendar,
    set_duration_units,
    update_calendar,
)
from waterfall.core.revisions.interface import (
    RevisionClosing,
    closers,
    mark_revision,
    register_closing,
)
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.logs import logging_context
from waterfall.witness.revisions import OpenedRevision, register_revision_filler

if TYPE_CHECKING:
    from collections.abc import Iterator

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.witness.description import Witness

# Each entry point, by the module that holds it.
ENTRY_POINTS = {
    "api": "waterfall.api.app",
    "worker": "waterfall.worker.main",
    "loader": "waterfall.witness.main",
}
# The registries only the loader of the witness reads.
WITNESS = "witness."
# What a process writes: the entries of each of its registries, each named by where it lives.
DUMP = """
import dataclasses, importlib, json, pkgutil, sys

from waterfall.platform.registry import registries


def named(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, tuple):
        return ":".join(named(part) for part in entry)
    if dataclasses.is_dataclass(entry):
        parts = ", ".join(named(getattr(entry, field.name)) for field in dataclasses.fields(entry))
        return f"{type(entry).__qualname__}({parts})"
    return f"{entry.__module__}.{getattr(entry, '__qualname__', type(entry).__qualname__)}"


for name in sys.argv[1:]:
    if name.endswith(".*"):
        package = importlib.import_module(name[:-2])
        for found in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            importlib.import_module(found.name)
    else:
        importlib.import_module(name)
held = {name: [named(entry) for entry in entries] for name, entries in registries().items()}
print(json.dumps(held))
"""
# Every registry of the core and of the witness EP-04 and EP-06 declare.
DECLARED = {
    "revisions.copy",
    "revisions.tasks_and_lines",
    "revisions.indicators",
    "revisions.closing",
    "resource_settings.idle_task_guard",
    "resource_settings.recalculation",
    "projects.attachments",
    "planning.facets",
    "exchanges.formats",
    "exchanges.exporters",
    "witness.revision_fillers",
}
PLANNING = "waterfall.core.planning.interface"
# What the socle of EP-06 registers (US-1380/L1), the copy of the nodes after the structures'.
REGISTERED = {
    "revisions.copy": [
        "waterfall.core.revisions.interface.structures.copy_structures",
        f"{PLANNING}.nodes.copy_nodes",
    ],
    "revisions.tasks_and_lines": [f"tasks:{PLANNING}.nodes.revision_has_tasks"],
    "resource_settings.idle_task_guard": [f"{PLANNING}.reference.tasks_left_idle"],
    "resource_settings.recalculation": [f"{PLANNING}.reference.reschedule_current_structures"],
    "projects.attachments": [
        (
            f"Attachments({PLANNING}.work_breakdown.work_breakdown_item_cited, "
            f"{PLANNING}.work_breakdown.detach_work_breakdown_item)"
        )
    ],
    "revisions.closing": [
        "history:waterfall.core.history.interface.closing.close_history",
        f"content:{PLANNING}.closing.delete_nodes",
    ],
    "exchanges.formats": [f"ms_project_schedule:{PLANNING}.msproject.MsProjectFormat"],
    "exchanges.exporters": [
        f"ms_project_schedule:{PLANNING}.msproject.MsProjectExporter",
        f"task_tree_image:{PLANNING}.task_tree.TaskTreeExporter",
    ],
    "witness.revision_fillers": ["waterfall.witness.tasks.fill"],
}


def registered_in(*modules: str) -> dict[str, list[str]]:
    """Give the registries of a process that imports these modules alone, by name."""
    result = subprocess.run(
        [sys.executable, "-c", DUMP, *modules],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def everything() -> dict[str, list[str]]:
    """Give the registries of a process that imports every module of the core and the witness."""
    return registered_in("waterfall.core.*", "waterfall.witness.*")


def test_every_registry_holds_what_the_socle_of_ep06_registers(
    everything: dict[str, list[str]],
) -> None:
    assert set(everything) == DECLARED
    for name, entries in REGISTERED.items():
        assert everything[name][: len(entries)] == entries, name


@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_holds_every_extension_of_the_registries_it_reads(
    entry_point: str, everything: dict[str, list[str]]
) -> None:
    # The API and the worker read no registry of the witness; the loader reads them all.
    held = registered_in(ENTRY_POINTS[entry_point])
    read = {
        name: entries
        for name, entries in everything.items()
        if entry_point == "loader" or not name.startswith(WITNESS)
    }
    assert {name: held.get(name) for name in read} == read


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


@dataclass(frozen=True)
class Closed:
    """A closing a module received: the revision, why, and its status then."""

    revision_id: UUID
    kind: str
    status: str


def test_a_closing_registered_runs_before_the_revision_is_marked_or_abandoned(
    api: ContractClient, stage: Scene
) -> None:
    closed: list[Closed] = []

    def close(closing: RevisionClosing) -> None:
        status = closing.session.scalar(
            select(Revision.status).where(Revision.id == closing.revision_id)
        )
        closed.append(Closed(closing.revision_id, closing.kind, str(status)))

    with ExitStack() as registered:
        registered.callback(register_closing("content", close))
        marked = open_revision(api, stage)
        with (
            logging_context(correlation_id="marking"),
            Session(stage.owner) as session,
            session.begin(),
        ):
            mark_revision(session, UUID(marked["revision_id"]), "v1.0", None, Act(None, utc_now()))
        abandoned = open_revision(api, stage)
        path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{abandoned['revision_id']}"
        response = api.delete(
            f"{path}?lock_version={abandoned['lock_version']}", headers=stage.manager.headers
        )
        assert response.status_code == 204, response.text
    assert closed == [
        Closed(UUID(marked["revision_id"]), "marked", "draft"),
        Closed(UUID(abandoned["revision_id"]), "abandoned", "draft"),
    ]


def test_the_closings_run_stage_by_stage_whatever_the_order_of_their_registration() -> None:
    # The history and its plans before the content of the revision (EP-06, "Les points
    # d'extension"): a part of the content registered first still runs after a part of the history
    # registered later, and the planning's nodes after the history's stacks in any process.
    def content(closing: RevisionClosing) -> None:
        del closing

    def history(closing: RevisionClosing) -> None:
        del closing

    with ExitStack() as registered:
        registered.callback(register_closing("content", content))
        registered.callback(register_closing("history", history))
        ordered = closers()
    assert ordered.index(history) < ordered.index(content)
    assert closers().index(close_history) < closers().index(delete_nodes)


EIGHT = Decimal(8)
WEEK = WeeklyHours(EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, Decimal(0), Decimal(0))
ATELIER = CalendarContent("Atelier", WEEK)
RENAMED = CalendarContent("Atelier B", WEEK)


def test_a_guard_registered_refuses_a_calendar_that_would_leave_a_task_idle(
    database: Database,
) -> None:
    asked: list[CalendarChange] = []

    def guard(_session: Session, change: CalendarChange) -> tuple[IdleProject, ...]:
        asked.append(change)
        return (IdleProject("Ligne de convoyage", "PRJ-001"), IdleProject("Sans code", None))

    act = Act(None, utc_now())
    with database.transaction() as session:
        calendar = create_calendar(session, ATELIER, act)
    with ExitStack() as registered:
        registered.callback(register_idle_task_guard(guard))
        with pytest.raises(UnprocessableError) as refused, database.transaction() as session:
            update_calendar(
                session,
                calendar.calendar_id,
                CalendarContent("Atelier", WEEK),
                calendar.lock_version,
                act,
            )
    assert (refused.value.code, refused.value.params) == (
        "TASK_WITHOUT_WORKING_HOURS",
        {
            "resource_roles": [],
            "projects": [
                {"project_label": "Ligne de convoyage", "project_code": "PRJ-001"},
                {"project_label": "Sans code", "project_code": None},
            ],
        },
    )
    [change] = asked
    assert (change.calendar_id, change.default, change.weekly_hours["saturday"]) == (
        calendar.calendar_id,
        False,
        Decimal(0),
    )


def test_a_recalculation_registered_runs_once_the_reference_is_written(
    database: Database,
) -> None:
    ran: list[str] = []
    act = Act(None, utc_now())
    with database.transaction() as session:
        install_duration_units(session, act)
        calendar = create_calendar(session, ATELIER, act)
    with ExitStack() as registered:
        registered.callback(register_recalculation(lambda _session, _at: ran.append("redated")))
        with database.transaction() as session:
            set_duration_units(
                session, DEFAULT_UNITS, get_duration_units(session).lock_version, act
            )
        assert ran == ["redated"]
        with database.transaction() as session:
            changed = update_calendar(
                session,
                calendar.calendar_id,
                CalendarContent("Atelier B", WEEK),
                calendar.lock_version,
                act,
            )
        assert ran == ["redated"] * 2
        with database.transaction() as session:
            set_default_calendar(session, calendar.calendar_id, changed.lock_version, act)
        assert ran == ["redated"] * 3


def test_the_attachments_registered_tell_and_detach_an_element_of_the_work_breakdown(
    session: Session,
) -> None:
    detached: list[tuple[UUID, UUID]] = []
    project_id, item_id = uuid4(), uuid4()
    assert not item_cited(session, item_id)
    with ExitStack() as registered:
        registered.callback(
            register_attachments(
                Attachments(
                    lambda _session, item: item == item_id,
                    lambda _session, project, item: detached.append((project, item)),
                )
            )
        )
        assert (item_cited(session, item_id), item_cited(session, uuid4())) == (True, False)
        detach_item(session, project_id, item_id)
    assert detached == [(project_id, item_id)]


def test_a_kind_has_one_facet_one_format_and_one_exporter_at_most() -> None:
    # Those of the planning, registered at the import of its interface, serve another kind here.
    held = (dict(facets()), dict(formats()), dict(exporters()))
    hooks = FacetHooks(
        read=lambda _session, _project, _nodes: {},
        copy=lambda _copy: None,
        delete=lambda _session, _project, _nodes: None,
        calendars=lambda _session, _project, _task: (),
    )
    with ExitStack() as registered:
        registered.callback(register_facet("estimate_line", hooks))
        registered.callback(register_format("estimate", MS_PROJECT_FORMAT))
        registered.callback(register_exporter("estimate", TASK_TREE_EXPORTER))
        assert (list(facets()), list(formats()), list(exporters())) == (
            ["estimate_line"],
            ["ms_project_schedule", "estimate"],
            ["ms_project_schedule", "task_tree_image", "estimate"],
        )
        with pytest.raises(ValueError, match="registered already"):
            register_facet("estimate_line", hooks)
        with pytest.raises(ValueError, match="has a format already"):
            register_format("estimate", MS_PROJECT_FORMAT)
        with pytest.raises(ValueError, match="has an exporter already"):
            register_exporter("estimate", MS_PROJECT_EXPORTER)
    assert (dict(facets()), dict(formats()), dict(exporters())) == held


@pytest.fixture
def fillers() -> Iterator[list[UUID]]:
    """Register a filler of the revisions of the witness that notes each revision opened."""
    opened: list[UUID] = []

    def note(_session: Session, _witness: Witness, revision: OpenedRevision) -> None:
        opened.append(revision.revision.revision_id.root)

    withdraw = register_revision_filler(note)
    yield opened
    withdraw()


def test_the_witness_fills_each_revision_it_opens_before_the_next_event(
    fillers: list[UUID], witness_loaded: Database
) -> None:
    # The 100, the 101 and the 102 of PRJ-001, in the order the chronology opens them.
    with witness_loaded.transaction() as session:
        revisions = session.scalars(
            select(Revision.id).order_by(Revision.created_at, Revision.id)
        ).all()
    assert fillers == list(revisions)
    assert len(fillers) == 3
