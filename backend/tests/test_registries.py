# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The registries of the extensions, filled in every process that needs them (#2180; EP-06).

A registry is filled at the import of the interface of the module that registers: a process that
never imports it holds a registry without its part, and copies a revision without its tasks, or
designates a reference without asking for them, in silence. Each entry point — the API
(``create_app``), the worker (``handlers``), the loader of the witness (``load_witness``) — is
imported in a process of its own, and its registries compared with those of a process that imports
every module of the core and of the witness: none lacks an extension that a module registers — the
worker those of the estimate included, which it imports from US-1500/L2 on (EP-07, "Le worker").
What the socles of EP-06 and EP-07 register is named, so that the comparison is never between two
empty lists.

Then how each registry acts, details of the realization which reprise no Vérif: the closing of a
revision, what its marking keeps and what follows the designation of a reference (EP-07), the guard
and the recalculation of the reference, the categories a line employs (EP-07), the attachments of
the work breakdown, the facets, the formats and the exporters, the fillers of the witness.
"""

import json
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import give_a_line
from planning_support import give_a_task
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.core.cost_settings.interface import category_is_employed, register_employment
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
    Units,
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
    CLOSING_STAGES,
    ReferenceDesignated,
    RevisionClosing,
    RevisionMarking,
    closers,
    mark_revision,
    register_closing,
    register_designation,
    register_indicators,
    register_marking,
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

    from waterfall.core.revisions.interface import RevisionCopy
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
# The registry whose order of registration does not count across its stages (#2470).
CLOSING = "revisions.closing"
# Every registry of the core and of the witness EP-04, EP-06 and EP-07 declare.
DECLARED = {
    "revisions.copy",
    "revisions.tasks_and_lines",
    "revisions.indicators",
    "revisions.marking",
    "revisions.designation",
    "revisions.rate_update",
    "cost_settings.employment",
    CLOSING,
    "resource_settings.idle_task_guard",
    "resource_settings.recalculation",
    "projects.attachments",
    "projects.opening",
    "projects.estimate_facts",
    "planning.facets",
    "exchanges.formats",
    "exchanges.exporters",
    "witness.revision_fillers",
}
PLANNING = "waterfall.core.planning.interface"
# What EP-06 registers (US-1380/L1, US-1390/L2), the copy of the nodes after the structures', and
# their redating after them.
REGISTERED = {
    "revisions.copy": [
        "waterfall.core.revisions.interface.structures.copy_structures",
        f"{PLANNING}.nodes.copy_nodes",
        f"{PLANNING}.reference.redate_copy",
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
    "projects.opening": [f"{PLANNING}.skeleton.opening_with_tasks"],
    CLOSING: [
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
ESTIMATE = "waterfall.core.estimate.interface"
CORE = "waterfall.core.estimate"
# The hooks of the facet of the lines, in the order of ``FacetHooks`` (US-1490/L3).
LINE_HOOKS = (
    f"{CORE}.reading.read_lines",
    f"{ESTIMATE}.facet.copy_lines",
    f"{ESTIMATE}.facet.delete_lines",
    f"{ESTIMATE}.facet.line_calendars",
    f"{CORE}.writing.create_line",
    f"{ESTIMATE}.facet.snapshot_lines",
    f"{ESTIMATE}.facet.restore_lines",
    f"{ESTIMATE}.facet.reinflate_lines",
    f"{CORE}.reading.totals_of",
    f"{CORE}.reading.filter_lines",
    f"{CORE}.reading.sort_lines",
    f"{ESTIMATE}.facet.line_dependencies",
    f"{ESTIMATE}.facet.judge_moved_lines",
    f"{CORE}.pasting.judge_line_cell",
    f"{CORE}.pasting.write_line_cell",
)
# What the estimate answers the projects of its lines (US-1490/L4), in the order of
# ``EstimateFacts``.
FACTS = (
    f"{ESTIMATE}.employment.subproject_is_cited",
    f"{ESTIMATE}.employment.subproject_is_estimated",
    f"{ESTIMATE}.employment.subproject_estimate_lines",
    f"{ESTIMATE}.contributors.roles_employed",
    f"{ESTIMATE}.contributors.marked_revision_has_lines",
    f"{ESTIMATE}.rates.reinflate_project",
    f"{ESTIMATE}.rates.hold_revision",
)
# What the socle of EP-07 registers without effect (US-1490/L1), after the planning's, and the
# facet and the question of the lines US-1490/L3 registers; the registries of EP-07 come with
# their stories (decisions of 2026-11-08, #2370): the employment and the facts of the lines with
# US-1490/L4, the marking, the designation and the rates written with US-1500/L2.
REGISTERED_BY_EP07 = {
    "planning.facets": [f"estimate_line:FacetHooks({', '.join(LINE_HOOKS)})"],
    "revisions.tasks_and_lines": [f"lines:{ESTIMATE}.lines.revision_has_lines"],
    "revisions.copy": [f"{CORE}.keeping.copy_rates"],
    "revisions.rate_update": [f"{CORE}.keeping.rate_update_offered"],
    CLOSING: [f"content:{CORE}.keeping.close_rates"],
    "resource_settings.idle_task_guard": [f"{ESTIMATE}.calendars.idle_tasks_for_role_calendar"],
    "exchanges.formats": [f"estimate:{ESTIMATE}.excel.EstimateFormat"],
    "exchanges.exporters": [f"estimate:{ESTIMATE}.excel.EstimateExporter"],
    "witness.revision_fillers": ["waterfall.witness.estimate_lines.fill"],
    "cost_settings.employment": [
        f"{ESTIMATE}.employment.category_is_employed:{CORE}.repricing.reprice_after_rate"
    ],
    "projects.estimate_facts": [f"EstimateFacts({', '.join(FACTS)})"],
    "revisions.marking": [f"{ESTIMATE}.rates.keep_images"],
    "revisions.designation": [f"{ESTIMATE}.rates.refresh_budgeted"],
}


def as_run(name: str, entries: list[str]) -> list[str]:
    """Give the entries of a registry in the order they act.

    The closings run stage by stage whatever the order of the imports (``closers``), each stage in
    the order of its registrations: a process that imports the planning before the history holds
    the same closings, which run in the same order.
    """
    if name != CLOSING:
        return entries
    return sorted(entries, key=lambda entry: CLOSING_STAGES.index(entry.split(":")[0]))


def registered_in(*modules: str) -> dict[str, list[str]]:
    """Give the registries of a process that imports these modules alone, by name, as they act."""
    result = subprocess.run(
        [sys.executable, "-c", DUMP, *modules],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    held: dict[str, list[str]] = json.loads(result.stdout)
    return {name: as_run(name, entries) for name, entries in held.items()}


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


def test_every_registry_holds_what_the_socle_of_ep07_registers_after_the_planning(
    everything: dict[str, list[str]],
) -> None:
    # The extensions of the estimate, each after those of EP-06 in its registry; the marking and the
    # designation filled by US-1500/L2.
    for name, entries in REGISTERED_BY_EP07.items():
        held = [entry for entry in everything[name] if entry not in REGISTERED.get(name, [])]
        assert held == entries, name


@pytest.mark.parametrize("entry_point", sorted(ENTRY_POINTS))
def test_each_entry_point_holds_every_extension_of_the_registries_it_reads(
    entry_point: str, everything: dict[str, list[str]]
) -> None:
    # The API and the worker read no registry of the witness; the loader reads them all. The worker
    # imports the interface of the estimate (US-1500/L2): nothing lacks, its marking keeps images.
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


def test_a_marking_registered_keeps_its_part_before_the_indicators_of_the_revision(
    api: ContractClient, stage: Scene
) -> None:
    # What EP-07 keeps of a revision being marked — its images, its rates —, in the transaction of
    # the marking, the revision judged and still current, before its indicators are computed.
    ran: list[tuple[str, UUID, str]] = []

    def keep(marking: RevisionMarking) -> None:
        status = marking.session.scalar(
            select(Revision.status).where(Revision.id == marking.revision_id)
        )
        assert (marking.project_id, marking.at) == (UUID(stage.project["project_id"]), at)
        ran.append(("kept", marking.revision_id, str(status)))

    def compute(_session: Session, revision_id: UUID) -> None:
        ran.append(("computed", revision_id, "draft"))

    at = utc_now()
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    with ExitStack() as registered:
        registered.callback(register_marking(keep))
        registered.callback(register_indicators(compute))
        with (
            logging_context(correlation_id="marking"),
            Session(stage.owner) as session,
            session.begin(),
        ):
            mark_revision(session, revision_id, "v1.0", None, Act(None, at))
    assert ran == [("kept", revision_id, "draft"), ("computed", revision_id, "draft")]


def test_a_designation_registered_follows_the_reference_once_it_is_designated(
    api: ContractClient, stage: Scene
) -> None:
    # What EP-07 refreshes once a reference is designated — the budgeted amounts of the current
    # revision —, in the transaction of the designation, the revision designated already.
    followed: list[tuple[UUID, UUID, bool]] = []

    def follow(designation: ReferenceDesignated) -> None:
        designated = designation.session.scalar(
            select(Revision.is_reference).where(Revision.id == designation.revision_id)
        )
        followed.append((designation.project_id, designation.revision_id, bool(designated)))

    project_id = stage.project["project_id"]
    revision_id = UUID(open_revision(api, stage)["revision_id"])
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        give_a_line(session.connection(), give_a_task(session.connection(), revision_id))
        mark_revision(session, revision_id, "v1.0", None, Act(None, utc_now()))
    path = f"{PROJECTS}/{project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    with ExitStack() as registered:
        registered.callback(register_designation(follow))
        response = api.put(
            f"{path}/reference-revision",
            headers=stage.manager.headers,
            json={"revision_id": str(revision_id), "confirmed": True, "lock_version": counter},
        )
    assert response.status_code == 200, response.text
    assert followed == [(UUID(project_id), revision_id, True)]


def test_an_employment_registered_names_the_categories_a_line_employs(
    session: Session,
) -> None:
    # The categories each answer registered names, gathered; none while nothing is registered.
    first, second, third = uuid4(), uuid4(), uuid4()
    asked = [first, second, third]
    assert category_is_employed(session, asked) == frozenset()
    with ExitStack() as registered:
        registered.callback(register_employment(lambda _session, _ids: frozenset({first})))
        registered.callback(
            register_employment(lambda _session, ids: frozenset(ids) - {first, third})
        )
        assert category_is_employed(session, asked) == frozenset({first, second})


EIGHT = Decimal(8)
WEEK = WeeklyHours(EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, Decimal(0), Decimal(0))
ATELIER = CalendarContent("Atelier", WEEK)
RENAMED = CalendarContent("Atelier B", WEEK)
SIX_DAYS = WeeklyHours(EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, Decimal(0))
SEVEN_HOURS = Units(Decimal(7), Decimal(35), Decimal(20))


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


def test_a_recalculation_registered_runs_once_what_dates_the_plannings_is_written(
    database: Database,
) -> None:
    ran: list[str] = []
    act = Act(None, utc_now())
    with database.transaction() as session:
        install_duration_units(session, act)
        calendar = create_calendar(session, ATELIER, act)
    with ExitStack() as registered:
        registered.callback(register_recalculation(lambda _session, _at: ran.append("redated")))
        # The same constants sent again are written, and redate nothing; others redate.
        for units in (DEFAULT_UNITS, SEVEN_HOURS):
            with database.transaction() as session:
                set_duration_units(session, units, get_duration_units(session).lock_version, act)
        assert ran == ["redated"]
        # A calendar that is not the default redates nothing, whatever its hours.
        longer = CalendarContent("Atelier B", SIX_DAYS)
        with database.transaction() as session:
            changed = update_calendar(
                session, calendar.calendar_id, longer, calendar.lock_version, act
            )
        assert ran == ["redated"]
        with database.transaction() as session:
            designated = set_default_calendar(
                session, calendar.calendar_id, changed.lock_version, act
            )
        assert ran == ["redated"] * 2
        # The default renamed alone redates nothing; its hours changed redate.
        counter = designated.lock_version
        for content in (CalendarContent("Atelier C", SIX_DAYS), RENAMED):
            with database.transaction() as session:
                counter = update_calendar(
                    session, calendar.calendar_id, content, counter, act
                ).lock_version
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
    # Those of the planning and of the estimate, registered at the import of their interfaces,
    # serve another kind here.
    held = (dict(facets()), dict(formats()), dict(exporters()))

    def copy(copy: RevisionCopy) -> None:
        del copy

    hooks = replace(facets()["estimate_line"], copy=copy)
    with ExitStack() as registered:
        registered.callback(register_facet("remaining", hooks))
        registered.callback(register_format("remaining", MS_PROJECT_FORMAT))
        registered.callback(register_exporter("remaining", TASK_TREE_EXPORTER))
        assert (list(facets()), list(formats()), list(exporters())) == (
            ["estimate_line", "remaining"],
            ["ms_project_schedule", "estimate", "remaining"],
            ["ms_project_schedule", "task_tree_image", "estimate", "remaining"],
        )
        with pytest.raises(ValueError, match="registered already"):
            register_facet("estimate_line", hooks)
        with pytest.raises(ValueError, match="registered already"):
            register_facet("remaining", hooks)
        with pytest.raises(ValueError, match="has a format already"):
            register_format("remaining", MS_PROJECT_FORMAT)
        with pytest.raises(ValueError, match="has an exporter already"):
            register_exporter("remaining", MS_PROJECT_EXPORTER)
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
