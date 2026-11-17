# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions read by whoever consults a grid without consulting them (US-2320/L2).

``listRevisions``, ``getRevision`` and ``listCostStructures`` are what the banner of a grid reads to
open it and to choose the base of a comparison: they accept ``revisions.read``, or one of
``planning.read``, ``estimate.read`` and ``remaining.read``. The writes and the commands of a
revision keep theirs, ``revisions.read`` first: refused by a 404 to a reader of a grid alone, as
before. Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any

import pytest
from projects_support import PROJECTS, Person, Scene, contribute, person
from projects_support import scene as make_scene

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

GRIDS = ("planning.read", "estimate.read", "remaining.read")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def opened(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    response = api.post(revisions_of(stage), headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def revisions_of(stage: Scene) -> str:
    """Give the path of the revisions of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/revisions"


def contributor(stage: Scene, realm: TestRealm, *permissions: str) -> Person:
    """Write an account holding ``permissions`` alone, inscribed as a contributor of the project."""
    who = person(stage.database, realm, *permissions, name="Lou")
    contribute(stage.database, stage.project["project_id"], who, "contributor")
    return who


def readings(api: ContractClient, stage: Scene, who: Person, revision_id: str) -> list[Any]:
    """Read the history, the revision and its structures, as ``who`` does: the three answers."""
    path = f"{revisions_of(stage)}/{revision_id}"
    return [
        api.get(revisions_of(stage), headers=who.headers),
        api.get(path, headers=who.headers),
        api.get(f"{path}/structures", headers=who.headers),
    ]


@pytest.mark.requirement("WF-REV-0080-A")
@pytest.mark.parametrize("permission", GRIDS)
def test_a_reader_of_a_grid_who_does_not_consult_the_revisions_reads_them_and_their_structures(
    api: ContractClient, stage: Scene, realm: TestRealm, permission: str
) -> None:
    # « Un utilisateur qui consulte le planning sans consulter les révisions y active une
    # comparaison » : its part of the three readings the banner of the grid makes, read as the
    # manager reads them, the commands apart, which follow the permissions of their reader.
    revision = opened(api, stage)
    reader = contributor(stage, realm, permission)
    history, read, structures = readings(api, stage, reader, revision["revision_id"])
    assert (history.status_code, read.status_code, structures.status_code) == (200, 200, 200)
    assert [item["revision_id"] for item in history.json()["items"]] == [revision["revision_id"]]
    assert history.json()["meta"]["total"] == 1
    kept = ("revision_id", "status", "reference_year", "lock_version")
    assert {key: read.json()[key] for key in kept} == {key: revision[key] for key in kept}
    [main] = structures.json()
    assert (main["revision_id"], main["kind"]) == (revision["revision_id"], "main")


@pytest.mark.requirement("WF-REV-0080-A")
def test_an_account_that_consults_neither_the_revisions_nor_a_grid_is_refused_them_as_unknown(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # A contributor of the project who holds none of the four reads nothing of its revisions: 404
    # NOT_FOUND, as before, the refusal that does not tell an unknown revision from a hidden one.
    revision = opened(api, stage)
    stranger = contributor(stage, realm, "risks.read", "actual_costs.read")
    for response in readings(api, stage, stranger, revision["revision_id"]):
        assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-REV-0080-A")
def test_a_reader_of_the_planning_who_is_no_contributor_of_the_project_is_refused_its_revisions(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # The quality on the project is judged as before: the project is not consultable to an account
    # that is neither its contributor nor holds ``all_projects_read``.
    revision = opened(api, stage)
    outsider = person(stage.database, realm, "planning.read", name="Sacha")
    for response in readings(api, stage, outsider, revision["revision_id"]):
        assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_writes_and_the_commands_of_a_revision_stay_closed_to_a_reader_of_the_grids(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # « La fonction Gestion des révisions et ses commandes lui restent fermées » : a contributor
    # who holds the three grids, read and write, and none of the revisions is refused the opening,
    # the abandonment and the marking of a revision as before, by the 404 of ``revisions.read``;
    # the revision stays as it was.
    revision = opened(api, stage)
    held = (*GRIDS, "planning.write", "estimate.write", "remaining.write")
    reader = contributor(stage, realm, *held)
    path = f"{revisions_of(stage)}/{revision['revision_id']}"
    asked = [
        api.post(revisions_of(stage), headers=reader.headers, json={}),
        api.delete(f"{path}?lock_version={revision['lock_version']}", headers=reader.headers),
        api.post(
            f"{path}/mark",
            headers=reader.headers,
            json={"version_name": "V1", "lock_version": revision["lock_version"]},
        ),
    ]
    for response in asked:
        assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
    still = api.get(path, headers=stage.manager.headers)
    assert (still.status_code, still.json()["status"]) == (200, "draft")
    assert still.json()["lock_version"] == revision["lock_version"]
