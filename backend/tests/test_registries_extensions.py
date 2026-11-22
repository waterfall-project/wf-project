# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the other registries act (#2180; EP-07 to EP-09).

Details of the realization which reprise no Vérif: the guard and the recalculation of the reference,
the attachments of the work breakdown, the facets, the formats and the exporters, the coverage of
the risks, the entries undone, the fillers of the witness.
"""

import importlib
from contextlib import ExitStack
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from project_rows import insert_project
from sqlalchemy import select
from witness_support import PRJ_001

from waterfall.core.costs.interface import ACTUAL_COSTS_FORMAT
from waterfall.core.estimate.interface import (
    NO_COVERAGE,
    REMAINING_EXPORTER,
    REMAINING_FORMAT,
    Coverage,
    register_coverage,
    risk_coverage,
)
from waterfall.core.exchanges.interface import (
    exporters,
    formats,
    register_exporter,
    register_format,
)
from waterfall.core.history.interface import (
    Undoable,
    register_undoable,
    undoables,
)
from waterfall.core.planning.interface import (
    MS_PROJECT_EXPORTER,
    MS_PROJECT_FORMAT,
    facets,
    register_facet,
)
from waterfall.core.projects.interface import (
    Attachments,
    detach_item,
    hold_items,
    item_cited,
    register_attachments,
    share_items,
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
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.interface import RISK_KINDS
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.registry import Registry
from waterfall.witness.revisions import register_revision_filler

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import Restoring, Snapshot
    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.database import Database
    from waterfall.witness.description import Witness
    from waterfall.witness.filling import Filling


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
        registered.callback(
            register_recalculation(lambda _session, _at, _entered: ran.append("redated"))
        )
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


def test_the_attachments_registered_tell_share_hold_and_detach_an_element_of_the_work_breakdown(
    session: Session,
) -> None:
    detached: list[tuple[UUID, UUID]] = []
    held: list[tuple[UUID, tuple[UUID, ...]]] = []
    shared: list[UUID] = []
    project_id, item_id = uuid4(), uuid4()
    # A project without revision: the planning registered shares none, and refuses an unknown one.
    session.execute(insert_project(id=project_id))
    assert not item_cited(session, item_id)
    with ExitStack() as registered:
        registered.callback(
            register_attachments(
                Attachments(
                    lambda _session, item: item == item_id,
                    lambda _session, project, item: detached.append((project, item)),
                    lambda _session, project, items: held.append((project, tuple(items))),
                    lambda _session, project: shared.append(project),
                )
            )
        )
        assert (item_cited(session, item_id), item_cited(session, uuid4())) == (True, False)
        share_items(session, project_id)
        hold_items(session, project_id, [item_id])
        detach_item(session, project_id, item_id)
    assert shared == [project_id]
    assert held == [(project_id, (item_id,))]
    assert detached == [(project_id, item_id)]


def test_a_kind_has_one_facet_one_format_and_one_exporter_at_most() -> None:
    # Every kind of import and of export has its format and its exporter from the socle of EP-09
    # on, registered at the import of the interfaces of the planning, the estimate and the actual
    # costs: a second is refused. A facet of another kind is added, then withdrawn.
    held = (dict(facets()), dict(formats()), dict(exporters()))
    assert (held[1]["remaining"], held[1]["actual_costs"], held[2]["remaining"]) == (
        REMAINING_FORMAT,
        ACTUAL_COSTS_FORMAT,
        REMAINING_EXPORTER,
    )

    def copy(copy: RevisionCopy) -> None:
        del copy

    hooks = replace(facets()["estimate_line"], copy=copy)
    with ExitStack() as registered:
        registered.callback(register_facet("remaining", hooks))
        assert list(facets()) == ["estimate_line", "remaining"]
        with pytest.raises(ValueError, match="registered already"):
            register_facet("estimate_line", hooks)
        with pytest.raises(ValueError, match="registered already"):
            register_facet("remaining", hooks)
        for kind in ("ms_project_schedule", "estimate", "remaining", "actual_costs"):
            with pytest.raises(ValueError, match="has a format already"):
                register_format(kind, MS_PROJECT_FORMAT)
        for kind in ("ms_project_schedule", "task_tree_image", "estimate", "remaining"):
            with pytest.raises(ValueError, match="has an exporter already"):
                register_exporter(kind, MS_PROJECT_EXPORTER)
    assert (dict(facets()), dict(formats()), dict(exporters())) == held


def test_the_coverage_of_the_risks_has_the_answer_of_the_risks_alone() -> None:
    # What EP-08 answers for a revision of a project, once, at the import of its interface: a second
    # answer is refused, the risks being one module's (the registry holds theirs, in
    # ``REGISTERED_BY_EP08``).
    def cover(_session: Session, _project: UUID, _revision: UUID) -> Coverage:
        return NO_COVERAGE

    with pytest.raises(ValueError, match="has its answer already"):
        register_coverage(cover)


def test_the_coverage_of_the_risks_is_zero_until_something_answers_it_once(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The registry the estimate declares, without the answer of the risks, which this test sets
    # aside for its duration: zero before an answer and after its withdrawal, the arguments passed
    # to the answer, a second answer refused.
    empty: Registry[Callable[[Session, UUID, UUID], Coverage]] = Registry()
    # ``interface.remaining_indicators`` is the function the package re-exports: the module by name.
    module = importlib.import_module("waterfall.core.estimate.interface.remaining_indicators")
    monkeypatch.setattr(module, "_COVERAGE", empty)
    project_id, revision_id = uuid4(), uuid4()
    asked: list[tuple[UUID, UUID]] = []
    answered = Coverage(
        Decimal("1000.00"),
        Decimal("400.00"),
        Decimal("250.00"),
        Decimal("260.00"),
        Decimal("350.00"),
    )

    def cover(_session: Session, project: UUID, revision: UUID) -> Coverage:
        asked.append((project, revision))
        return answered

    assert risk_coverage(session, project_id, revision_id) == NO_COVERAGE
    with ExitStack() as registered:
        registered.callback(register_coverage(cover))
        assert risk_coverage(session, project_id, revision_id) == answered
        with pytest.raises(ValueError, match="has its answer already"):
            register_coverage(cover)
    assert risk_coverage(session, project_id, revision_id) == NO_COVERAGE
    assert asked == [(project_id, revision_id)]


def test_a_kind_of_entry_is_undone_by_one_module_at_most() -> None:
    # A tool of the registries, which covers no requirement: the risks undo their four kinds (EP-08,
    # US-2590/L2), registered at the import of their interface; another kind is the planning's until
    # a module registers it; a second module for the same kind refused; none once withdrawn.
    def lock(_session: Session, _project: UUID, _states: Snapshot) -> None:
        return None

    def read(_session: Session, _project: UUID, _ids: tuple[UUID, ...]) -> Snapshot:
        return ()

    def restore(_session: Session, _project: UUID, _restoring: Restoring, _act: Act) -> None:
        return None

    risks = undoables()
    assert set(risks) == set(RISK_KINDS)
    undoable = Undoable(("planning.write",), lock, read, restore)
    with ExitStack() as registered:
        registered.callback(register_undoable("node_move", undoable))
        assert undoables() == {**risks, "node_move": undoable}
        with pytest.raises(ValueError, match="undone by a module already"):
            register_undoable("risk_create", undoable)
    assert undoables() == risks


@pytest.fixture
def fillers() -> Iterator[list[tuple[UUID, UUID | None]]]:
    """Register a filler of the structures of the witness that notes each structure it fills."""
    filled: list[tuple[UUID, UUID | None]] = []

    def note(_session: Session, _witness: Witness, filling: Filling) -> None:
        filled.append((filling.revision.revision_id.root, filling.structure_id))

    withdraw = register_revision_filler(note)
    yield filled
    withdraw()


def test_the_witness_fills_each_structure_it_opens_before_the_next_event(
    fillers: list[tuple[UUID, UUID | None]], witness_loaded: Database
) -> None:
    # The offer's main structure, the amendment 1 of the 101, the 102's, its amendment 2 (EP-08).
    with witness_loaded.transaction() as session:
        ids = select(Revision.id).where(Revision.project_id == PRJ_001)
        offer, reference, current = session.scalars(ids.order_by(Revision.created_at, Revision.id))
    first, second = (UUID(f"01926f3a-7c00-7000-8000-000000000{n}") for n in (212, 203))
    assert fillers == [(offer, None), (reference, first), (current, None), (current, second)]
