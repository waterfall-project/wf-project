# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the differentials share (EP-08, US-2550/L3): opening one, writing in it.

A differential is opened through the service (``createCostStructure``) in the current revision of a
project costed (``risks_support.costed``), and read and written by the operations of the main
structure: ``on`` gives the tree of the grids pointed at it, the lines (``estimate_support.Lines``)
following. The fabric ``risks_support.differential`` writes an empty one around the service; this
one is the copy of the main structure the service makes.
"""

import copy
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from access_rows import role
from estimate_support import Lines
from nodes_support import signed_in
from projects_support import PROJECTS
from sqlalchemy import delete, insert

from waterfall.core.access_roles.tables import UserAccessRole

if TYPE_CHECKING:
    from nodes_support import Tree
    from projects_support import Person
    from realm import TestRealm
    from risks_support import Costed
    from support import ContractClient


def structures_path(project: Costed) -> str:
    """Give the path of the structures of the current revision of a project costed."""
    return f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/structures"


def open_amendment(
    api: ContractClient, project: Costed, label: str = "Avenant 1", **sent: Any
) -> Any:
    """Ask for a differential, as the manager does; give the answer."""
    body = {"kind": "amendment", "label": label, **sent}
    return api.post(structures_path(project), headers=project.stage.manager.headers, json=body)


def opened_amendment(api: ContractClient, project: Costed, label: str = "Avenant 1") -> str:
    """Open a differential that must be opened; give its identifier."""
    answer = open_amendment(api, project, label)
    assert answer.status_code == 201, answer.text
    return answer.json()["structure_id"]


def listed(api: ContractClient, project: Costed, who: Any = None) -> list[dict[str, Any]]:
    """List the structures of the current revision, as the manager does by default."""
    headers = (who or project.stage.manager).headers
    answer = api.get(structures_path(project), headers=headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def on(tree: Tree, structure_id: str) -> Tree:
    """Give the tree of the grids, pointed at another structure of the same revision."""
    pointed = copy.copy(tree)
    pointed.structure_id = structure_id
    pointed.path = f"{tree.path.rsplit('/', 1)[0]}/{structure_id}"
    return pointed


def lines_on(project: Costed, structure_id: str) -> Lines:
    """Give the lines of a structure of the project costed, written through the service."""
    return Lines(on(project.tree, structure_id))


def revision_path(project: Costed) -> str:
    """Give the path of the current revision of a project costed."""
    return f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"


def commands_of(described: dict[str, Any]) -> dict[str, tuple[bool, list[str]]]:
    """Give the commands an object of the contract carries: available or not, what each lacks."""
    return {
        each["command"]: (each["is_available"], each["missing_conditions"])
        for each in described["available_commands"]
    }


def revision_commands(
    api: ContractClient, project: Costed, who: Any = None
) -> dict[str, tuple[bool, list[str]]]:
    """Read the commands of the current revision: available or not, the conditions each lacks."""
    headers = (who or project.stage.manager).headers
    answer = api.get(revision_path(project), headers=headers)
    assert answer.status_code == 200, answer.text
    return commands_of(answer.json())


def started_marking(api: ContractClient, project: Costed) -> None:
    """Ask for the marking of the current revision, which the worker does not run: a task waits."""
    path = revision_path(project)
    held = api.get(path, headers=project.stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=project.stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": held["lock_version"]},
    )
    assert asked.status_code == 202, asked.text


def contributor_with(project: Costed, realm: TestRealm, *permissions: str) -> Person:
    """Give a contributor of the project, with a session of sign-in, who holds ``permissions``.

    The three readings of the grids come with them: such a contributor reads the structure and
    writes only what it is granted.
    """
    stage = project.stage
    who = signed_in(stage, realm)
    held = role(
        stage.database,
        f"Rôle {uuid4().hex}",
        permissions=("planning.read", "estimate.read", "remaining.read", *permissions),
    )
    with stage.database.transaction() as session:
        session.execute(delete(UserAccessRole).where(UserAccessRole.user_account_id == who.user_id))
        session.execute(
            insert(UserAccessRole).values(user_account_id=who.user_id, access_role_id=held)
        )
    return who
