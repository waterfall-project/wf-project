# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a revision keeps of the reference at its marking, and its budgeted amounts (US-1500/L2).

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file; US-1500 writes
its tests here ("Les tests du back"). A project's first revision employs two categories of labour —
the engineering of the role ``ING``, on the default calendar, rated 65.00, and the commissioning of
the role ``MES``, on a calendar of its own, rated 60.00 — and a category of material; its marking
keeps the images of what its lines employ, the rates it was priced at, and the rate of inflation and
the probability of winning of its project (``register_marking``). What the reference or the project
becomes then changes nothing of it: ``getRevision`` serves its ``snapshot``, ``listNodes`` its lines
on its images. A current revision follows them: a new rate of inflation, a rate of the reference
written, a reference designated price it again; a change of a calendar or of a role that would leave
one of its tasks without an hour is refused. Every answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Bearer, Costing, LineReference, Lines, add_role, costing
from estimate_support import insert_line as insert_line_row
from nodes_support import Tree, mark, opened, refusal
from projects_support import PROJECTS, Scene, person
from projects_support import scene as make_scene
from sqlalchemy import select, update

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    create_cost_category,
    list_hourly_rates,
    set_cost_category_activation,
    set_hourly_rate,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface import set_role_activation
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REFERENCE = "/api/v1/reference"
# The hours of a role that works the weekend alone, and of one that works four hours a day.
WEEKEND = (0, 0, 0, 0, 0, 8, 8)
HALF_DAYS = (4, 4, 4, 4, 4, 0, 0)
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class Offer:
    """A first revision, its tree, its lines and what they employ.

    ``engineering`` the line of the role ``ING``, ``starting`` the one of ``MES``, ``wiring`` the
    task that bears the first.
    """

    revision: dict[str, Any]
    tree: Tree
    lines: Lines
    wiring: dict[str, Any]
    engineering: dict[str, Any]
    starting: dict[str, Any]
    commissioning: UUID
    role: UUID


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated 65.00 this year."""
    return costing(stage.database)


def commissioning(database: Database) -> tuple[UUID, UUID]:
    """Add a category of labour rated 60.00 this year, and a role ``MES`` of it; give them."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = session.scalars(select(CostType.id).where(CostType.code == "MO")).one()
        draft = CostCategoryDraft("MO-002", "Mise en service", "641002", nature)
        category = create_cost_category(session, draft, act).cost_category_id
        set_hourly_rate(session, (category, YEAR), Decimal("60.00"), None, act)
    return category, add_role(database, "MES", (8, 8, 8, 8, 8, 0, 0), category)


@pytest.fixture
def offer(api: ContractClient, stage: Scene, costs: Costing) -> Offer:
    """Open a first revision: a line of each role and one of material; it is not marked yet."""
    category, role = commissioning(stage.database)
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    lines = Lines(tree)
    wiring = tree.made("Câblage")
    engineering = node_of(
        lines.made(wiring, quantity="1", resource_role_id=str(costs.role), hours="10")
    )
    lines.made(wiring, quantity="1", cost_category_id=str(costs.material), unit_disbursement="350")
    started = tree.made("Mise en service")
    starting = node_of(lines.made(started, quantity="1", resource_role_id=str(role), hours="10"))
    return Offer(revision, tree, lines, wiring, engineering, starting, category, role)


def node_of(written: dict[str, Any]) -> dict[str, Any]:
    """Give the node of the line a write gave back."""
    return written["nodes"][0]


def base(stage: Scene) -> str:
    """Give the path of the revisions of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/revisions"


def read(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> dict[str, Any]:
    """Read a revision, as its manager does."""
    answer = api.get(f"{base(stage)}/{revision['revision_id']}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def listed(api: ContractClient, stage: Scene) -> dict[str, dict[str, Any]]:
    """Read the history of the project, by revision."""
    answer = api.get(base(stage), headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return {each["revision_id"]: each for each in answer.json()["items"]}


def facets(tree: Tree) -> dict[str, dict[str, Any]]:
    """Read the facets of the lines of a tree, by node."""
    return {
        item["node_id"]: item["estimate_line"]
        for item in tree.items()
        if item.get("estimate_line") is not None
    }


def open_next(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the next revision, as the manager does; give it."""
    answer = api.post(base(stage), headers=stage.manager.headers, json={})
    assert answer.status_code == 201, answer.text
    return answer.json()


def set_project(api: ContractClient, stage: Scene, **values: str) -> None:
    """Change the rates of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    answer = api.patch(
        path, headers=stage.manager.headers, json={**values, "lock_version": counter}
    )
    assert answer.status_code == 200, answer.text


def correct_rate(database: Database, category: UUID, amount: str) -> None:
    """Correct the rate of a category for the year, at the version it bears."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        held = next(each for each in list_hourly_rates(session, category) if each.year == YEAR)
        set_hourly_rate(session, (category, YEAR), Decimal(amount), held.audit.lock_version, act)


def deactivate(database: Database, role: UUID, category: UUID) -> None:
    """Deactivate a role and a category of the reference, by the service of the reference."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        counter = session.scalars(select(ResourceRole.lock_version).where(ResourceRole.id == role))
        set_role_activation(session, role, is_active=False, lock_version=counter.one(), act=act)
        counter = session.scalars(
            select(CostCategory.lock_version).where(CostCategory.id == category)
        )
        set_cost_category_activation(
            session, category, is_active=False, lock_version=counter.one(), act=act
        )


def kept_rates(stage: Scene, revision: dict[str, Any]) -> dict[UUID, tuple[Decimal, str]]:
    """Read the rates a revision keeps, by category: their amount and their origin."""
    with stage.database.transaction() as session:
        rows = session.execute(
            select(RevisionRate.cost_category_id, RevisionRate.amount, RevisionRate.origin).where(
                RevisionRate.revision_id == UUID(revision["revision_id"])
            )
        ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def amounts(tree: Tree) -> dict[str, tuple[str, str, str]]:
    """Read the base, budgeted and re-estimated amounts of the lines of a tree, by node."""
    return {
        node: (each["base_amount"], each["budgeted_amount"], each["reestimated_amount"])
        for node, each in facets(tree).items()
    }


# --- What the marking keeps --------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0030-A")
def test_a_marked_revision_shows_the_role_and_the_amounts_of_its_marking_after_they_change(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « Après désactivation d'un rôle et correction de son taux horaire, une révision marquée qui
    # les employait affiche toujours le rôle et les montants d'origine. » : its snapshot keeps the
    # role active and the rate of 65.00, its lines name the role, active, at their amounts.
    mark(stage, offer.revision)
    before = amounts(offer.tree)
    deactivate(stage.database, costs.role, costs.labour)
    correct_rate(stage.database, costs.labour, "80.00")
    employed = read(api, stage, offer.revision)["snapshot"]["employed_reference"]
    roles = {each["code"]: each for each in employed["resource_roles"]}
    assert set(roles) == {"ING", "MES"}
    assert (roles["ING"]["label"], roles["ING"]["is_active"]) == ("Ingénieur", True)
    assert {each["cost_category_id"]: each["amount"] for each in employed["hourly_rates"]} == {
        str(costs.labour): "65.00",
        str(offer.commissioning): "60.00",
    }
    assert {each["year"] for each in employed["hourly_rates"]} == {YEAR}
    categories = {each["code"]: each["is_active"] for each in employed["cost_categories"]}
    assert categories == {"MO-001": True, "MO-002": True, "MAT-001": True}
    calendars = {each["label"]: each["is_default"] for each in employed["calendars"]}
    assert calendars["Semaine MES"] is False
    line = facets(offer.tree)[offer.engineering["node_id"]]
    assert (line["resource_role_label"], line["uses_inactive_object"]) == ("Ingénieur", False)
    assert line["base_amount"] == "650.00"
    assert amounts(offer.tree) == before


@pytest.mark.requirement("WF-REV-0030-A")
def test_a_marking_whose_roles_all_work_on_calendars_of_their_own_keeps_the_default_calendar(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # The default calendar is kept at every marking, whatever the calendars the roles employ: a
    # line of the role ``WE`` alone, on the calendar of its own, and the default one is imaged.
    role = add_role(stage.database, "WE", WEEKEND)
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    Lines(tree).made(tree.made("Veille"), quantity="1", resource_role_id=str(role), hours="8")
    mark(stage, revision)
    calendars = read(api, stage, revision)["snapshot"]["employed_reference"]["calendars"]
    with stage.database.transaction() as session:
        default = session.scalars(select(Calendar.id).where(Calendar.is_default.is_(True))).one()
    assert {each["calendar_id"] for each in calendars if each["is_default"]} == {str(default)}
    assert {each["label"] for each in calendars if not each["is_default"]} == {"Semaine WE"}
    del costs


@pytest.mark.requirement("WF-REV-0030-A")
def test_the_rates_of_the_project_changed_leave_those_a_marked_revision_kept(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # « La modification du taux d'inflation ou de la probabilité de gain du projet laisse inchangées
    # les valeurs conservées par une révision marquée. » : the current revision presents those of
    # its project, the marked one those of its marking.
    set_project(api, stage, inflation_rate="0.03", win_probability="0.6")
    current = read(api, stage, offer.revision)
    assert (current["inflation_rate"], current["win_probability"]) == ("0.03", "0.6")
    assert "snapshot" not in current
    mark(stage, offer.revision)
    set_project(api, stage, inflation_rate="0.05", win_probability="0.4")
    marked = read(api, stage, offer.revision)
    assert (marked["inflation_rate"], marked["win_probability"]) == ("0.03", "0.6")


@pytest.mark.requirement("WF-REV-0070-A")
def test_the_history_shows_the_year_and_the_rates_kept_by_a_marked_revision(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # « L'année de référence, le taux d'inflation et la probabilité de gain affichés pour une
    # révision marquée sont ceux conservés à son marquage, même après modification de ceux du
    # projet. » : ``listRevisions`` and ``getRevision``, the current revision on its project's.
    set_project(api, stage, inflation_rate="0.02", win_probability="0.7")
    mark(stage, offer.revision)
    set_project(api, stage, inflation_rate="0.04", win_probability="0.3")
    following = open_next(api, stage)
    history = listed(api, stage)
    kept = history[offer.revision["revision_id"]]
    assert (kept["reference_year"], kept["inflation_rate"], kept["win_probability"]) == (
        YEAR,
        "0.02",
        "0.7",
    )
    assert "snapshot" not in kept
    current = history[following["revision_id"]]
    assert (current["inflation_rate"], current["win_probability"]) == ("0.04", "0.3")
    assert read(api, stage, offer.revision)["inflation_rate"] == "0.02"


@pytest.mark.requirement("WF-REV-0070-A")
def test_a_marked_revision_shows_its_lines_as_they_were_at_its_marking(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « … l'ouverture de l'une d'elles affiche son planning, son devis et ses montants tels qu'ils
    # étaient au marquage. » : its lines on its images and its amounts, whatever the reference and
    # the project become since.
    mark(stage, offer.revision)
    before = facets(offer.tree)
    with stage.database.transaction() as session:
        session.execute(
            update(ResourceRole).where(ResourceRole.id == costs.role).values(label="Ingénieur B")
        )
        session.execute(
            update(CostCategory)
            .where(CostCategory.id == offer.commissioning)
            .values(label="Mise en route")
        )
    correct_rate(stage.database, costs.labour, "90.00")
    set_project(api, stage, inflation_rate="0.09")
    assert facets(offer.tree) == before
    line = before[offer.starting["node_id"]]
    assert (line["cost_category_label"], line["resource_role_label"]) == (
        "Mise en service",
        "Rôle MES",
    )


@pytest.mark.requirement("WF-REF-0130-A")
def test_a_rate_corrected_and_a_role_moved_to_another_category_leave_a_marked_revision_whole(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « Après correction d'un taux horaire et changement de la catégorie d'un rôle, les montants
    # d'une révision marquée qui les employait sont identiques à ceux relevés avant la
    # modification. »
    mark(stage, offer.revision)
    before = amounts(offer.tree)
    correct_rate(stage.database, costs.labour, "75.00")
    with stage.database.transaction() as session:
        session.execute(
            update(ResourceRole)
            .where(ResourceRole.id == costs.role)
            .values(cost_category_id=offer.commissioning)
        )
    assert amounts(offer.tree) == before
    employed = read(api, stage, offer.revision)["snapshot"]["employed_reference"]
    role = next(each for each in employed["resource_roles"] if each["code"] == "ING")
    assert (role["cost_category_id"], role["cost_category_label"]) == (
        str(costs.labour),
        "Ingénierie",
    )


@pytest.mark.requirement("WF-REF-0130-A")
def test_a_rate_written_prices_again_the_current_revisions_that_keep_none_not_the_marked_ones(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # A rate of the reference is corrected (WF-REF-0050): the current revision whose lines are
    # priced at it follows, in the transaction of the rate (EP-07, "Le calcul des montants"); the
    # marked one keeps the rate of its marking, and the revision opened from it the rate it copied.
    correct_rate(stage.database, costs.labour, "70.00")
    assert facets(offer.tree)[offer.engineering["node_id"]]["base_amount"] == "700.00"
    mark(stage, offer.revision)
    following = open_next(api, stage)
    tree = Tree(api, stage, following)
    correct_rate(stage.database, costs.labour, "72.00")
    assert facets(offer.tree)[offer.engineering["node_id"]]["base_amount"] == "700.00"
    assert {each["base_amount"] for each in facets(tree).values()} == {"700.00", "350.00", "600.00"}
    assert kept_rates(stage, following)[costs.labour] == (Decimal("70.00"), "reference")


@pytest.mark.requirement("WF-REV-0010-A")
def test_a_revision_opened_from_a_marked_one_copies_the_rates_of_its_marking(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « … à année de référence égale, elle porte aussi les mêmes valeurs de référentiel » (#2620):
    # the reference corrected after the marking, the copy keeps the rate kept at the marking.
    mark(stage, offer.revision)
    assert kept_rates(stage, offer.revision) == {
        costs.labour: (Decimal("65.00"), "reference"),
        offer.commissioning: (Decimal("60.00"), "reference"),
    }
    correct_rate(stage.database, costs.labour, "80.00")
    following = open_next(api, stage)
    assert kept_rates(stage, following)[costs.labour] == (Decimal("65.00"), "reference")
    tree = Tree(api, stage, following)
    assert "650.00" in {each["base_amount"] for each in facets(tree).values()}


# --- A current revision ------------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0020-A")
def test_a_role_and_a_category_deactivated_leave_a_current_revision_priced_and_markable(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « On désactive un rôle de ressource et une catégorie de coût employés par une révision en
    # cours. La révision reste calculable et peut être marquée sans que ses lignes soient
    # modifiées. » : its lines read, flagged, at their amounts; the marking keeps them so.
    before = amounts(offer.tree)
    deactivate(stage.database, costs.role, costs.labour)
    line = facets(offer.tree)[offer.engineering["node_id"]]
    assert (line["uses_inactive_object"], line["resource_role_label"]) == (True, "Ingénieur")
    assert amounts(offer.tree) == before
    mark(stage, offer.revision)
    marked = read(api, stage, offer.revision)
    assert marked["status"] == "marked"
    roles = marked["snapshot"]["employed_reference"]["resource_roles"]
    assert {each["code"]: each["is_active"] for each in roles}["ING"] is False
    assert amounts(offer.tree) == before


@pytest.mark.requirement("WF-REF-0010-A")
def test_a_role_deactivated_stays_named_on_the_lines_that_employ_it(
    stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « Un objet désactivé n'apparaît plus dans les listes de choix, mais reste affiché sur les
    # éléments qui l'emploient. » : the line of the current revision names its role and its
    # category, deactivated, and says it uses a deactivated object.
    deactivate(stage.database, costs.role, costs.labour)
    line = facets(offer.tree)[offer.engineering["node_id"]]
    assert (line["resource_role_label"], line["cost_category_label"]) == ("Ingénieur", "Ingénierie")
    assert line["uses_inactive_object"] is True


@pytest.mark.requirement("WF-PRJ-0040-A")
def test_a_new_rate_of_inflation_prices_the_current_revision_again_and_no_marked_one(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « La modification du taux d'inflation laisse inchangés les montants des révisions marquées. »
    # and, in the current revision, the lines consumed after the year of reference are priced
    # again, the others not (the provision line is EP-08's).
    later = offer.tree.made(
        "Exploitation",
        task={
            "scheduling_mode": "manual",
            "start": {"date": f"{YEAR + 2}-11-06"},
            "finish": {"date": f"{YEAR + 2}-11-07"},
        },
    )
    future = node_of(
        offer.lines.made(later, quantity="1", resource_role_id=str(costs.role), hours="10")
    )
    before = amounts(offer.tree)
    set_project(api, stage, inflation_rate="0.03")
    after = amounts(offer.tree)
    projected = (Decimal("650.00") * Decimal("1.0609")).quantize(Decimal("0.01"))
    assert Decimal(after[future["node_id"]][2]) == projected
    assert after[future["node_id"]][0] == "650.00"
    assert after[offer.engineering["node_id"]] == before[offer.engineering["node_id"]]
    mark(stage, offer.revision)
    set_project(api, stage, inflation_rate="0.05")
    assert amounts(offer.tree) == after
    assert read(api, stage, offer.revision)["inflation_rate"] == "0.03"


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_reference_designated_gives_the_current_lines_its_budgeted_amounts_and_nought_else(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « Une ligne créée dans la révision de référence porte des montants budgété et réestimé
    # égaux ; une ligne créée après porte un montant budgété nul. » : the designation refreshes the
    # current revision by the lineage (``register_designation``); a line it lacks, nought.
    mark(stage, offer.revision)
    following = open_next(api, stage)
    tree = Tree(api, stage, following)
    lines = Lines(tree)
    task = next(item for item in tree.items() if item["kind"] == "task")
    added = node_of(
        lines.made(task, quantity="2", cost_category_id=str(costs.material), unit_disbursement="10")
    )
    held = amounts(tree)
    # No reference yet: the budgeted amounts are read as the re-estimated ones.
    assert all(budgeted == reestimated for _, budgeted, reestimated in held.values())
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    designated = api.put(
        f"{path}/reference-revision",
        headers=stage.manager.headers,
        json={
            "revision_id": offer.revision["revision_id"],
            "confirmed": True,
            "lock_version": counter,
        },
    )
    assert designated.status_code == 200, designated.text
    reference = amounts(offer.tree)
    assert all(budgeted == reestimated for _, budgeted, reestimated in reference.values())
    refreshed = amounts(tree)
    assert refreshed[added["node_id"]][1] == "0.00"
    copied = {node: each for node, each in refreshed.items() if node != added["node_id"]}
    assert sorted(each[1] for each in copied.values()) == sorted(
        each[1] for each in reference.values()
    )
    assert {node: each[2] for node, each in refreshed.items()} == {
        node: each[2] for node, each in held.items()
    }


# --- The guard of the calendars of the roles -----------------------------------------------------


def calendar_of(database: Database, role: UUID) -> tuple[UUID, int]:
    """Give the calendar of a role, and its counter."""
    with database.transaction() as session:
        row = session.execute(
            select(Calendar.id, Calendar.lock_version)
            .join(ResourceRole, ResourceRole.calendar_id == Calendar.id)
            .where(ResourceRole.id == role)
        ).one()
    return row[0], row[1]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_calendar_change_that_would_idle_a_task_is_refused_naming_the_project(
    api: ContractClient, stage: Scene, realm: TestRealm, offer: Offer
) -> None:
    # « La modification d'un calendrier qui laisserait une tâche sans heure dans un projet que le
    # manager ne peut pas consulter est refusée en nommant ce projet par son libellé et son code ;
    # un projet en chiffrage sans code est nommé par son seul libellé. » : the calendar of the role
    # of a line left without an hour; the role named, nothing written. Hours left on a day pass.
    admin = person(stage.database, realm, "resource_settings.read", "resource_settings.write")
    calendar, counter = calendar_of(stage.database, offer.role)
    path = f"{REFERENCE}/calendars/{calendar}"
    idle = dict.fromkeys(DAYS, "0")
    refused = api.patch(
        path,
        headers=admin.headers,
        json={"label": "Semaine MES", "weekly_hours": idle, "lock_version": counter},
    )
    assert refusal(refused) == (
        422,
        "TASK_WITHOUT_WORKING_HOURS",
        {
            "resource_roles": [
                {"resource_role_id": str(offer.role), "code": "MES", "label": "Rôle MES"}
            ],
            "projects": [{"project_label": stage.project["label"], "project_code": None}],
        },
    )
    half = dict(zip(DAYS, (str(each) for each in HALF_DAYS), strict=True))
    accepted = api.patch(
        path,
        headers=admin.headers,
        json={"label": "Semaine MES", "weekly_hours": half, "lock_version": counter},
    )
    assert accepted.status_code == 200, accepted.text


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_role_given_a_calendar_that_meets_no_other_of_its_task_is_refused(
    api: ContractClient, stage: Scene, realm: TestRealm, costs: Costing, offer: Offer
) -> None:
    # ``updateResourceRole``: the role ``MES`` joins the engineer on the wiring, then is given a
    # calendar of weekends alone, which never meets the engineer's: refused, the two roles and the
    # project named; a calendar of four hours a day passes.
    offer.lines.made(offer.wiring, quantity="1", resource_role_id=str(offer.role), hours="4")
    admin = person(stage.database, realm, "resource_settings.read", "resource_settings.write")
    weekend = add_role(stage.database, "WE", WEEKEND)
    half = add_role(stage.database, "MI", HALF_DAYS)
    with stage.database.transaction() as session:
        role = session.get_one(ResourceRole, offer.role)
        body = {
            "code": role.code,
            "label": role.label,
            "cost_category_id": str(role.cost_category_id),
            "capacity": {"monthly_hours": "140.00", "headcount": "1"},
            "lock_version": role.lock_version,
        }
    path = f"{REFERENCE}/resource-roles/{offer.role}"
    refused = api.patch(
        path,
        headers=admin.headers,
        json={**body, "calendar_id": str(calendar_of(stage.database, weekend)[0])},
    )
    status, code, params = refusal(refused)
    assert (status, code) == (422, "TASK_WITHOUT_WORKING_HOURS")
    assert {each["code"] for each in params["resource_roles"]} == {"ING", "MES"}
    assert params["projects"] == [{"project_label": stage.project["label"], "project_code": None}]
    accepted = api.patch(
        path,
        headers=admin.headers,
        json={**body, "calendar_id": str(calendar_of(stage.database, half)[0])},
    )
    assert accepted.status_code == 200, accepted.text
    del costs


# --- Every attempt on a marked revision, and a marking during an entry ----------------------------


@pytest.mark.requirement("WF-REV-0020-A")
def test_every_attempt_to_change_a_marked_revision_is_refused(
    api: ContractClient, stage: Scene, costs: Costing, offer: Offer
) -> None:
    # « Toute tentative de modification d'une révision marquée est refusée, quel que soit le point
    # d'entrée. » : a line written or added, its rates updated: 409 ``revision_draft``, nothing
    # written (the import of an estimate is US-1550's).
    mark(stage, offer.revision)
    before = (amounts(offer.tree), kept_rates(stage, offer.revision))
    nodes_before = {item["node_id"] for item in offer.tree.items()}
    marked = read(api, stage, offer.revision)
    draft = {"missing_condition": "revision_draft"}
    changed = offer.lines.change(offer.engineering, quantity="3")
    assert refusal(changed) == (409, "STATE_FORBIDS_OPERATION", draft)
    added = offer.lines.create(
        offer.wiring, quantity="1", resource_role_id=str(costs.role), hours="1"
    )
    assert refusal(added) == (409, "STATE_FORBIDS_OPERATION", draft)
    rates = api.post(
        f"{base(stage)}/{offer.revision['revision_id']}/rate-update",
        headers=stage.manager.headers,
        json={"cost_category_ids": [str(costs.labour)], "lock_version": marked["lock_version"]},
    )
    assert refusal(rates) == (409, "STATE_FORBIDS_OPERATION", draft)
    # The tree: a task created, moved, deleted; the revision abandoned.
    assert refusal(offer.tree.create("Autre")) == (409, "STATE_FORBIDS_OPERATION", draft)
    nodes = f"{offer.tree.path}/nodes"
    wiring = offer.tree.node(offer.wiring["node_id"])
    moving = api.post(
        f"{nodes}/move",
        headers=stage.manager.headers,
        json={
            "node_ids": [wiring["node_id"]],
            "parent_id": None,
            "lock_version": wiring["lock_version"],
        },
    )
    assert refusal(moving) == (409, "STATE_FORBIDS_OPERATION", draft)
    deleting = api.delete(
        f"{nodes}/{wiring['node_id']}?lock_version={wiring['lock_version']}",
        headers=stage.manager.headers,
    )
    assert refusal(deleting) == (409, "STATE_FORBIDS_OPERATION", draft)
    abandoning = api.delete(
        f"{base(stage)}/{offer.revision['revision_id']}?lock_version={marked['lock_version']}",
        headers=stage.manager.headers,
    )
    assert refusal(abandoning) == (409, "STATE_FORBIDS_OPERATION", draft)
    assert (amounts(offer.tree), kept_rates(stage, offer.revision)) == before
    assert {item["node_id"] for item in offer.tree.items()} == nodes_before


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_marking_asked_during_an_entry_waits_for_it_and_keeps_what_it_wrote(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # A write of the tree holds its revision ``FOR SHARE`` until it commits; the marking, which
    # locks it ``FOR UPDATE``, waits, then keeps the role of the line the write added — the images
    # are those of the revision as it is marked, nothing written in it after.
    category, role = commissioning(stage.database)
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    task = tree.made("Câblage")
    Lines(tree).made(task, quantity="1", resource_role_id=str(costs.role), hours="10")
    project_id, revision_id = UUID(stage.project["project_id"]), UUID(revision["revision_id"])
    bearer = Bearer(project_id, revision_id, UUID(tree.structure_id), UUID(task["node_id"]))
    reference = LineReference(uuid4(), category, uuid4(), uuid4(), role)
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(
            select(Revision.id).where(Revision.id == revision_id).with_for_update(read=True)
        )
        insert_line_row(connection, bearer, reference, rank=2)
        marking = pool.submit(mark, stage, revision)
        with pytest.raises(FutureTimeout):
            marking.result(timeout=1.5)
    marking.result(timeout=30)
    employed = read(api, stage, revision)["snapshot"]["employed_reference"]
    assert {each["code"] for each in employed["resource_roles"]} == {"ING", "MES"}
    assert {each["cost_category_id"] for each in employed["hourly_rates"]} == {
        str(costs.labour),
        str(category),
    }


# --- The order of the locks of the writes that price a revision again ---------------------------


@pytest.mark.requirement("WF-REF-0050-A")
def test_a_line_created_during_a_rate_written_is_priced_at_the_new_rate(
    stage: Scene, costs: Costing, offer: Offer
) -> None:
    # The rate written prices the current revision again under the lock of each structure, the
    # lines read under it: a line a write of the tree created while the structure was held, and
    # committed, is priced with the others, not left at the old rate.
    project_id, revision_id = UUID(stage.project["project_id"]), UUID(offer.revision["revision_id"])
    structure_id = UUID(offer.tree.structure_id)
    # Under a task that bears no line yet: nothing but the lines read names it to be priced again.
    empty = offer.tree.made("Veille")
    bearer = Bearer(project_id, revision_id, structure_id, UUID(empty["node_id"]))
    reference = LineReference(uuid4(), costs.labour, uuid4(), uuid4(), costs.role)
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(
            select(CostStructure.id).where(CostStructure.id == structure_id).with_for_update()
        )
        added = insert_line_row(connection, bearer, reference, rank=9)
        pricing = pool.submit(correct_rate, stage.database, costs.labour, "80.00")
        with pytest.raises(FutureTimeout):
            pricing.result(timeout=1.5)
    pricing.result(timeout=30)
    with stage.database.transaction() as session:
        priced = session.scalars(
            select(EstimateLine.base_amount).where(EstimateLine.node_id == added)
        ).one()
    assert priced == Decimal("1600.00")


@pytest.mark.requirement("WF-PRJ-0040-A")
def test_a_new_rate_of_inflation_waits_for_the_current_revision_before_the_project(
    api: ContractClient, stage: Scene, offer: Offer
) -> None:
    # The current revision is held ``FOR UPDATE`` (a marking in the making): ``updateProject``
    # shares it before it locks the project, so it waits for the revision with the project free.
    revision_id = UUID(offer.revision["revision_id"])
    project_id = UUID(stage.project["project_id"])
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(select(Revision.id).where(Revision.id == revision_id).with_for_update())
        changing = pool.submit(set_project, api, stage, inflation_rate="0.03")
        with pytest.raises(FutureTimeout):
            changing.result(timeout=1.5)
        with stage.owner.begin() as other:
            other.execute(
                select(Project.id).where(Project.id == project_id).with_for_update(nowait=True)
            )
    changing.result(timeout=30)
    assert read(api, stage, offer.revision)["inflation_rate"] == "0.03"
