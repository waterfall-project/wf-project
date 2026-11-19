# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential, its reading against it, and its state (US-3050/L2).

A differential is born with its base, the copy of the main structure at the same instant, which no
operation serves: not listed, not found by its identifier (404), deleted with its differential, and
counted by nothing that reads the structures of a revision — its commands and its indicators are
the same with or without it. ``listNodes`` reads a differential against its base, and no longer
against the main structure: what it presents added, modified or removed is what it designates,
whatever the main structure received since (#4035 for the provision line of a risk); a differential
merged is read so in the revision its merge marked. ``CostStructure.is_up_to_date`` says a
differential up to date while the main structure bears the counter its base was taken at, and its
command ``rebase`` is available once it is out of date (#4173). Every answer is checked against the
contract (``ContractClient``).
"""

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from amendments_support import (
    BEFORE,
    MAIN_ADDED,
    MAIN_REESTIMATED,
    MAIN_REMOVED,
    MAIN_RENAMED,
    OWN_ADDED,
    OWN_REMOVED,
    OWN_RENAMED,
    commands_of,
    listed,
    on,
    opened_amendment,
    out_of_date,
    revision_commands,
    structures_path,
)
from estimate_support import Costing, costing
from nodes_support import Tree, mark
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, Risks, costed, declared
from sqlalchemy import delete, select, update

from waterfall.core.planning.tables import Node
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the provision's among them."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def base_of(project: Costed, structure_id: str) -> CostStructure | None:
    """Read the base of a differential, around the service."""
    with project.stage.database.transaction() as session:
        found = session.scalars(
            select(CostStructure).where(CostStructure.differential_id == UUID(structure_id))
        ).first()
        if found is not None:
            session.expunge(found)
        return found


def shape_of(session: Session, structure_id: UUID) -> list[tuple[UUID, str]]:
    """Read the nodes of a structure by their lineage and their kind, in that order."""
    rows = session.execute(
        select(Node.lineage_id, Node.kind).where(Node.structure_id == structure_id)
    )
    return sorted((lineage, kind) for lineage, kind in rows)


def lineages(project: Costed, structure_id: UUID) -> list[tuple[UUID, str]]:
    """Read the nodes of a structure by their lineage and their kind, in that order."""
    with project.stage.database.transaction() as session:
        return shape_of(session, structure_id)


def timeless(document: object) -> object:
    """Give a document of the service without the instants it was computed at."""
    if isinstance(document, dict):
        held = cast("dict[str, object]", document)
        return {key: timeless(value) for key, value in held.items() if key != "computed_at"}
    if isinstance(document, list):
        return [timeless(each) for each in cast("list[object]", document)]
    return document


def marks(tree: Tree) -> dict[str, str]:
    """Read the mark of each node a differential returns, by its label."""
    return {
        (each["task"] or each["estimate_line"])["label"]: each["difference"]
        for each in tree.items()
    }


def state_of(api: ContractClient, project: Costed, structure_id: str) -> dict[str, Any]:
    """Read a structure as the list of its revision gives it."""
    return next(each for each in listed(api, project) if each["structure_id"] == structure_id)


# --- The base ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_opened_has_its_base_the_copy_of_the_main_structure_listed_nowhere(
    api: ContractClient, project: Costed
) -> None:
    # « createCostStructure crée avec le différentiel sa base, copie de la structure principale au
    # même instant ; listCostStructures ne la rend pas » : a structure of the revision, naming its
    # differential, that holds the nodes of the main structure under their lineage, but the
    # provision line of a risk, as the differential does (#4008).
    declared(project)
    structure_id = opened_amendment(api, project)
    base = base_of(project, structure_id)
    assert base is not None
    assert (base.kind, base.revision_id, base.is_merged) == ("base", project.revision_id, False)
    differential = lineages(project, UUID(structure_id))
    assert lineages(project, base.id) == differential
    assert len(differential) == len(lineages(project, project.structure_id)) - 1
    kinds = [each["kind"] for each in listed(api, project)]
    assert sorted(kinds) == ["amendment", "main", "risk"]
    assert str(base.id) not in {each["structure_id"] for each in listed(api, project)}


@pytest.mark.requirement("WF-REV-0100-A")
def test_every_operation_that_names_the_base_by_its_identifier_answers_404(
    api: ContractClient, project: Costed
) -> None:
    # « toute opération qui la nomme par son identifiant répond 404 », as for a structure unknown.
    structure_id = opened_amendment(api, project)
    base = base_of(project, structure_id)
    assert base is not None
    headers = project.stage.manager.headers
    path = f"{structures_path(project)}/{base.id}"
    answers = {
        "listNodes": api.get(f"{path}/nodes", headers=headers),
        "createNode": api.post(
            f"{path}/nodes",
            headers=headers,
            json={"kind": "task", "parent_id": None, "task": {"label": "Intrus"}},
        ),
        "updateCostStructure": api.patch(
            path, headers=headers, json={"label": "Intrus", "lock_version": base.lock_version}
        ),
        "deleteCostStructure": api.delete(
            path, headers=headers, params={"lock_version": base.lock_version}
        ),
        "getStructureMergeReport": api.get(f"{path}/merge", headers=headers),
        "resolveRowNumber": api.get(f"{path}/rows/1", headers=headers),
    }
    for operation, answer in answers.items():
        assert answer.status_code == 404, (operation, answer.text)
        assert answer.json()["code"] == "NOT_FOUND", operation
    assert base_of(project, structure_id) is not None


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_abandonment_of_a_differential_deletes_its_base_with_it(
    api: ContractClient, project: Costed
) -> None:
    # « deleteCostStructure la supprime avec son différentiel » : the base and its nodes.
    structure_id = opened_amendment(api, project)
    base = base_of(project, structure_id)
    assert base is not None
    held = state_of(api, project, structure_id)
    answer = api.delete(
        f"{structures_path(project)}/{structure_id}",
        headers=project.stage.manager.headers,
        params={"lock_version": held["lock_version"]},
    )
    assert answer.status_code == 204, answer.text
    assert base_of(project, structure_id) is None
    assert lineages(project, base.id) == []
    assert len(lineages(project, project.structure_id)) == 4


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_that_bears_a_base_lists_its_commands_and_its_indicators_as_without_it(
    api: ContractClient, project: Costed
) -> None:
    # « une révision qui porte une base liste generate_skeleton et ses autres commandes comme sans
    # elle, et ses indicateurs sont les mêmes » : the base deleted around the service, the
    # differential left, nothing the revision says changes.
    risks = Risks(api, project)
    structure_id = opened_amendment(api, project)
    on(project.tree, structure_id).made("Essais")

    def said() -> tuple[object, ...]:
        documents = (timeless(risks.indicators()), timeless(risks.remaining()))
        return (revision_commands(api, project), *documents)

    with_base = said()
    base = base_of(project, structure_id)
    assert base is not None
    with project.stage.owner.begin() as connection:
        connection.execute(delete(Node).where(Node.structure_id == base.id))
        connection.execute(delete(CostStructure).where(CostStructure.id == base.id))
    assert said() == with_base
    skeleton = revision_commands(api, project)["generate_skeleton"]
    assert skeleton == (False, ["main_structure_without_tasks"])


# --- The reading against the base ----------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_is_read_against_its_base_whatever_the_main_structure_received(
    api: ContractClient, project: Costed
) -> None:
    # « après une tâche ajoutée, un libellé changé, une ligne réestimée et une tâche retirée dans la
    # structure principale, le différentiel présente added, modified et removed les seuls nœuds
    # qu'il a écrits, et unchanged tous les autres ».
    found = out_of_date(api, project)
    read = marks(found.amendment)
    assert read == {
        STUDY: "unchanged",
        "Plans": "unchanged",
        "Réalisation": "unchanged",
        MAIN_REESTIMATED[0]: "unchanged",
        BEFORE[1]: "unchanged",
        OWN_RENAMED[1]: "modified",
        OWN_REMOVED: "removed",
        OWN_ADDED: "added",
    }
    assert MAIN_ADDED not in read
    assert MAIN_RENAMED[1] not in read
    main = {(each["task"] or each["estimate_line"])["label"] for each in project.tree.items()}
    assert {MAIN_ADDED, MAIN_RENAMED[1], OWN_REMOVED, BEFORE[2]} <= main
    assert MAIN_REMOVED not in main


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_provision_line_of_a_risk_of_the_main_structure_is_not_read_removed(
    api: ContractClient, project: Costed
) -> None:
    # « la ligne de provision d'un risque de la structure principale n'y est pas présentée retirée »
    # (#4035): a risk declared, a differential opened, no node marked.
    declared(project)
    amendment = on(project.tree, opened_amendment(api, project))
    items = amendment.items()
    assert {each["difference"] for each in items} == {"unchanged"}
    assert len(items) == 4


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_merged_differential_is_read_in_the_revision_marked_against_the_base_it_had(
    api: ContractClient, project: Costed
) -> None:
    # « un différentiel fusionné se relit, dans la révision que sa fusion a marquée, contre la base
    # qu'il avait à sa fusion » : the merge is US-2560's; here the differential is marked merged
    # around the service, the main structure written after its opening.
    structure_id = opened_amendment(api, project)
    amendment = on(project.tree, structure_id)
    amendment.made(OWN_ADDED)
    project.tree.made(MAIN_ADDED)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(structure_id))
            .values(is_merged=True)
        )
    mark(project.stage, project.tree.revision)
    read = marks(amendment)
    assert read == {
        STUDY: "unchanged",
        "Plans": "unchanged",
        "Réalisation": "unchanged",
        MAIN_REESTIMATED[0]: "unchanged",
        OWN_ADDED: "added",
    }
    assert state_of(api, project, structure_id)["is_up_to_date"] is None


# --- The state -----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_is_up_to_date_until_a_write_advances_the_main_structure(
    api: ContractClient, project: Costed
) -> None:
    # « CostStructure dit un différentiel à jour à son ouverture, […] en retard dès qu'une écriture
    # avance le compteur de la structure principale, et rend nul cet état pour la structure
    # principale et pour un devis propre ; la commande de mise à jour est listée sur un
    # différentiel non fusionné, disponible s'il est en retard ».
    risk = declared(project)
    first = opened_amendment(api, project, "Avenant 1")
    opened = state_of(api, project, first)
    assert opened["is_up_to_date"] is True
    assert commands_of(opened)["rebase"] == (False, ["structure_out_of_date"])
    # A write of the differential itself leaves it up to date.
    on(project.tree, first).made(OWN_ADDED)
    assert state_of(api, project, first)["is_up_to_date"] is True
    project.tree.made(MAIN_ADDED)
    second = opened_amendment(api, project, "Avenant 2")
    held = {each["structure_id"]: each for each in listed(api, project)}
    assert held[first]["is_up_to_date"] is False
    assert commands_of(held[first])["rebase"] == (True, [])
    assert held[second]["is_up_to_date"] is True
    assert held[project.tree.structure_id]["is_up_to_date"] is None
    assert held[str(risk.structure_id)]["is_up_to_date"] is None
    for structure_id in (project.tree.structure_id, str(risk.structure_id)):
        assert "rebase" not in commands_of(held[structure_id])
    mark(project.stage, project.tree.revision)
    after = {each["structure_id"]: commands_of(each) for each in listed(api, project)}
    assert after[first]["rebase"] == (False, ["revision_draft"])
    assert after[second]["rebase"] == (False, ["revision_draft", "structure_out_of_date"])


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_command_rebase_follows_the_permission_to_manage_the_revisions(
    api: ContractClient, project: Costed
) -> None:
    # « sous la permission de create_structure » : a reader of the project is listed none.
    structure_id = opened_amendment(api, project)
    project.tree.made(MAIN_ADDED)
    found = next(
        each
        for each in listed(api, project, project.stage.reader)
        if each["structure_id"] == structure_id
    )
    assert found["is_up_to_date"] is False
    assert "rebase" not in commands_of(found)


# --- The copy of a revision ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_created_takes_up_each_differential_with_its_base_and_its_state(
    api: ContractClient, project: Costed
) -> None:
    # « la copie d'une révision marquée reprend avec chaque différentiel non fusionné sa base, sous
    # la lignée de sa structure, et son état, à jour ou en retard » — the opening of the revision
    # redates its main structure, which advances its counter: the state is the one of the revision
    # marked all the same.
    stage = project.stage
    late = opened_amendment(api, project, "Avenant en retard")
    project.tree.made(MAIN_ADDED)
    fresh = opened_amendment(api, project, "Avenant à jour")
    sources = {each: base_of(project, each) for each in (late, fresh)}
    mark(stage, project.tree.revision)
    created = api.post(
        f"{PROJECTS}/{project.project_id}/revisions", headers=stage.manager.headers, json={}
    )
    assert created.status_code == 201, created.text
    new_id = created.json()["revision_id"]
    path = structures_path(project).replace(str(project.revision_id), new_id)
    taken = {
        each["label"]: each
        for each in api.get(path, headers=stage.manager.headers).json()
        if each["kind"] == "amendment"
    }
    assert taken["Avenant en retard"]["is_up_to_date"] is False
    assert commands_of(taken["Avenant en retard"])["rebase"] == (True, [])
    assert taken["Avenant à jour"]["is_up_to_date"] is True
    with stage.database.transaction() as session:
        for label, source in (("Avenant en retard", late), ("Avenant à jour", fresh)):
            base = sources[source]
            assert base is not None
            copy = session.scalars(
                select(CostStructure).where(
                    CostStructure.differential_id == UUID(taken[label]["structure_id"])
                )
            ).one()
            assert (copy.kind, copy.lineage_id, str(copy.revision_id)) == (
                "base",
                base.lineage_id,
                new_id,
            )
            assert shape_of(session, base.id) == shape_of(session, copy.id)
    copied = Tree(api, stage, created.json())
    assert {
        each["difference"] for each in on(copied, taken["Avenant à jour"]["structure_id"]).items()
    } == {"unchanged"}
