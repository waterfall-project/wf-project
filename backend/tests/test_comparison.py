# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (US-1530).

``compareRevisions`` reads two marked revisions matched by lineage, as ``listNodes`` reads a
structure: the tree of the compared one in the order of the plan, each node marked, the removed
ones at the place they had, read-only; the totals and the meta of the compared one; and the
differences of the amounts by nature and by subproject, each line under the key it carries in each
revision (#1751). A first revision — two summary tasks, three tasks under them and one beside, a
line under each — is marked; the next one, copied from it, changes a line's subproject, another's
category, a third's hours, moves a task under the other summary, adds a task with its line and
deletes the task beside, and is marked. Every answer is checked against the contract.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file; US-1530 writes
its tests here ("Les tests du back").
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import YEAR, Costing, Lines, costing
from nodes_support import Tree, opened, refusal, set_progress
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
)
from waterfall.core.cost_settings.tables import CostType
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REQUIREMENT = "WF-REV-0080-A"
# An instant of the year after the one the first revision is priced at.
LATER = datetime(YEAR + 1, 1, 12, 10, tzinfo=UTC)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated 65.00 this year."""
    return costing(stage.database)


def mark(stage: Scene, revision: dict[str, Any], version: str) -> None:
    """Mark a revision by the transaction of the worker, under a version of its own."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        mark_revision(session, UUID(revision["revision_id"]), version, None, Act(None, utc_now()))


def subcontracting(database: Database) -> UUID:
    """Add a nature of subcontracting, which is no labour, and a category of it; give the latter."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("ST", "Sous-traitance", "non_labor"), act)
        draft = CostCategoryDraft("ST-001", "Études sous-traitées", "604001", nature.cost_type_id)
        return create_cost_category(session, draft, act).cost_category_id


def subproject(api: ContractClient, stage: Scene, code: str, label: str) -> str:
    """Create a subproject of the project, as the manager does; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]


def labour(costs: Costing, label: str, hours: str = "10") -> dict[str, Any]:
    """Give a labour line: one engineer at 65.00 an hour, ten hours unless said."""
    return {"label": label, "quantity": "1", "resource_role_id": str(costs.role), "hours": hours}


def material(costs: Costing, label: str, amount: str) -> dict[str, Any]:
    """Give a line of material: one at the amount said."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def label_of(item: dict[str, Any]) -> str:
    """Give the label of a node returned: its task's, or its line's."""
    facet = item.get("task") or item.get("estimate_line")
    assert facet is not None
    return facet["label"]


def by_label(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Give the nodes returned by their label."""
    return {label_of(each): each for each in items}


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def comparison(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], dict[str, Any]], query: str = ""
) -> Any:
    """Ask for the comparison of two revisions, as the manager does; give the answer."""
    base, compared = pair
    path = (
        f"{PROJECTS}/{stage.project['project_id']}/revisions/comparison"
        f"?from_revision_id={base['revision_id']}&to_revision_id={compared['revision_id']}{query}"
    )
    return api.get(path, headers=stage.manager.headers)


def compared(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], dict[str, Any]], query: str = ""
) -> dict[str, Any]:
    """Compare two revisions, which must be compared; give the comparison."""
    answer = comparison(api, stage, pair, query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def marks(found: dict[str, Any]) -> list[tuple[str, int, str, list[str]]]:
    """Give each node returned by its label, its level, its mark and what changes of it."""
    return [
        (label_of(each), each["level"], each["difference"], each["changes"])
        for each in found["items"]
    ]


def deltas(found: dict[str, Any]) -> dict[tuple[str, str | None], tuple[str, str]]:
    """Give the differences of amounts by dimension and label."""
    return {
        (each["dimension"], each["label"]): (each["budgeted_delta"], each["reestimated_delta"])
        for each in found["amount_deltas"]
    }


@dataclass(frozen=True)
class Pair:
    """Two revisions marked, the second copied from the first and changed; what they name."""

    offer: dict[str, Any]
    amendment: dict[str, Any]
    offer_tree: Tree
    amendment_tree: Tree
    subproject_id: str


@pytest.fixture
def pair(api: ContractClient, stage: Scene, costs: Costing) -> Pair:
    """Mark an offer, then an amendment that changes, moves, adds and removes its nodes."""
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    lines = Lines(tree)
    studies = tree.made("Études")
    design = tree.made("Conception", parent_id=studies["node_id"])
    lines.made(design, **labour(costs, "Conception — Ingénieur"))
    plans = tree.made("Plans", parent_id=studies["node_id"])
    lines.made(plans, **material(costs, "Tirages", "350.00"))
    site = tree.made("Installation")
    mounting = tree.made("Montage", parent_id=site["node_id"])
    lines.made(mounting, **labour(costs, "Montage — Ingénieur", "20"))
    acceptance = tree.made("Réception")
    lines.made(acceptance, **material(costs, "Banc d'essais", "100.00"))
    mark(stage, offer, "v1.0")
    other_category = subcontracting(stage.database)
    sent = subproject(api, stage, "CMD", "Poste de commande")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    changing = Lines(following)
    nodes = by_label(following.items())
    changing.changed(nodes["Conception — Ingénieur"], subproject_id=sent)
    changing.changed(nodes["Tirages"], cost_category_id=str(other_category))
    changing.changed(nodes["Montage — Ingénieur"], hours="30")
    gone = nodes["Réception"]
    path = f"{following.path}/nodes/{gone['node_id']}?lock_version={gone['lock_version']}"
    assert api.delete(path, headers=stage.manager.headers).status_code == 200
    moving = {
        "node_ids": [nodes["Plans"]["node_id"]],
        "parent_id": nodes["Installation"]["node_id"],
        "lock_version": counter(following),
    }
    moved = api.post(f"{following.path}/nodes/move", headers=stage.manager.headers, json=moving)
    assert moved.status_code == 200, moved.text
    wiring = following.made("Câblage", parent_id=nodes["Installation"]["node_id"])
    changing.made(wiring, **material(costs, "Câbles", "200.00"))
    mark(stage, amendment, "v2.0")
    return Pair(offer, amendment, tree, following, sent)


def revisions(pair: Pair) -> tuple[dict[str, Any], dict[str, Any]]:
    """Give the offer and the amendment, the base and the compared revision."""
    return pair.offer, pair.amendment


# --- The tree and its marks -----------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_the_tree_of_the_compared_revision_is_marked_node_by_node_the_removed_ones_in_place(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # The tree of the compared revision in the order of the plan, each node marked by lineage: a
    # line by its amounts, its subproject or its category; a task added with its line; the task
    # deleted and its line at the place they had, last, read-only; the summaries whose content
    # changes modified, their own values unchanged.
    found = compared(api, stage, revisions(pair))
    assert marks(found) == [
        ("Études", 1, "modified", []),
        ("Conception", 2, "modified", []),
        ("Conception — Ingénieur", 3, "modified", ["subproject"]),
        ("Installation", 1, "modified", []),
        ("Montage", 2, "modified", []),
        ("Montage — Ingénieur", 3, "modified", ["budgeted_amount", "reestimated_amount"]),
        ("Plans", 2, "modified", ["parent"]),
        ("Tirages", 3, "modified", ["cost_category"]),
        ("Câblage", 2, "added", []),
        ("Câbles", 3, "added", []),
        ("Réception", 1, "removed", []),
        ("Banc d'essais", 2, "removed", []),
    ]
    assert [each["row_number"] for each in found["items"]] == list(range(1, 13))
    removed = by_label(found["items"])
    offer = by_label(pair.offer_tree.items())
    assert removed["Réception"]["node_id"] == offer["Réception"]["node_id"]
    assert removed["Réception"]["position"] == 3
    assert removed["Banc d'essais"]["parent_id"] == offer["Réception"]["node_id"]
    assert removed["Réception"]["editable_fields"] == []
    assert removed["Banc d'essais"]["editable_fields"] == []


@pytest.mark.requirement(REQUIREMENT)
def test_a_task_moved_under_another_summary_is_presented_modified_and_both_summaries_too(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » : returned once,
    # at its new place, ``parent`` among its changes; the summary it left and the one it joined,
    # modified by their content.
    found = by_label(compared(api, stage, revisions(pair))["items"])
    plans = found["Plans"]
    assert (plans["difference"], plans["changes"]) == ("modified", ["parent"])
    assert plans["parent_id"] == found["Installation"]["node_id"]
    assert found["Études"]["difference"] == found["Installation"]["difference"] == "modified"
    labels = [label_of(each) for each in compared(api, stage, revisions(pair))["items"]]
    assert labels.count("Plans") == 1


@pytest.mark.requirement(REQUIREMENT)
def test_a_task_is_modified_by_its_dates_its_duration_and_its_state(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « pour une tâche, ses dates, sa durée, son état et son parent » : a task lengthened and
    # started between the two revisions, the other untouched.
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    longer = tree.made("Câblage")
    Lines(tree).made(longer, **labour(costs, "Câblage — Ingénieur"))
    tree.made("Essais")
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    nodes = by_label(following.items())
    following.changed(nodes["Câblage"], duration={"value": "5", "unit": "d"})
    set_progress(stage, nodes["Câblage"]["node_id"], "started", date(2026, 11, 2))
    mark(stage, amendment, "v2.0")
    found = by_label(compared(api, stage, (offer, amendment))["items"])
    assert found["Câblage"]["changes"] == ["dates", "duration", "progress"]
    assert (found["Essais"]["difference"], found["Essais"]["changes"]) == ("unchanged", [])
    # Its line, at the same amounts, its hours spread over the same year: unchanged.
    assert (
        found["Câblage — Ingénieur"]["difference"],
        found["Câblage — Ingénieur"]["changes"],
    ) == (
        "unchanged",
        [],
    )


def follow(tree: Tree, node: dict[str, Any], predecessor: dict[str, Any]) -> None:
    """Make a task follow another, finish to start, through the service."""
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": predecessor["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": node["lock_version"],
    }
    path = f"{tree.path}/nodes/{node['node_id']}/predecessors"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement(REQUIREMENT)
def test_the_predecessors_are_numbered_in_the_union_a_removed_task_naming_the_compared_node(
    api: ContractClient, stage: Scene
) -> None:
    # A removed node occupies its row: the predecessor of a task after it is numbered in the union,
    # and that of the removed task named by the node of its lineage in the compared revision.
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    preparing = tree.made("Préparation")
    follow(tree, tree.made("Essais"), preparing)
    receiving = tree.made("Recette")
    follow(tree, tree.made("Clôture"), receiving)
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    gone = by_label(following.items())["Essais"]
    path = f"{following.path}/nodes/{gone['node_id']}?lock_version={gone['lock_version']}"
    assert api.delete(path, headers=stage.manager.headers).status_code == 200
    mark(stage, amendment, "v2.0")
    found = compared(api, stage, (offer, amendment))
    nodes = by_label(found["items"])
    assert [(label_of(each), each["difference"]) for each in found["items"]] == [
        ("Préparation", "unchanged"),
        ("Essais", "removed"),
        ("Recette", "unchanged"),
        ("Clôture", "unchanged"),
    ]
    named = [
        (each["predecessor_node_id"], each["predecessor_row_number"])
        for label in ("Essais", "Clôture")
        for each in nodes[label]["predecessors"]
    ]
    assert named == [(nodes["Préparation"]["node_id"], 1), (nodes["Recette"]["node_id"], 3)]


@pytest.mark.requirement(REQUIREMENT)
def test_an_identical_pair_returns_every_node_unchanged_and_no_amount_difference(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # A revision compared with itself: every node unchanged, the totals and the meta of the
    # revision as ``listNodes`` reads them, no difference of amount; never a refusal.
    found = compared(api, stage, (pair.offer, pair.offer))
    read = pair.offer_tree.read()
    assert read.status_code == 200, read.text
    listed = read.json()
    assert {each["difference"] for each in found["items"]} == {"unchanged"}
    assert {tuple(each["changes"]) for each in found["items"]} == {()}
    assert [each["node_id"] for each in found["items"]] == [
        each["node_id"] for each in listed["items"]
    ]
    assert (found["totals"], found["meta"]) == (listed["totals"], listed["meta"])
    assert found["amount_deltas"] == []


# --- The amounts --------------------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_each_line_counts_under_the_key_it_carries_in_each_revision(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # #1751: a line whose subproject changes counts its 650.00 out of « hors sous-projet » and into
    # the subproject, its amount unchanged; one whose category changes nature, its 350.00 out of the
    # material and into the subcontracting; the hours of a third, 650.00 more; the line added,
    # 200.00, the line removed, 100.00 less. Without a reference, the budgeted amount is read as
    # the re-estimated one. The sum by subproject equals the sum by nature.
    found = compared(api, stage, revisions(pair))
    assert deltas(found) == {
        ("cost_type", "Main-d'œuvre"): ("650.00", "650.00"),
        ("cost_type", "Matériel"): ("-250.00", "-250.00"),
        ("cost_type", "Sous-traitance"): ("350.00", "350.00"),
        ("subproject", "Poste de commande"): ("650.00", "650.00"),
        ("subproject", None): ("100.00", "100.00"),
    }
    keyed = {(each["dimension"], each["label"]): each["key"] for each in found["amount_deltas"]}
    assert keyed[("subproject", None)] == "unassigned"
    assert keyed[("subproject", "Poste de commande")] == pair.subproject_id
    for dimension in ("cost_type", "subproject"):
        summed = sum(
            Decimal(each["reestimated_delta"])
            for each in found["amount_deltas"]
            if each["dimension"] == dimension
        )
        assert summed == Decimal("750.00")


@pytest.mark.requirement(REQUIREMENT)
def test_a_key_whose_two_differences_are_nought_is_left_out(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # A line moved under another task, its amount unchanged, nets nought under its keys: they are
    # omitted, and the comparison of the two revisions presents no difference of amount.
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    lines = Lines(tree)
    lines.made(tree.made("Câblage"), **material(costs, "Câbles", "200.00"))
    tree.made("Essais")
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    nodes = by_label(following.items())
    moving = {
        "node_ids": [nodes["Câbles"]["node_id"]],
        "parent_id": nodes["Essais"]["node_id"],
        "lock_version": counter(following),
    }
    moved = api.post(f"{following.path}/nodes/move", headers=stage.manager.headers, json=moving)
    assert moved.status_code == 200, moved.text
    mark(stage, amendment, "v2.0")
    found = compared(api, stage, (offer, amendment))
    assert found["amount_deltas"] == []
    assert marks(found) == [
        ("Câblage", 1, "modified", []),
        ("Essais", 1, "modified", []),
        ("Câbles", 2, "modified", ["parent"]),
    ]


@pytest.mark.requirement(REQUIREMENT)
def test_the_revisions_are_read_on_the_natures_they_kept(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # The nature of a category is read on the images of each revision: renamed in the reference
    # after both markings, the material keeps the label it had.
    with stage.database.transaction() as session:
        session.execute(update(CostType).where(CostType.code == "MAT").values(label="Fournitures"))
    found = compared(api, stage, revisions(pair))
    assert ("cost_type", "Matériel") in deltas(found)
    assert ("cost_type", "Fournitures") not in deltas(found)


@pytest.mark.requirement(REQUIREMENT)
def test_between_two_reference_years_only_the_re_estimated_amounts_differ_by_the_rates(
    api: ContractClient, stage: Scene, costs: Costing, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Entre deux révisions d'années de référence différentes, les montants réestimés diffèrent
    # en outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu'à la nouvelle année
    # de référence (WF-REV-0060) ; les tâches et les montants budgétés restent [les mêmes]. » :
    # the offer designated the reference, the next revision opened the next year at a rate of
    # inflation of 3 %, its rate projected, and marked; the tasks unchanged, no budgeted
    # difference, the labour line modified by its re-estimated amount alone (#1754).
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    Lines(tree).made(tree.made("Câblage"), **labour(costs, "Câblage — Ingénieur"))
    mark(stage, offer, "v1.0")
    designate(api, stage, offer)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    monkeypatch.setattr("waterfall.api.revisions.utc_now", lambda: LATER)
    amendment = opened(api, stage)
    assert amendment["reference_year"] == YEAR + 1
    following = Tree(api, stage, amendment)
    mark(stage, amendment, "v2.0")
    found = compared(api, stage, (offer, amendment))
    before = by_label(tree.items())["Câblage — Ingénieur"]["estimate_line"]
    after = by_label(following.items())["Câblage — Ingénieur"]["estimate_line"]
    line = by_label(found["items"])["Câblage — Ingénieur"]
    assert before["budgeted_amount"] == after["budgeted_amount"]
    assert before["reestimated_amount"] != after["reestimated_amount"]
    assert (line["difference"], line["changes"]) == ("modified", ["reestimated_amount"])
    assert by_label(found["items"])["Câblage"]["changes"] == []
    moved = Decimal(after["reestimated_amount"]) - Decimal(before["reestimated_amount"])
    assert deltas(found) == {
        ("cost_type", "Main-d'œuvre"): ("0.00", str(moved)),
        ("subproject", None): ("0.00", str(moved)),
    }


# --- The reading, as listNodes reads a structure -------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_the_totals_and_the_meta_are_those_of_the_compared_revision(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # The totals of the compared revision, without the removed nodes, and its meta, as
    # ``listNodes`` reads it; ``difference`` does not restrict them.
    listed = pair.amendment_tree.read().json()
    for query in ("", "&difference=added"):
        found = compared(api, stage, revisions(pair), query)
        assert (found["totals"], found["meta"]) == (listed["totals"], listed["meta"])
        assert found["from_revision_id"] == pair.offer["revision_id"]
        assert found["to_revision_id"] == pair.amendment["revision_id"]


@pytest.mark.requirement(REQUIREMENT)
def test_difference_keeps_the_marks_named_their_ancestors_and_their_amounts_alone(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # « Différences seules » : the nodes added and removed, each judged on its own mark, with their
    # ancestors; the differences of amounts of the lines it retains alone.
    found = compared(api, stage, revisions(pair), "&difference=added,removed")
    assert marks(found) == [
        ("Installation", 1, "modified", []),
        ("Câblage", 2, "added", []),
        ("Câbles", 3, "added", []),
        ("Réception", 1, "removed", []),
        ("Banc d'essais", 2, "removed", []),
    ]
    assert deltas(found) == {
        ("cost_type", "Matériel"): ("100.00", "100.00"),
        ("subproject", None): ("100.00", "100.00"),
    }
    modified = compared(api, stage, revisions(pair), "&difference=modified")
    labels = [label_of(each) for each in modified["items"]]
    assert "Conception — Ingénieur" in labels
    assert "Câbles" not in labels
    refused = comparison(api, stage, revisions(pair), "&difference=unchanged")
    assert refused.status_code == 422, refused.text


@pytest.mark.requirement(REQUIREMENT)
def test_a_subtree_is_a_window_onto_the_union_a_removed_task_included(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # ``subtree_of`` a task of the compared revision: its subtree, the line moved into it counting
    # its whole difference there; of a removed task: its removed nodes, zero totals, and the
    # differences of its removed line.
    found = compared(api, stage, revisions(pair))
    nodes = by_label(found["items"])
    site = compared(api, stage, revisions(pair), f"&subtree_of={nodes['Installation']['node_id']}")
    assert [label_of(each) for each in site["items"]] == [
        "Installation",
        "Montage",
        "Montage — Ingénieur",
        "Plans",
        "Tirages",
        "Câblage",
        "Câbles",
    ]
    assert deltas(site) == {
        ("cost_type", "Main-d'œuvre"): ("650.00", "650.00"),
        ("cost_type", "Matériel"): ("-150.00", "-150.00"),
        ("cost_type", "Sous-traitance"): ("350.00", "350.00"),
        ("subproject", None): ("850.00", "850.00"),
    }
    gone = compared(api, stage, revisions(pair), f"&subtree_of={nodes['Réception']['node_id']}")
    assert marks(gone) == [
        ("Réception", 1, "removed", []),
        ("Banc d'essais", 2, "removed", []),
    ]
    assert (gone["totals"]["estimate_line_count"], gone["totals"]["reestimated_amount"]) == (
        0,
        "0.00",
    )
    assert deltas(gone) == {
        ("cost_type", "Matériel"): ("-100.00", "-100.00"),
        ("subproject", None): ("-100.00", "-100.00"),
    }


@pytest.mark.requirement(REQUIREMENT)
def test_kinds_search_fields_and_a_column_filter_read_the_comparison_as_list_nodes(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # The parameters of ``listNodes``: ``kinds`` chooses what is returned, the amounts counted
    # whatever it is; the search retains a removed task on its label in the base revision; a bound
    # on an amount judges a removed line on its own; ``fields`` names what is returned of each node,
    # its mark always; a bound refused as ``listNodes`` refuses it.
    whole = compared(api, stage, revisions(pair))
    tasks = compared(api, stage, revisions(pair), "&kinds=task")
    assert [label_of(each) for each in tasks["items"]] == [
        "Études",
        "Conception",
        "Installation",
        "Montage",
        "Plans",
        "Câblage",
        "Réception",
    ]
    assert tasks["amount_deltas"] == whole["amount_deltas"]
    searched = compared(api, stage, revisions(pair), "&search=Récep")
    assert marks(searched) == [
        ("Réception", 1, "removed", []),
        ("Banc d'essais", 2, "removed", []),
    ]
    bounded = compared(api, stage, revisions(pair), "&reestimated_amount_max=150")
    assert [label_of(each) for each in bounded["items"] if each["kind"] == "estimate_line"] == [
        "Banc d'essais"
    ]
    chosen = compared(api, stage, revisions(pair), "&fields=task.label,estimate_line.label")
    first = chosen["items"][0]
    assert set(first) == {
        "node_id",
        "row_number",
        "level",
        "lock_version",
        "task",
        "difference",
        "changes",
    }
    assert first["task"] == {"label": "Études"}
    inverted = comparison(
        api, stage, revisions(pair), "&reestimated_amount_min=10&reestimated_amount_max=5"
    )
    assert inverted.status_code == 422, inverted.text
    assert inverted.json()["fields"][0]["pointer"] == "/query/reestimated_amount_max"


@pytest.mark.requirement(REQUIREMENT)
def test_the_sort_orders_the_lines_under_each_task_a_removed_one_among_them(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # The sort of the lines, a removed line ordered on its own values among those of its task;
    # without the sort, the removed line stays at the place it had.
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    lines = Lines(tree)
    task = tree.made("Fourniture")
    lines.made(task, **material(costs, "Armoire", "500.00"))
    lines.made(task, **material(costs, "Borniers", "50.00"))
    lines.made(task, **material(costs, "Câbles", "200.00"))
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    gone = by_label(following.items())["Borniers"]
    path = f"{following.path}/nodes/{gone['node_id']}?lock_version={gone['lock_version']}"
    assert api.delete(path, headers=stage.manager.headers).status_code == 200
    mark(stage, amendment, "v2.0")
    plain = compared(api, stage, (offer, amendment))
    assert [label_of(each) for each in plain["items"]] == [
        "Fourniture",
        "Armoire",
        "Borniers",
        "Câbles",
    ]
    ordered = compared(
        api, stage, (offer, amendment), "&sort_by=reestimated_amount&sort_order=desc"
    )
    assert [label_of(each) for each in ordered["items"]] == [
        "Fourniture",
        "Armoire",
        "Câbles",
        "Borniers",
    ]


# --- The refusals --------------------------------------------------------------------------------


@pytest.mark.requirement(REQUIREMENT)
def test_the_current_revision_is_refused_and_one_of_another_project_is_not_found(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # Two marked revisions only: the current one, which still changes under its reader, refused
    # by its missing condition, on either side (409); a revision of another project, or unknown,
    # not found (404).
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    Lines(tree).made(tree.made("Câblage"), **labour(costs, "Câblage — Ingénieur"))
    mark(stage, offer, "v1.0")
    current = opened(api, stage)
    for pair in ((offer, current), (current, offer)):
        status, code, params = refusal(comparison(api, stage, pair))
        assert (status, code, params) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": "revision_marked"},
        )
    other = create(api, stage.manager, label="Extension")
    answer = api.post(
        f"{PROJECTS}/{other['project_id']}/revisions", headers=stage.manager.headers, json={}
    )
    assert answer.status_code == 201, answer.text
    foreign = answer.json()
    for pair in ((offer, foreign), (foreign, offer), (offer, {"revision_id": str(uuid4())})):
        assert refusal(comparison(api, stage, pair))[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement(REQUIREMENT)
def test_the_comparison_is_read_under_the_permission_to_consult_the_estimate(
    api: ContractClient, stage: Scene, pair: Pair
) -> None:
    # A contributor of the project compares; an account that is none of its contributors does not
    # see the project (404).
    query = (
        f"?from_revision_id={pair.offer['revision_id']}"
        f"&to_revision_id={pair.amendment['revision_id']}"
    )
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/comparison{query}"
    assert api.get(path, headers=stage.participant.headers).status_code == 200
    assert api.get(path, headers=stage.outsider.headers).status_code == 404


def designate(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> None:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    held = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {"revision_id": revision["revision_id"], "confirmed": True, "lock_version": held}
    answer = api.put(f"{path}/reference-revision", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
