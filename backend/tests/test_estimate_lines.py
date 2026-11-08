# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of an estimate read, created, changed and priced (US-1490/L3).

``createNode`` of a line, ``updateEstimateLine``, ``listNodes`` with the facet of the line, its
filters, its sort and its totals, ``getComputedValueDependencies`` and ``resolveRowNumber`` of a
line, on the main structure of the current revision of a project its manager made
(``nodes_support``), its labour category rated for the year of the revision and a category of
material beside it (``estimate_support``). Every answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Costing, Lines, add_role, costing
from nodes_support import Tree, faults, mark, opened, refusal, set_progress
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    create_cost_category,
    set_hourly_rate,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

RATE = Decimal("65.00")
CENT = Decimal("0.01")
STATE_FORBIDS = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def labour(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a labour line of the role of the scene: one engineer for ten hours, unless said."""
    return {"quantity": "1", "resource_role_id": str(costs.role), "hours": "10", **line}


def material(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a line of material: one at 350.00, unless said."""
    held = {"quantity": "1", "cost_category_id": str(costs.material), "unit_disbursement": "350.00"}
    return {**held, **line}


def facet(written: dict[str, Any]) -> dict[str, Any]:
    """Give the facet of the line a write gave back."""
    return written["nodes"][0]["estimate_line"]


def set_inflation(api: ContractClient, stage: Scene, rate: str) -> None:
    """Give the project of the stage an inflation rate, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    answer = api.patch(
        path, headers=stage.manager.headers, json={"inflation_rate": rate, "lock_version": counter}
    )
    assert answer.status_code == 200, answer.text


def designate(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> None:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {"revision_id": revision["revision_id"], "confirmed": True, "lock_version": counter}
    answer = api.put(f"{path}/reference-revision", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def line_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read the line of a label in a structure."""
    return next(
        item
        for item in tree.items()
        if item["kind"] == "estimate_line" and item["estimate_line"]["label"] == label
    )


def nature_of_labour(stage: Scene) -> UUID:
    """Give the nature of labour of the scene."""
    with stage.database.transaction() as session:
        found = session.scalar(select(CostType.id).where(CostType.code == "MO"))
    assert found is not None
    return found


# --- The creation ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_line_is_created_under_its_task_labelled_and_priced(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The line is placed under its task, its label composed of the task's and the role's, its
    # category its role's, priced at the rate of the year; the task and the totals follow.
    task = tree.made("Mise en service")
    written = lines.made(task, **labour(costs))
    [node] = written["nodes"]
    assert (node["kind"], node["parent_id"], node["position"], node["level"]) == (
        "estimate_line",
        task["node_id"],
        1,
        2,
    )
    line = node["estimate_line"]
    assert line["label"] == "Mise en service — Ingénieur"
    assert (line["cost_category_id"], line["cost_category_label"]) == (
        str(costs.labour),
        "Ingénierie",
    )
    assert (line["resource_role_label"], line["hours"], line["unit_disbursement"]) == (
        "Ingénieur",
        "10",
        None,
    )
    # On a project without a reference, the budgeted amount is the re-estimated one.
    assert (line["base_amount"], line["reestimated_amount"], line["budgeted_amount"]) == (
        "650.00",
        "650.00",
        "650.00",
    )
    assert (line["consumption_year"], line["payment_delay_days"]) == (YEAR, 0)
    assert (line["is_computed"], line["uses_inactive_object"]) == (False, False)
    assert line["remaining_entry"] == {"is_available": True, "missing_conditions": []}
    assert node["computed_fields"] == ["estimate_line.cost_category_id"]
    assert node["editable_fields"] == [
        "estimate_line.label",
        "estimate_line.resource_role_id",
        "estimate_line.quantity",
        "estimate_line.hours",
        "estimate_line.payment_delay_days",
        "estimate_line.subproject_id",
    ]
    [above] = written["ancestors"]
    assert (above["node_id"], above["task"]["base_amount"]) == (task["node_id"], "650.00")
    assert written["totals"]["estimate_line_count"] == 1
    assert (written["totals"]["hours"], written["totals"]["base_amount"]) == ("10", "650.00")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_line_is_placed_among_the_lines_of_its_task_before_its_subtasks(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # After the last line by default, at their head after ``null``, after its sibling, after the
    # last line when the sibling named is a subtask (#1187); a milestone bears a line; a parent
    # that is no task, or a sibling of another parent, is refused.
    task = tree.made("Câblage")
    subtask = tree.made("Repérage", parent_id=task["node_id"])
    first = lines.made(task, **material(costs, label="Câbles"))["nodes"][0]
    head = lines.made(task, **material(costs, label="Gaines"), after_node_id=None)["nodes"][0]
    after = lines.made(task, **material(costs, label="Borniers"), after_node_id=head["node_id"])
    tail = lines.made(task, **material(costs, label="Colliers"), after_node_id=subtask["node_id"])
    assert facet(after)["label"] == "Borniers"
    assert facet(tail)["label"] == "Colliers"
    under = [
        item["estimate_line"]["label"] if item["kind"] == "estimate_line" else item["task"]["label"]
        for item in tree.items()
    ]
    assert under == ["Câblage", "Gaines", "Borniers", "Câbles", "Colliers", "Repérage"]
    assert tree.node(first["node_id"])["position"] == 3
    milestone = tree.made("Réception", task={"duration": {"value": "0", "unit": "d"}})
    assert facet(lines.made(milestone, **material(costs)))["label"] == "Réception"
    assert faults(lines.create(first["node_id"], **material(costs))) == [
        ("/parent_id", "UNKNOWN_TASK", {})
    ]
    stray = lines.create(task, **material(costs), after_node_id=milestone["node_id"])
    assert faults(stray) == [("/after_node_id", "NODE_NOT_SIBLING", {})]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_line_refuses_the_fields_its_kind_does_not_accept(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Une ligne de main-d'œuvre refuse la saisie d'un débours ; une ligne hors main-d'œuvre
    # refuse celle d'une charge et d'un rôle. » At the creation as at the modification; a role
    # sent makes the line a labour line.
    task = tree.made("Câblage")
    assert faults(lines.create(task, **labour(costs, unit_disbursement="12.00"))) == [
        ("/estimate_line/unit_disbursement", "FIELD_NOT_ACCEPTED", {})
    ]
    assert faults(lines.create(task, **material(costs, hours="4"))) == [
        ("/estimate_line/hours", "FIELD_NOT_ACCEPTED", {})
    ]
    worked = lines.made(task, **labour(costs))["nodes"][0]
    bought = lines.made(task, **material(costs))["nodes"][0]
    assert faults(lines.change(worked, unit_disbursement="1.00")) == [
        ("/unit_disbursement", "FIELD_NOT_ACCEPTED", {})
    ]
    assert faults(lines.change(bought, hours="2", resource_role_id=str(costs.role))) == [
        ("/resource_role_id", "FIELD_NOT_ACCEPTED", {}),
        ("/hours", "FIELD_NOT_ACCEPTED", {}),
    ]
    assert worked["estimate_line"]["resource_role_id"] == str(costs.role)
    assert bought["estimate_line"]["hours"] is None
    assert bought["computed_fields"] == []
    assert "estimate_line.unit_disbursement" in bought["editable_fields"]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_line_without_category_or_with_a_negative_figure_is_refused(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # Without a role, the category is required; a category of labour asks for a role; the figures
    # and the payment delay are never negative; an object unknown is named.
    task = tree.made("Câblage")
    assert faults(lines.create(task, quantity="1", unit_disbursement="3.00")) == [
        ("/estimate_line/cost_category_id", "VALUE_REQUIRED", {})
    ]
    assert faults(lines.create(task, **material(costs, cost_category_id=str(costs.labour)))) == [
        ("/estimate_line/resource_role_id", "RESOURCE_ROLE_REQUIRED", {})
    ]
    negative = lines.create(task, **material(costs, quantity="-1", unit_disbursement="-2.00"))
    assert faults(negative) == [
        ("/estimate_line/unit_disbursement", "VALUE_OUT_OF_RANGE", {"minimum": 0}),
        ("/estimate_line/quantity", "VALUE_OUT_OF_RANGE", {"minimum": 0}),
    ]
    late = lines.create(task, **material(costs, payment_delay_days=-1))
    assert late.status_code == 422, late.text
    assert [each["pointer"] for each in late.json()["fields"]] == [
        "/estimate_line/payment_delay_days"
    ]
    unknown = lines.create(task, **labour(costs, resource_role_id=str(uuid4())))
    assert faults(unknown) == [("/estimate_line/resource_role_id", "UNKNOWN_RESOURCE_ROLE", {})]
    elsewhere = lines.create(task, **material(costs, subproject_id=str(uuid4())))
    assert faults(elsewhere) == [("/estimate_line/subproject_id", "UNKNOWN_SUBPROJECT", {})]
    assert tree.items("?kinds=estimate_line") == []


@pytest.mark.requirement("WF-REF-0010-A")
def test_a_deactivated_object_is_refused_to_an_entry_and_flagged_on_the_line_that_holds_it(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The line keeps a role deactivated since, and says so; an entry that would give it one is
    # refused (``INACTIVE_REFERENCE_OBJECT``), as a figure sent null where one is required.
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    welder = add_role(stage.database, "SOUD", (8, 8, 8, 8, 8, 0, 0))
    with stage.database.transaction() as session:
        session.execute(
            update(ResourceRole).where(ResourceRole.code == "SOUD").values(is_active=False)
        )
    assert faults(lines.change(node, resource_role_id=str(welder))) == [
        ("/resource_role_id", "INACTIVE_REFERENCE_OBJECT", {})
    ]
    assert faults(lines.change(node, hours=None, payment_delay_days=None)) == [
        ("/hours", "VALUE_REQUIRED", {}),
        ("/payment_delay_days", "VALUE_REQUIRED", {}),
    ]
    assert faults(lines.create(task, **material(costs, cost_category_id=str(uuid4())))) == [
        ("/estimate_line/cost_category_id", "UNKNOWN_COST_CATEGORY", {})
    ]
    with stage.database.transaction() as session:
        session.execute(
            update(ResourceRole).where(ResourceRole.code == "ING").values(is_active=False)
        )
    assert tree.node(node["node_id"])["estimate_line"]["uses_inactive_object"] is True
    assert lines.change(node, quantity="2").status_code == 200


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_labour_line_two_years_after_the_reference_is_projected_by_the_inflation(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Pour une ligne consommée dans l'année de référence, le montant d'une ligne de main-d'œuvre
    # est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour cette
    # année ; pour une ligne consommée deux ans plus tard, avec un taux d'inflation de 3 %, il vaut
    # ce produit fois 1,0609 (WF-DEV-0030). »
    set_inflation(api, stage, "0.03")
    now = tree.made("Études")
    later = tree.made(
        "Exploitation",
        task={
            "scheduling_mode": "manual",
            "start": {"date": f"{YEAR + 2}-11-06"},
            "finish": {"date": f"{YEAR + 2}-11-07"},
        },
    )
    present = facet(lines.made(now, **labour(costs, quantity="2")))
    future = facet(lines.made(later, **labour(costs, quantity="2")))
    product = 2 * 10 * RATE
    assert (present["base_amount"], present["reestimated_amount"]) == (str(product), str(product))
    assert present["consumption_year"] == YEAR
    assert future["base_amount"] == str(product)
    projected = (product * Decimal("1.0609")).quantize(CENT)
    assert Decimal(future["reestimated_amount"]) == projected
    assert future["consumption_year"] == YEAR + 2


@pytest.mark.requirement("WF-DEV-0020-A")
def test_no_amount_is_entered_and_each_names_what_it_depends_on(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Aucun des deux montants n'est saisissable. » Neither write has a field for them, an unknown
    # field is refused, and ``getComputedValueDependencies`` names what each depends on.
    task = tree.made("Câblage")
    refused = lines.create(task, **labour(costs, base_amount="1.00"))
    assert faults(refused) == [("/estimate_line/base_amount", "FIELD_NOT_ACCEPTED", {})]
    worked = lines.made(task, **labour(costs))["nodes"][0]
    bought = lines.made(task, **material(costs))["nodes"][0]
    assert faults(lines.change(worked, reestimated_amount="1.00", quantity="2")) == [
        ("/reestimated_amount", "FIELD_NOT_ACCEPTED", {})
    ]

    def rules(node: dict[str, Any], field: str) -> Any:
        path = f"{tree.path}/nodes/{node['node_id']}/dependencies?field={field}"
        return api.get(path, headers=stage.manager.headers)

    assert rules(worked, "estimate_line.base_amount").json()["depends_on"] == ["hourly_rate"]
    assert rules(bought, "estimate_line.base_amount").json()["depends_on"] == ["unit_disbursement"]
    assert rules(worked, "estimate_line.budgeted_amount").json()["depends_on"] == [
        "reference_revision",
        "inflation",
    ]
    assert rules(worked, "estimate_line.reestimated_amount").json()["depends_on"] == [
        "remaining_reviews",
        "inflation",
    ]
    assert rules(worked, "estimate_line.cost_category_id").json() == {
        "node_id": worked["node_id"],
        "field": "estimate_line.cost_category_id",
        "depends_on": ["resource_role"],
        "rows": [],
    }
    assert refusal(rules(bought, "estimate_line.cost_category_id"))[:2] == (
        422,
        "VALIDATION_FAILED",
    )
    amounts = rules(task, "task.base_amount").json()
    assert amounts["depends_on"] == ["lines_and_subordinates"]
    assert [row["label"] for row in amounts["rows"]] == ["Câblage — Ingénieur", "Câblage"]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_category_of_provision_is_refused_to_a_line_entered(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « La création à la main d'une ligne dont la catégorie relève d'une nature de type provision
    # pour risques est refusée. » At the creation as at the modification.
    task = tree.made("Câblage")
    provision = material(costs, cost_category_id=str(costs.provision))
    assert faults(lines.create(task, **provision)) == [
        ("/estimate_line/cost_category_id", "PROVISION_CATEGORY_RESERVED", {})
    ]
    bought = lines.made(task, **material(costs))["nodes"][0]
    assert faults(lines.change(bought, cost_category_id=str(costs.provision))) == [
        ("/cost_category_id", "PROVISION_CATEGORY_RESERVED", {})
    ]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_the_category_of_a_labour_line_is_its_roles(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « La catégorie d'une ligne de main-d'œuvre n'est pas saisissable : c'est celle de son
    # rôle. » Another refused, its own accepted, a role changed giving it its category.
    task = tree.made("Câblage")
    other = labour(costs, cost_category_id=str(costs.material))
    assert faults(lines.create(task, **other)) == [
        ("/estimate_line/cost_category_id", "COMPUTED_VALUE", {})
    ]
    own = lines.made(task, **labour(costs, cost_category_id=str(costs.labour)))["nodes"][0]
    assert own["computed_fields"] == ["estimate_line.cost_category_id"]
    assert faults(lines.change(own, cost_category_id=str(costs.material))) == [
        ("/cost_category_id", "COMPUTED_VALUE", {})
    ]
    act = Act(None, utc_now())
    with stage.database.transaction() as session:
        draft = CostCategoryDraft("MO-002", "Soudure", "641002", nature_of_labour(stage))
        welding = create_cost_category(session, draft, act).cost_category_id
        set_hourly_rate(session, (welding, YEAR), Decimal("80.00"), None, act)
    welder = add_role(stage.database, "SOUD", (8, 8, 8, 8, 8, 0, 0), welding)
    changed = facet(lines.changed(own, resource_role_id=str(welder)))
    assert (changed["resource_role_label"], changed["cost_category_id"]) == (
        "Rôle SOUD",
        str(welding),
    )
    assert changed["base_amount"] == "800.00"


@pytest.mark.requirement("WF-DEV-0010-A")
def test_a_line_whose_category_has_no_rate_is_refused_then_priced_once_rated(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Le refus énumère les catégories de coût sans taux horaire pour l'année de référence. »
    # « Le calcul aboutit dès que ces taux sont renseignés. » At the creation and at a role changed.
    act = Act(None, utc_now())
    with stage.database.transaction() as session:
        draft = CostCategoryDraft(
            "MO-002", "Ingénierie électrique", "641002", nature_of_labour(stage)
        )
        electric = create_cost_category(session, draft, act).cost_category_id
    role = add_role(stage.database, "ELEC", (8, 8, 8, 8, 8, 0, 0), electric)
    task = tree.made("Câblage")
    missing = (
        422,
        "HOURLY_RATE_MISSING",
        {
            "missing_rates": [
                {"cost_category_id": str(electric), "label": "Ingénierie électrique", "year": YEAR}
            ]
        },
    )
    assert refusal(lines.create(task, **labour(costs, resource_role_id=str(role)))) == missing
    worked = lines.made(task, **labour(costs))["nodes"][0]
    assert refusal(lines.change(worked, resource_role_id=str(role))) == missing
    with stage.database.transaction() as session:
        set_hourly_rate(session, (electric, YEAR), Decimal("70.00"), None, act)
    made = facet(lines.made(task, **labour(costs, resource_role_id=str(role))))
    assert made["base_amount"] == "700.00"
    assert facet(lines.changed(worked, resource_role_id=str(role)))["base_amount"] == "700.00"


# --- The budgeted amount -----------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0020-A")
def test_the_budgeted_amount_follows_the_reference_and_the_lines_added_after_it_have_none(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Une ligne créée dans la révision de référence porte des montants budgété et réestimé
    # égaux ; une ligne créée après porte un montant budgété nul. »
    # « La saisie d'une charge de 80 heures sur une ligne de quantité 1 budgétée à 100 heures,
    # consommée dans l'année de référence, donne un montant réestimé de 80 fois le taux et laisse
    # le montant budgété inchangé. »
    task = tree.made("Câblage")
    lines.made(task, **labour(costs, hours="100"))
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    kept = line_of(tree, "Câblage — Ingénieur")["estimate_line"]
    assert (kept["budgeted_amount"], kept["reestimated_amount"]) == ("6500.00", "6500.00")
    current = Tree(api, stage, opened(api, stage))
    following = Lines(current)
    copied = line_of(current, "Câblage — Ingénieur")
    assert copied["estimate_line"]["budgeted_amount"] == "6500.00"
    entered = facet(following.changed(copied, hours="80"))
    assert (entered["reestimated_amount"], entered["budgeted_amount"]) == ("5200.00", "6500.00")
    task_now = next(item for item in current.items() if item["kind"] == "task")
    added = facet(following.made(task_now, **material(costs)))
    assert (added["budgeted_amount"], added["reestimated_amount"]) == ("0.00", "350.00")
    # The modification of the current revision leaves the marked one as it was (WF-DAT-0010).
    assert line_of(tree, "Câblage — Ingénieur")["estimate_line"] == kept


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_next_revision_holds_as_many_lines_as_the_marked_one_and_changes_none_of_it(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Après marquage d'une révision puis création de la suivante, le nombre de lignes de chaque
    # table portant l'identifiant de la nouvelle révision égale celui de la révision marquée. »
    # « Une modification dans la révision en cours ne change aucune ligne portant l'identifiant
    # d'une révision marquée. »
    task = tree.made("Câblage")
    lines.made(task, **labour(costs))
    lines.made(task, **material(costs))
    mark(stage, tree.revision)

    def of_revision(revision_id: str) -> list[tuple[Any, ...]]:
        with stage.database.transaction() as session:
            rows = session.execute(
                select(EstimateLine, Node.lineage_id)
                .join(Node, Node.id == EstimateLine.node_id)
                .where(Node.revision_id == UUID(revision_id))
                .order_by(Node.lineage_id)
            ).all()
            return [
                (lineage, line.label, line.quantity, line.base_amount, line.lock_version)
                for line, lineage in rows
            ]

    before = of_revision(tree.revision["revision_id"])
    current = Tree(api, stage, opened(api, stage))
    after = of_revision(current.revision["revision_id"])
    assert len(after) == len(before) == 2
    assert [each[:4] for each in after] == [each[:4] for each in before]
    Lines(current).changed(line_of(current, "Câblage — Ingénieur"), quantity="3")
    assert of_revision(tree.revision["revision_id"]) == before


# --- The modification --------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0040-A")
def test_a_modification_writes_what_it_sends_at_the_counter_read(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # Only what is sent changes; a counter of another write is refused (412); a labour line keeps
    # its role (``RESOURCE_ROLE_REQUIRED``); a subproject of the project is named by its label.
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs, payment_delay_days=30))["nodes"][0]
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-CMD", "label": "Poste de commande"},
    )
    assert answer.status_code == 201, answer.text
    subproject = answer.json()["subproject_id"]
    written = lines.changed(node, label="Câblage des armoires", subproject_id=subproject)
    line = facet(written)
    assert (line["label"], line["hours"], line["payment_delay_days"]) == (
        "Câblage des armoires",
        "10",
        30,
    )
    assert (line["subproject_id"], line["subproject_label"]) == (subproject, "Poste de commande")
    assert written["nodes"][0]["lock_version"] == node["lock_version"] + 1
    stale = lines.change(node, quantity="2")
    assert refusal(stale) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": node["lock_version"] + 1},
    )
    current = written["nodes"][0]
    assert faults(lines.change(current, resource_role_id=None)) == [
        ("/resource_role_id", "RESOURCE_ROLE_REQUIRED", {})
    ]
    assert lines.change(current).status_code == 422
    outside = lines.changed(current, subproject_id=None)
    assert facet(outside)["subproject_label"] is None
    assert refusal(lines.change({"node_id": task["node_id"], "lock_version": 1}, label="x"))[
        :2
    ] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-IHM-0110-A")
def test_two_writes_of_one_line_at_once_leave_one_refused_by_its_counter(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    """Two writes at once: one wins, the other is refused (412) by the counter the first advanced.

    The test shows the outcome, not which of the lock and the counter produced it; the next test
    shows that a write waits for the lock of its structure.
    """
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]

    def change(hours: str) -> Any:
        return lines.change(node, hours=hours)

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(change, ["20", "30"]))
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    [won] = [answer.json() for answer in answers if answer.status_code == 200]
    assert facet(won)["hours"] == line_of(tree, facet(won)["label"])["estimate_line"]["hours"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_of_a_line_waits_for_the_lock_of_its_structure(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # Another transaction holds the structure ``FOR UPDATE``: the write starts, waits, and answers
    # once the lock is released, at the counter it read; a bare check of the counter would answer
    # at once.
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(
            select(CostStructure.id)
            .where(CostStructure.id == UUID(tree.structure_id))
            .with_for_update()
        )
        waiting = pool.submit(lines.change, node, hours="20")
        with pytest.raises(FutureTimeout):
            waiting.result(timeout=1.5)
    answer = waiting.result(timeout=30)
    assert answer.status_code == 200, answer.text
    assert facet(answer.json())["hours"] == "20"


@pytest.mark.requirement("WF-IHM-0040-A")
def test_a_modification_that_sends_nothing_beside_its_counter_is_refused(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # No field is sent beside ``lock_version`` (``minProperties``): 422 ``VALIDATION_FAILED``,
    # naming no field, and the line is left as it was.
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    answer = lines.change(node)
    assert refusal(answer) == (422, "VALIDATION_FAILED", {})
    assert "fields" not in answer.json()
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]


# --- The state and the rights ------------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_line_of_a_completed_task_of_the_main_structure_is_neither_created_nor_changed(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « La modification d'une ligne portée par une tâche terminée est refusée. » On the main
    # structure, after the conditions of the revision; the line names no field it accepts, and
    # no re-estimate (#1767).
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    set_progress(stage, task["node_id"], "completed", tree.created_at.date())
    completed = (409, STATE_FORBIDS, {"missing_condition": "task_not_completed"})
    assert refusal(lines.create(task, **material(costs))) == completed
    assert refusal(lines.change(node, quantity="2")) == completed
    read = tree.node(node["node_id"])
    assert read["editable_fields"] == []
    assert read["estimate_line"]["remaining_entry"] == {
        "is_available": False,
        "missing_conditions": ["task_not_completed"],
    }


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_line_of_a_marked_revision_or_of_a_terminal_project_is_not_written(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    mark(stage, tree.revision)
    marked = (409, STATE_FORBIDS, {"missing_condition": "revision_draft"})
    assert refusal(lines.create(task, **material(costs))) == marked
    assert refusal(lines.change(node, quantity="2")) == marked
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    terminal = (409, STATE_FORBIDS, {"missing_condition": "project_not_terminal"})
    assert refusal(lines.change(node, quantity="2")) == terminal


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_line_is_not_written_while_a_background_task_runs(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    running = (409, STATE_FORBIDS, {"missing_condition": "no_background_task_running"})
    assert refusal(lines.create(task, **material(costs))) == running
    assert refusal(lines.change(node, quantity="2")) == running


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_line_is_changed_by_a_contributor_who_may_write_the_estimate(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing, realm: TestRealm
) -> None:
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    reading = person(stage.database, realm, "project_settings.read", "estimate.read")
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(lines.change(node, reading, quantity="2")) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "estimate.write"},
    )
    seeing = person(stage.database, realm, "estimate.read", "estimate.write", "all_projects_read")
    assert refusal(lines.change(node, seeing, quantity="2")) == (
        403,
        "NOT_CONTRIBUTOR",
        {"missing_condition": "is_contributor"},
    )
    assert lines.change(node, stage.participant, quantity="2").status_code == 200


# --- The reading -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0130-A")
def test_the_filters_of_the_line_retain_lines_with_their_tasks_and_the_totals_follow(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    cabling = tree.made("Câblage")
    tests = tree.made("Essais")
    lines.made(cabling, **labour(costs))
    lines.made(cabling, **material(costs, label="Câbles", unit_disbursement="120.00"))
    lines.made(tests, **material(costs, label="Consommables"))

    def labels(query: str) -> list[str]:
        return [
            item["estimate_line"]["label"] if item["estimate_line"] else item["task"]["label"]
            for item in tree.items(query)
        ]

    assert labels(f"?cost_category_id={costs.material}") == [
        "Câblage",
        "Câbles",
        "Essais",
        "Consommables",
    ]
    assert labels(f"?resource_role_id={costs.role}") == ["Câblage", "Câblage — Ingénieur"]
    assert labels("?base_amount_min=300.00&base_amount_max=400.00") == ["Essais", "Consommables"]
    assert labels("?hours_min=1") == ["Câblage", "Câblage — Ingénieur"]
    assert labels(f"?cost_type_id={nature_of_labour(stage)}") == [
        "Câblage",
        "Câblage — Ingénieur",
    ]
    assert len(labels("?subproject_id=unassigned")) == 5
    assert labels("?previous_quantity_min=0") == []
    read = tree.read(f"?cost_category_id={costs.material}").json()
    assert read["totals"] == {
        "task_count": 2,
        "estimate_line_count": 2,
        "hours": "0",
        "base_amount": "470.00",
        "budgeted_amount": "470.00",
        "reestimated_amount": "470.00",
    }
    # ``kinds`` chooses what is returned; the totals stay those of the lines retained.
    tasks = tree.read("?kinds=task").json()
    assert [item["kind"] for item in tasks["items"]] == ["task", "task"]
    assert tasks["totals"]["estimate_line_count"] == 3
    assert tasks["totals"]["base_amount"] == "1120.00"
    assert tasks["items"][0]["task"]["reestimated_amount"] == "770.00"
    with stage.database.transaction() as session:
        session.execute(
            update(CostCategory).where(CostCategory.id == costs.material).values(is_active=False)
        )
    assert labels("?uses_inactive_object=true") == [
        "Câblage",
        "Câbles",
        "Essais",
        "Consommables",
    ]


@pytest.mark.requirement("WF-IHM-0060-A")
def test_the_lines_are_sorted_under_each_task_which_keeps_its_place(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # Sorted by a decreasing amount, each task returns its lines from the greatest to the least;
    # a line without hours comes after the others ascending, before them descending.
    cabling = tree.made("Câblage")
    tests = tree.made("Essais")
    lines.made(cabling, **material(costs, label="Petit", unit_disbursement="10.00"))
    lines.made(cabling, **labour(costs, label="Moyen"))
    lines.made(cabling, **material(costs, label="Grand", unit_disbursement="900.00"))
    lines.made(tests, **material(costs, label="Seul"))

    def labels(query: str) -> list[str]:
        return [
            item["estimate_line"]["label"] if item["estimate_line"] else item["task"]["label"]
            for item in tree.items(query)
        ]

    assert labels("?sort_by=base_amount&sort_order=desc") == [
        "Câblage",
        "Grand",
        "Moyen",
        "Petit",
        "Essais",
        "Seul",
    ]
    assert labels("?sort_by=hours") == ["Câblage", "Moyen", "Petit", "Grand", "Essais", "Seul"]
    assert labels("?sort_by=hours&sort_order=desc") == [
        "Câblage",
        "Petit",
        "Grand",
        "Moyen",
        "Essais",
        "Seul",
    ]
    assert labels("?sort_by=label") == ["Câblage", "Grand", "Moyen", "Petit", "Essais", "Seul"]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_row_number_resolves_to_a_line_by_its_label(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    task = tree.made("Câblage")
    node = lines.made(task, **labour(costs))["nodes"][0]
    answer = api.get(f"{tree.path}/rows/2", headers=stage.manager.headers)
    assert answer.json() == {
        "node_id": node["node_id"],
        "row_number": 2,
        "label": "Câblage — Ingénieur",
        "kind": "estimate_line",
    }
