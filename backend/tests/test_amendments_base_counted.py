# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential, priced with its revision and counted by nothing (US-3050/L2).

What prices or redates every structure of a revision writes the base with the others — a rate of
the reference, the inflation of the project, the budgeted amounts a designation refreshes —: a
differential no one wrote stays ``unchanged`` against it. What reads a revision by lineage reads its
main structure alone: the budgeted amount of a line is that of its lineage in the main structure
of the reference, not in a differential or a base. And what counts the nodes or the lines of a
revision or of a project leaves the base out: a subproject only a base bears is deleted, the
revision whose main structure and differential hold no task bears none, the key of the cache of
the indicators is that of the revision without its bases. The abandonment of a revision deletes
the bases of its differentials with every other row (WF-DAT-0010).
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import deleted, listed, node_labelled, on, opened_amendment
from estimate_support import YEAR, Costing, Lines, costing
from nodes_support import Tree, mark
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, Risks, costed, material
from sqlalchemy import delete, func, select, update

from waterfall.core.cost_settings.interface import set_hourly_rate
from waterfall.core.cost_settings.tables import HourlyRate
from waterfall.core.estimate.interface import forget_subproject, lines_stamp, subproject_is_cited
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.interface import revision_content_stamp
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.interface import revision_has_tasks_and_lines
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The labour line the tests add to the main structure, and the task in two years that bears one.
WIRING, LATER = "Câblage", "Exploitation"
WIRED, OPERATED = "Câblage MO", "Exploitation MO"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the labour one rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def labour(costs: Costing, label: str, hours: str = "10") -> dict[str, Any]:
    """Give a labour line of the role of the scene: one engineer for the hours said."""
    return {"label": label, "quantity": "1", "resource_role_id": str(costs.role), "hours": hours}


def base_id(project: Costed, structure_id: str) -> UUID:
    """Read the identifier of the base of a differential, around the service."""
    with project.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.id).where(CostStructure.differential_id == UUID(structure_id))
        )
    assert found is not None
    return found


def amounts(tree: Tree) -> dict[str, tuple[str, str | None]]:
    """Read the re-estimated and budgeted amounts of each line of a structure, by its label."""
    return {
        each["estimate_line"]["label"]: (
            each["estimate_line"]["reestimated_amount"],
            each["estimate_line"]["budgeted_amount"],
        )
        for each in tree.items()
        if each["kind"] == "estimate_line"
    }


def base_amounts(project: Costed, structure_id: UUID) -> dict[str, tuple[str, str | None]]:
    """Read the amounts of each line of a base, by its label, around the service."""
    with project.stage.database.transaction() as session:
        line = EstimateLine
        rows = session.execute(
            select(line.label, line.reestimated_amount, line.budgeted_amount)
            .join(Node, Node.id == line.node_id)
            .where(Node.structure_id == structure_id)
        )
        return {
            label: (str(amount), None if budgeted is None else str(budgeted))
            for label, amount, budgeted in rows
        }


def differences(tree: Tree) -> set[str]:
    """Read the marks a differential gives its nodes."""
    return {each["difference"] for each in tree.items()}


def set_inflation(api: ContractClient, stage: Scene, rate: str) -> None:
    """Give the project of the stage an inflation rate, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    answer = api.patch(
        path, headers=stage.manager.headers, json={"inflation_rate": rate, "lock_version": counter}
    )
    assert answer.status_code == 200, answer.text


def correct_rate(stage: Scene, costs: Costing, amount: str) -> None:
    """Correct the rate of labour of the year, as the cost settings do: the revisions follow."""
    with stage.database.transaction() as session:
        counter = session.scalar(
            select(HourlyRate.lock_version).where(
                HourlyRate.cost_category_id == costs.labour, HourlyRate.year == YEAR
            )
        )
        set_hourly_rate(
            session, (costs.labour, YEAR), Decimal(amount), counter, Act(None, utc_now())
        )


def designate(api: ContractClient, stage: Scene, revision_id: UUID) -> None:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {"revision_id": str(revision_id), "confirmed": True, "lock_version": counter}
    answer = api.put(f"{path}/reference-revision", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def next_revision(api: ContractClient, project: Costed) -> Costed:
    """Open the revision that follows a marked one; give the project costed as it stands in it."""
    revision = Risks(api, project).revision()
    tree = Tree(api, project.stage, revision)
    return replace(
        project,
        tree=tree,
        lines=Lines(tree),
        revision_id=UUID(revision["revision_id"]),
        structure_id=UUID(tree.structure_id),
    )


# --- What prices a revision ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_rate_and_an_inflation_written_after_the_opening_price_the_base_with_the_others(
    api: ContractClient, project: Costed, costs: Costing
) -> None:
    # « un différentiel n'est lu modifié que par ce qu'il désigne » : a rate of the reference and
    # the inflation of the project, written after its opening, price again the main structure, the
    # differential and its base alike — the differential, written by no one, stays unchanged.
    stage = project.stage
    tree, lines = project.tree, project.lines
    lines.made(tree.made(WIRING), **labour(costs, WIRED))
    later = tree.made(
        LATER,
        task={
            "scheduling_mode": "manual",
            "start": {"date": f"{YEAR + 2}-11-06"},
            "finish": {"date": f"{YEAR + 2}-11-07"},
        },
    )
    lines.made(later, **labour(costs, OPERATED))
    structure_id = opened_amendment(api, project)
    amendment = on(tree, structure_id)
    lines.changed(node_labelled(tree, WIRED), hours="30")
    before = amounts(tree)[OPERATED][0]
    assert amounts(amendment)[OPERATED][0] == before
    set_inflation(api, stage, "0.03")
    correct_rate(stage, costs, "70.00")
    main = amounts(tree)
    assert main[WIRED][0] == "2100.00"
    assert Decimal(main[OPERATED][0]) > Decimal("700.00") > Decimal(before)
    assert differences(amendment) == {"unchanged"}
    own = amounts(amendment)
    assert (own[WIRED][0], own[OPERATED][0]) == ("700.00", main[OPERATED][0])
    base = base_amounts(project, base_id(project, structure_id))
    assert {label: amount for label, (amount, _) in base.items()} == {
        label: amount for label, (amount, _) in own.items()
    }


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_budgeted_amount_is_read_on_the_main_structure_of_the_reference_and_written_on_all(
    api: ContractClient, project: Costed, costs: Costing
) -> None:
    # The reference holds a differential and its base, both left behind by the main structure: a
    # designation gives each line of the current revision — of its main structure, its differential
    # and its base — the budgeted amount of its lineage in the main structure of the reference;
    # the revision opened after takes it from there too. The differential stays unchanged.
    stage = project.stage
    tree, lines = project.tree, project.lines
    lines.made(tree.made(WIRING), **labour(costs, WIRED))
    opened_amendment(api, project, "Avenant de la référence")
    lines.changed(node_labelled(tree, WIRED), hours="30")
    mark(stage, tree.revision)
    current = next_revision(api, project)
    taken = next(
        each["structure_id"] for each in listed(api, current) if each["kind"] == "amendment"
    )
    designate(api, stage, project.revision_id)
    budgeted = "1950.00"
    assert amounts(current.tree)[WIRED] == ("1950.00", budgeted)
    amendment = on(current.tree, taken)
    assert amounts(amendment)[WIRED] == ("650.00", budgeted)
    assert base_amounts(current, base_id(current, taken))[WIRED] == ("650.00", budgeted)
    assert differences(amendment) == {"unchanged"}
    mark(stage, current.tree.revision, "v2.0")
    following = next_revision(api, current)
    assert amounts(following.tree)[WIRED][1] == budgeted


# --- What counts a revision or a project ---------------------------------------------------------


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_a_base_alone_bears_is_deleted(api: ContractClient, project: Costed) -> None:
    # « ligne retirée de la principale et du différentiel, sous-projet supprimable » : the base of
    # the differential still holds the line, which no operation serves; the subproject is neither
    # estimated nor refused, and the line of the base bears it no more once it is deleted.
    stage = project.stage
    risks = Risks(api, project)
    subproject = risks.subproject("SP1")
    task = node_labelled(project.tree, MAKING)
    line = {**material(project.costs, "Grue", "50.00"), "subproject_id": subproject}
    project.lines.made(task, **line)
    structure_id = opened_amendment(api, project)
    deleted(project.tree, "Grue", stage.manager)
    deleted(on(project.tree, structure_id), "Grue", stage.manager)
    base = base_id(project, structure_id)
    assert "Grue" in base_amounts(project, base)
    path = f"{PROJECTS}/{project.project_id}/subprojects"
    held = api.get(path, headers=stage.manager.headers).json()
    found = next(each for each in held if each["subproject_id"] == subproject)
    command = next(each for each in found["available_commands"] if each["command"] == "delete")
    assert (command["is_available"], command["missing_conditions"]) == (True, [])
    answer = api.delete(
        f"{path}/{subproject}",
        headers=stage.manager.headers,
        params={"lock_version": found["lock_version"]},
    )
    assert answer.status_code == 204, answer.text
    with stage.database.transaction() as session:
        kept = session.scalar(
            select(EstimateLine.subproject_id)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == base, EstimateLine.label == "Grue")
        )
    assert kept is None


def base_line_with_subproject(api: ContractClient, project: Costed) -> tuple[str, str, UUID]:
    """Leave a subproject borne by the line of a base alone; give it, the differential, the base.

    The line is written in the main structure before the differential opens, then removed from
    the main structure and from the differential: the base still holds it.
    """
    subproject = Risks(api, project).subproject("SP1")
    line = {**material(project.costs, "Grue", "50.00"), "subproject_id": subproject}
    project.lines.made(node_labelled(project.tree, MAKING), **line)
    structure_id = opened_amendment(api, project)
    deleted(project.tree, "Grue", project.stage.manager)
    deleted(on(project.tree, structure_id), "Grue", project.stage.manager)
    return subproject, structure_id, base_id(project, structure_id)


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_base_a_merged_differential_keeps_in_its_marked_revision_cites_its_subproject(
    api: ContractClient, project: Costed
) -> None:
    # « Celle d'un sous-projet référencé par une révision marquée est refusée » (#4212): the base a
    # merged differential keeps in the revision its merge marks is never written, and its line
    # holds the key of the subproject — the subproject is cited, its deletion unavailable, though
    # no line any operation serves names it; while the revision is current, the base does not
    # cite it.
    stage = project.stage
    subproject, structure_id, _ = base_line_with_subproject(api, project)
    with stage.database.transaction() as session:
        cited = subproject_is_cited(session, project.project_id, [UUID(subproject)])
    assert cited == frozenset()
    with stage.database.transaction() as session:
        session.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(structure_id))
            .values(is_merged=True)
        )
    mark(stage, project.tree.revision)
    with stage.database.transaction() as session:
        cited = subproject_is_cited(session, project.project_id, [UUID(subproject)])
    assert cited == {UUID(subproject)}
    path = f"{PROJECTS}/{project.project_id}/subprojects"
    held = api.get(path, headers=stage.manager.headers).json()
    found = next(each for each in held if each["subproject_id"] == subproject)
    command = next(each for each in found["available_commands"] if each["command"] == "delete")
    assert (command["is_available"], command["missing_conditions"]) == (
        False,
        ["subproject_not_cited"],
    )


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_line_of_a_base_held_by_the_session_keeps_its_subproject_forgotten_at_its_flush(
    api: ContractClient, project: Costed
) -> None:
    # #4212: the deletion of a subproject a line of a base alone bears forgets it on that line; a
    # line of the base loaded in the transaction that forgets the subproject is synchronised with
    # it, and a change of another of its columns, flushed after, does not write the key back.
    subproject, _, base = base_line_with_subproject(api, project)
    with project.stage.database.transaction() as session:
        loaded = session.scalars(
            select(EstimateLine)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == base, EstimateLine.label == "Grue")
        ).one()
        assert loaded.subproject_id == UUID(subproject)
        forget_subproject(session, project.project_id, UUID(subproject))
        assert loaded.subproject_id is None
        loaded.label = "Grue mobile"
        session.flush()
    assert base_amounts(project, base).keys() == {"Plans", "Fabrication", "Grue mobile"}
    with project.stage.database.transaction() as session:
        kept = session.scalar(
            select(EstimateLine.subproject_id).where(EstimateLine.node_id == loaded.node_id)
        )
    assert kept is None


@pytest.mark.requirement("WF-CYC-0030-A")
def test_a_revision_whose_tasks_only_a_base_holds_bears_no_task_nor_line(
    api: ContractClient, project: Costed
) -> None:
    # The tasks taken from the main structure and from the differential: the base still holds
    # them, which the designation of the reference does not count.
    stage = project.stage
    structure_id = opened_amendment(api, project)
    for tree in (project.tree, on(project.tree, structure_id)):
        for label in (STUDY, MAKING):
            deleted(tree, label, stage.manager)
    with stage.database.transaction() as session:
        assert session.scalar(
            select(func.count())
            .select_from(Node)
            .where(Node.structure_id == base_id(project, structure_id))
        )
        bearing = revision_has_tasks_and_lines(session, project.project_id, project.revision_id)
        assert bearing is False


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_key_of_the_cache_of_the_indicators_does_not_count_the_base(
    api: ContractClient, project: Costed
) -> None:
    # « l'empreinte ne compte pas la base » : the stamps of the nodes and of the lines are the same
    # with the base and once it is deleted around the service — its nodes, its tasks and its lines
    # would change the counts.
    stage = project.stage
    structure_id = opened_amendment(api, project)
    on(project.tree, structure_id).made("Essais")

    def stamps() -> tuple[object, object]:
        with stage.database.transaction() as session:
            return (
                revision_content_stamp(session, project.project_id, project.revision_id),
                lines_stamp(session, project.project_id, project.revision_id),
            )

    with_base = stamps()
    base = base_id(project, structure_id)
    with stage.owner.begin() as connection:
        nodes = select(Node.id).where(Node.structure_id == base)
        connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(nodes)))
        connection.execute(delete(Task).where(Task.node_id.in_(nodes)))
        connection.execute(delete(Node).where(Node.structure_id == base))
        connection.execute(delete(CostStructure).where(CostStructure.id == base))
    assert stamps() == with_base


# --- The abandonment of a revision ---------------------------------------------------------------


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_abandonment_of_a_revision_deletes_its_differential_and_its_base_with_every_row(
    api: ContractClient, project: Costed
) -> None:
    # « L'abandon d'une révision en cours ne laisse aucune ligne portant son identifiant » : its
    # differential, its base — which names it — and their nodes, tasks and lines with the rest.
    stage = project.stage
    mark(stage, project.tree.revision)
    current = next_revision(api, project)
    structure_id = opened_amendment(api, current)
    amendment = on(current.tree, structure_id)
    Lines(amendment).made(amendment.made("Essais"), **material(current.costs, "Banc", "50.00"))
    revision = current.revision_id

    def counts() -> dict[str, int]:
        with stage.database.transaction() as session:
            nodes = select(Node.id).where(Node.revision_id == revision)

            def count(table: Any, *criteria: Any) -> int:
                return session.scalar(select(func.count()).select_from(table).where(*criteria)) or 0

            return {
                "cost_structure": count(CostStructure, CostStructure.revision_id == revision),
                "base": count(
                    CostStructure,
                    CostStructure.revision_id == revision,
                    CostStructure.kind == "base",
                ),
                "node": count(Node, Node.revision_id == revision),
                "task": count(Task, Task.node_id.in_(nodes)),
                "task_link": count(TaskLink, TaskLink.revision_id == revision),
                "estimate_line": count(EstimateLine, EstimateLine.node_id.in_(nodes)),
                "revision_rate": count(RevisionRate, RevisionRate.revision_id == revision),
            }

    before = counts()
    assert before["base"] == 1
    assert before["node"] > 0
    assert before["estimate_line"] > 0
    path = f"{PROJECTS}/{project.project_id}/revisions/{revision}"
    held = api.get(path, headers=stage.manager.headers).json()
    answer = api.delete(
        path, headers=stage.manager.headers, params={"lock_version": held["lock_version"]}
    )
    assert answer.status_code == 204, answer.text
    assert counts() == dict.fromkeys(before, 0)
