# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the portfolio share (EP-11, "Les tests et les contrôles"): four projects.

The fabrics every lot of the back starts from, so that none builds its own (US-2670/L1): on the
platform of a scene, a project In progress, an offer at 40 %, a project completed in the period and
an offer lost, each priced and marked. Each is written through the interfaces of the modules, at the
instants of a chronology of 2026 that their ``Act`` imposes, as the loader of the witness writes its
own (WF-CYC-0130): its creation, its revisions opened and marked, its probability, its reference
designated, its code, its exit. Its task and its two lines — eight hours of the role of the scene
and a unit of material — are written through the service, which dates nothing the portfolio reads.
A view read on 3 June 2026, the date of the witness, retains in its default period the completion
of 15 April and the loss of 15 March (WF-CYC-0130, the example of the lost offer); the project of
the scene itself stays Created, which no view counts. A helper several test modules of the portfolio
read lives here, never in one of them.
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from estimate_support import YEAR, Costing, Lines, costing
from nodes_support import Tree
from projects_support import MANAGING
from sqlalchemy import select

from waterfall.core.cost_settings.interface import set_hourly_rate
from waterfall.core.projects.interface import (
    ExitRequest,
    ProjectChange,
    ProjectDraft,
    Viewer,
    create_project,
    exit_project,
    stored_lock_version,
    update_project,
)
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.interface import (
    ReferenceToDesignate,
    create_revision,
    current_revision,
    designate_reference,
    mark_revision,
)
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from uuid import UUID

    from projects_support import Scene
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.projects.interface import ExitState, ProjectState

# The year of the chronology, whose rate the labour of the lines asks for (``reference_year``).
CHRONOLOGY_YEAR = 2026
# The date a view reads the fabrics at, that of the witness: a past date once the clock passes it.
READ_ON = date(2026, 6, 3)
# The probability of winning of the offer, and of the offer lost.
OFFER_PROBABILITY = Decimal("0.40")
LOST_PROBABILITY = Decimal("0.25")
# The lines of the task of each project: the hours of the role of the scene, the unit of material.
HOURS = "8"
MATERIAL = "1000.00"
# The names of the markings: the offer, then the review of a project In progress.
OFFER, REVIEW = "Offre v1.0", "Revue de mars"
# The reason of the loss.
LOST_REASON = "Offre d'un concurrent moins chère"


def at(month: int, day: int) -> datetime:
    """Give the instant of a day of the chronology, at nine in the morning in universal time."""
    return datetime(CHRONOLOGY_YEAR, month, day, 9, 0, tzinfo=UTC)


# The chronology: a project opened, priced and marked as an offer, then designated and coded In
# progress, reviewed and marked again; an offer opened later, marked; their exits.
OPENED = at(1, 5)
OFFER_MARKED = at(1, 12)
DESIGNATED = at(1, 19)
REVIEW_OPENED = at(2, 2)
REVIEW_MARKED = at(3, 2)
OFFERS_OPENED = at(2, 2)
OFFERS_MARKED = at(2, 16)
LOST_ON = at(3, 15)
COMPLETED_ON = at(4, 15)


@dataclass(frozen=True)
class Fabricated:
    """A project of the fabrics: its identifier, its label, its state, its marked revisions.

    ``marked`` names each revision by its version name, with the instant of its marking.
    """

    project_id: UUID
    label: str
    state: ProjectState
    marked: dict[str, tuple[UUID, datetime]]


@dataclass(frozen=True)
class Portfolio:
    """The four projects of the fabrics, on the platform of a scene, its categories rated."""

    stage: Scene
    costs: Costing
    in_progress: Fabricated
    offer: Fabricated
    completed: Fabricated
    lost: Fabricated

    @property
    def projects(self) -> tuple[Fabricated, ...]:
        """Give the four, in the order of their fabrics."""
        return (self.in_progress, self.offer, self.completed, self.lost)


class _Writer:
    """Writes a project through the interfaces as its manager, at the instants it is given."""

    def __init__(self, api: ContractClient, stage: Scene, costs: Costing) -> None:
        self.api = api
        self.stage = stage
        self.costs = costs
        self.viewer = Viewer(stage.manager.user_id, MANAGING)

    def act(self, instant: datetime) -> Act:
        return Act(self.stage.manager.user_id, instant)

    def created(self, label: str, instant: datetime) -> UUID:
        """Create a project, open its first revision and price it there; give the project."""
        with self.stage.database.transaction() as session:
            project_id = create_project(
                session, ProjectDraft(label), self.act(instant), self.viewer
            ).project_id
            revision = create_revision(session, project_id, self.act(instant), self.viewer)
        self.priced(project_id, revision.revision_id)
        return project_id

    def priced(self, project_id: UUID, revision_id: UUID) -> None:
        """Write a task and its two lines in the main structure of a revision, by the service."""
        stage = replace(self.stage, project={"project_id": str(project_id)})
        tree = Tree(self.api, stage, {"revision_id": str(revision_id)})
        lines = Lines(tree)
        task = tree.made("Études")
        lines.made(task, quantity="1", resource_role_id=str(self.costs.role), hours=HOURS)
        lines.made(
            task,
            label="Matériel",
            quantity="1",
            cost_category_id=str(self.costs.material),
            unit_disbursement=MATERIAL,
        )

    def changed(self, project_id: UUID, instant: datetime, **values: object) -> None:
        """Change attributes of a project at its counter."""
        with self.stage.database.transaction() as session:
            change = ProjectChange(values, stored_lock_version(session, project_id))
            update_project(session, project_id, change, self.act(instant), self.viewer)

    def marked(self, project_id: UUID, name: str, instant: datetime) -> tuple[UUID, datetime]:
        """Mark the current revision of a project by the transaction of the worker; give it."""
        with (
            logging_context(correlation_id="marking"),
            self.stage.database.transaction() as session,
        ):
            revision_id = current_of(session, project_id)
            mark_revision(session, revision_id, name, None, self.act(instant))
        return revision_id, instant

    def opened(self, project_id: UUID, instant: datetime) -> None:
        """Open the current revision of a project, a copy of its last marked one."""
        with self.stage.database.transaction() as session:
            create_revision(session, project_id, self.act(instant), self.viewer)

    def designated(self, project_id: UUID, revision_id: UUID, instant: datetime) -> None:
        """Designate a marked revision the reference, at its instant."""
        with self.stage.database.transaction() as session:
            designated = ReferenceToDesignate(
                revision_id, stored_lock_version(session, project_id), at=instant
            )
            designate_reference(session, project_id, designated, self.act(instant), self.viewer)

    def exited(
        self, project_id: UUID, to_state: ExitState, reason: str | None, instant: datetime
    ) -> None:
        """Take a project without a current revision out of its cycle."""
        with self.stage.database.transaction() as session:
            request = ExitRequest(to_state, reason, stored_lock_version(session, project_id))
            exit_project(session, project_id, request, self.act(instant), self.viewer)

    def under_way(self, label: str, code: str) -> tuple[UUID, dict[str, tuple[UUID, datetime]]]:
        """Write a project In progress: its offer marked and designated, its review marked."""
        project_id = self.created(label, OPENED)
        offer = self.marked(project_id, OFFER, OFFER_MARKED)
        self.designated(project_id, offer[0], DESIGNATED)
        self.changed(project_id, DESIGNATED, code=code)
        self.opened(project_id, REVIEW_OPENED)
        review = self.marked(project_id, REVIEW, REVIEW_MARKED)
        return project_id, {OFFER: offer, REVIEW: review}

    def offered(
        self, label: str, probability: Decimal
    ) -> tuple[UUID, dict[str, tuple[UUID, datetime]]]:
        """Write an offer at a probability of winning, marked."""
        project_id = self.created(label, OFFERS_OPENED)
        self.changed(project_id, OFFERS_OPENED, win_probability=probability)
        return project_id, {OFFER: self.marked(project_id, OFFER, OFFERS_MARKED)}


def current_of(session: Session, project_id: UUID) -> UUID:
    """Read the current revision of a project, which its marking takes."""
    found = current_revision(session, project_id)
    assert found is not None
    return found


def rated(stage: Scene, costs: Costing) -> None:
    """Rate the labour of the scene for the year of the chronology, when it is not the current."""
    if YEAR == CHRONOLOGY_YEAR:
        return
    with stage.database.transaction() as session:
        labour = session.scalar(
            select(ResourceRole.cost_category_id).where(ResourceRole.id == costs.role)
        )
        assert labour is not None
        rate = (labour, CHRONOLOGY_YEAR)
        set_hourly_rate(session, rate, Decimal("65.00"), None, Act(None, OPENED))


def another_in_progress(api: ContractClient, fabrics: Portfolio, label: str, code: str) -> UUID:
    """Write one more project In progress on the platform of the fabrics, as they are; give it."""
    writer = _Writer(api, fabrics.stage, fabrics.costs)
    with logging_context(correlation_id="portfolio-another"):
        return writer.under_way(label, code)[0]


def portfolio(api: ContractClient, stage: Scene) -> Portfolio:
    """Write the four projects of the fabrics on the platform of a scene, as its manager.

    Under a correlation of their own, as the journal asks of every action it inscribes.
    """
    costs = costing(stage.database)
    rated(stage, costs)
    writer = _Writer(api, stage, costs)
    with logging_context(correlation_id="portfolio-fabrics"):
        running, running_marked = writer.under_way("Rénovation de la ligne 3", "PRJ-2671")
        offer, offer_marked = writer.offered("Extension du dépôt", OFFER_PROBABILITY)
        completed, completed_marked = writer.under_way("Poste de livraison", "PRJ-2672")
        writer.exited(completed, "completed", None, COMPLETED_ON)
        lost, lost_marked = writer.offered("Passerelle du quai", LOST_PROBABILITY)
        writer.exited(lost, "lost", LOST_REASON, LOST_ON)
    return Portfolio(
        stage,
        costs,
        Fabricated(running, "Rénovation de la ligne 3", "in_progress", running_marked),
        Fabricated(offer, "Extension du dépôt", "pricing", offer_marked),
        Fabricated(completed, "Poste de livraison", "completed", completed_marked),
        Fabricated(lost, "Passerelle du quai", "lost", lost_marked),
    )
