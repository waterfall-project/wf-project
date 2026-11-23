# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The differences of a comparison, the totals of its base and the marks it folds on (US-2340/L1).

``compareRevisions`` gives each modified node the difference of each date, duration and amount
that differs (``deltas``, WF-IHM-0150), the totals of the base on the nodes it retains and their
difference with those of the revision read (``base_totals``, ``totals_delta``, WF-IHM-0160), and
marks modified each summary that bears a difference, unchanged each node of a branch without one
(WF-IHM-0170): the grid computes none of them. Under a filter of progress, ``include_differences``
retains the nodes in difference the filter leaves out, counted in the totals. An offer is marked,
the current revision opened from it and changed; every answer is checked against the contract.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, opened, set_progress
from projects_support import Scene
from projects_support import scene as make_scene
from test_comparison import by_label, compared, label_of, labour, mark, material

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

TOTALS_FIELDS = (
    "task_count",
    "estimate_line_count",
    "hours",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated 65.00 this year."""
    return costing(stage.database)


@pytest.fixture
def pair(api: ContractClient, stage: Scene, costs: Costing) -> tuple[dict[str, Any], Tree]:
    """Mark an offer at 1 000.00, a line of 100.00 in it; open the current revision from it.

    « Études » bears « Conception » (ten hours at 65.00) and « Plans » (« Tirages », 250.00);
    « Réception », of two days, bears « Banc d'essais », 100.00.
    """
    return built(api, stage, costs, started=False)


@pytest.fixture
def started_pair(api: ContractClient, stage: Scene, costs: Costing) -> tuple[dict[str, Any], Tree]:
    """Give the pair of ``pair``, « Conception » started since 2 November in the offer."""
    return built(api, stage, costs, started=True)


def built(
    api: ContractClient, stage: Scene, costs: Costing, *, started: bool
) -> tuple[dict[str, Any], Tree]:
    """Make the offer, « Conception » started if asked, mark it, and open the current revision."""
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    lines = Lines(tree)
    studies = tree.made("Études")
    design = tree.made("Conception", parent_id=studies["node_id"])
    lines.made(design, **labour(costs, "Conception — Ingénieur"))
    plans = tree.made("Plans", parent_id=studies["node_id"])
    lines.made(plans, **material(costs, "Tirages", "250.00"))
    acceptance = tree.made("Réception", task={"duration": {"value": "2", "unit": "d"}})
    lines.made(acceptance, **material(costs, "Banc d'essais", "100.00"))
    if started:
        set_progress(stage, design["node_id"], "started", date(2026, 11, 2))
    mark(stage, offer, "v1.0")
    current = opened(api, stage)
    return offer, Tree(api, stage, current)


def read(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree], query: str = ""
) -> dict[str, Any]:
    """Compare the current revision with the offer, its base."""
    offer, current = pair
    return compared(api, stage, (offer, current.revision), query)


def figures(totals: dict[str, Any]) -> tuple[Any, ...]:
    """Give the fields of totals, the counts as numbers and the hours and amounts as decimals."""
    return tuple(
        each if isinstance(each, int) else Decimal(each)
        for each in (totals[name] for name in TOTALS_FIELDS)
    )


def balanced(found: dict[str, Any]) -> bool:
    """Tell whether ``totals_delta`` is ``totals`` less ``base_totals``, field by field."""
    now, then, delta = (figures(found[name]) for name in ("totals", "base_totals", "totals_delta"))
    return all(a - b == c for a, b, c in zip(now, then, delta, strict=True))


def remove(stage: Scene, current: Tree, node: dict[str, Any]) -> None:
    """Delete a node of the current revision, as the manager does."""
    path = f"{current.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    assert current.api.delete(path, headers=stage.manager.headers).status_code == 200


# --- The differences of each value ----------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0150-A")
def test_each_date_duration_and_amount_that_differs_gives_its_difference(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « l'écart à la base de chaque date, en jours calendaires, de chaque durée, en temps de
    # travail, et de chaque montant » : « Réception », two days in the base, one week read — the
    # difference in the unit read, 0.6 week at forty hours, its finish three days later, from the
    # Tuesday to the Friday —, which gives the other tasks three days of float more, a value the
    # planning engine computes, which bears no difference (#4312); a line of twelve hours for ten,
    # 130.00 more, its task and the summary above it with it. The hours of a line are no amount:
    # they bear no difference.
    _, current = pair
    nodes = by_label(current.items())
    current.changed(nodes["Réception"], duration={"value": "1", "unit": "w"})
    Lines(current).changed(nodes["Conception — Ingénieur"], hours="12")
    found = by_label(read(api, stage, pair)["items"])
    assert found["Réception"]["deltas"] == {
        "task": {"duration": {"value": "0.6", "unit": "w"}, "finish": 3}
    }
    amounts = {"base_amount": "130.00", "budgeted_amount": "130.00", "reestimated_amount": "130.00"}
    assert found["Conception — Ingénieur"]["deltas"] == {"estimate_line": amounts}
    assert found["Conception"]["deltas"] == found["Études"]["deltas"] == {"task": amounts}
    # « Plans » gains the float alone: unchanged, without a difference.
    assert found["Plans"]["difference"] == "unchanged"
    labels = ("Plans", "Tirages", "Banc d'essais")
    assert {found[each]["deltas"] is None for each in labels} == {True}


@pytest.mark.requirement("WF-IHM-0150-A")
def test_the_differences_are_those_of_the_fields_read_and_of_a_modified_node_alone(
    api: ContractClient, stage: Scene, costs: Costing, pair: tuple[dict[str, Any], Tree]
) -> None:
    # The differences reduced to the fields read, as ``base``; empty for a node modified by none of
    # them; null for a node added, removed or unchanged, which weighs in the totals alone.
    _, current = pair
    nodes = by_label(current.items())
    current.changed(nodes["Réception"], duration={"value": "3", "unit": "d"})
    remove(stage, current, nodes["Tirages"])
    Lines(current).made(nodes["Plans"], **material(costs, "Câbles", "80.00"))
    query = "&fields=task.label,task.finish,estimate_line.label"
    found = by_label(read(api, stage, pair, query)["items"])
    assert found["Réception"]["deltas"] == {"task": {"finish": 1}}
    assert found["Banc d'essais"]["deltas"] is None
    assert (found["Plans"]["difference"], found["Plans"]["deltas"]) == ("modified", {})
    labels = ("Tirages", "Câbles", "Conception — Ingénieur")
    marks = {each: found[each]["difference"] for each in labels}
    assert list(marks.values()) == ["removed", "added", "unchanged"]
    assert {found[each]["deltas"] is None for each in marks} == {True}


# --- The totals of the base -----------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0160-A")
def test_a_line_removed_counts_in_the_totals_of_the_base_and_their_difference_alone(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « Entre une base à 1 000 et une révision lue à 1 200 [...] 1 200, 1 000 et l'écart de 200. Une
    # ligne de 100 retirée depuis la base compte dans le total de la base et dans l'écart, non dans
    # le total de la révision lue. » : « Tirages » from 250.00 to 550.00, « Banc d'essais » of
    # 100.00 removed. Read whole, from the reading kept of the base.
    _, current = pair
    nodes = by_label(current.items())
    Lines(current).changed(nodes["Tirages"], unit_disbursement="550.00")
    remove(stage, current, nodes["Banc d'essais"])
    found = read(api, stage, pair)
    totals, base, delta = (found[name] for name in ("totals", "base_totals", "totals_delta"))
    amounts = ("reestimated_amount", "budgeted_amount")
    assert [totals[each] for each in amounts] == ["1200.00", "1200.00"]
    assert [base[each] for each in amounts] == ["1000.00", "1000.00"]
    assert [delta[each] for each in amounts] == ["200.00", "200.00"]
    counts = ("task_count", "estimate_line_count")
    assert [(totals[each], base[each], delta[each]) for each in counts] == [(4, 4, 0), (2, 3, -1)]
    assert balanced(found)
    assert totals == current.read().json()["totals"]


@pytest.mark.requirement("WF-IHM-0160-A")
def test_a_filter_retains_the_same_nodes_in_the_totals_of_the_base(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « sur les mêmes lignes retenues : un filtre s'applique aux deux » : the subtree of
    # « Réception », whose line is removed, counts it in the base alone; a line retained by the
    # category it carries in the revision read counts what the base carried of it.
    _, current = pair
    nodes = by_label(current.items())
    Lines(current).changed(nodes["Tirages"], unit_disbursement="550.00")
    remove(stage, current, nodes["Banc d'essais"])
    window = read(api, stage, pair, f"&subtree_of={nodes['Réception']['node_id']}")
    assert figures(window["totals"])[:2] == (1, 0)
    assert window["base_totals"]["estimate_line_count"] == 1
    assert window["totals_delta"]["reestimated_amount"] == "-100.00"
    assert balanced(window)
    category = nodes["Tirages"]["estimate_line"]["cost_category_id"]
    material_lines = read(api, stage, pair, f"&cost_category_id={category}")
    assert material_lines["totals"]["reestimated_amount"] == "550.00"
    assert material_lines["base_totals"]["reestimated_amount"] == "350.00"
    assert material_lines["totals_delta"]["estimate_line_count"] == -1
    assert balanced(material_lines)


@pytest.mark.requirement("WF-IHM-0160-A")
def test_an_identical_pair_gives_the_totals_of_the_base_equal_and_a_nought_difference(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    offer, _ = pair
    for query in ("", "&kinds=task"):
        found = compared(api, stage, (offer, offer), query)
        assert found["base_totals"] == found["totals"]
        assert set(figures(found["totals_delta"])) == {0}


# --- The lines in difference of the remaining to commit ------------------------------------------


@pytest.mark.requirement("WF-IHM-0150-A")
def test_the_nodes_in_difference_a_filter_of_progress_leaves_out_are_retained_and_counted(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « Dans la grille de reste à engager, une ligne en écart d'une tâche non démarrée apparaît
    # sans être demandée » : no task is started; read with the tasks in progress alone, nothing
    # is retained, but with ``include_differences``, each node in difference and its ancestors,
    # counted in the totals of both revisions; the unchanged ones stay left out.
    _, current = pair
    nodes = by_label(current.items())
    Lines(current).changed(nodes["Tirages"], unit_disbursement="550.00")
    remove(stage, current, nodes["Banc d'essais"])
    alone = read(api, stage, pair, "&progress=started")
    assert (alone["items"], alone["totals"]["task_count"]) == ([], 0)
    found = read(api, stage, pair, "&progress=started&include_differences=true")
    assert [(label_of(each), each["difference"]) for each in found["items"]] == [
        ("Études", "modified"),
        ("Plans", "modified"),
        ("Tirages", "modified"),
        ("Réception", "modified"),
        ("Banc d'essais", "removed"),
    ]
    totals, base = found["totals"], found["base_totals"]
    assert (totals["task_count"], totals["estimate_line_count"]) == (3, 1)
    assert (base["task_count"], base["estimate_line_count"]) == (3, 2)
    assert (totals["reestimated_amount"], base["reestimated_amount"]) == ("550.00", "350.00")
    assert balanced(found)
    every = read(api, stage, pair, "&progress=not_started&include_differences=true")
    assert every == read(api, stage, pair, "&progress=not_started")


@pytest.mark.requirement("WF-IHM-0150-A")
def test_a_summary_of_a_state_asked_is_retained_as_a_reading_retains_it_with_the_differences(
    api: ContractClient, stage: Scene, started_pair: tuple[dict[str, Any], Tree]
) -> None:
    # The state judged on the view of a node is the one ``listNodes`` filters on, a summary's
    # derived from its subordinates (``views.State``): « Conception » started in both revisions
    # makes « Études » started in both, neither in difference; « Réception », renamed, is, and
    # is retained with the differences. « Études » stays, as a reading retains it, by its state.
    pair = started_pair
    _, current = pair
    nodes = by_label(current.items())
    assert nodes["Études"]["task"]["progress"] == "started"
    current.changed(nodes["Réception"], label="Réception sur site")
    alone = read(api, stage, pair, "&progress=started")
    found = read(api, stage, pair, "&progress=started&include_differences=true")
    assert [(label_of(each), each["difference"]) for each in alone["items"]] == [
        ("Études", "unchanged"),
        ("Conception", "unchanged"),
        ("Conception — Ingénieur", "unchanged"),
    ]
    assert [(label_of(each), each["difference"]) for each in found["items"]] == [
        ("Études", "unchanged"),
        ("Conception", "unchanged"),
        ("Conception — Ingénieur", "unchanged"),
        ("Réception sur site", "modified"),
    ]
    listed = current.read("?progress=started").json()
    assert alone["totals"] == listed["totals"]
    assert found["totals"]["task_count"] == alone["totals"]["task_count"] + 1
    assert balanced(found)


@pytest.mark.requirement("WF-IHM-0160-A")
def test_an_identical_pair_under_a_filter_of_progress_gives_the_totals_of_the_reading(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # Widened, the totals are counted by the union, not read: on a pair identical they are those
    # of ``listNodes`` on the same nodes, and their difference with the base's is nought. The
    # current revision, just opened, is the offer again; its reading is the one a marked revision
    # has no way to give here.
    _, current = pair
    for state in ("not_started", "started"):
        query = f"&progress={state}"
        listed = current.read(f"?progress={state}").json()["totals"]
        for widened in ("", "&include_differences=true"):
            found = read(api, stage, pair, query + widened)
            assert found["totals"] == listed
            assert found["base_totals"] == found["totals"]
            assert set(figures(found["totals_delta"])) == {0}


# --- The marks the grid folds on -----------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0170-A")
def test_a_summary_that_bears_a_difference_is_modified_and_a_branch_without_one_unchanged(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « la grille n'affiche que les lignes marquées et leurs récapitulatives » : a line renamed
    # alone marks its task and the summary above it modified by their content, nothing else of
    # them differing; « Conception » and « Réception », branches without difference, are
    # unchanged to their lines, whatever the fields read.
    _, current = pair
    nodes = by_label(current.items())
    Lines(current).changed(nodes["Tirages"], label="Tirages A3")
    for query in ("", "&kinds=task", "&fields=task.label"):
        found = read(api, stage, pair, query)["items"]
        marks = {each["node_id"]: (each["difference"], tuple(each["changes"])) for each in found}
        for label in ("Études", "Plans"):
            assert marks[nodes[label]["node_id"]] == ("modified", ())
        unchanged = ("Conception", "Conception — Ingénieur", "Réception", "Banc d'essais")
        returned = [nodes[each]["node_id"] for each in unchanged if nodes[each]["node_id"] in marks]
        assert len(returned) == (2 if query == "&kinds=task" else 4)
        assert {marks[each] for each in returned} == {("unchanged", ())}
