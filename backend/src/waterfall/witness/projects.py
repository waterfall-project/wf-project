# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects of the witness, and the local accounts of their contributors.

``projects.json`` and ``project.json``: the local accounts of Waterfall alone, which never sign
in, then PRJ-002 and PRJ-001 with their client, each under the identifier the witness imposes.

The accounts are those the contributors of the witness name (``contributors.json``), described as
``users.json`` describes them; each is created by the interface of the accounts without any
identity provider, its subject drawn from its identifier, and the one the witness says
deactivated is deactivated after, each under an address of the domain ``waterfall.test``, all at
the instant of the first event of the chronology, the installation. The projects are created by
the very rules of the creation (``load_project``), the minimal reference included, in the state
``created``, at the instant the chronology creates them: PRJ-001 at its ``project_created``,
PRJ-002, which the chronology does not date, at the same one. A project bears its code from its
creation unless the chronology enters it (PRJ-001: the order received); its states and its
revisions are written by the events of the chronology (``revisions``).
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
from waterfall.witness import timeline
from waterfall.witness.description import is_loaded
from waterfall.witness.timeline import CodeEntered

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness

PROJECTS_FILE = "projects.json"
CONTRIBUTORS_FILE = "contributors.json"
USERS_FILE = "users.json"
WITNESS_DOMAIN = "waterfall.test"


def _address(email: str | None) -> str:
    """Give the address a local account of the witness bears: its name, in ``waterfall.test``.

    The addresses of ``users.json`` are those of the fake back; an account of the platform bears
    none that is not in the domain reserved to the tests (WF-QUA-0040).
    """
    return "" if not email else f"{email.partition('@')[0]}@{WITNESS_DOMAIN}"


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
    chronology = timeline.read(witness)
    entered = {write.project for _, write in chronology.writes() if isinstance(write, CodeEntered)}
    _load_accounts(session, witness, timeline.at(witness, chronology.events[0].occurred_at))
    for project in projects:
        client = None if project.client is None else project.client.root
        code = None if project.code is None or project.code.root in entered else project.code.root
        draft = ProjectDraft(project.label, project.description, client, code)
        load_project(
            session, ProjectLoad(project.project_id.root, draft), timeline.created(witness, project)
        )
    return True


def _load_accounts(session: Session, witness: Witness, act: Act) -> None:
    """Create the local accounts of the contributors, the deactivated one deactivated after."""
    contributors = witness.read(CONTRIBUTORS_FILE, ContributorList).items
    described = {user.user_id.root: user for user in witness.read(USERS_FILE, Users).items}
    for contributor in contributors:
        user = described[contributor.user_id.root]
        last_name, first_name = user.last_name, user.first_name
        identity = Identity(
            "" if last_name is None else last_name.root,
            "" if first_name is None else first_name.root,
            _address(user.email),
        )
        account = create_local_account(
            session, identity, f"witness-{user.user_id.root}", act, user.user_id.root
        )
        if not contributor.is_active:
            set_account_activation(
                session,
                account.user_id,
                is_active=False,
                lock_version=account.lock_version,
                act=act,
            )
