# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects of the witness, and the local accounts of their contributors.

``projects.json`` and ``project.json``: the local accounts of Waterfall alone, which never sign
in, then PRJ-002 and PRJ-001 with their client, each under the identifier the witness imposes.

The accounts are those the contributors of the witness name (``contributors.json``), described as
``users.json`` describes them; each is created by the interface of the accounts without any
identity provider, its subject drawn from its identifier, and the one the witness says
deactivated is deactivated after. The projects are created by the rules of the creation, in the
state ``created``, but for the minimal reference, which the roles of resources of the witness will
complete with US-0850 (``load_project``): their code, their states and their revisions are written
by the events of the chronology (US-0990).
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import ContributorList, Project, User
from waterfall.core.projects.interface import (
    ProjectDraft,
    ProjectLoad,
    load_project,
    projects_present,
)
from waterfall.core.users.interface import Identity, create_local_account, set_account_activation
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

PROJECTS_FILE = "projects.json"
CONTRIBUTORS_FILE = "contributors.json"
USERS_FILE = "users.json"


class Projects(BaseModel):
    """The projects of the witness, as ``listProjects`` answers them."""

    items: list[Project]


class Users(BaseModel):
    """The accounts of the witness, as ``listUsers`` answers them."""

    items: list[User]


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    projects = witness.read(PROJECTS_FILE, Projects).items
    imposed = {project.project_id.root for project in projects}
    if is_loaded(imposed, projects_present(session, imposed)):
        return False
    _load_accounts(session, witness)
    for project in projects:
        client = None if project.client is None else project.client.root
        draft = ProjectDraft(project.label, project.description, client)
        load_project(session, ProjectLoad(project.project_id.root, draft), witness.act)
    return True


def _load_accounts(session: Session, witness: Witness) -> None:
    """Create the local accounts of the contributors, the deactivated one deactivated after."""
    contributors = witness.read(CONTRIBUTORS_FILE, ContributorList).items
    described = {user.user_id.root: user for user in witness.read(USERS_FILE, Users).items}
    for contributor in contributors:
        user = described[contributor.user_id.root]
        last_name, first_name = user.last_name, user.first_name
        identity = Identity(
            "" if last_name is None else last_name.root,
            "" if first_name is None else first_name.root,
            user.email or "",
        )
        account = create_local_account(
            session, identity, f"witness-{user.user_id.root}", witness.act, user.user_id.root
        )
        if not contributor.is_active:
            set_account_activation(
                session,
                account.user_id,
                is_active=False,
                lock_version=account.lock_version,
                act=witness.act,
            )
