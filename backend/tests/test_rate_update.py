# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rates of a revision, their proposal and their update (US-1500/L1).

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file; US-1500 writes
its tests here ("Les tests du back"). A project whose first revision, of the year, employs two
categories of labour — the engineering, rated this year and the next, and the commissioning, rated
this year alone — is marked; the next revision is opened by ``createRevision``, the clock of the
service set to the next year, or the same year. It keeps the rates its source was priced at,
projected by the inflation of the project, or replaced by those of its year when its creation
accepts the update (``revision_rate``); ``getRateUpdateProposal`` presents them, and
``applyRateUpdate`` accepts them later (#1756). Every answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Costing, Lines, add_role, costing, rate_row
from nodes_support import Tree, faults, mark, opened, refusal
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from sqlalchemy import insert, select, update

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    create_cost_category,
    set_hourly_rate,
)
from waterfall.core.cost_settings.tables import CostType
from waterfall.core.estimate.keeping import reprice_revision
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.interface import lines_of_revision, structures_of
from waterfall.core.planning.tables import Node
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import revision_structures
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

# The year after the one the first revision is priced at, and an instant of it.
NEXT = YEAR + 1
LATER = datetime(NEXT, 1, 12, 10, tzinfo=UTC)
STATE_FORBIDS = "STATE_FORBIDS_OPERATION"


@dataclass(frozen=True)
class Offer:
    """A first revision marked, its lines, and the categories they employ."""

    revision: dict[str, Any]
    engineering: UUID
    commissioning: UUID
    material: UUID


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated 65.00 this year."""
    return costing(stage.database)


def commissioning(database: Database) -> tuple[UUID, UUID]:
    """Add a category of labour, rated 60.00 this year alone, and a role of it; give them."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = session.scalars(select(CostType.id).where(CostType.code == "MO")).one()
        draft = CostCategoryDraft("MO-002", "Mise en service", "641002", nature)
        category = create_cost_category(session, draft, act).cost_category_id
        set_hourly_rate(session, (category, YEAR), Decimal("60.00"), None, act)
    return category, add_role(database, "MES", (8, 8, 8, 8, 8, 0, 0), category)


def rate_next_year(database: Database, category: UUID, amount: str) -> None:
    """Rate a category for the next year in the reference."""
    with database.transaction() as session:
        set_hourly_rate(session, (category, NEXT), Decimal(amount), None, Act(None, utc_now()))


@pytest.fixture
def offer(api: ContractClient, stage: Scene, costs: Costing) -> Offer:
    """Open a first revision, give it a line of each category of labour and one of material, mark.

    The project inflates at 3 %; the engineering is rated 70.00 for the next year.
    """
    category, role = commissioning(stage.database)
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    lines = Lines(tree)
    wiring = tree.made("Câblage")
    lines.made(wiring, quantity="1", resource_role_id=str(costs.role), hours="10")
    lines.made(wiring, quantity="1", cost_category_id=str(costs.material), unit_disbursement="350")
    starting = tree.made("Mise en service")
    lines.made(starting, quantity="1", resource_role_id=str(role), hours="10")
    mark(stage, revision)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    rate_next_year(stage.database, costs.labour, "70.00")
    return Offer(revision, costs.labour, category, costs.material)


@pytest.fixture
def next_year(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Set the clock of the service that opens a revision and updates its rates to the next year."""
    monkeypatch.setattr("waterfall.api.revisions.utc_now", lambda: LATER)
    monkeypatch.setattr("waterfall.api.rate_update.utc_now", lambda: LATER)
    return LATER


def base(stage: Scene) -> str:
    """Give the path of the revisions of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/revisions"


def open_next(api: ContractClient, stage: Scene, **body: Any) -> dict[str, Any]:
    """Open the next revision, as the manager does; give it."""
    answer = api.post(base(stage), headers=stage.manager.headers, json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()


def proposal(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> dict[str, Any]:
    """Read the proposal of the rates of a revision."""
    path = f"{base(stage)}/{revision['revision_id']}/rate-update"
    answer = api.get(path, headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def apply(
    api: ContractClient, stage: Scene, revision: dict[str, Any], *categories: UUID, **body: Any
) -> Any:
    """Send the update of the rates of the categories named, at the counter read; give the reply."""
    sent = {
        "cost_category_ids": [str(each) for each in categories],
        "lock_version": revision["lock_version"],
        **body,
    }
    path = f"{base(stage)}/{revision['revision_id']}/rate-update"
    return api.post(path, headers=stage.manager.headers, json=sent)


def read(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> dict[str, Any]:
    """Read a revision again."""
    answer = api.get(f"{base(stage)}/{revision['revision_id']}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def missing(revision: dict[str, Any], command: str = "apply_rate_update") -> list[str]:
    """Give the conditions a command of a revision lacks."""
    return next(
        each["missing_conditions"]
        for each in revision["available_commands"]
        if each["command"] == command
    )


def kept(stage: Scene, revision: dict[str, Any]) -> dict[UUID, tuple[Decimal, str]]:
    """Read the rates a revision keeps, by category: their amount and their origin."""
    with stage.database.transaction() as session:
        rows = session.execute(
            select(RevisionRate.cost_category_id, RevisionRate.amount, RevisionRate.origin).where(
                RevisionRate.revision_id == UUID(revision["revision_id"])
            )
        ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def amounts(stage: Scene, revision: dict[str, Any]) -> dict[UUID, tuple[Decimal, Decimal]]:
    """Read the base and re-estimated amounts of the lines of a revision, by category."""
    with stage.database.transaction() as session:
        rows = session.execute(
            select(
                EstimateLine.cost_category_id,
                EstimateLine.base_amount,
                EstimateLine.reestimated_amount,
            )
            .join(
                Node,
                (Node.project_id == EstimateLine.project_id) & (Node.id == EstimateLine.node_id),
            )
            .where(Node.revision_id == UUID(revision["revision_id"]))
        ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def counter(stage: Scene, revision: dict[str, Any]) -> int:
    """Read the counter of a revision in the base."""
    with stage.database.transaction() as session:
        found = session.scalar(
            select(Revision.lock_version).where(Revision.id == UUID(revision["revision_id"]))
        )
    assert found is not None
    return found


def structure_counters(session: Session, revision_id: UUID) -> list[tuple[int, datetime | None]]:
    """Read the counter and the instant of the dates of the structures of a revision."""
    rows = session.execute(
        select(CostStructure.lock_version, CostStructure.scheduled_at)
        .where(CostStructure.revision_id == revision_id)
        .order_by(CostStructure.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


# --- The rates kept at the creation -----------------------------------------------------------


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_revision_created_the_next_year_bears_it_and_presents_the_rates_category_by_category(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # « Une révision créée en 2027 porte l'année de référence 2027. À sa création, lorsque la
    # précédente portait 2026, l'écart est présenté catégorie par catégorie et la mise à jour peut
    # être refusée. » : the clock set to the next year; each category of labour the lines employ,
    # its rate projected beside that of the year (``reference_rate``), or alone without one
    # (``inflated_previous``); the material, no labour, is not presented.
    revision = open_next(api, stage)
    assert revision["reference_year"] == next_year.year == NEXT
    assert proposal(api, stage, revision) == {
        "target_year": NEXT,
        "categories": [
            {
                "cost_category_id": str(offer.engineering),
                "label": "Ingénierie",
                "previous_amount": "66.95",
                "proposed_amount": "70.00",
                "source": "reference_rate",
            },
            {
                "cost_category_id": str(offer.commissioning),
                "label": "Mise en service",
                "previous_amount": "61.80",
                "proposed_amount": "61.80",
                "source": "inflated_previous",
            },
        ],
    }
    assert missing(revision) == []


@pytest.mark.requirement("WF-REV-0060-A")
@pytest.mark.requirement("WF-REV-0010-A")
def test_a_category_refused_or_without_a_rate_is_priced_at_the_previous_rate_projected(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # « Une catégorie refusée ou sans taux pour 2027 est chiffrée au taux de 2026 corrigé d'une
    # année d'inflation. » and, of WF-REV-0010, « sinon, elle porte [...] pour chaque catégorie dont
    # la mise à jour de WF-REV-0060 n'a pas été acceptée, le taux précédent projeté par le taux
    # d'inflation du projet jusqu'à la nouvelle année de référence » : the update refused at the
    # creation, both rates kept projected — 65.00 and 60.00 at 3 % —, and the lines priced at them.
    del next_year
    revision = open_next(api, stage, apply_rate_update=False)
    assert kept(stage, revision) == {
        offer.engineering: (Decimal("66.95"), "projected"),
        offer.commissioning: (Decimal("61.80"), "projected"),
    }
    priced = amounts(stage, revision)
    assert priced[offer.engineering][0] == Decimal("669.50")
    assert priced[offer.commissioning][0] == Decimal("618.00")
    assert priced[offer.material][0] == Decimal("350.00")


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_revision_created_with_the_update_is_priced_at_the_rates_of_its_year(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # The update accepted at the creation (``apply_rate_update``): the engineering, rated for the
    # year, at its rate, kept as of the reference; the commissioning, without one, keeps its rate
    # projected, and its update remains offered (WF-REV-0060, #1764).
    del next_year
    revision = open_next(api, stage, apply_rate_update=True)
    assert kept(stage, revision) == {
        offer.engineering: (Decimal("70.00"), "reference"),
        offer.commissioning: (Decimal("61.80"), "projected"),
    }
    assert amounts(stage, revision)[offer.engineering][0] == Decimal("700.00")
    presented = proposal(api, stage, revision)["categories"]
    assert [each["cost_category_id"] for each in presented] == [str(offer.commissioning)]


@pytest.mark.requirement("WF-REV-0010-A")
def test_a_revision_created_the_same_year_keeps_the_rates_of_its_source(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # « à année de référence égale, elle porte aussi les mêmes valeurs de référentiel » : the rates
    # its source was priced at, copied as of the reference, the lines at the same amounts; nothing
    # proposed, and the command lacks ``rate_update_available``.
    revision = open_next(api, stage)
    assert revision["reference_year"] == YEAR
    assert kept(stage, revision) == {
        offer.engineering: (Decimal("65.00"), "reference"),
        offer.commissioning: (Decimal("60.00"), "reference"),
    }
    assert amounts(stage, revision) == amounts(stage, offer.revision)
    assert proposal(api, stage, revision) == {"target_year": YEAR, "categories": []}
    assert missing(revision) == ["rate_update_available"]


@pytest.mark.requirement("WF-REV-0010-A")
def test_a_revision_abandoned_takes_its_rates_with_it_and_another_is_created(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # « Après abandon d'une révision en cours, le projet présente les données de la dernière
    # révision marquée, et une nouvelle révision peut être créée. » : the rates it kept go with it.
    del next_year, offer
    revision = open_next(api, stage)
    path = f"{base(stage)}/{revision['revision_id']}?lock_version={revision['lock_version']}"
    assert api.delete(path, headers=stage.manager.headers).status_code == 204
    assert kept(stage, revision) == {}
    assert open_next(api, stage)["reference_year"] == NEXT


# --- The update accepted later -------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_update_refused_at_the_creation_is_accepted_later_and_prices_the_revision_again(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # « Une mise à jour refusée à la création d'une révision est acceptée ensuite depuis la
    # révision en cours, qui est alors rechiffrée au taux de 2027 pour cette catégorie. » : the
    # revision answered one version higher, stamped by the update; the engineering at 70.00, its
    # line priced again, the commissioning left projected and still presented (#1756).
    revision = open_next(api, stage)
    answer = apply(api, stage, revision, offer.engineering)
    assert answer.status_code == 200, answer.text
    updated = answer.json()
    assert updated["lock_version"] == revision["lock_version"] + 1
    assert updated["audit"]["updated_at"] == next_year.isoformat().replace("+00:00", "Z")
    assert kept(stage, revision)[offer.engineering] == (Decimal("70.00"), "reference")
    priced = amounts(stage, revision)
    assert priced[offer.engineering] == (Decimal("700.00"), Decimal("700.00"))
    assert priced[offer.commissioning][0] == Decimal("618.00")
    presented = proposal(api, stage, revision)["categories"]
    assert [each["cost_category_id"] for each in presented] == [str(offer.commissioning)]
    assert missing(updated) == []
    # Accepted without a rate of the year, the commissioning keeps its rate projected, and is
    # proposed still (#2619, option 2): the rate of the year, once entered in the reference, is
    # proposed and accepted in its turn, as of the reference; nothing remains to propose then.
    again = apply(api, stage, updated, offer.commissioning)
    assert again.status_code == 200, again.text
    assert kept(stage, revision)[offer.commissioning] == (Decimal("61.80"), "projected")
    assert amounts(stage, revision)[offer.commissioning][0] == Decimal("618.00")
    [still] = proposal(api, stage, revision)["categories"]
    assert (still["cost_category_id"], still["source"]) == (
        str(offer.commissioning),
        "inflated_previous",
    )
    assert missing(again.json()) == []
    rate_next_year(stage.database, offer.commissioning, "63.00")
    [rated] = proposal(api, stage, revision)["categories"]
    assert (rated["proposed_amount"], rated["source"]) == ("63.00", "reference_rate")
    last = apply(api, stage, again.json(), offer.commissioning)
    assert last.status_code == 200, last.text
    assert kept(stage, revision)[offer.commissioning] == (Decimal("63.00"), "reference")
    assert amounts(stage, revision)[offer.commissioning][0] == Decimal("630.00")
    assert proposal(api, stage, revision)["categories"] == []
    assert missing(last.json()) == ["rate_update_available"]


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_update_at_a_stale_counter_or_of_a_category_not_proposed_writes_nothing(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # #1756: the counter of the revision read is asked, stale 412; a category the proposal does not
    # present — the material, of disbursement — is refused by its rank, an empty list on the list,
    # 422; nothing is written, and the revision keeps its version.
    del next_year
    revision = open_next(api, stage)
    before = (kept(stage, revision), amounts(stage, revision), counter(stage, revision))
    stale = apply(api, stage, {**revision, "lock_version": 99}, offer.engineering)
    assert refusal(stale) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": revision["lock_version"]},
    )
    assert faults(apply(api, stage, revision, offer.engineering, offer.material)) == [
        ("/cost_category_ids/1", "UNKNOWN_COST_CATEGORY", {})
    ]
    assert faults(apply(api, stage, revision)) == [("/cost_category_ids", "VALUE_REQUIRED", {})]
    assert faults(apply(api, stage, revision, offer.engineering, offer.engineering)) == [
        ("/cost_category_ids/1", "VALIDATION_FAILED", {})
    ]
    without = api.post(
        f"{base(stage)}/{revision['revision_id']}/rate-update",
        headers=stage.manager.headers,
        json={"cost_category_ids": [str(offer.engineering)]},
    )
    assert faults(without) == [("/lock_version", "VALUE_REQUIRED", {})]
    assert (kept(stage, revision), amounts(stage, revision), counter(stage, revision)) == before


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_update_is_refused_on_a_marked_revision_or_without_a_category_proposed(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # The conditions of ``apply_rate_update``, in the order of the contract (#1351): a marked
    # revision keeps its rates (``revision_draft``), a proposal without a category refuses
    # (``rate_update_available``); nothing is written.
    marked = read(api, stage, offer.revision)
    assert missing(marked) == ["revision_draft"]
    assert refusal(apply(api, stage, marked, offer.engineering)) == (
        409,
        STATE_FORBIDS,
        {"missing_condition": "revision_draft"},
    )
    assert proposal(api, stage, marked) == {"target_year": YEAR, "categories": []}
    same_year = open_next(api, stage)
    assert refusal(apply(api, stage, same_year, offer.engineering)) == (
        409,
        STATE_FORBIDS,
        {"missing_condition": "rate_update_available"},
    )


@pytest.mark.requirement("WF-REV-0060-A")
def test_an_update_is_refused_while_the_revision_is_being_marked(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    del next_year
    revision = open_next(api, stage)
    asked = api.post(
        f"{base(stage)}/{revision['revision_id']}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v2.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    during = read(api, stage, revision)
    assert missing(during) == ["no_background_task_running"]
    assert refusal(apply(api, stage, during, offer.engineering)) == (
        409,
        STATE_FORBIDS,
        {"missing_condition": "no_background_task_running"},
    )
    assert kept(stage, revision)[offer.engineering] == (Decimal("66.95"), "projected")


@pytest.mark.requirement("WF-REV-0060-A")
def test_a_rate_projected_of_a_category_no_line_employs_offers_no_update(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # The command and the proposal ask the same question (#1351): a rate projected of a category no
    # line of the revision employs presents nothing and offers nothing (#2621).
    revision = open_next(api, stage)
    with stage.owner.begin() as connection:
        connection.execute(
            insert(RevisionRate).values(
                **rate_row(
                    UUID(stage.project["project_id"]),
                    UUID(revision["revision_id"]),
                    uuid4(),
                    origin="projected",
                )
            )
        )
    assert proposal(api, stage, revision)["categories"] == []
    assert missing(read(api, stage, revision)) == ["rate_update_available"]
    del offer


@pytest.mark.requirement("WF-REV-0060-A")
def test_the_structures_replayed_are_those_the_planning_names_for_the_lines_priced_again(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # A structure replayed has its counter and its instant moved: the update replays those the
    # planning names for the lines of a category accepted (``structures_of``). A revision holds
    # one structure for now: the choice between two of one revision waits for the differentials of
    # EP-08 (#2621), so the planning is asked here on the nodes of two revisions, each naming its
    # own, then the structure of the lines priced again is replayed.
    first, second = (UUID(each["revision_id"]) for each in (offer.revision, open_next(api, stage)))
    with stage.database.transaction() as session:
        project_id = UUID(stage.project["project_id"])
        nodes = {
            revision: list(lines_of_revision(session, project_id, revision).values())[:1]
            for revision in (first, second)
        }
        assert structures_of(session, project_id, []) == ()
        for revision, held in nodes.items():
            assert structures_of(session, project_id, held) == revision_structures(
                session, project_id, revision
            )
        before = structure_counters(session, second)
        reprice_revision(session, (project_id, second), next_year, {offer.engineering})
        assert structure_counters(session, second) != before


# --- Two updates at once -------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_two_updates_of_the_rates_at_once_leave_one_refused_by_its_counter(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # Two updates sent at the same counter: one wins, the other is refused (412) by the counter the
    # first advanced; the revision advances once, its line priced once at the rate of the year.
    del next_year
    revision = open_next(api, stage)

    def send(category: UUID) -> Any:
        return apply(api, stage, revision, category)

    # Both the engineering: whichever wins writes the rate of the year, the commissioning, without
    # one, staying projected (#2619).
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(send, [offer.engineering, offer.engineering]))
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    assert counter(stage, revision) == revision["lock_version"] + 1
    origins = sorted(origin for _, origin in kept(stage, revision).values())
    assert origins == ["projected", "reference"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_update_of_the_rates_waits_for_the_lock_of_its_revision(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # Another transaction holds the revision ``FOR UPDATE``, as a marking does: the update starts,
    # waits, and answers once the lock is released, at the counter it read.
    del next_year
    revision = open_next(api, stage)
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(
            select(Revision.id)
            .where(Revision.id == UUID(revision["revision_id"]))
            .with_for_update()
        )
        waiting = pool.submit(apply, api, stage, revision, offer.engineering)
        with pytest.raises(FutureTimeout):
            waiting.result(timeout=1.5)
    answer = waiting.result(timeout=30)
    assert answer.status_code == 200, answer.text
    assert amounts(stage, revision)[offer.engineering][0] == Decimal("700.00")


# --- A revision unknown, or of another project --------------------------------------------------


@pytest.mark.requirement("WF-REV-0060-A")
def test_the_proposal_and_the_update_of_an_unknown_revision_or_of_another_project_are_not_found(
    api: ContractClient, stage: Scene, offer: Offer, next_year: datetime
) -> None:
    # The revision is looked for in the project of the path (404, never a revision of another):
    # an identifier no revision bears, and a revision of the project of the stage named under
    # another project of the same manager; the reading and the update alike, nothing written.
    del next_year
    revision = open_next(api, stage)
    other = create(api, stage.manager, label="Autre projet")["project_id"]
    before = (kept(stage, revision), counter(stage, revision))
    paths = [
        f"{base(stage)}/{uuid4()}/rate-update",
        f"{PROJECTS}/{other}/revisions/{revision['revision_id']}/rate-update",
    ]
    body = {"cost_category_ids": [str(offer.engineering)], "lock_version": revision["lock_version"]}
    for path in paths:
        read_it = api.get(path, headers=stage.manager.headers)
        assert (read_it.status_code, read_it.json()["code"]) == (404, "NOT_FOUND")
        sent = api.post(path, headers=stage.manager.headers, json=body)
        assert (sent.status_code, sent.json()["code"]) == (404, "NOT_FOUND")
    assert (kept(stage, revision), counter(stage, revision)) == before
