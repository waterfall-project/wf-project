# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit (US-1600).

``getRemainingIndicators`` on a project In progress (``remaining_support``): a reference of three
sets — the cabling, the tests and what no subproject bears — budgeted 1 000, 500 of actual cost
imported, a review marked In progress at 600 and a current revision at 550. The total and its
ventilation, the margin on the reference and the difference with the review before, the margin and
the zone of each subproject, the absent deltas, the revision read, the coverage at nought. The
margins of the module run without a base. Every answer is checked against the contract.

The socle (US-1580/L1) fixed the results EP-10 reads, which the first test keeps.
"""

from annotationlib import Format, get_annotations
from dataclasses import fields
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import cost, load_import
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, opened
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked
from sqlalchemy import update

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
)
from waterfall.core.costs.interface import UNASSIGNED
from waterfall.core.estimate.interface import (
    CalculationContext,
    Coverage,
    RemainingIndicators,
    RevisionRemaining,
    SubprojectBalance,
    register_coverage,
    remaining_indicators,
    remaining_of_revision,
)
from waterfall.core.estimate.remaining.balancing import (
    balances,
    delta_to_previous,
    delta_to_reference,
    distributed,
)
from waterfall.core.estimate.tables import EstimateLine
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

BASIS = "reestimated_amount_basis"
D = Decimal


def test_the_indicators_and_the_remaining_of_a_revision_answer_their_results() -> None:
    # What EP-10 reads from the socle on (EP-09, "Ce que le cadrage laisse à EP-10"): the results
    # are fixed; the margins are amounts, never absent (#2715), the zone one of two words.
    assert (
        get_annotations(remaining_indicators, format=Format.FORWARDREF)["return"]
        is RemainingIndicators
    )
    assert (
        get_annotations(remaining_of_revision, format=Format.FORWARDREF)["return"]
        is RevisionRemaining
    )
    assert [field.name for field in fields(RevisionRemaining)] == ["total", "by_line"]
    assert [field.name for field in fields(CalculationContext)] == [
        "revision_id",
        "revision_status",
        "computed_at",
        "scope",
        "is_stored",
    ]
    assert [field.name for field in fields(RemainingIndicators)] == [
        "context",
        "total",
        "by_cost_type",
        "by_subproject",
        "coverage",
        "delta_to_reference",
        "delta_to_previous_revision",
    ]
    assert [field.name for field in fields(SubprojectBalance)] == [
        "key",
        "label",
        "budget",
        "actual_cost",
        "remaining",
        "variance",
        "is_over_budget",
        "zone",
    ]
    held = get_annotations(SubprojectBalance, format=Format.STRING)
    assert (held["budget"], held["variance"], held["zone"]) == ("Decimal", "Decimal", "AlertZone")


# --- The margins, without a base ------------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_subproject_over_its_budget_is_signalled_and_the_others_are_not() -> None:
    # « Un sous-projet dont le coût réel augmenté du reste à engager dépasse son budget est
    # signalé par la couleur, les autres non. » Exactly at its budget, a subproject is not over.
    found = {
        each.key: each
        for each in balances(
            {"a": D(400), "b": D(300), UNASSIGNED: D(300)},
            {"a": D(200), "b": D(100), UNASSIGNED: D(200)},
            {"a": D(300), "b": D(150), UNASSIGNED: D(100)},
        )
    }
    assert [(each.variance, each.is_over_budget) for each in found.values()] == [
        (D(-100), True),
        (D(50), False),
        (D(0), False),
    ]


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_margins_of_the_subprojects_sum_to_that_of_the_project_unassigned_included() -> None:
    # « La marge sur le budget du projet égale la somme des marges de ses sous-projets, ensemble
    # hors sous-projet compris. » A subproject with a cost alone, none of the three naming another,
    # and the unassigned set always there, last.
    budgets = {"a": D(400), UNASSIGNED: D(300)}
    actual_costs = {"a": D(200), "c": D(70), UNASSIGNED: D(20)}
    remainings = {"a": D(300), "b": D(10)}
    found = balances(budgets, actual_costs, remainings)
    assert [each.key for each in found] == ["a", "b", "c", UNASSIGNED]
    assert sum(each.variance for each in found) == delta_to_reference(
        budgets, actual_costs, remainings
    )
    assert found[-1].variance == D(280)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_project_without_reference_has_no_margin_and_no_review_before_no_difference() -> None:
    # « … l'écart correspondant est absent plutôt que nul ; sur un projet sans révision de
    # référence, la marge sur le budget l'est aussi. » None, not nought; and a subproject without
    # budget has the amount nought, its margin the opposite of what it has committed (#2715).
    assert delta_to_reference(None, {UNASSIGNED: D(500)}, {UNASSIGNED: D(550)}) is None
    assert delta_to_reference({}, {}, {}) == D(0)
    assert delta_to_previous(D(550), None) is None
    assert delta_to_previous(D(550), D(550)) == D(0)
    [only] = balances({}, {UNASSIGNED: D(500)}, {UNASSIGNED: D(550)})
    assert (only.budget, only.variance, only.is_over_budget) == (D(0), D(-1050), True)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_ventilation_shares_sum_to_one_the_largest_carrying_the_remainder() -> None:
    # The shares of the module of the estimate: four decimal places, the sum exactly one.
    found = distributed({"a": D(1), "b": D(1), "c": D(1)}, {"a": "Un", "b": "Deux", "c": None})
    assert [(each.key, each.label, each.amount.value) for each in found] == [
        ("a", "Un", D(1)),
        ("b", "Deux", D(1)),
        ("c", None, D(1)),
    ]
    shares = [each.share.value for each in found]
    assert shares == [D("0.3334"), D("0.3333"), D("0.3333")]
    assert sum((share or D(0) for share in shares), D(0)) == D(1)
    nothing = distributed({"a": D(0)}, {})
    assert (nothing[0].share.value, nothing[0].share.reason) == (None, "no_total")


# --- The service ----------------------------------------------------------------------------------


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


def subproject(api: ContractClient, stage: Scene, code: str, label: str) -> str:
    """Create a subproject of the project of the stage; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]


def supplies(costs: Costing, label: str, amount: str, subproject_id: str | None) -> dict[str, Any]:
    """Give a line of supplies at the amount said, borne by a subproject or by none."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
        **({} if subproject_id is None else {"subproject_id": subproject_id}),
    }


def other_provision(stage: Scene) -> UUID:
    """Give a category of the provision kind, under a nature other than the one installed."""
    act = Act(None, utc_now())
    with stage.database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("RSV", "Réserve", "provision"), act)
        draft = CostCategoryDraft("RSV-001", "Réserve de risques", "606002", nature.cost_type_id)
        return create_cost_category(session, draft, act).cost_category_id


def reestimate(tree: Tree, label: str, amount: str, **extra: str) -> None:
    """Re-estimate the line of a label at the amount said, as the manager does."""
    line = line_named(tree, label)
    sent = {BASIS: {"unit_disbursement": amount}, "lock_version": line["lock_version"], **extra}
    path = f"{tree.path}/nodes/{line['node_id']}/remaining"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


@pytest.fixture
def cabling(api: ContractClient, stage: Scene) -> str:
    """Give the subproject of the cabling."""
    return subproject(api, stage, "SP-1", "Câblage")


@pytest.fixture
def testing(api: ContractClient, stage: Scene) -> str:
    """Give the subproject of the tests."""
    return subproject(api, stage, "SP-2", "Essais")


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing, cabling: str, testing: str) -> Review:
    """Give the project In progress, its reference budgeted 1 000 and its actual cost 500.

    The cabling at 400, the tests at 300, what no subproject bears at 300; 200, 100 and 200 of
    actual cost, the last imputed to the project alone by a line without code.
    """

    def build(tree: Tree, lines: Lines) -> None:
        lines.made(tree.made("Câblage"), **supplies(costs, "Fournitures", "400", cabling))
        lines.made(tree.made("Essais"), **supplies(costs, "Banc", "300", testing))
        lines.made(tree.made("Divers"), **supplies(costs, "Outillage", "300", None))

    found = in_progress(api, stage, build)
    load_import(
        stage,
        UUID(stage.project["project_id"]),
        [cost("A", "SP-1", "200.00"), cost("B", "SP-2", "100.00"), cost("C", None, "200.00")],
    )
    return found


@pytest.fixture
def reviewed(api: ContractClient, stage: Scene, review: Review) -> Tree:
    """Give the current revision at 550, after a review marked In progress at 600.

    The review reestimated the cabling to 250, the tests to 150, the rest to 200; the revision
    opened from it holds them, and brings the cabling to 300 and the rest to 100.
    """
    reestimate(review.tree, "Fournitures", "250")
    reestimate(review.tree, "Banc", "150")
    reestimate(review.tree, "Outillage", "200")
    review_marked(stage, review.tree.revision, "v2.0")
    current = Tree(api, stage, opened(api, stage))
    reestimate(current, "Fournitures", "300")
    reestimate(current, "Outillage", "100")
    return current


def indicators(
    api: ContractClient, stage: Scene, revision_id: str | None = None, expect: int = 200
) -> Any:
    """Read the indicators of the project, the revision named or the one the service picks."""
    query = "" if revision_id is None else f"?revision_id={revision_id}"
    answer = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/remaining-indicators{query}",
        headers=stage.manager.headers,
    )
    assert answer.status_code == expect, answer.text
    return answer.json()


def balance(body: dict[str, Any], key: str) -> dict[str, Any]:
    """Give the balance of a key of the subprojects of an answer."""
    return next(each for each in body["by_subproject"] if each["key"] == key)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_budget_1000_cost_500_remaining_550_give_a_margin_of_minus_50_and_a_difference_of_minus_50(
    api: ContractClient, stage: Scene, reviewed: Tree
) -> None:
    # « Sur un projet de budget 1 000, de coût réel 500 et de reste à engager 550, la marge sur le
    # budget vaut - 50 ; un reste à engager passé de 600 à 550 depuis la revue précédente donne un
    # écart de - 50. » The review before is the revision marked In progress at 600.
    body = indicators(api, stage)
    assert (body["total"], body["delta_to_reference"]) == ("550.00", "-50.00")
    assert body["delta_to_previous_revision"] == "-50.00"
    assert body["context"]["revision_id"] == reviewed.revision["revision_id"]
    assert (body["context"]["revision_status"], body["context"]["is_stored"]) == ("draft", False)
    assert body["context"]["scope"] == "project"
    with stage.database.transaction() as session:
        held = remaining_of_revision(
            session, UUID(stage.project["project_id"]), UUID(reviewed.revision["revision_id"])
        )
    assert held.total == D("550.00")


@pytest.mark.requirement("WF-RAE-0020-A")
@pytest.mark.usefixtures("reviewed")
def test_a_subproject_over_its_budget_is_in_alert_and_the_others_are_nominal(
    api: ContractClient, stage: Scene, cabling: str, testing: str
) -> None:
    # « Un sous-projet dont le coût réel augmenté du reste à engager dépasse son budget est
    # signalé par la couleur, les autres non. » The server classifies: the cabling, 200 and 300
    # against 400, is over; the tests and the set out of any subproject are not.
    body = indicators(api, stage)
    assert [each["key"] for each in body["by_subproject"]] == [
        *sorted([cabling, testing]),
        "unassigned",
    ]
    assert balance(body, cabling) == {
        "key": cabling,
        "label": "Câblage",
        "budget": "400.00",
        "actual_cost": "200.00",
        "remaining": "300.00",
        "variance": "-100.00",
        "is_over_budget": True,
        "zone": "alert",
    }
    assert balance(body, testing) == {
        "key": testing,
        "label": "Essais",
        "budget": "300.00",
        "actual_cost": "100.00",
        "remaining": "150.00",
        "variance": "50.00",
        "is_over_budget": False,
        "zone": "nominal",
    }
    # Exactly at its budget, the set out of any subproject is not over: 300 = 200 + 100.
    assert balance(body, "unassigned") == {
        "key": "unassigned",
        "budget": "300.00",
        "actual_cost": "200.00",
        "remaining": "100.00",
        "variance": "0.00",
        "is_over_budget": False,
        "zone": "nominal",
    }


@pytest.mark.requirement("WF-RAE-0020-A")
@pytest.mark.usefixtures("reviewed")
def test_the_margin_of_the_project_is_the_sum_of_those_of_its_subprojects_the_unassigned_included(
    api: ContractClient, stage: Scene
) -> None:
    # « La marge sur le budget du projet égale la somme des marges de ses sous-projets, ensemble
    # hors sous-projet compris. » The lines without a subproject and the line of cost imputed to
    # the project alone are the unassigned set; a cost whose code no subproject bears falls there.
    load_import(stage, UUID(stage.project["project_id"]), [cost("D", "SP-9", "30.00")])
    body = indicators(api, stage)
    assert balance(body, "unassigned")["actual_cost"] == "230.00"
    assert sum(D(each["variance"]) for each in body["by_subproject"]) == D(
        body["delta_to_reference"]
    )
    assert body["delta_to_reference"] == "-80.00"


@pytest.mark.requirement("WF-RAE-0020-A")
@pytest.mark.usefixtures("review")
def test_without_a_review_before_the_difference_is_null_and_without_a_reference_so_is_the_margin(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur un projet dont aucune révision n'a été marquée à l'état En cours avant celle qui est
    # lue, l'écart correspondant est absent plutôt que nul ; sur un projet sans révision de
    # référence, la marge sur le budget l'est aussi. » The reference was marked in pricing: an
    # offer is not a review; the current revision has a margin and no difference.
    body = indicators(api, stage)
    assert body["delta_to_previous_revision"] is None
    assert body["delta_to_reference"] == "-500.00"
    assert body["total"] == "1000.00"


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_project_without_a_reference_has_a_null_margin_and_budgets_of_nought(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « … sur un projet sans révision de référence, la marge sur le budget l'est aussi [absente]. »
    # The contract's ``Money`` of the budget and of the margin of a subproject is an amount: nought,
    # and the margin the opposite of what the set has committed (#2715).
    tree = Tree(api, stage, opened(api, stage))
    Lines(tree).made(tree.made("Câblage"), **supplies(costs, "Fournitures", "100", None))
    load_import(stage, UUID(stage.project["project_id"]), [cost("A", None, "50.00")])
    body = indicators(api, stage)
    assert (body["delta_to_reference"], body["delta_to_previous_revision"]) == (None, None)
    assert body["by_subproject"] == [
        {
            "key": "unassigned",
            "budget": "0.00",
            "actual_cost": "50.00",
            "remaining": "100.00",
            "variance": "-150.00",
            "is_over_budget": True,
            "zone": "alert",
        }
    ]


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_total_is_ventilated_by_nature_of_cost_in_shares_that_sum_to_one(
    api: ContractClient, stage: Scene, reviewed: Tree, costs: Costing
) -> None:
    # The total is the remaining of the lines of the tasks not completed; a labour line of 10 hours
    # at 65.00 makes it two natures, and the shares, four decimals, sum to one.
    Lines(reviewed).made(
        reviewed.made("Réglages"),
        label="Ajustage",
        quantity="1",
        resource_role_id=str(costs.role),
        hours="10",
    )
    body = indicators(api, stage)
    assert body["total"] == "1200.00"
    by_type = {each["label"]: each for each in body["by_cost_type"]}
    assert by_type["Matériel"]["amount"] == "550.00"
    assert D(by_type["Matériel"]["share"]["value"]) + D(
        next(each["share"]["value"] for label, each in by_type.items() if label != "Matériel")
    ) == D(1)
    assert sum(D(each["amount"]) for each in body["by_cost_type"]) == D(body["total"])
    assert all(each["share"]["is_computable"] for each in body["by_cost_type"])


def reference_with(
    api: ContractClient, stage: Scene, costs: Costing, cabling: str, **values: Any
) -> Review:
    """Give the project In progress, its reference built as ``review`` is, a line of it written.

    The line "Fournitures" (cabling, 400) of the reference gets the columns said, written around
    the service before the reference is marked: no reference writes a budgeted amount of its own.
    """

    def build(tree: Tree, lines: Lines) -> None:
        lines.made(tree.made("Câblage"), **supplies(costs, "Fournitures", "400", cabling))
        lines.made(tree.made("Divers"), **supplies(costs, "Outillage", "300", None))
        node_id = UUID(line_named(tree, values.pop("label"))["node_id"])
        with stage.owner.begin() as connection:
            connection.execute(
                update(EstimateLine).where(EstimateLine.node_id == node_id).values(**values)
            )

    return in_progress(api, stage, build)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_nature_provision_is_served_at_nought_and_left_out_of_the_total(
    api: ContractClient, stage: Scene, reviewed: Tree, costs: Costing
) -> None:
    # « … la nature provision à zéro » : a provision line of the revision (its category of the
    # provision kind, put around the service as the risks of EP-08 will), in a task started or not,
    # figures with an amount of nought and a share of nought, and the total leaves it out. A second
    # one, of another nature, under a task completed, is served at nought too, whatever the state
    # of its task.
    Lines(reviewed).made(reviewed.made("Risques"), **supplies(costs, "Aléa", "900", None))
    Lines(reviewed).made(reviewed.made("Clos"), **supplies(costs, "Réserve", "700", None))
    # The task is completed while its line is still of material: a line of provision is no longer
    # reestimated, and the category is changed under the service afterwards.
    reestimate(reviewed, "Réserve", "0", completed_on="2026-06-03")
    reserve_category = other_provision(stage)
    for label, category in (("Aléa", costs.provision), ("Réserve", reserve_category)):
        with stage.owner.begin() as connection:
            connection.execute(
                update(EstimateLine)
                .where(EstimateLine.node_id == UUID(line_named(reviewed, label)["node_id"]))
                .values(cost_category_id=category)
            )
    body = indicators(api, stage)
    assert body["total"] == "550.00"
    by_type = {each["label"]: each for each in body["by_cost_type"]}
    assert len(by_type) == 3
    held = [each for label, each in by_type.items() if label != "Matériel"]
    assert [each["amount"] for each in held] == ["0.00", "0.00"]
    shares = [D(each["share"]["value"]) for each in (by_type["Matériel"], *held)]
    assert shares == [D(1), D(0), D(0)]
    assert sum(D(each["amount"]) for each in body["by_cost_type"]) == D(body["total"])


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_budget_of_the_reference_reads_its_budgeted_amounts_not_its_reestimated(
    api: ContractClient, stage: Scene, costs: Costing, cabling: str
) -> None:
    # « … le budget de la référence … » : a line of the reference budgeted 450 and reestimated 999
    # counts 450; with the 300 of the other line, the budget is 750 and the cabling holds 450.
    reference_with(
        api,
        stage,
        costs,
        cabling,
        label="Fournitures",
        budgeted_amount=D("450.00"),
        reestimated_amount=D(999),
    )
    body = indicators(api, stage)
    assert balance(body, cabling)["budget"] == "450.00"
    assert sum(D(each["budget"]) for each in body["by_subproject"]) == D("750.00")


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_provision_line_of_the_reference_is_left_out_of_its_budget(
    api: ContractClient, stage: Scene, costs: Costing, cabling: str
) -> None:
    # « … provisions exclues » (WF-IND-0020) : the outlay line of the reference, put in the
    # provision kind, leaves a budget of 400 and none to what no subproject bears.
    reference_with(api, stage, costs, cabling, label="Outillage", cost_category_id=costs.provision)
    body = indicators(api, stage)
    assert balance(body, "unassigned")["budget"] == "0.00"
    assert sum(D(each["budget"]) for each in body["by_subproject"]) == D("400.00")


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_lines_of_the_tasks_completed_count_for_nought_and_ventilate_nothing(
    api: ContractClient, stage: Scene, reviewed: Tree
) -> None:
    # « … le reste à engager … somme des réestimés des lignes des tâches non terminées » : every
    # line set to nought completes its task, the total is nought and nothing is left to ventilate;
    # the subprojects keep their budget and their actual cost, and a remaining of nought.
    for label in ("Fournitures", "Banc", "Outillage"):
        reestimate(reviewed, label, "0", completed_on="2026-06-03")
    body = indicators(api, stage)
    assert (body["total"], body["by_cost_type"]) == ("0.00", [])
    assert body["delta_to_reference"] == "500.00"
    assert body["delta_to_previous_revision"] == "-600.00"
    assert sum(D(each["remaining"]) for each in body["by_subproject"]) == D(0)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_revision_named_is_read_else_the_current_one_else_the_last_one_marked(
    api: ContractClient, stage: Scene, reviewed: Tree, review: Review
) -> None:
    # « getRemainingIndicators lit la révision nommée, ou la révision en cours, ou la dernière
    # marquée sans elle. » The reference, marked in pricing, is read at its 1 000 with no review
    # before; the review marked In progress at 600, with the margin of its time.
    named = indicators(api, stage, review.reference["revision_id"])
    assert (named["total"], named["context"]["revision_status"]) == ("1000.00", "marked")
    assert (named["delta_to_previous_revision"], named["delta_to_reference"]) == (None, "-500.00")
    marked = indicators(api, stage, review.tree.revision["revision_id"])
    assert (marked["total"], marked["context"]["revision_status"]) == ("600.00", "marked")
    assert (marked["delta_to_previous_revision"], marked["delta_to_reference"]) == (None, "-100.00")
    # The current revision is marked in its turn: no revision is current, the last marked is read,
    # with the review before it.
    review_marked(stage, reviewed.revision, "v3.0")
    last = indicators(api, stage)
    assert last["context"]["revision_id"] == reviewed.revision["revision_id"]
    assert (last["total"], last["delta_to_previous_revision"]) == ("550.00", "-50.00")


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_revision_unknown_or_of_another_project_is_not_found(
    api: ContractClient, stage: Scene, review: Review
) -> None:
    # The revision named belongs to the project; no revision at all is none to read.
    indicators(api, stage, str(uuid4()), expect=404)
    other = create(api, stage.manager, label="Autre projet")
    answer = api.get(
        f"{PROJECTS}/{other['project_id']}/remaining-indicators"
        f"?revision_id={review.reference['revision_id']}",
        headers=stage.manager.headers,
    )
    assert answer.status_code == 404, answer.text


@pytest.mark.requirement("WF-RAE-0020-A")
@pytest.mark.usefixtures("reviewed")
def test_the_coverage_is_nought_until_the_risks_answer_and_then_what_they_say(
    api: ContractClient, stage: Scene
) -> None:
    # « La couverture des risques présente la réserve de référence, … » : an écart vers EP-08. The
    # coverage is nought while nothing answers, whatever the project holds; the answer registered
    # is served as it is, then withdrawn.
    nought = {
        "reserve": "0.00",
        "remaining_provisions": "0.00",
        "occurred_cost": "0.00",
        "occurred_reestimated": "0.00",
        "coverage_variance": "0.00",
    }
    assert indicators(api, stage)["coverage"] == nought

    def answer(_session: Session, _project_id: UUID, _revision_id: UUID) -> Coverage:
        return Coverage(D("850.00"), D("750.00"), D("200.00"), D("210.00"), D("-100.00"))

    withdraw = register_coverage(answer)
    try:
        served = indicators(api, stage)["coverage"]
    finally:
        withdraw()
    assert served == {
        "reserve": "850.00",
        "remaining_provisions": "750.00",
        "occurred_cost": "200.00",
        "occurred_reestimated": "210.00",
        "coverage_variance": "-100.00",
    }
    assert indicators(api, stage)["coverage"] == nought
