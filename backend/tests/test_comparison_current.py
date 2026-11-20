# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of a revision, current or marked, with a marked base (US-2320/L3, WF-REV-0080).

``compareRevisions`` reads the revision read in its state of the moment when it is current —
its columns, nothing kept of it (US-2220) —, and the base in its reading kept (US-2270); a current
base is refused. Each node is judged on every value it carries, whatever ``fields`` reads, and a
modified node gives what its base carried of what differs (``base``), reduced to the fields read.
The comparison is read by whoever consults one of the three grids. The Vérifs of WF-REV-0080-A
that US-2320 takes as criteria are proved on PRJ-001 of the witness, its current revision 102
compared with the reference 101 it was opened from; its own criteria on a project of a test, which
is not In progress: a revision opened from it carries no remaining to commit before the review
(``previous_*``), a value that would differ. Every answer is checked against the contract.
"""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, opened
from projects_support import PROJECTS, Person, Scene, contribute, person
from projects_support import scene as make_scene
from sqlalchemy import select
from test_comparison import by_label, compared, follow, labour, mark, material, subproject
from test_kept_readings import kept_row, place_of
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102, read
from test_witness_tasks import structure_of

from waterfall.api.comparison import comparison_body, kept_comparison
from waterfall.api.nodes import node_body, read_body
from waterfall.core.estimate.interface import ComparisonAsked, compare_revisions
from waterfall.core.planning.interface import NodeFilters
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REQUIREMENT = "WF-REV-0080-A"
GRIDS = ("planning.read", "estimate.read", "remaining.read")
# Three tasks of PRJ-001 unchanged from the reference 101 to the current revision 102, not
# started, under « Installation sur site »; and « Poste de commande », another summary.
SITE = "01926f3a-7c00-7000-8000-000000000561"
MOUNTING = "01926f3a-7c00-7000-8000-000000000562"
COMMISSIONING = "01926f3a-7c00-7000-8000-000000000565"
CONTROL = "01926f3a-7c00-7000-8000-000000000551"


# --- A project of a test -------------------------------------------------------------------------


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
    """Mark an offer of tasks, lines and a link; open the current revision from it, unchanged."""
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    lines = Lines(tree)
    studies = tree.made("Études")
    design = tree.made("Conception", parent_id=studies["node_id"])
    lines.made(design, **labour(costs, "Conception — Ingénieur"))
    sent = subproject(api, stage, "CMD", "Poste de commande")
    plans = tree.made("Plans", parent_id=studies["node_id"])
    lines.made(plans, **material(costs, "Tirages", "350.00"), subproject_id=sent)
    follow(tree, plans, design)
    tree.made("Réception")
    mark(stage, offer, "v1.0")
    current = opened(api, stage)
    return offer, Tree(api, stage, current)


def asked(offer: dict[str, Any], current: Tree) -> tuple[dict[str, Any], dict[str, Any]]:
    """Give the offer for base, and the current revision read."""
    return offer, current.revision


@pytest.mark.requirement(REQUIREMENT)
def test_a_revision_opened_and_not_modified_compares_unchanged_to_its_source_node_by_node(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # Nothing of a node that changes from one revision to the other without the node changing —
    # its identifiers, its counter, its row, the lists of what is computed or enterable — marks
    # it: read whole, from what is kept, and filtered, from the rows; the source with itself too.
    offer, current = pair
    for query in ("", "&kinds=task", "&fields=task.label,estimate_line.label"):
        found = compared(api, stage, asked(offer, current), query)
        assert len(found["items"]) == len(current.items(query.replace("&", "?", 1)))
        assert {(each["difference"], tuple(each["changes"])) for each in found["items"]} == {
            ("unchanged", ())
        }
        assert {each["base"] is None for each in found["items"]} == {True}
    itself = compared(api, stage, (offer, offer))
    assert {(each["difference"], each["base"]) for each in itself["items"]} == {("unchanged", None)}


@pytest.mark.requirement(REQUIREMENT)
def test_a_task_renamed_alone_is_modified_and_its_mark_does_not_depend_on_the_fields_read(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « une tâche seulement renommée l'est » : read after the write, the current revision carries
    # its mark, nothing kept of the reading before; ``other`` and the label of the base, which the
    # planning, reading the dates alone, does not read: the same mark, an empty base.
    offer, current = pair
    assert compared(api, stage, asked(offer, current))["items"][0]["difference"] == "unchanged"
    current.changed(by_label(current.items())["Réception"], label="Réception usine")
    found = by_label(compared(api, stage, asked(offer, current))["items"])
    renamed = found["Réception usine"]
    assert (renamed["difference"], renamed["changes"]) == ("modified", ["other"])
    assert renamed["base"] == {"task": {"label": "Réception"}}
    planned = compared(api, stage, asked(offer, current), "&fields=task.start,task.finish")
    last = planned["items"][-1]
    assert (last["difference"], last["changes"], last["base"]) == ("modified", ["other"], {})
    assert {each["difference"] for each in planned["items"][:-1]} == {"unchanged"}


@pytest.mark.requirement(REQUIREMENT)
def test_each_value_that_differs_gives_its_base_a_node_named_by_the_node_returned(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], Tree]
) -> None:
    # « pour une ligne, ses grandeurs et ses montants ; et toute autre colonne » : a line's hours
    # and amounts, its subproject with its label; a task's predecessor, named by the node of its
    # lineage the comparison returns and its row there; a task moved, its parent in the base, so
    # named.
    offer, current = pair
    nodes = by_label(current.items())
    Lines(current).changed(nodes["Conception — Ingénieur"], hours="12")
    Lines(current).changed(nodes["Tirages"], subproject_id=None)
    follow(current, nodes["Plans"], nodes["Réception"])
    moving = {
        "node_ids": [nodes["Conception"]["node_id"]],
        "parent_id": nodes["Réception"]["node_id"],
        "lock_version": counter(stage, current),
    }
    moved = api.post(f"{current.path}/nodes/move", headers=stage.manager.headers, json=moving)
    assert moved.status_code == 200, moved.text
    found = by_label(compared(api, stage, asked(offer, current))["items"])
    line = found["Conception — Ingénieur"]
    assert line["changes"] == ["budgeted_amount", "reestimated_amount", "other"]
    assert line["base"]["estimate_line"]["hours"] == "10"
    assert line["base"]["estimate_line"]["reestimated_amount"] == "650.00"
    assert found["Tirages"]["changes"] == ["subproject"]
    assert set(found["Tirages"]["base"]["estimate_line"]) == {"subproject_id", "subproject_label"}
    assert found["Tirages"]["base"]["estimate_line"]["subproject_label"] == "Poste de commande"
    [link] = found["Plans"]["base"]["predecessors"]
    design = found["Conception"]
    assert (link["predecessor_node_id"], link["predecessor_row_number"]) == (
        design["node_id"],
        design["row_number"],
    )
    assert "parent" in design["changes"]
    assert design["base"]["parent_id"] == found["Études"]["node_id"]


def counter(stage: Scene, tree: Tree) -> int:
    """Read the counter of a structure, which every write of its tree advances."""
    with stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


# --- PRJ-001 of the witness ----------------------------------------------------------------------


def comparing(base: UUID, read_one: UUID, query: str = "") -> str:
    """Give the path of the comparison of PRJ-001 of a revision read with a base."""
    return (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison"
        f"?from_revision_id={base}&to_revision_id={read_one}{query}"
    )


def writer(witness: Database, realm: TestRealm) -> Person:
    """Write a contributor of PRJ-001 who writes its planning."""
    who = person(witness, realm, "planning.read", "planning.write", name="Lou")
    contribute(witness, str(PRJ_001), who, "contributor")
    return who


def current_structure(witness: Database) -> tuple[str, int]:
    """Give the path of the main structure of the current revision 102, and its counter."""
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
        held = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == structure)
        )
    assert held is not None
    return f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}", held


def node_of(api: ContractClient, who: Person, path: str, node_id: str) -> dict[str, Any]:
    """Read a node of the current revision as it stands."""
    answer = api.get(f"{path}/nodes?subtree_of={node_id}&kinds=task", headers=who.headers)
    assert answer.status_code == 200, answer.text
    return next(each for each in answer.json()["items"] if each["node_id"] == node_id)


@pytest.mark.requirement(REQUIREMENT)
def test_a_task_moved_in_the_current_revision_is_presented_modified_with_its_former_summary(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » : the revision
    # read current, « Mise en service » moved under « Poste de commande », marked by its parent,
    # « Installation sur site » for parent in the base; both summaries modified.
    who = writer(witness, realm)
    path, held = current_structure(witness)
    moving = {"node_ids": [COMMISSIONING], "parent_id": CONTROL, "lock_version": held}
    moved = api.post(f"{path}/nodes/move", headers=who.headers, json=moving)
    assert moved.status_code == 200, moved.text
    found = {
        each["node_id"]: each
        for each in read(api, witness, realm, comparing(REVISION_101, REVISION_102))["items"]
    }
    commissioning = found[COMMISSIONING]
    assert (commissioning["difference"], commissioning["changes"][0]) == ("modified", "parent")
    assert commissioning["parent_id"] == CONTROL
    assert commissioning["base"]["parent_id"] == SITE
    assert found[SITE]["difference"] == found[CONTROL]["difference"] == "modified"


@pytest.mark.requirement(REQUIREMENT)
def test_a_finish_pushed_back_five_days_is_modified_and_brought_back_is_no_longer(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # « une tâche dont la fin y est repoussée de cinq jours est présentée modifiée, avec la date de
    # fin de la base ; la date ramenée à celle de la base, la tâche n'est plus présentée
    # modifiée. » : the first leaf of the current revision, not started and in automatic mode, that
    # the comparison with the 101 presents unchanged, whose finish five days later is a working day
    # — the mounting on site is modified by a line since the reference is the 101 the amendment 1
    # produced (EP-08).
    who = writer(witness, realm)
    path, _ = current_structure(witness)
    whole = read(api, witness, realm, comparing(REVISION_101, REVISION_102))["items"]
    target = next(
        each["node_id"]
        for each in whole
        if each["kind"] == "task"
        and each["difference"] == "unchanged"
        and not each["task"]["is_summary"]
        and each["task"]["scheduling_mode"] == "automatic"
        and each["task"]["progress"] == "not_started"
        and (date.fromisoformat(each["task"]["finish"]["date"]) + timedelta(days=5)).weekday() < 5
    )
    url = comparing(REVISION_101, REVISION_102, f"&subtree_of={target}")

    def mounting() -> dict[str, Any]:
        found = read(api, witness, realm, url)["items"]
        return next(each for each in found if each["node_id"] == target)

    def finishing(**sent: Any) -> None:
        body = {**sent, "lock_version": node_of(api, who, path, target)["lock_version"]}
        answer = api.patch(f"{path}/nodes/{target}/task", headers=who.headers, json=body)
        assert answer.status_code == 200, answer.text

    before = mounting()
    assert before["difference"] == "unchanged"
    task = before["task"]
    finish = task["finish"]
    later = date.fromisoformat(finish["date"]) + timedelta(days=5)
    # The dates of an automatic task are computed: it is entered manual, its finish with it.
    finishing(scheduling_mode="manual", finish={**finish, "date": later.isoformat()})
    pushed = mounting()
    assert (pushed["difference"], pushed["changes"][0]) == ("modified", "dates")
    assert pushed["task"]["finish"]["date"] == later.isoformat()
    assert pushed["base"]["task"]["finish"] == finish
    finishing(scheduling_mode=task["scheduling_mode"], duration=task["duration"])
    assert (mounting()["difference"], mounting()["base"]) == ("unchanged", None)


@pytest.mark.requirement(REQUIREMENT)
def test_the_offer_read_against_the_reference_presents_removed_the_tasks_the_reference_adds(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # « La comparaison d'une révision marquée à une révision marquée postérieure présente retirées
    # les tâches que la seconde ajoute. » : the offer 100 read, the reference 101 for base.
    added = read(api, witness, realm, comparing(REVISION_100, REVISION_101, "&difference=added"))
    query = "&difference=removed"
    removed = read(api, witness, realm, comparing(REVISION_101, REVISION_100, query))
    tasks = {
        each["lineage_id"]
        for each in added["items"]
        if each["kind"] == "task" and each["difference"] == "added"
    }
    assert tasks
    assert {
        each["lineage_id"]
        for each in removed["items"]
        if each["kind"] == "task" and each["difference"] == "removed"
    } == tasks
    assert all(each["editable_fields"] == [] for each in removed["items"] if each["base"] is None)


@pytest.mark.requirement(REQUIREMENT)
@pytest.mark.parametrize("permission", GRIDS)
def test_a_reader_of_a_grid_who_does_not_consult_the_revisions_reads_the_comparison(
    api: ContractClient, witness: Database, realm: TestRealm, permission: str
) -> None:
    # « Un utilisateur qui consulte le planning sans consulter les révisions y active une
    # comparaison. » : a contributor of PRJ-001 holding the permission of one grid alone, without
    # ``revisions.read``, compares the current revision with the reference; one holding none of
    # the three is refused it as a project it may not see (404), as an outsider is.
    reader = person(witness, realm, permission, name="Lou")
    contribute(witness, str(PRJ_001), reader, "contributor")
    url = comparing(REVISION_101, REVISION_102, f"&subtree_of={SITE}")
    answer = api.get(url, headers=reader.headers)
    assert answer.status_code == 200, answer.text
    assert answer.json()["items"][0]["node_id"] == SITE
    stranger = person(witness, realm, "risks.read", "revisions.read", name="Sacha")
    contribute(witness, str(PRJ_001), stranger, "contributor")
    refused = api.get(url, headers=stranger.headers)
    assert (refused.status_code, refused.json()["code"]) == (404, "NOT_FOUND")
    outsider = person(witness, realm, permission, name="Noa")
    assert api.get(url, headers=outsider.headers).status_code == 404


@pytest.mark.requirement(REQUIREMENT)
def test_the_current_revision_read_from_its_columns_is_the_body_of_its_rows_nothing_kept(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The base read in its reading kept, the current revision in its columns (US-2220): the same
    # body, to the byte, as read from the rows of both; nothing kept of the current revision.
    asked_of = ComparisonAsked(REVISION_101, REVISION_102, NodeFilters())
    with witness.transaction() as session:
        rows = bytes(
            read_body(
                comparison_body(compare_revisions(session, PRJ_001, asked_of, node_body), None)
            ).body
        )
        kept = kept_comparison(session, PRJ_001, asked_of, None)
        assert kept is not None
        assert bytes(read_body(kept).body) == rows
    assert kept_row(witness, place_of(witness, REVISION_102)) is None
    assert kept_row(witness, place_of(witness, REVISION_101)) is not None
    # The provision lines of 752 and 753, which the occurrence and the dismissal took away from the
    # 102, are removed (EP-08).
    found = read(api, witness, realm, comparing(REVISION_101, REVISION_102))
    assert {each["difference"] for each in found["items"]} == {
        "added",
        "modified",
        "removed",
        "unchanged",
    }
