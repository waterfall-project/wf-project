# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the summary tasks and its PNG, through the service (US-1440/L2).

``listNodes`` with ``summaries_only`` and ``max_level`` on a plan of four levels and on one without
summary, then ``requestExport`` of the kind ``task_tree_image``: the worker draws the image, which
``getBackgroundTaskResult`` serves, with the header in the language of the account that asked; an
image beyond the ceiling of pixels fails the task without being drawn. Every answer is checked
against the contract. The drawing itself is tested without a database in ``test_task_tree_image``.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from nodes_support import Tree, opened, scheduled_at
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import update
from sqlalchemy.orm import Session
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.planning import task_tree_image
from waterfall.core.planning.interface import task_tree
from waterfall.core.planning.task_tree_image import TreeNode, render_task_tree_image
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.installation import read_settings
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.worker.exchanges import ExportTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from datetime import date

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.core.planning.task_tree_image import TreeLayout
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
TOO_LARGE = "TASK_TREE_IMAGE_TOO_LARGE"
PROJECT_LABEL = "Modernisation du poste de commande"
MILESTONE = {"duration": {"value": "0", "unit": "d"}}
CURRENT = {"fr": "révision courante", "en": "current revision"}
STUDIES = TreeNode(
    "Études", (TreeNode("Conception", (TreeNode("Schémas", (TreeNode("Relecture"),)),)),)
)
SITE = TreeNode("Chantier", (TreeNode("Pose"),))


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give what the application reaches: the queue of the test, and a bucket to keep files in."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the application that deposits its tasks and keeps its files for the test."""
    app = create_app(services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test that runs the exports, into the bucket of the test."""
    queue.prepare()
    return Worker(database, queue, {"export": ExportTask(backups_bucket)}, "worker", AT_ONCE)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def four_levels(tree: Tree) -> None:
    """Make a plan of four levels with leaves and milestones among its summaries.

    Études (1) > Conception (2) > Schémas (3) > Relecture (4) > Relecture finale (a leaf), and a
    milestone under Études; Chantier (1) > Pose (2) > Câblage (a leaf); Essais (a leaf) and
    Livraison (a milestone) at the first level.
    """
    made: dict[str, dict[str, Any]] = {}

    def add(label: str, parent: str | None = None, **body: Any) -> None:
        parent_id = None if parent is None else made[parent]["node_id"]
        made[label] = tree.made(label, parent_id=parent_id, **body)

    add("Études")
    add("Conception", "Études")
    add("Schémas", "Conception")
    add("Relecture", "Schémas")
    add("Relecture finale", "Relecture")
    add("Chantier")
    add("Pose", "Chantier")
    add("Câblage", "Pose")
    add("Essais")
    add("Livraison", task=MILESTONE)
    add("Jalon d'études", "Études", task=MILESTONE)


def speak(owner: Engine, user_id: UUID, language: str) -> None:
    """Set the language an account displays, as its holder does."""
    with owner.begin() as connection:
        connection.execute(
            update(UserAccount)
            .where(UserAccount.id == user_id)
            .values(display_preferences={"language": language})
        )


def drawn(
    columns: tuple[TreeNode, ...], language: str, day: date, depth: int, revision: str | None = None
) -> bytes:
    """Draw the tree these inputs say, as the exporter must: the PNG the worker has to give."""
    return render_task_tree_image(
        project=TreeNode(PROJECT_LABEL, columns),
        depth=depth,
        language=language,
        revision=revision or CURRENT[language],
        computed_on=day,
    )


def exported(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, **body: Any
) -> tuple[str, dict[str, Any]]:
    """Request the image of the tree of the revision, have the worker run it; give the task."""
    path = f"{PROJECTS}/{stage.project['project_id']}/exports"
    sent = {"kind": "task_tree_image", "revision_id": tree.revision["revision_id"], **body}
    asked = api.post(path, headers=stage.manager.headers, json=sent)
    assert asked.status_code == 202, asked.text
    task_id = asked.json()["task_id"]
    assert worker.step()
    done = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers)
    assert done.status_code == 200, done.text
    return task_id, done.json()


def downloaded(api: ContractClient, stage: Scene, task_id: str) -> Any:
    """Download the result of an export as the manager does."""
    answer = api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)
    assert answer.status_code == 200
    assert answer.headers["content-type"] == "image/png"
    return answer


@pytest.mark.requirement("WF-PLA-0110-A")
def test_the_tree_at_level_two_holds_the_summaries_of_the_first_two_levels_of_a_four_level_plan(
    tree: Tree,
) -> None:
    four_levels(tree)
    answer = tree.read("?kinds=task&summaries_only=true&max_level=2")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert [(item["task"]["label"], item["level"]) for item in body["items"]] == [
        ("Études", 1),
        ("Conception", 2),
        ("Chantier", 1),
        ("Pose", 2),
    ]
    # The depth is the structure's, whatever level is asked: the front reads it from here.
    assert body["meta"]["summary_depth"] == 4
    assert tree.read("?summaries_only=true&max_level=1").json()["meta"]["summary_depth"] == 4
    assert tree.labels("?summaries_only=true&max_level=4") == [
        "Études",
        "Conception",
        "Schémas",
        "Relecture",
        "Chantier",
        "Pose",
    ]


@pytest.mark.requirement("WF-PLA-0110-A")
def test_no_milestone_and_no_leaf_appears_whatever_the_level_asked(tree: Tree) -> None:
    four_levels(tree)
    for level in range(1, 7):
        items = tree.items(f"?kinds=task&summaries_only=true&max_level={level}")
        assert items
        assert all(item["task"]["is_summary"] for item in items)
        assert not {"Livraison", "Jalon d'études", "Essais", "Câblage", "Relecture finale"} & {
            item["task"]["label"] for item in items
        }
    # Without the filter the leaves are there: the check above discriminates.
    assert "Livraison" in tree.labels("?max_level=1")


@pytest.mark.requirement("WF-PLA-0110-A")
def test_a_plan_of_leaves_alone_has_a_summary_depth_of_nought_and_no_node_in_the_tree(
    tree: Tree,
) -> None:
    for label in ("Essais", "Recette"):
        tree.made(label)
    tree.made("Livraison", task=MILESTONE)
    answer = tree.read("?kinds=task&summaries_only=true&max_level=3")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["items"] == []
    assert body["meta"]["summary_depth"] == 0
    assert body["totals"]["task_count"] == 0


@pytest.mark.requirement("WF-PLA-0120-A")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_the_image_is_drawn_by_the_worker_and_downloaded_as_png_in_the_account_language(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker, language: str
) -> None:
    four_levels(tree)
    speak(stage.owner, stage.manager.user_id, language)
    task_id, done = exported(api, stage, worker, tree, depth=2)
    assert (done["kind"], done["status"], done["problem"]) == ("export", "succeeded", None)
    answer = downloaded(api, stage, task_id)
    disposition = answer.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="task-tree')
    assert disposition.endswith('.png"')
    columns = (
        TreeNode("Études", (TreeNode("Conception"),)),
        TreeNode("Chantier", (TreeNode("Pose"),)),
    )
    day = scheduled_at(tree).date()
    assert answer.content == drawn(columns, language, day, 2)
    # The header is the language's: the other one draws another image.
    other = "en" if language == "fr" else "fr"
    assert answer.content != drawn(columns, other, day, 2)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_content_depends_only_on_the_depth_and_a_depth_beyond_the_plan_gives_it_whole(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker
) -> None:
    four_levels(tree)
    speak(stage.owner, stage.manager.user_id, "en")
    day = scheduled_at(tree).date()

    def image(**body: Any) -> bytes:
        task_id, _ = exported(api, stage, worker, tree, **body)
        return downloaded(api, stage, task_id).content

    whole = image()
    assert whole == drawn((STUDIES, SITE), "en", day, 4)
    assert image(depth=4) == whole
    assert image(depth=9) == whole
    shallow = drawn((TreeNode("Études"), TreeNode("Chantier")), "en", day, 1)
    assert image(depth=1) == shallow
    assert shallow != whole


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_plan_without_summary_exports_the_node_of_the_project_alone(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker
) -> None:
    tree.made("Essais")
    speak(stage.owner, stage.manager.user_id, "fr")
    task_id, done = exported(api, stage, worker, tree)
    assert done["status"] == "succeeded"
    answer = downloaded(api, stage, task_id)
    assert answer.content == drawn((), "fr", scheduled_at(tree).date(), 1)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_an_account_that_follows_the_default_is_served_in_the_language_of_the_installation(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker, database: Database
) -> None:
    tree.made("Essais")
    with database.transaction() as session:
        language = read_settings(session).default_language
    task_id, _ = exported(api, stage, worker, tree)
    answer = downloaded(api, stage, task_id)
    assert answer.content == drawn((), language, scheduled_at(tree).date(), 1)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_header_names_a_marked_revision_by_its_version_name(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker
) -> None:
    studies = tree.made("Études")
    tree.made("Relevés", parent_id=studies["node_id"])
    speak(stage.owner, stage.manager.user_id, "en")
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        revision_id = UUID(tree.revision["revision_id"])
        mark_revision(session, revision_id, "v1.0", None, Act(None, utc_now()))
    task_id, done = exported(api, stage, worker, tree)
    assert done["status"] == "succeeded"
    answer = downloaded(api, stage, task_id)
    day = scheduled_at(tree).date()
    assert answer.content == drawn((TreeNode("Études"),), "en", day, 1, revision="v1.0")


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_label_with_line_breaks_is_drawn_on_one_line_as_the_same_label_without_them(
    api: ContractClient, stage: Scene, tree: Tree, worker: Worker
) -> None:
    # The service lets a break into a label (#2482): the exporter brings it back to one line.
    tree.made("Études\nde  détail\r\n\tfinales")
    speak(stage.owner, stage.manager.user_id, "en")
    task_id, done = exported(api, stage, worker, tree)
    assert done["status"] == "succeeded"
    answer = downloaded(api, stage, task_id)
    day = scheduled_at(tree).date()
    assert answer.content == drawn((), "en", day, 1)  # a leaf: the node of the project alone
    leaf = tree.made("Fin", parent_id=tree.items()[0]["node_id"])
    assert leaf["task"]["label"] == "Fin"
    task_id, _ = exported(api, stage, worker, tree)
    again = downloaded(api, stage, task_id)
    assert again.content == drawn((TreeNode("Études de détail finales"),), "en", day, 1)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_an_image_beyond_the_ceiling_of_pixels_fails_the_task_with_its_code_and_is_not_drawn(
    stage: Scene,
    tree: Tree,
    worker: Worker,
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    four_levels(tree)
    laid: list[TreeLayout] = []

    def refuse_to_draw(layout: TreeLayout) -> bytes:
        laid.append(layout)
        return b""

    monkeypatch.setattr(task_tree_image, "MAX_PIXELS", 10_000)
    monkeypatch.setattr(task_tree, "draw_task_tree", refuse_to_draw)
    task_id, done = exported(tree.api, stage, worker, tree, depth=4)
    assert (done["status"], done["result_url"]) == ("failed", None)
    assert (done["problem"]["code"], done["problem"]["status"]) == (TOO_LARGE, 422)
    assert laid == []
    assert backups_bucket.size(f"exports/{task_id}.png") is None
    gone = tree.api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)
    assert gone.status_code == 409
