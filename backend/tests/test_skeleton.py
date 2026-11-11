# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The skeleton of a planning engendered from the work breakdown (US-1460, WF-PRJ-0030).

``generatePlanningSkeleton`` on the main structure of a revision the manager of a project opened:
a summary task per work package and per order item, attached to it, a leaf of a day per
deliverable, an end milestone per order item and per work package with their links, the nodes
given in the order of the plan (``NodesWritten``); the commands ``generate_skeleton`` of the
revision and of the project that state in advance whether it is offered, and the refusals that
follow them, in their order. Every answer is checked against the contract.
"""

import json
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from nodes_support import Tree, entries, mark, opened, refusal, signed_in
from planning_support import insert_task
from projects_support import PROJECTS, Person, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import WITNESS

from waterfall.core.planning.tables import Node, TaskLink
from waterfall.core.projects.commands import Running, commands_of
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

SKELETON = "skeleton"
PROJECT_LABEL = "Modernisation du poste de commande"
# The phrase of the example, the project it describes, and the day its planning starts on.
EXAMPLE_LABEL = "Rénovation du poste de livraison"
EXAMPLE_START = date(2026, 6, 3)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def generate(tree: Tree, who: Person | None = None) -> Any:
    """Ask for the skeleton of the revision of a tree, as its manager does by default."""
    revision = tree.revision["revision_id"]
    path = f"{PROJECTS}/{tree.stage.project['project_id']}/revisions/{revision}/{SKELETON}"
    return tree.api.post(path, headers=(who or tree.stage.manager).headers)


def generated(tree: Tree) -> dict[str, Any]:
    """Generate the skeleton, which must be generated; give what is answered."""
    answer = generate(tree)
    assert answer.status_code == 201, answer.text
    return answer.json()


def lotted(tree: Tree, *packages: tuple[str, list[tuple[str, list[str]]]]) -> None:
    """Write the work breakdown of the project: packages of items of deliverables, by label."""
    path = f"{PROJECTS}/{tree.stage.project['project_id']}/work-breakdown"
    headers = tree.stage.manager.headers
    read = tree.api.get(path, headers=headers).json()
    sent = [
        {
            "label": label,
            "order_items": [
                {"label": item, "deliverables": [{"label": each} for each in deliverables]}
                for item, deliverables in items
            ],
        }
        for label, items in packages
    ]
    answer = tree.api.put(
        path, headers=headers, json={"work_packages": sent, "lock_version": read["lock_version"]}
    )
    assert answer.status_code == 200, answer.text


def rewritten(tree: Tree, edit: Callable[[list[dict[str, Any]]], None]) -> None:
    """Write the work breakdown back, its elements kept by their identifiers, after ``edit``."""
    path = f"{PROJECTS}/{tree.stage.project['project_id']}/work-breakdown"
    headers = tree.stage.manager.headers
    read = tree.api.get(path, headers=headers).json()
    packages = read["work_packages"]
    edit(packages)
    answer = tree.api.put(
        path,
        headers=headers,
        json={"work_packages": packages, "lock_version": read["lock_version"]},
    )
    assert answer.status_code == 200, answer.text


def labels(written: dict[str, Any]) -> list[str]:
    """Give the labels of the nodes written, in the order given."""
    return [each["task"]["label"] for each in written["nodes"]]


def by_label(written: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Give the nodes written by label (the labels of the tests are distinct)."""
    return {each["task"]["label"]: each for each in written["nodes"]}


def parents(written: dict[str, Any]) -> dict[str, str | None]:
    """Give the label of the parent of each node written, none for a root."""
    names = {each["node_id"]: each["task"]["label"] for each in written["nodes"]}
    return {
        each["task"]["label"]: names[each["parent_id"]] if each["parent_id"] else None
        for each in written["nodes"]
    }


def follows(written: dict[str, Any]) -> dict[str, list[str]]:
    """Give the labels of the predecessors of each node written that has some."""
    names = {each["node_id"]: each["task"]["label"] for each in written["nodes"]}
    return {
        each["task"]["label"]: [names[link["predecessor_node_id"]] for link in each["predecessors"]]
        for each in written["nodes"]
        if each.get("predecessors")
    }


def commands(body: dict[str, Any]) -> dict[str, tuple[bool, list[str]]]:
    """Give the commands a revision or a project lists: availability, conditions it lacks."""
    return {
        each["command"]: (each["is_available"], each["missing_conditions"])
        for each in body["available_commands"]
    }


def revision_of(tree: Tree) -> dict[str, Any]:
    """Read the revision of a tree."""
    path = f"{PROJECTS}/{tree.stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    answer = tree.api.get(path, headers=tree.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def project_of(tree: Tree) -> dict[str, Any]:
    """Read the project of a tree."""
    path = f"{PROJECTS}/{tree.stage.project['project_id']}"
    answer = tree.api.get(path, headers=tree.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


# --- What is generated ------------------------------------------------------------------------


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_two_work_packages_and_three_order_items_give_their_summaries_leaves_and_milestones(
    tree: Tree,
) -> None:
    # « La génération sur un lotissement de deux lots et trois postes produit les récapitulatives,
    # rattachées à leur lot ou à leur poste, les feuilles et les jalons attendus, avec leurs
    # liaisons. »
    lotted(
        tree,
        ("Lot A", [("Poste A1", ["Plan", "Note"]), ("Poste A2", [])]),
        ("Lot B", [("Poste B1", ["Rapport"])]),
    )
    written = generated(tree)
    # In the order of the plan: a work package, each of its items followed by its deliverables and
    # its end milestone, then its own end milestone.
    assert labels(written) == [
        "Lot A",
        "Poste A1",
        "Plan",
        "Note",
        "Fin de « Poste A1 »",
        "Poste A2",
        "Fin de « Poste A2 »",
        "Fin de « Lot A »",
        "Lot B",
        "Poste B1",
        "Rapport",
        "Fin de « Poste B1 »",
        "Fin de « Lot B »",
    ]
    assert parents(written) == {
        "Lot A": None,
        "Poste A1": "Lot A",
        "Plan": "Poste A1",
        "Note": "Poste A1",
        "Fin de « Poste A1 »": "Poste A1",
        "Poste A2": "Lot A",
        "Fin de « Poste A2 »": "Poste A2",
        "Fin de « Lot A »": "Lot A",
        "Lot B": None,
        "Poste B1": "Lot B",
        "Rapport": "Poste B1",
        "Fin de « Poste B1 »": "Poste B1",
        "Fin de « Lot B »": "Lot B",
    }
    nodes = by_label(written)
    packages = {name: nodes[name]["task"] for name in ("Lot A", "Lot B")}
    items = {name: nodes[name]["task"] for name in ("Poste A1", "Poste A2", "Poste B1")}
    for name, task in (*packages.items(), *items.items()):
        assert task["is_summary"] is True, name
    for task in packages.values():
        assert task["order_item_id"] is None
        assert task["work_package_id"] is not None
        assert task["work_breakdown_label"] in {"Lot A", "Lot B"}
    for task in items.values():
        assert task["work_package_id"] is None
        assert task["order_item_id"] is not None
    # A leaf per deliverable, automatic, of a day, attached to nothing: no task holds a deliverable.
    for name in ("Plan", "Note", "Rapport"):
        task = nodes[name]["task"]
        assert task["scheduling_mode"] == "automatic"
        assert task["duration"] == {"value": "1", "unit": "d"}
        assert task["is_summary"] is False
        assert task["is_milestone"] is False
        assert task["order_item_id"] is None
        assert task["work_package_id"] is None
    ends = [name for name in nodes if name.startswith("Fin de")]
    assert len(ends) == 5
    for name in ends:
        assert nodes[name]["task"]["is_milestone"] is True
        assert nodes[name]["task"]["order_item_id"] is None
        assert nodes[name]["task"]["work_package_id"] is None
    # The milestone of an item follows its deliverables, that of a work package those of its
    # items, finish to start without lag; an item without a deliverable has nothing to follow.
    assert follows(written) == {
        "Fin de « Poste A1 »": ["Plan", "Note"],
        "Fin de « Lot A »": ["Fin de « Poste A1 »", "Fin de « Poste A2 »"],
        "Fin de « Poste B1 »": ["Rapport"],
        "Fin de « Lot B »": ["Fin de « Poste B1 »"],
    }
    for link in nodes["Fin de « Lot A »"]["predecessors"]:
        assert (link["link_type"], link["lag"]) == ("finish_to_start", {"value": "0", "unit": "d"})
    assert nodes["Fin de « Poste A1 »"]["predecessors"][0]["predecessor_row_number"] == 3
    # The answer is that of a write of the grid, and the grid reads what it says.
    assert written["ancestors"] == []
    assert written["rescheduled"] == []
    assert written["totals"]["task_count"] == 13
    assert [each["row_number"] for each in written["nodes"]] == list(range(1, 14))
    assert [each["task"]["label"] for each in tree.items()] == labels(written)


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_default_work_breakdown_gives_what_the_contract_example_says(tree: Tree) -> None:
    # « Sur le lotissement par défaut, la génération produit une récapitulative de lot, une
    # récapitulative de poste sans feuille, et leurs deux jalons de fin. »
    example = json.loads((WITNESS / "skeleton_generated.json").read_text(encoding="utf-8"))["value"]
    with tree.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(tree.structure_id))
            .values(planning_start_on=EXAMPLE_START)
        )
    before = tree.api.get(f"{tree.path}/nodes", headers=tree.stage.manager.headers).json()
    assert before["items"] == []
    listed = tree.api.get(tree.path.rsplit("/", 1)[0], headers=tree.stage.manager.headers).json()
    read_counter = next(
        each["lock_version"] for each in listed if each["structure_id"] == tree.structure_id
    )
    written = generated(tree)

    def shape(body: dict[str, Any], label: str) -> list[dict[str, Any]]:
        """Give the nodes without their identifiers: their places, links and facets.

        The properties the example writes are compared, the optional ones it leaves out are not.
        """
        rows = {each["node_id"]: each["row_number"] for each in body["nodes"]}
        shaped: list[dict[str, Any]] = []
        for each, stated in zip(body["nodes"], example["nodes"], strict=True):
            task = {
                name: (value.replace(label, "<project>") if isinstance(value, str) else value)
                for name, value in each["task"].items()
                if name in stated["task"] and name not in {"order_item_id", "work_package_id"}
            }
            attached = [each["task"].get("order_item_id"), each["task"].get("work_package_id")]
            shaped.append(
                {
                    "position": each["position"],
                    "row_number": each["row_number"],
                    "level": each["level"],
                    "parent": rows.get(each["parent_id"]),
                    "lock_version": each["lock_version"],
                    "task": task,
                    "attached": [value is not None for value in attached],
                    "predecessors": [
                        (link["predecessor_row_number"], link["link_type"], link["lag"])
                        for link in each.get("predecessors", [])
                    ],
                    "computed_fields": each["computed_fields"],
                    "editable_fields": each["editable_fields"],
                }
            )
        return shaped

    assert shape(written, PROJECT_LABEL) == shape(example, EXAMPLE_LABEL)
    assert written["ancestors"] == example["ancestors"] == []
    assert written["rescheduled"] == example["rescheduled"] == []
    assert written["reinflated"] == example["reinflated"] == []
    assert written["totals"] == example["totals"]
    # The structure is born at 1, as every resource (E-16, #2542), and the generation takes it to
    # 2, the counter the example writes.
    assert read_counter == 1
    assert written["structure_lock_version"] == example["structure_lock_version"] == 2


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_work_breakdown_changed_afterwards_moves_and_deletes_no_task(tree: Tree) -> None:
    # « Renommer un poste ensuite ne change aucune tâche ; le supprimer ne déplace ni ne supprime
    # aucune tâche, et retire le seul rattachement de celle qui le portait (WF-PLA-0170). »
    lotted(tree, ("Lot", [("Poste", ["Plan"])]))
    written = generated(tree)
    before = labels(written)

    def rename(packages: list[dict[str, Any]]) -> None:
        packages[0]["order_items"][0]["label"] = "Poste renommé"

    rewritten(tree, rename)
    renamed = {each["task"]["label"]: each for each in tree.items()}
    assert list(renamed) == before
    assert renamed["Poste"]["task"]["work_breakdown_label"] == "Poste renommé"
    assert renamed["Poste"]["task"]["order_item_id"] is not None

    def remove(packages: list[dict[str, Any]]) -> None:
        packages[0]["order_items"] = []

    rewritten(tree, remove)
    kept = {each["task"]["label"]: each for each in tree.items()}
    # Removed, the item leaves its summary where it was and only its attachment goes.
    assert list(kept) == before
    assert [each["node_id"] for each in tree.items()] == [
        each["node_id"] for each in written["nodes"]
    ]
    assert [each["parent_id"] for each in tree.items()] == [
        each["parent_id"] for each in written["nodes"]
    ]
    task = kept["Poste"]["task"]
    assert (task["order_item_id"], task["work_package_id"]) == (None, None)
    assert kept["Lot"]["task"]["work_package_id"] is not None


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_work_package_without_an_order_item_gives_a_summary_and_its_end_milestone(
    tree: Tree,
) -> None:
    lotted(tree, ("Lot", []))
    written = generated(tree)
    assert labels(written) == ["Lot", "Fin de « Lot »"]
    assert follows(written) == {}
    assert written["totals"]["task_count"] == 2


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_work_breakdown_of_the_longest_labels_gives_milestones_that_fit(tree: Tree) -> None:
    longest = "L" * 300
    lotted(tree, (longest, [(longest, [longest])]))
    written = generated(tree)
    assert [len(label) for label in labels(written)] == [300, 300, 300, 300, 300]
    assert labels(written)[3].startswith("Fin de « LLL")
    assert labels(written)[3].endswith("… »")


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_end_milestone_of_a_label_that_leaves_room_for_its_words_keeps_it_whole(
    tree: Tree,
) -> None:
    whole = "é" * 289
    lotted(tree, (whole, []))
    written = generated(tree)
    assert labels(written) == [whole, f"Fin de « {whole} »"]


# --- Judged first, in the order of the command ------------------------------------------------


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_structure_that_has_a_task_refuses_the_skeleton_and_writes_nothing(tree: Tree) -> None:
    # « Elle n’est plus proposée dès que la structure principale comporte une tâche »
    tree.made("Études")
    answer = generate(tree)
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "main_structure_without_tasks"},
    )
    assert tree.labels() == ["Études"]


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_skeleton_generated_is_not_offered_again(tree: Tree) -> None:
    generated(tree)
    labels_before = tree.labels()
    assert refusal(generate(tree)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "main_structure_without_tasks"},
    )
    assert tree.labels() == labels_before


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_structure_with_tasks_is_named_before_the_background_task_that_runs(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    # « …`main_structure_without_tasks` puis `no_background_task_running` »
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    # The revision is still a draft while the marking runs, and has no task: the task is named.
    assert refusal(generate(tree)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    # A structure that has a task as well: its own condition comes first.
    with stage.owner.begin() as connection:
        project_id = UUID(stage.project["project_id"])
        insert_task(
            connection, project_id, UUID(tree.revision["revision_id"]), UUID(tree.structure_id)
        )
    assert refusal(generate(tree))[2] == {"missing_condition": "main_structure_without_tasks"}


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_marked_revision_refuses_the_skeleton_by_revision_draft_alone(
    tree: Tree, stage: Scene
) -> None:
    # « …`revision_draft` sur une révision marquée »
    tree.made("Études")
    mark(stage, tree.revision)
    assert refusal(generate(tree)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    assert refusal(generate(tree))[2] == {"missing_condition": "project_not_terminal"}


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_skeleton_is_not_generated_on_a_revision_of_another_project_or_unknown(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    unknown = api.post(f"{path}/{UUID(int=7)}/{SKELETON}", headers=stage.manager.headers)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    other = f"{PROJECTS}/{UUID(int=9)}/revisions/{tree.revision['revision_id']}/{SKELETON}"
    assert refusal(api.post(other, headers=stage.manager.headers))[:2] == (404, "NOT_FOUND")
    assert tree.labels() == []


@pytest.mark.requirement("WF-ADM-0110-A")
def test_who_may_not_write_the_planning_does_not_generate_it(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    assert refusal(generate(tree, stage.reader))[:2] == (403, "PERMISSION_MISSING")
    seeing = person(stage.database, realm, "planning.read", "planning.write", "all_projects_read")
    assert refusal(generate(tree, seeing))[:2] == (403, "NOT_CONTRIBUTOR")
    assert refusal(generate(tree, stage.outsider))[:2] == (404, "NOT_FOUND")
    reading = person(stage.database, realm, "project_settings.read", "planning.read")
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(generate(tree, reading)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "planning.write"},
    )
    assert generate(tree, stage.participant).status_code == 201


# --- The commands that say it in advance ------------------------------------------------------


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_revision_lists_the_skeleton_after_the_entry_of_the_planning_until_it_has_a_task(
    tree: Tree,
) -> None:
    # « Elle n’est plus proposée dès que la structure principale comporte une tâche »
    listed = [each["command"] for each in revision_of(tree)["available_commands"]]
    assert listed[:2] == ["edit_planning", "generate_skeleton"]
    assert commands(revision_of(tree))["generate_skeleton"] == (True, [])
    tree.made("Études")
    assert commands(revision_of(tree))["generate_skeleton"] == (
        False,
        ["main_structure_without_tasks"],
    )
    mark(tree.stage, tree.revision)
    assert commands(revision_of(tree))["generate_skeleton"] == (False, ["revision_draft"])


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_revision_names_the_structure_with_tasks_before_the_background_task(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    tree.made("Études")
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    assert commands(revision_of(tree))["generate_skeleton"] == (
        False,
        ["main_structure_without_tasks", "no_background_task_running"],
    )


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_project_without_a_revision_lists_the_skeleton_judged_on_the_revision_to_open(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    listed = api.get(path, headers=stage.manager.headers).json()
    # Listed just before the imports of a revision (``ProjectCommand``).
    assert [each["command"] for each in listed["available_commands"]][-5:] == [
        "exclude_cost_lines",
        "generate_skeleton",
        "import_planning",
        "import_estimate",
        "import_remaining",
    ]
    assert commands(listed)["generate_skeleton"] == (True, [])
    # Listed to whoever holds the planning permission, unavailable to who cannot open a revision.
    writing = person(
        stage.database, realm, "planning.read", "planning.write", "project_settings.read"
    )
    contribute(stage.database, stage.project["project_id"], writing, "contributor")
    seen = api.get(path, headers=writing.headers).json()
    assert commands(seen)["generate_skeleton"] == (False, ["may_create_revision"])
    assert "generate_skeleton" not in commands(api.get(path, headers=stage.reader.headers).json())
    # As soon as a revision is in progress, the project no longer lists it: the revision does.
    opened(api, stage)
    assert "generate_skeleton" not in commands(api.get(path, headers=stage.manager.headers).json())


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_project_judges_the_skeleton_on_the_last_marked_revision_that_its_opening_copies(
    tree: Tree,
) -> None:
    tree.made("Études")
    mark(tree.stage, tree.revision)
    seen = project_of(tree)
    assert seen["current_revision_id"] is None
    assert commands(seen)["generate_skeleton"] == (False, ["main_structure_without_tasks"])
    # The revision opened is that copy, and says the same.
    copy = Tree(tree.api, tree.stage, opened(tree.api, tree.stage))
    assert copy.labels() == ["Études"]
    assert commands(revision_of(copy))["generate_skeleton"] == (
        False,
        ["main_structure_without_tasks"],
    )


# --- The history and the rows -----------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_skeleton_is_one_entry_of_the_history_and_its_counter_is_the_next_entrys(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    lotted(tree, ("Lot", [("Poste", ["Plan"])]))
    writer = signed_in(stage, realm)
    answer = generate(tree, writer)
    assert answer.status_code == 201, answer.text
    written = answer.json()
    kept = entries(stage)
    assert [(each.kind, len(each.node_ids)) for each in kept] == [("node_create", 5)]
    assert {str(each) for each in kept[0].node_ids} == {
        each["node_id"] for each in written["nodes"]
    }
    # The next entry carries the counter the answer gave.
    node = written["nodes"][0]
    changed = tree.change(node, writer, label="Lot renommé")
    assert changed.status_code == 200, changed.text
    after = tree.api.get(
        f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}/structures",
        headers=stage.manager.headers,
    ).json()
    assert after[0]["lock_version"] == written["structure_lock_version"] + 1


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_links_and_the_nodes_are_those_of_the_main_structure_of_the_revision(
    tree: Tree, stage: Scene
) -> None:
    lotted(tree, ("Lot", [("Poste", ["Plan", "Note"])]))
    written = generated(tree)
    with stage.database.transaction() as session:
        nodes = session.scalars(
            select(Node).where(Node.revision_id == UUID(tree.revision["revision_id"]))
        ).all()
        links = session.scalars(select(TaskLink)).all()
    assert {str(each.id) for each in nodes} == {each["node_id"] for each in written["nodes"]}
    assert {each.structure_id for each in nodes} == {UUID(tree.structure_id)}
    assert {each.lineage_id for each in nodes} == {each.id for each in nodes}
    assert len(links) == 3
    assert {(each.link_type, each.lag_unit, each.in_conflict) for each in links} == {
        ("finish_to_start", "d", False)
    }


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_the_project_names_the_background_task_before_the_tasks_of_the_revision_to_open() -> None:
    held = {"planning.write", "revisions.write"}
    busy = Running(no_task_running=False, mapping_complete=True, opening_has_tasks=True)
    listed = dict(commands_of(held, "contributor", "pricing", None, running=busy))
    assert listed["generate_skeleton"] == (
        "no_background_task_running",
        "main_structure_without_tasks",
    )
    # Nothing is listed to who cannot write the planning, nor on a project with a revision.
    idle = Running(no_task_running=True, mapping_complete=True)
    assert "generate_skeleton" not in dict(
        commands_of({"revisions.write"}, "contributor", "pricing", None, running=idle)
    )
    assert "generate_skeleton" not in dict(
        commands_of(held, "contributor", "pricing", UUID(int=1), running=idle)
    )
