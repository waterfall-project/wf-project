# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks (US-1510).

``getEstimateIndicators`` sums the amounts the lines keep: the total, its breakdowns by nature, by
subproject and by work package, its differences with the reference and with the marked revision
before it; ``getMissingRates`` names the categories of labour a revision employs without a rate for
its year. The shares and the pure sums are checked without a database; every answer of the service
is checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Costing, Lines, costing, imaged
from nodes_support import Tree, faults, mark, opened, put_facts, refusal, work_breakdown
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, insert, select, update

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
    set_hourly_rate,
)
from waterfall.core.cost_settings.tables import CostCategory, HourlyRate
from waterfall.core.estimate.shares import distribution, share_of, shown
from waterfall.core.estimate.tables import RevisionCategory
from waterfall.core.projects.tables import WorkPackage
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MISSING = "hourly_rate_missing"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated 65.00 this year."""
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
    """Give a labour line: one engineer for ten hours at 65.00, that is 650.00, unless said."""
    return {"quantity": "1", "resource_role_id": str(costs.role), "hours": "10", **line}


def material(costs: Costing, amount: str = "350.00", **line: Any) -> dict[str, Any]:
    """Give a line of material: one at 350.00, unless said."""
    held = {
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }
    return {**held, **line}


def path(stage: Scene, tail: str = "") -> str:
    """Give the address of the indicators of the estimate of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/estimate-indicators{tail}"


def read(api: ContractClient, stage: Scene, query: str = "") -> dict[str, Any]:
    """Read the indicators as the manager does; they must be given."""
    answer = api.get(path(stage) + query, headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def rates(api: ContractClient, stage: Scene, query: str = "") -> list[dict[str, Any]]:
    """Read the rates the estimate lacks as the manager does; they must be given."""
    answer = api.get(path(stage, "/missing-rates") + query, headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def value(figure: dict[str, Any]) -> str | None:
    """Give the value of an amount or a share that may not be computed."""
    return figure["value"]


def by_label(rows: list[dict[str, Any]]) -> dict[str | None, dict[str, Any]]:
    """Give the rows of a ventilation by their label."""
    return {each["label"]: each for each in rows}


def subproject(api: ContractClient, stage: Scene, code: str, label: str) -> str:
    """Create a subproject of the project, as the manager does; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]


def designate(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> None:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    path_ = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path_, headers=stage.manager.headers).json()["lock_version"]
    sent = {"revision_id": revision["revision_id"], "confirmed": True, "lock_version": counter}
    answer = api.put(f"{path_}/reference-revision", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def unrate(stage: Scene, category: UUID) -> None:
    """Withdraw the rate of a category for this year from the reference, around the service."""
    with stage.owner.begin() as connection:
        connection.execute(
            delete(HourlyRate).where(
                HourlyRate.cost_category_id == category, HourlyRate.year == YEAR
            )
        )


# --- The shares: no database ---------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_shares_of_a_distribution_sum_to_one_the_largest_carrying_the_remainder() -> None:
    # « La somme des totaux par nature égale le total général, et la somme de leurs pourcentages
    # vaut cent. » : three equal thirds are 0.3333 each, the remainder of the roundings, 0.0001,
    # going to the first of the largest.
    assert distribution([Decimal(100)] * 3) == [
        Decimal("0.3334"),
        Decimal("0.3333"),
        Decimal("0.3333"),
    ]
    assert distribution([Decimal(650), Decimal(350)]) == [Decimal("0.65"), Decimal("0.35")]
    assert sum(distribution([Decimal("12.34"), Decimal("56.78"), Decimal("0.01")])) == 1


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_share_that_four_places_would_make_nought_is_given_to_its_first_significant_digit() -> (
    None
):
    # « la somme de leurs pourcentages vaut cent » (docs/api/README.md, « Une part… ») : 0.0000309
    # is 0.00003, 0.99996 is one, a half goes away from zero, and the largest part of a
    # distribution carries the remainder of the roundings whatever its places.
    assert share_of(Decimal("0.0000309"), Decimal(1)) == Decimal("0.00003")
    assert share_of(Decimal("0.99996"), Decimal(1)) == Decimal(1)
    assert share_of(Decimal("0.00005"), Decimal(1)) == Decimal("0.0001")
    assert share_of(Decimal("0.00004"), Decimal(1)) == Decimal("0.00004")
    shares = distribution([Decimal("0.01"), Decimal("10000000.00")])
    assert (shown(shares[0]), shown(shares[1])) == ("0.000000001", "0.999999999")
    assert shown(Decimal("1.0000")) == "1"
    assert shown(Decimal("0.1370")) == "0.137"


# --- The total and its ventilations ---------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_amounts_by_nature_sum_to_the_total_and_their_shares_to_one(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « La somme des totaux par nature égale le total général, et la somme de leurs pourcentages
    # vaut cent. » : two tasks, each with a line of labour (650.00 and 1 300.00) and a line of
    # material (350.00 and 100.00); the total is the re-estimated amount of the lines.
    wiring = tree.made("Câblage")
    lines.made(wiring, **labour(costs))
    lines.made(wiring, **material(costs))
    testing = tree.made("Essais")
    lines.made(testing, **labour(costs, hours="20"))
    lines.made(testing, **material(costs, "100.00"))
    found = read(api, stage)
    assert value(found["total"]) == "2400.00"
    natures = found["by_cost_type"]
    assert [(each["label"], value(each["amount"]), value(each["share"])) for each in natures] == [
        ("Main-d'œuvre", "1950.00", "0.8125"),
        ("Matériel", "450.00", "0.1875"),
    ]
    assert sum(Decimal(value(each["amount"]) or 0) for each in natures) == Decimal("2400.00")
    assert sum(Decimal(value(each["share"]) or 0) for each in natures) == 1


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_ventilations_sum_to_the_total_whatever_the_remainder_of_the_roundings(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « La somme des totaux par nature égale le total général, et la somme de leurs pourcentages
    # vaut cent. » : by subproject here, the set out of any subproject last — three subprojects of
    # 100.00 make thirds, the first carrying the 0.0001 of the roundings; a fourth part of 100.00,
    # out of any subproject, makes four quarters.
    task = tree.made("Fourniture")
    for code, label in (("A", "Armoires"), ("B", "Boîtiers"), ("C", "Câbles")):
        sent = subproject(api, stage, code, label)
        lines.made(task, **material(costs, "100.00", subproject_id=sent))
    found = read(api, stage)
    assert [
        (each["label"], value(each["amount"]), value(each["share"]))
        for each in found["by_subproject"]
    ] == [
        ("Armoires", "100.00", "0.3334"),
        ("Boîtiers", "100.00", "0.3333"),
        ("Câbles", "100.00", "0.3333"),
    ]
    assert sum(Decimal(value(each["share"]) or 0) for each in found["by_subproject"]) == 1
    assert sum(Decimal(value(each["amount"]) or 0) for each in found["by_subproject"]) == Decimal(
        value(found["total"]) or 0
    )
    lines.made(task, **material(costs, "100.00"))
    found = read(api, stage)
    assert [(each["key"] == "unassigned", each["label"]) for each in found["by_subproject"]] == [
        (False, "Armoires"),
        (False, "Boîtiers"),
        (False, "Câbles"),
        (True, None),
    ]
    assert {value(each["share"]) for each in found["by_subproject"]} == {"0.25"}


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_part_that_four_places_make_nought_is_given_to_its_first_significant_digit(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « la somme de leurs pourcentages vaut cent » : 0.01 against 10 000 000.00 is a share of
    # 0.000000001, never nought, the largest carrying the rest.
    task = tree.made("Fourniture")
    small = subproject(api, stage, "S", "Petit")
    large = subproject(api, stage, "L", "Grand")
    lines.made(task, **material(costs, "0.01", subproject_id=small))
    lines.made(task, **material(costs, "10000000.00", subproject_id=large))
    shares = {each["label"]: value(each["share"]) for each in read(api, stage)["by_subproject"]}
    assert shares == {"Petit": "0.000000001", "Grand": "0.999999999"}


# --- The work packages ------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_work_packages_are_absent_until_a_task_bears_them_then_total_their_subtree(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Sur un planning importé dont aucune tâche n'est rattachée à un lot, les totaux par lot sont
    # absents plutôt que nuls ; après rattachement d'une récapitulative au lot 1, son total
    # apparaît, et il vaut celui de son sous-arbre ; après rattachement d'une feuille à un lot, le
    # total de ce lot est le montant des lignes de cette feuille. » : a planning of tasks none
    # of which bears a work package, a summary task with two subtasks and a task apart.
    summary = tree.made("Études")
    cabling = tree.made("Câblage", parent_id=summary["node_id"])
    drawing = tree.made("Plans", parent_id=summary["node_id"])
    apart = tree.made("Livraison")
    lines.made(cabling, **labour(costs))
    lines.made(drawing, **material(costs))
    lines.made(apart, **material(costs, "50.00"))
    package, _ = work_breakdown(stage)
    before = read(api, stage)
    assert value(before["total"]) == "1050.00"
    assert len(before["by_work_package"]) == 2
    for each in before["by_work_package"]:
        assert (each["amount"]["value"], each["amount"]["reason"]) == (
            None,
            "work_package_without_task",
        )
        assert (each["share"]["value"], each["share"]["reason"]) == (
            None,
            "work_package_without_task",
        )
        assert each["amount"]["is_computable"] is False
    first = before["by_work_package"][0]["key"]
    assert before["by_work_package"][1]["key"] == str(package)
    # The import of EP-06 does not write `work_package_id`: the attachment is the one `updateNode`
    # makes, and it is the property proven here.
    tree.changed(tree.node(summary["node_id"]), work_package_id=first)
    after = by_label(read(api, stage)["by_work_package"])
    attached = next(each for each in after.values() if each["key"] == first)
    assert (value(attached["amount"]), value(attached["share"])) == ("1000.00", "0.9524")
    other = next(each for each in after.values() if each["key"] == str(package))
    assert other["amount"]["reason"] == "work_package_without_task"
    tree.changed(tree.node(apart["node_id"]), work_package_id=str(package))
    leaves = {each["key"]: each for each in read(api, stage)["by_work_package"]}
    assert value(leaves[first]["amount"]) == "1000.00"
    assert (value(leaves[str(package)]["amount"]), value(leaves[str(package)]["share"])) == (
        "50.00",
        "0.0476",
    )


# --- The rates ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0010-A")
def test_the_rates_a_category_lacks_are_named_and_the_amounts_that_depend_on_them_are_not_computed(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Le refus énumère les catégories de coût sans taux horaire pour l'année de référence. » :
    # the rate of the engineering withdrawn from the reference, `getMissingRates` names the
    # category and the year; the total, the nature of labour, the subproject and the work package
    # that carry its line, and the shares and differences that relate to the total, are not
    # computed (`hourly_rate_missing`, `params.missing_rates`); the material is, its share not.
    task = tree.made("Câblage")
    lines.made(task, **labour(costs))
    lines.made(task, **material(costs))
    assert rates(api, stage) == []
    package = read(api, stage)["by_work_package"][0]["key"]
    put_facts(stage, task["node_id"], work_package_id=UUID(package))
    unrate(stage, costs.labour)
    year = tree.revision["reference_year"]
    named = [{"cost_category_id": str(costs.labour), "label": "Ingénierie", "year": year}]
    assert rates(api, stage) == named
    assert rates(api, stage, f"?revision_id={tree.revision['revision_id']}") == named
    found = read(api, stage)
    expected = {"is_computable": False, "value": None, "reason": MISSING}
    assert found["total"] == {**expected, "params": {"missing_rates": named}}
    natures = by_label(found["by_cost_type"])
    assert natures["Main-d'œuvre"]["amount"] == {**expected, "params": {"missing_rates": named}}
    assert natures["Matériel"]["amount"] == {
        "is_computable": True,
        "value": "350.00",
        "reason": None,
    }
    assert natures["Matériel"]["share"] == {**expected, "params": {"missing_rates": named}}
    assert found["by_subproject"][0]["amount"]["reason"] == MISSING
    assert found["by_work_package"][0]["amount"]["reason"] == MISSING
    assert found["by_work_package"][0]["share"]["reason"] == MISSING
    assert found["delta_to_reference"] is None


@pytest.mark.requirement("WF-DEV-0010-A")
def test_the_calculation_succeeds_as_soon_as_the_rates_are_entered(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Le calcul aboutit dès que ces taux sont renseignés. » : after `setHourlyRate` the list is
    # empty and the amounts are computed again, to the cent the lines keep.
    task = tree.made("Câblage")
    lines.made(task, **labour(costs))
    unrate(stage, costs.labour)
    assert read(api, stage)["total"]["reason"] == MISSING
    with stage.database.transaction() as session:
        set_hourly_rate(session, (costs.labour, YEAR), Decimal("65.00"), None, Act(None, utc_now()))
    assert rates(api, stage) == []
    found = read(api, stage)
    assert found["total"] == {"is_computable": True, "value": "650.00", "reason": None}
    assert found["by_cost_type"][0]["share"] == {
        "is_computable": True,
        "value": "1",
        "reason": None,
    }


@pytest.mark.requirement("WF-DEV-0010-A")
def test_an_estimate_of_lines_outside_labour_is_computed_without_any_hourly_rate(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Un devis qui ne porte que des lignes hors main-d'œuvre et une ligne de provision se calcule
    # sans aucun taux horaire. » : the lines outside labour, here — the provision line is EP-08's,
    # the provisions identified being nought until it: no rate at all, nothing missing.
    task = tree.made("Fourniture")
    lines.made(task, **material(costs))
    unrate(stage, costs.labour)
    assert rates(api, stage) == []
    found = read(api, stage)
    assert found["total"] == {"is_computable": True, "value": "350.00", "reason": None}
    assert found["provisions_identified"] == "0.00"
    assert [(each["label"], value(each["amount"])) for each in found["by_cost_type"]] == [
        ("Matériel", "350.00")
    ]


# --- The revision, the scope, the differences, the context --------------------------------------


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_differences_are_the_estimate_read_minus_the_reference_and_the_marked_one_before(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « L'écart avec la révision de référence … » (WF-DEV-0060) : null without a reference and
    # without a marked revision before; then the estimate read minus theirs, positive when it
    # exceeds, the reference itself at nought; the revision named, else the current, else the last
    # one marked, `is_stored` false and the status in the context.
    task = tree.made("Câblage")
    lines.made(task, **labour(costs))
    current = read(api, stage)
    assert (current["delta_to_reference"], current["delta_to_previous_revision"]) == (None, None)
    assert current["context"]["revision_id"] == tree.revision["revision_id"]
    assert (current["context"]["revision_status"], current["context"]["is_stored"]) == (
        "draft",
        False,
    )
    assert current["context"]["scope"] == "project"
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    last = read(api, stage)
    assert last["context"]["revision_id"] == tree.revision["revision_id"]
    assert last["context"]["revision_status"] == "marked"
    assert last["delta_to_reference"] == {"is_computable": True, "value": "0.00", "reason": None}
    assert last["delta_to_previous_revision"] is None
    following = Tree(api, stage, opened(api, stage))
    added = Lines(following)
    bearer = next(item for item in following.items() if item["kind"] == "task")
    added.made(bearer, **material(costs))
    now = read(api, stage)
    assert now["context"]["revision_id"] == following.revision["revision_id"]
    assert value(now["total"]) == "1000.00"
    assert value(now["delta_to_reference"]) == "350.00"
    assert value(now["delta_to_previous_revision"]) == "350.00"
    named = read(api, stage, f"?revision_id={tree.revision['revision_id']}")
    assert value(named["total"]) == "650.00"
    assert named["context"]["revision_id"] == tree.revision["revision_id"]
    assert value(named["delta_to_reference"]) == "0.00"


@pytest.mark.requirement("WF-IND-0020-A")
def test_a_scope_counts_the_lines_of_the_subproject_alone_and_an_unknown_one_is_refused(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Restreint à un sous-projet (`scope`), chaque montant compte les lignes de ce sous-projet
    # seules » : the project, a subproject, the set out of any subproject; a subproject the project
    # does not have, or an identifier that is none, is refused on `/query/scope`.
    task = tree.made("Câblage")
    sent = subproject(api, stage, "CMD", "Poste de commande")
    lines.made(task, **labour(costs, subproject_id=sent))
    lines.made(task, **material(costs))
    assert value(read(api, stage)["total"]) == "1000.00"
    inside = read(api, stage, f"?scope={sent}")
    assert value(inside["total"]) == "650.00"
    assert inside["context"]["scope"] == sent
    assert [
        (each["key"], value(each["amount"]), value(each["share"]))
        for each in inside["by_subproject"]
    ] == [(sent, "650.00", "1")]
    assert [(each["label"], value(each["amount"])) for each in inside["by_cost_type"]] == [
        ("Main-d'œuvre", "650.00")
    ]
    outside = read(api, stage, "?scope=unassigned")
    assert (value(outside["total"]), outside["context"]["scope"]) == ("350.00", "unassigned")
    assert [each["key"] for each in outside["by_subproject"]] == ["unassigned"]
    assert read(api, stage, "?scope=project")["context"]["scope"] == "project"
    for unknown in (str(uuid4()), "ailleurs"):
        answer = api.get(path(stage) + f"?scope={unknown}", headers=stage.manager.headers)
        assert faults(answer) == [("/query/scope", "UNKNOWN_SUBPROJECT", {})]
        assert answer.json()["code"] == "VALIDATION_FAILED"


@pytest.mark.requirement("WF-DEV-0060-A")
@pytest.mark.usefixtures("tree")
def test_a_revision_that_is_not_the_projects_is_refused_by_both_operations(
    api: ContractClient, stage: Scene
) -> None:
    # The revision named is one of the project (404 otherwise); the rates are read likewise.
    for target in (path(stage), path(stage, "/missing-rates")):
        answer = api.get(f"{target}?revision_id={uuid4()}", headers=stage.manager.headers)
        assert refusal(answer)[:2] == (404, "NOT_FOUND")


# --- The order of the ventilations, the empty sums, the paths a rate or a nature changes ---------


@pytest.mark.requirement("WF-DEV-0060-A")
def test_the_ventilations_follow_the_order_of_the_identifiers_the_contract_shows(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The example of the contract lists the subprojects in the order of their identifiers — the
    # order of their creation — then `unassigned`, and the natures by their identifiers: not by
    # label. A nature created last whose label comes first, and a subproject likewise.
    act = Act(None, utc_now())
    with stage.database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("ACH", "Achats", "non_labor"), act)
        draft = CostCategoryDraft("ACH-001", "Achats divers", "606002", nature.cost_type_id)
        purchase = create_cost_category(session, draft, act).cost_category_id
    task = tree.made("Fourniture")
    for code, label in (("Z", "Zèbre"), ("A", "Alpha")):
        sent = subproject(api, stage, code, label)
        lines.made(task, **material(costs, "100.00", subproject_id=sent))
    lines.made(task, **material(costs, "10.00", cost_category_id=str(purchase)))
    lines.made(task, **labour(costs))
    found = read(api, stage)
    assert [each["label"] for each in found["by_subproject"]] == ["Zèbre", "Alpha", None]
    assert found["by_subproject"][-1]["key"] == "unassigned"
    assert [each["label"] for each in found["by_cost_type"]] == [
        "Main-d'œuvre",
        "Matériel",
        "Achats",
    ]


@pytest.mark.requirement("WF-DEV-0060-A")
def test_an_empty_sum_is_written_to_the_cent_and_a_nil_total_has_no_share(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # An estimate without a line totals "0.00"; a work package whose task bears no line too, its
    # share without a total; a total nil leaves its parts without a share (`no_total`).
    task = tree.made("Câblage")
    empty = read(api, stage)
    assert empty["total"] == {"is_computable": True, "value": "0.00", "reason": None}
    assert empty["by_cost_type"] == []
    tree.changed(tree.node(task["node_id"]), work_package_id=empty["by_work_package"][0]["key"])
    bare = read(api, stage)["by_work_package"][0]
    assert bare["amount"] == {"is_computable": True, "value": "0.00", "reason": None}
    assert bare["share"]["reason"] == "no_total"
    lines.made(task, **material(costs, "0.00"))
    nil = read(api, stage)
    assert value(nil["total"]) == "0.00"
    part = nil["by_cost_type"][0]
    assert value(part["amount"]) == "0.00"
    assert (part["share"]["value"], part["share"]["reason"]) == (None, "no_total")
    assert nil["by_subproject"][0]["share"]["reason"] == "no_total"


def missing_of(tree: Tree, costs: Costing) -> list[dict[str, Any]]:
    """Give the rate of the labour as the indicators name it when it is missing."""
    return [
        {
            "cost_category_id": str(costs.labour),
            "label": "Ingénierie",
            "year": tree.revision["reference_year"],
        }
    ]


@pytest.mark.requirement("WF-DEV-0010-A")
def test_the_differences_are_not_computed_while_a_rate_is_missing(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # Never a budget wrongly priced: with a reference and a marked revision before, the estimate
    # read lacking the rate of its labour has neither difference.
    task = tree.made("Câblage")
    lines.made(task, **material(costs))
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    following = Tree(api, stage, opened(api, stage))
    bearer = next(item for item in following.items() if item["kind"] == "task")
    Lines(following).made(bearer, **labour(costs))
    unrate(stage, costs.labour)
    found = read(api, stage)
    expected = {"is_computable": False, "value": None, "reason": MISSING}
    params = {"params": {"missing_rates": missing_of(following, costs)}}
    assert found["delta_to_reference"] == {**expected, **params}
    assert found["delta_to_previous_revision"] == {**expected, **params}


@pytest.mark.requirement("WF-DEV-0010-A")
def test_a_difference_with_a_revision_that_lacks_a_rate_is_not_computed(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The other revision of a difference is judged on its rates too: the reference, marked with
    # a labour line whose rate is gone, makes the difference not computable though the estimate
    # read, which bears no labour, is.
    task = tree.made("Câblage")
    lines.made(task, **labour(costs))
    unrate(stage, costs.labour)
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    following = Tree(api, stage, opened(api, stage))
    for item in following.items():
        if item["kind"] == "estimate_line":
            path_ = f"{following.path}/nodes/{item['node_id']}?lock_version={item['lock_version']}"
            gone = api.delete(path_, headers=stage.manager.headers)
            assert gone.status_code == 200, gone.text
    bearer = next(item for item in following.items() if item["kind"] == "task")
    Lines(following).made(bearer, **material(costs))
    found = read(api, stage)
    assert found["total"] == {"is_computable": True, "value": "350.00", "reason": None}
    expected = {"is_computable": False, "value": None, "reason": MISSING}
    params = {"params": {"missing_rates": missing_of(following, costs)}}
    assert found["delta_to_reference"] == {**expected, **params}
    assert found["delta_to_previous_revision"] == {**expected, **params}


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_marked_revision_is_read_on_the_natures_it_kept(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The nature of a category is read on the images of the revision marked: changed afterwards
    # in the settings, it stays what it was at the marking. The marking writes no image yet
    #: the image a marking keeps is written around the service, before it.
    lines.made(tree.made("Fourniture"), **material(costs))
    project_id, revision_id = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    with stage.owner.begin() as connection:
        labour_type = connection.scalar(
            select(CostCategory.cost_type_id).where(CostCategory.id == costs.labour)
        )
        material_type = connection.scalar(
            select(CostCategory.cost_type_id).where(CostCategory.id == costs.material)
        )
        image = {
            **imaged(project_id, revision_id),
            "cost_category_id": costs.material,
            "code": "MAT-001",
            "label": "Matériel électrique",
            "cost_type_id": material_type,
            "cost_type_label": "Matériel",
            "cost_type_kind": "non_labor",
            "cost_type_is_active": True,
            "accounting_code": "606001",
        }
        connection.execute(insert(RevisionCategory).values(**image))
    mark(stage, tree.revision)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostCategory)
            .where(CostCategory.id == costs.material)
            .values(cost_type_id=labour_type)
        )
    marked = read(api, stage)
    assert [(each["label"], value(each["amount"])) for each in marked["by_cost_type"]] == [
        ("Matériel", "350.00")
    ]


@pytest.mark.requirement("WF-DEV-0060-A")
def test_a_work_package_left_out_of_the_work_breakdown_is_totalled_if_a_marked_task_bears_it(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # A lot taken out of the work breakdown that a task of a revision marked still bears is
    # presented after those entered, under its label, with its total.
    task = tree.made("Câblage")
    lines.made(task, **material(costs))
    package, _ = work_breakdown(stage)
    tree.changed(tree.node(task["node_id"]), work_package_id=str(package))
    mark(stage, tree.revision)
    with stage.owner.begin() as connection:
        connection.execute(
            update(WorkPackage)
            .where(WorkPackage.id == package)
            .values(deleted_at=WorkPackage.created_at)
        )
    packages = read(api, stage)["by_work_package"]
    assert packages[-1]["key"] == str(package)
    assert (packages[-1]["label"], value(packages[-1]["amount"])) == ("Lot", "350.00")
    assert all(each["key"] != str(package) for each in packages[:-1])


@pytest.mark.requirement("WF-IND-0020-A")
def test_a_scope_restricts_the_work_packages_and_the_differences(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The scope retains the lines of a subproject for the work packages as for the differences:
    # the reference carries 650.00 of the subproject and 350.00 outside; the revision read adds
    # 100.00 in the subproject and 40.00 outside, so +100.00 in the scope, +140.00 over all.
    task = tree.made("Câblage")
    sent = subproject(api, stage, "CMD", "Poste de commande")
    lines.made(task, **labour(costs, subproject_id=sent))
    lines.made(task, **material(costs))
    package = read(api, stage)["by_work_package"][0]["key"]
    tree.changed(tree.node(task["node_id"]), work_package_id=package)
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    following = Tree(api, stage, opened(api, stage))
    added = Lines(following)
    bearer = next(item for item in following.items() if item["kind"] == "task")
    added.made(bearer, **material(costs, "100.00", subproject_id=sent))
    added.made(bearer, **material(costs, "40.00"))
    inside = read(api, stage, f"?scope={sent}")
    assert value(inside["total"]) == "750.00"
    assert value(inside["delta_to_reference"]) == "100.00"
    assert value(inside["delta_to_previous_revision"]) == "100.00"
    assert value(read(api, stage)["delta_to_reference"]) == "140.00"
    held = {each["key"]: each for each in inside["by_work_package"]}
    assert (value(held[package]["amount"]), value(held[package]["share"])) == ("750.00", "1")
    outside = read(api, stage, "?scope=unassigned")
    assert value(outside["by_work_package"][0]["amount"]) == "390.00"
