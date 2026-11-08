# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the tasks: read, created, changed, its dependencies, a row number (US-1380/L2).

``listNodes``, ``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies`` and
``resolveRowNumber`` on the main structure of a revision a project's manager opened, every answer
checked against the contract: the tree numbered and filtered, a task created and placed, its
facet changed field by field, what a computed value depends on, a number resolved; the engine
replayed at each write, its entry of the history kept, the refusals of the state and of the
rights; the nodes deleted with an abandoned revision, copied into the next one; two writes of one
structure at once. The links, the states and the inscriptions their stories write are written
around the service (``planning_support``).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import (
    FRIDAY,
    NEXT_MONDAY,
    SATURDAY,
    Tree,
    faults,
    instant,
    opened,
    put_facts,
    put_risk,
    refusal,
    scheduled_at,
    set_progress,
    work_breakdown,
)
from planning_support import DAY, insert_link
from project_rows import STAMP
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import insert

from waterfall.core.planning.tables import TrackingEntry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


# --- Reading -----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0080-A")
def test_an_empty_structure_reads_no_node_nought_totals_and_the_instant_of_its_creation(
    tree: Tree,
) -> None:
    answer = tree.read()
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["items"] == []
    assert body["totals"] == {
        "task_count": 0,
        "estimate_line_count": 0,
        "hours": "0",
        "base_amount": "0.00",
        "budgeted_amount": "0.00",
        "reestimated_amount": "0.00",
    }
    assert body["meta"]["summary_depth"] == 0
    assert datetime.fromisoformat(body["meta"]["scheduled_at"]) == scheduled_at(tree)


@pytest.mark.requirement("WF-PLA-0080-A")
def test_the_tree_is_read_depth_first_numbered_levelled_and_placed(tree: Tree) -> None:
    studies = tree.made("Études")
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    review = tree.made("Revue de conception", parent_id=studies["node_id"])
    site = tree.made("Installation sur site")
    read = tree.items()
    assert [item["node_id"] for item in read] == [
        studies["node_id"],
        detail["node_id"],
        review["node_id"],
        site["node_id"],
    ]
    assert [(item["row_number"], item["level"], item["position"]) for item in read] == [
        (1, 1, 1),
        (2, 2, 1),
        (3, 2, 2),
        (4, 1, 2),
    ]
    assert [item["task"]["is_summary"] for item in read] == [True, False, False, False]
    body = tree.read().json()
    assert body["meta"]["summary_depth"] == 1
    assert body["totals"]["task_count"] == 4


@pytest.mark.requirement("WF-PLA-0080-A")
def test_the_filters_retain_tasks_with_their_ancestors_and_count_only_those_retained(
    tree: Tree, stage: Scene
) -> None:
    studies = tree.made("Études")
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    tree.made(
        "Réception des études",
        parent_id=studies["node_id"],
        task={"duration": {"value": "0", "unit": "d"}},
    )
    site = tree.made("Installation sur site", task={"description": "Câblage et ÉQUIPEMENTS"})
    set_progress(stage, detail["node_id"], "started", DAY)
    # The search ignores case and accents; the ancestors come back, out of the count.
    answer = tree.read("?search=etudes%20DE")
    assert [item["task"]["label"] for item in answer.json()["items"]] == [
        "Études",
        "Études de détail",
    ]
    assert answer.json()["totals"]["task_count"] == 1
    assert tree.labels("?description=equipements") == ["Installation sur site"]
    assert tree.labels(f"?subtree_of={studies['node_id']}") == [
        "Études",
        "Études de détail",
        "Réception des études",
    ]
    assert tree.labels("?progress=started") == ["Études", "Études de détail"]
    assert tree.labels("?is_milestone=true") == ["Études", "Réception des études"]
    assert tree.labels("?summaries_only=true&max_level=1") == ["Études"]
    assert tree.labels("?max_level=1") == ["Études", "Installation sur site"]
    assert tree.labels("?scheduling_mode=manual") == []
    assert tree.labels(f"?start_from={DAY}&start_to={DAY}&max_level=1") == [
        "Études",
        "Installation sur site",
    ]
    # ``kinds`` chooses what is returned, the count does not change with it.
    lines = tree.read("?kinds=estimate_line")
    assert lines.json()["items"] == []
    assert lines.json()["totals"]["task_count"] == 4
    # The filters of the line retain lines, which EP-07 brings: none of the tasks goes.
    assert len(tree.items("?quantity_min=1&quantity_max=5&base_amount_min=0.00")) == 4
    assert tree.items(f"?subtree_of={uuid4()}") == []
    assert site["node_id"] not in {item["node_id"] for item in tree.items("?is_critical=false")}


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_work_package_or_an_order_item_shows_the_task_that_bears_it_its_subtree_and_parents(
    tree: Tree, stage: Scene
) -> None:
    # « ne laisse voir que la tâche qui le porte, son sous-arbre et ses parents »
    studies = tree.made("Études")
    carrying = tree.made("Lot câblage", parent_id=studies["node_id"])
    tree.made("Tirage", parent_id=carrying["node_id"])
    site = tree.made("Chantier")
    ordered = tree.made("Poste pupitres", parent_id=site["node_id"])
    tree.made("Livraison", parent_id=site["node_id"])
    package, item = work_breakdown(stage)
    put_facts(stage, carrying["node_id"], work_package_id=package)
    put_facts(stage, ordered["node_id"], order_item_id=item)
    assert tree.labels(f"?work_package_id={package}") == ["Études", "Lot câblage", "Tirage"]
    assert tree.labels(f"?order_item_id={item}") == ["Chantier", "Poste pupitres"]
    assert tree.labels(f"?work_package_id={uuid4()}") == []


@pytest.mark.requirement("WF-PLA-0080-A")
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?finish_overdue=true", ["Retard"]),
        ("?finish_overdue=false", ["Fini", "Neuf"]),
        ("?started_on_from=2026-11-03", ["Fini"]),
        ("?started_on_to=2026-11-02", ["Retard"]),
        ("?completed_on_from=2026-11-05&completed_on_to=2026-11-05", ["Fini"]),
        ("?completed_on_to=2026-11-04", []),
        ("?duration_min=2&duration_max=5", ["Fini"]),
        ("?duration_max=1", ["Retard"]),
        ("?total_float_min=1", ["Fini"]),
        ("?total_float_max=0", ["Retard"]),
        # No physical progress is stored nor computed before EP-07: a bound retains none of the
        # three tasks, which the unfiltered reading (the last case) shows to exist.
        ("?physical_progress_min=10", []),
        ("?physical_progress_max=10", []),
        ("?physical_progress_min=0&physical_progress_max=100", []),
        ("", ["Retard", "Fini", "Neuf"]),
        ("?is_from_risk=true", ["Retard", "Neuf"]),
        ("?is_from_risk=false", ["Fini"]),
        ("?origin_risk_ids={first}", ["Retard"]),
        ("?origin_risk_ids={first},{second}", ["Retard", "Neuf"]),
        ("?is_critical=true", ["Retard"]),
    ],
)
def test_a_filter_of_the_state_the_float_the_duration_or_the_risk_retains_the_tasks_it_names(
    tree: Tree, stage: Scene, query: str, expected: list[str]
) -> None:
    late, done, new = (tree.made(label) for label in ("Retard", "Fini", "Neuf"))
    first, second = uuid4(), uuid4()
    later = date(2099, 1, 1)
    put_facts(
        stage,
        late["node_id"],
        progress="started",
        started_on=DAY,
        total_float_days=Decimal(0),
        is_critical=True,
    )
    put_facts(
        stage,
        done["node_id"],
        progress="completed",
        started_on=DAY + timedelta(days=1),
        completed_on=DAY + timedelta(days=3),
        duration_value=Decimal(3),
        finish_date=later,
        total_float_days=Decimal(5),
        is_critical=False,
    )
    put_facts(
        stage,
        new["node_id"],
        duration_value=Decimal(10),
        finish_date=later,
        total_float_days=None,
        is_critical=False,
    )
    put_risk(stage, late["node_id"], first)
    put_risk(stage, new["node_id"], second)
    assert tree.labels(query.format(first=first, second=second)) == expected


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_retains_its_inscribed_tasks_without_their_ancestors(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    studies = tree.made("Études")
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    created = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/timelines",
        headers=stage.manager.headers,
        json={"label": "Comité de pilotage"},
    ).json()["timeline_id"]
    with stage.database.transaction() as session:
        session.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                project_id=UUID(stage.project["project_id"]),
                lineage_id=UUID(detail["lineage_id"]),
                kind="timeline",
                timeline_id=UUID(created),
                **STAMP,
            )
        )
    read = tree.items(f"?kinds=task&timeline_id={created}")
    assert [item["task"]["label"] for item in read] == ["Études de détail"]
    assert read[0]["task"]["tracking"] == [{"kind": "timeline", "timeline_id": created}]
    assert tree.items(f"?timeline_id={uuid4()}") == []


# A filter malformed or inverted, and the fault it is refused by.
MALFORMED: list[tuple[str, tuple[str, str, dict[str, str]]]] = [
    (
        "?total_float_min=5&total_float_max=1",
        ("/query/total_float_max", "VALUE_OUT_OF_RANGE", {"minimum": "5"}),
    ),
    (
        "?start_from=2026-05-01&start_to=2026-04-01",
        ("/query/start_to", "VALUE_OUT_OF_RANGE", {"minimum": "2026-05-01"}),
    ),
    (
        "?reestimated_amount_min=10000.00&reestimated_amount_max=1000.00",
        ("/query/reestimated_amount_max", "VALUE_OUT_OF_RANGE", {"minimum": "10000.00"}),
    ),
    ("?duration_min=dix", ("/query/duration_min", "NUMBER_INVALID", {})),
    ("?base_amount_max=1.234", ("/query/base_amount_max", "NUMBER_INVALID", {})),
    ("?finish_to=2026-02-30", ("/query/finish_to", "DATE_INVALID", {})),
    ("?fields=task.duration_days", ("/query/fields", "FIELD_NOT_ACCEPTED", {})),
    ("?progress=ongoing", ("/query/progress", "VALIDATION_FAILED", {})),
]


@pytest.mark.requirement("WF-PLA-0080-A")
@pytest.mark.parametrize(("query", "expected"), MALFORMED)
def test_a_malformed_or_inverted_filter_is_refused_on_its_parameter(
    tree: Tree, query: str, expected: tuple[str, str, dict[str, Any]]
) -> None:
    assert faults(tree.read(query)) == [expected]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_fields_returns_what_it_names_and_the_four_always_returned(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    tree.made("Études")
    # A reading that names its fields returns less than the schema of a node requires: it is
    # judged on its own, not by the schema the contract gives a node whole (#2485): the client
    # of the service, not the ``ContractClient`` that validates every answer.
    answer = api.client.get(
        f"{tree.path}/nodes?fields=task.label,task.duration,parent_id",
        headers=stage.manager.headers,
    )
    assert answer.status_code == 200, answer.text
    item = answer.json()["items"][0]
    assert set(item) == {"node_id", "row_number", "level", "lock_version", "task", "parent_id"}
    assert item["task"] == {"label": "Études", "duration": {"value": "1", "unit": "d"}}


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_is_started_once_a_subordinate_is_and_completed_after_the_last(
    tree: Tree, stage: Scene
) -> None:
    # « Une récapitulative dont une subordonnée est démarrée est démarrée ; elle n'est terminée
    # qu'après la dernière. »
    studies = tree.made("Études")
    first = tree.made("Études de détail", parent_id=studies["node_id"])
    last = tree.made("Revue de conception", parent_id=studies["node_id"])
    assert tree.node(studies["node_id"])["task"]["progress"] == "not_started"
    set_progress(stage, first["node_id"], "started", DAY)
    summary = tree.node(studies["node_id"])["task"]
    assert (summary["progress"], summary["started_on"]) == ("started", DAY.isoformat())
    set_progress(stage, first["node_id"], "completed", DAY)
    assert tree.node(studies["node_id"])["task"]["progress"] == "started"
    set_progress(stage, last["node_id"], "completed", FRIDAY)
    summary = tree.node(studies["node_id"])["task"]
    assert (summary["progress"], summary["completed_on"]) == ("completed", FRIDAY.isoformat())


# --- Creation ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_task_created_without_mode_nor_duration_is_an_automatic_leaf_of_a_day(
    tree: Tree,
) -> None:
    answer = tree.create("Études")
    assert answer.status_code == 201, answer.text
    body = answer.json()
    node = body["nodes"][0]
    assert node["lock_version"] == 1
    assert node["lineage_id"] == node["node_id"]
    task = node["task"]
    assert task["scheduling_mode"] == "automatic"
    assert task["duration"] == {"value": "1", "unit": "d"}
    assert (task["start"], task["finish"]) == (instant(DAY, "0"), instant(DAY, "8"))
    assert (task["is_summary"], task["is_milestone"], task["progress"]) == (
        False,
        False,
        "not_started",
    )
    assert task["calendar_hours"]["saturday"] == "0"
    assert node["computed_fields"] == ["task.start", "task.finish"]
    assert node["editable_fields"] == [
        "task.label",
        "task.description",
        "task.scheduling_mode",
        "task.duration",
        "task.progress",
        "task.predecessors",
        "task.order_item_id",
        "task.work_package_id",
        "task.tracking",
    ]
    assert (body["ancestors"], body["rescheduled"], body["reinflated"]) == ([], [], [])
    assert body["totals"]["task_count"] == 1
    again = tree.create("Revue").json()
    assert again["structure_lock_version"] == body["structure_lock_version"] + 1
    assert again["totals"]["task_count"] == 2
    # The structure's dates were computed by this write: its instant moved on.
    meta = tree.read().json()["meta"]
    assert datetime.fromisoformat(meta["scheduled_at"]) == scheduled_at(tree) > tree.created_at


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_leaf_that_receives_a_subtask_becomes_its_summary_and_is_returned_as_its_ancestor(
    tree: Tree,
) -> None:
    note = tree.made("Note de calcul")
    answer = tree.create("Relevé des réglages", parent_id=note["node_id"])
    assert answer.status_code == 201, answer.text
    body = answer.json()
    assert body["nodes"][0]["level"] == 2
    [summary] = body["ancestors"]
    assert summary["node_id"] == note["node_id"]
    assert summary["lock_version"] == 1
    assert summary["task"]["is_summary"] is True
    assert summary["task"]["duration"] == {"value": "1", "unit": "d"}
    assert summary["computed_fields"] == [
        "task.scheduling_mode",
        "task.duration",
        "task.start",
        "task.finish",
        "task.progress",
    ]
    assert "task.duration" not in summary["editable_fields"]
    assert summary["task"]["physical_progress"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_budgeted_amount",
    }


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_manual_leaf_that_receives_a_subtask_becomes_an_automatic_summary_written_with_it(
    tree: Tree,
) -> None:
    manual = {"scheduling_mode": "manual", "start": {"date": FRIDAY.isoformat()}}
    reception = tree.made("Réception", task={**manual, "finish": {"date": NEXT_MONDAY.isoformat()}})
    body = tree.create("Essais", parent_id=reception["node_id"]).json()
    [summary] = body["ancestors"]
    assert summary["task"]["scheduling_mode"] == "automatic"
    assert summary["lock_version"] == 2
    # Its dates are its subordinate's now, at the planning start.
    assert summary["task"]["start"] == instant(DAY, "0")


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_manual_task_created_with_its_dates_alone_has_its_hours_completed(tree: Tree) -> None:
    # #1769, #1770: the start begins its day, the finish ends its hours, on the default calendar.
    node = tree.made(
        "Réception provisoire",
        task={
            "scheduling_mode": "manual",
            "start": {"date": DAY.isoformat()},
            "finish": {"date": (DAY + timedelta(days=2)).isoformat()},
        },
    )
    task = node["task"]
    assert task["start"] == instant(DAY, "0")
    assert task["finish"] == instant(DAY + timedelta(days=2), "8")
    assert task["duration"] == {"value": "3", "unit": "d"}
    assert (task["total_float"], task["is_critical"]) == (None, False)
    assert node["computed_fields"] == []
    assert {"task.start", "task.finish"} <= set(node["editable_fields"])


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_creation_on_a_day_without_hours_or_beyond_its_hours_is_refused_and_writes_nothing(
    tree: Tree,
) -> None:
    saturday = tree.create(
        "Réception",
        task={
            "scheduling_mode": "manual",
            "start": {"date": SATURDAY.isoformat()},
            "finish": {"date": NEXT_MONDAY.isoformat(), "hours": "9"},
        },
    )
    assert faults(saturday) == [
        (
            "/task/start/date",
            "NON_WORKING_DAY",
            {"date": SATURDAY.isoformat(), "next_working_day": NEXT_MONDAY.isoformat()},
        ),
        ("/task/finish/hours", "VALUE_OUT_OF_RANGE", {"maximum": "8"}),
    ]
    below = tree.create(
        "Réception",
        task={
            "scheduling_mode": "manual",
            "start": {"date": DAY.isoformat(), "hours": "-1"},
            "finish": {"date": DAY.isoformat()},
        },
    )
    assert faults(below) == [("/task/start/hours", "VALUE_OUT_OF_RANGE", {"minimum": "0"})]
    computed = tree.create("Études", task={"start": {"date": DAY.isoformat()}})
    assert faults(computed) == [("/task/start", "COMPUTED_VALUE", {})]
    assert tree.items() == []


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_task_is_placed_after_the_sibling_named_at_their_head_or_after_the_last(
    tree: Tree,
) -> None:
    first = tree.made("Premier")
    tree.made("Dernier")
    tree.made("Second", after_node_id=first["node_id"])
    tree.made("Tête", after_node_id=None)
    assert tree.labels() == ["Tête", "Premier", "Second", "Dernier"]
    assert [item["position"] for item in tree.items()] == [1, 2, 3, 4]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_a_place_after_a_node_that_is_no_sibling_is_refused(tree: Tree) -> None:
    studies = tree.made("Études")
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    for after in (detail["node_id"], str(uuid4())):
        answer = tree.create("Note", after_node_id=after)
        assert faults(answer) == [("/after_node_id", "NODE_NOT_SIBLING", {})]
    unknown = tree.create("Note", parent_id=str(uuid4()))
    assert faults(unknown) == [("/parent_id", "UNKNOWN_TASK", {})]
    assert len(tree.items()) == 2


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_milestone_receives_no_subtask_and_nothing_is_created(tree: Tree) -> None:
    # « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. »
    milestone = tree.made("Réception des études", task={"duration": {"value": "0", "unit": "d"}})
    assert milestone["task"]["is_milestone"] is True
    assert "task.duration" not in milestone["editable_fields"]
    answer = tree.create("Note de calcul", parent_id=milestone["node_id"])
    assert faults(answer) == [
        (
            "/parent_id",
            "MILESTONE_HAS_NO_SUBTASK",
            {"node_id": milestone["node_id"], "label": "Réception des études"},
        )
    ]
    assert len(tree.items()) == 1


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_summary_whose_only_subordinate_is_a_milestone_lasts_nought_and_stays_a_summary(
    tree: Tree,
) -> None:
    # « Une récapitulative dont la seule subordonnée est un jalon a une durée nulle et reste une
    # récapitulative. »
    reception = tree.made("Réception")
    body = tree.create(
        "Procès-verbal",
        parent_id=reception["node_id"],
        task={"duration": {"value": "0", "unit": "d"}},
    ).json()
    summary = body["ancestors"][0]["task"]
    assert (summary["is_summary"], summary["is_milestone"]) == (True, False)
    assert summary["duration"] == {"value": "0", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_task_created_beyond_fifteen_years_is_refused_by_its_label_and_nothing_is_created(
    tree: Tree,
) -> None:
    # « Le déplacement d'une tâche qui porterait la fin du projet à quinze ans et un jour de son
    # début est refusé, et la tâche est nommée. »
    answer = tree.create("Exploitation", task={"duration": {"value": "200", "unit": "mo"}})
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": None, "label": "Exploitation"}},
    )
    assert tree.items() == []


# --- Modification ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0040-A")
def test_a_modification_writes_what_it_sends_alone_and_advances_the_version(tree: Tree) -> None:
    node = tree.made("Études", task={"description": "Avant-projet"})
    body = tree.changed(node, label="Études détaillées")
    written = body["nodes"][0]
    assert written["lock_version"] == 2
    assert written["task"]["label"] == "Études détaillées"
    assert written["task"]["description"] == "Avant-projet"
    cleared = tree.changed(written, description=None)["nodes"][0]
    assert cleared["task"]["description"] is None
    assert cleared["lock_version"] == 3
    assert (
        body["structure_lock_version"]
        < tree.changed(cleared, label="Études")["structure_lock_version"]
    )


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_duration_is_kept_in_its_unit_and_redates_the_successor_it_moves(
    tree: Tree, stage: Scene
) -> None:
    first = tree.made("Préparation")
    second = tree.made("Reprise")
    with stage.database.transaction() as session:
        session.execute(
            insert_link(
                UUID(stage.project["project_id"]),
                UUID(tree.revision["revision_id"]),
                UUID(tree.structure_id),
                UUID(first["node_id"]),
                UUID(second["node_id"]),
            )
        )
    body = tree.changed(first, duration={"value": "1", "unit": "w"})
    task = body["nodes"][0]["task"]
    assert task["duration"] == {"value": "1", "unit": "w"}
    assert task["finish"] == instant(FRIDAY, "8")
    [moved] = body["rescheduled"]
    assert moved["node_id"] == second["node_id"]
    assert moved["start"] == instant(NEXT_MONDAY, "0")
    assert tree.node(second["node_id"])["lock_version"] == 1
    assert tree.node(second["node_id"])["predecessors"] == [
        {
            "predecessor_node_id": first["node_id"],
            "predecessor_row_number": 1,
            "link_type": "finish_to_start",
            "lag": {"value": "0", "unit": "d"},
        }
    ]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_task_turned_manual_keeps_its_dates_then_takes_those_entered(tree: Tree) -> None:
    node = tree.made("Mise en service", task={"duration": {"value": "2", "unit": "d"}})
    manual = tree.changed(node, scheduling_mode="manual")["nodes"][0]
    assert manual["task"]["start"] == instant(DAY, "0")
    assert manual["task"]["finish"] == instant(DAY + timedelta(days=1), "8")
    assert manual["computed_fields"] == []
    dated = tree.changed(
        manual,
        start={"date": NEXT_MONDAY.isoformat()},
        finish={"date": (NEXT_MONDAY + timedelta(days=4)).isoformat()},
    )["nodes"][0]
    assert dated["task"]["start"] == instant(NEXT_MONDAY, "0")
    assert dated["task"]["finish"] == instant(NEXT_MONDAY + timedelta(days=4), "8")
    assert dated["task"]["duration"] == {"value": "5", "unit": "d"}
    # A duration entered alone moves its finish from its start.
    shorter = tree.changed(dated, duration={"value": "16", "unit": "h"})["nodes"][0]
    assert shorter["task"]["finish"] == instant(NEXT_MONDAY + timedelta(days=1), "8")
    back = tree.changed(shorter, scheduling_mode="automatic")["nodes"][0]
    assert back["task"]["start"] == instant(DAY, "0")


@pytest.mark.requirement("WF-PLA-0040-A")
def test_the_dates_and_mode_of_a_summary_are_not_entered_its_subordinates_named(
    tree: Tree,
) -> None:
    # « Les dates et l'état d'une récapitulative ne sont pas saisissables. »
    summary = tree.made("Poste de commande")
    first = tree.made("Câblage", parent_id=summary["node_id"])
    second = tree.made("Essais", parent_id=summary["node_id"])
    read = tree.node(summary["node_id"])
    answer = tree.change(
        read,
        scheduling_mode="automatic",
        finish={"date": FRIDAY.isoformat()},
        duration={"value": "3", "unit": "d"},
    )
    assert faults(answer) == [
        ("/scheduling_mode", "COMPUTED_VALUE", {}),
        ("/duration", "COMPUTED_VALUE", {}),
        (
            "/finish",
            "SUMMARY_TASK_DERIVED",
            {"subordinate_node_ids": [first["node_id"], second["node_id"]]},
        ),
    ]
    assert tree.node(summary["node_id"])["lock_version"] == read["lock_version"]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_the_date_of_an_automatic_task_and_the_duration_of_a_milestone_are_refused(
    tree: Tree,
) -> None:
    automatic = tree.made("Montage")
    assert faults(tree.change(automatic, finish={"date": FRIDAY.isoformat()})) == [
        ("/finish", "COMPUTED_VALUE", {})
    ]
    milestone = tree.made("Réception usine", task={"duration": {"value": "0", "unit": "d"}})
    assert faults(tree.change(milestone, duration={"value": "1", "unit": "d"})) == [
        ("/duration", "FIELD_NOT_ACCEPTED", {})
    ]
    manual = tree.changed(automatic, scheduling_mode="manual")["nodes"][0]
    assert faults(tree.change(manual, start={"date": SATURDAY.isoformat()})) == [
        (
            "/start/date",
            "NON_WORKING_DAY",
            {"date": SATURDAY.isoformat(), "next_working_day": NEXT_MONDAY.isoformat()},
        )
    ]
    assert faults(tree.change(manual, finish={"date": DAY.isoformat(), "hours": "10"})) == [
        ("/finish/hours", "VALUE_OUT_OF_RANGE", {"maximum": "8"})
    ]


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_finish_entered_fifteen_years_and_a_day_after_the_start_is_refused_naming_the_task(
    tree: Tree,
) -> None:
    node = tree.made(
        "Pupitres",
        task={
            "scheduling_mode": "manual",
            "start": {"date": DAY.isoformat()},
            "finish": {"date": DAY.isoformat()},
        },
    )
    beyond = date(DAY.year + 15, DAY.month, DAY.day) + timedelta(days=1)
    while beyond.weekday() >= 5:
        beyond += timedelta(days=1)
    answer = tree.change(node, finish={"date": beyond.isoformat()})
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": node["node_id"], "label": "Pupitres"}},
    )
    assert tree.node(node["node_id"])["lock_version"] == 1


@pytest.mark.requirement("WF-PLA-0150-A")
@pytest.mark.parametrize(
    "duration",
    [
        {"value": "99999999999", "unit": "d"},
        {"value": "9999999", "unit": "mo"},
        {"value": "5000", "unit": "d"},
    ],
    ids=["days-beyond-the-calendar", "months-beyond-the-calendar", "days-beyond-fifteen-years"],
)
def test_a_manual_duration_so_long_that_its_finish_is_no_date_is_refused_naming_the_task(
    tree: Tree, duration: dict[str, str]
) -> None:
    node = tree.made(
        "Pupitres",
        task={
            "scheduling_mode": "manual",
            "start": {"date": DAY.isoformat()},
            "finish": {"date": DAY.isoformat()},
        },
    )
    answer = tree.change(node, duration=duration)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": node["node_id"], "label": "Pupitres"}},
    )
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_modification_at_a_stale_version_or_of_an_unknown_node_is_refused(tree: Tree) -> None:
    node = tree.made("Études")
    tree.changed(node, label="Études détaillées")
    stale = tree.change(node, label="Autre")
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    unknown = tree.change({**node, "node_id": str(uuid4())}, label="Autre")
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    alone = tree.change(node)
    assert refusal(alone)[:2] == (422, "VALIDATION_FAILED")
    assert tree.node(node["node_id"])["task"]["label"] == "Études détaillées"


# --- Dependencies and row numbers ---------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0030-A")
def test_a_computed_value_names_what_it_depends_on_and_an_entered_one_is_refused(
    tree: Tree,
) -> None:
    summary = tree.made("Études")
    first = tree.made("Études de détail", parent_id=summary["node_id"])
    second = tree.made(
        "Pupitres",
        parent_id=summary["node_id"],
        task={
            "scheduling_mode": "manual",
            "start": {"date": DAY.isoformat()},
            "finish": {"date": DAY.isoformat()},
        },
    )

    def asked(node: dict[str, Any], field: str) -> Any:
        path = f"{tree.path}/nodes/{node['node_id']}/dependencies?field={field}"
        return tree.api.get(path, headers=tree.stage.manager.headers)

    finish = asked(summary, "task.finish")
    assert finish.status_code == 200, finish.text
    assert finish.json() == {
        "node_id": summary["node_id"],
        "field": "task.finish",
        "depends_on": ["subordinates"],
        "rows": [
            {"node_id": first["node_id"], "row_number": 2, "label": "Études de détail"},
            {"node_id": second["node_id"], "row_number": 3, "label": "Pupitres"},
        ],
    }
    start = asked(first, "task.start").json()
    assert (start["depends_on"], start["rows"]) == (["scheduling"], [])
    assert asked(second, "task.total_float").json()["depends_on"] == ["manual_mode"]
    assert asked(first, "task.total_float").json()["depends_on"] == ["float_dates"]
    assert asked(first, "task.base_amount").json()["depends_on"] == ["lines_and_subordinates"]
    assert refusal(asked(second, "task.start")) == (
        422,
        "VALIDATION_FAILED",
        {"field": "task.start"},
    )
    assert faults(asked(first, "task.nothing")) == [("/query/field", "VALIDATION_FAILED", {})]
    assert refusal(asked({"node_id": str(uuid4())}, "task.start"))[:2] == (404, "NOT_FOUND")


def test_a_row_number_resolves_to_its_node_whatever_the_filters_and_none_beyond(
    tree: Tree,
) -> None:
    tree.made("Études")
    reception = tree.made("Réception")

    def resolved(number: object) -> Any:
        return tree.api.get(f"{tree.path}/rows/{number}", headers=tree.stage.manager.headers)

    answer = resolved(2)
    assert answer.status_code == 200, answer.text
    assert answer.json() == {
        "node_id": reception["node_id"],
        "row_number": 2,
        "label": "Réception",
        "kind": "task",
    }
    assert refusal(resolved(3)) == (404, "NOT_FOUND", {})
    assert faults(resolved(0))[0][0] == "/path/row_number"
