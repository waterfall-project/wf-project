# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation (FBS-3.2).

``listOrgNodes``, ``createOrgNode``, ``updateOrgNode`` and ``setOrgNodeActivation``.

The active nodes are read by any open session, for they serve as vocabulary to the projects; the
deactivated ones, and every write, ask for the permission to change the resource settings
(``resource_settings.write``, WF-REF-0150, WF-ADM-0100). The commands a node carries are those
of a caller who holds it.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel, Text
from waterfall.api.contract.models import LockVersion, OrgNode, OrgNodeUpdate, OrgNodeWrite
from waterfall.api.contract.models import ResourceRole as ResourceRoleRead
from waterfall.api.evaluation import Acting, Requires, RequiresForInactive
from waterfall.api.queries import refuse_query
from waterfall.api.resource_roles import described as described_roles
from waterfall.core.resource_settings.interface import (
    ACTIVE_ONLY,
    NodeFilters,
    NodeView,
    NodeWrite,
    create_node,
    list_nodes,
    read_roles,
    set_activation,
    update_node,
)
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError

router = APIRouter(tags=["reference"])

CHANGE = "resource_settings.write"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# Any open session reads the active nodes; ``Requires()`` asks nothing but the session, and comes
# before the guard of the deactivated ones, which a caller who may not read would otherwise be told.
READ = [Depends(Requires()), Depends(RequiresForInactive(CHANGE))]
WRITE = [Depends(Requires(CHANGE))]


class OrgNodeActivation(ContractModel):
    """The body of ``setOrgNodeActivation``: the state asked for, at the version read."""

    is_active: bool
    lock_version: LockVersion


class OrgNodeActivationChanged(ContractModel):
    """What ``setOrgNodeActivation`` answers: the nodes and the roles whose state changed."""

    org_nodes: list[OrgNode]
    resource_roles: list[ResourceRoleRead]


def described(session: Session, views: list[NodeView]) -> list[OrgNode]:
    """Describe nodes as the contract does, their authors named as they are today."""
    wanted = {
        author
        for view in views
        for author in (view.created_by, view.updated_by)
        if author is not None
    }
    authors = read_authors(session, wanted)
    return [
        OrgNode.model_validate(
            {
                "org_node_id": view.node_id,
                "code": view.code,
                "label": view.label,
                "parent_id": view.parent_id,
                "parent_label": view.parent_label,
                "level": view.level,
                "is_active": view.is_active,
                "available_commands": [
                    {
                        "command": command.command,
                        "is_available": command.is_available,
                        "missing_conditions": list(command.missing_conditions),
                    }
                    for command in view.commands
                ],
                "audit": {
                    "created_at": view.created_at,
                    "created_by": actor_ref(
                        None if view.created_by is None else authors.get(view.created_by)
                    ),
                    "updated_at": view.updated_at,
                    "updated_by": actor_ref(
                        None if view.updated_by is None else authors.get(view.updated_by)
                    ),
                },
                "lock_version": view.lock_version,
            }
        )
        for view in views
    ]


class NodesQuery(BaseModel):
    """The parameters of the query of the tree, as the contract names them."""

    search: Annotated[Text | None, StringConstraints(min_length=1, max_length=200)] = None
    code: Annotated[Text | None, StringConstraints(min_length=1, max_length=20)] = None
    level: Annotated[int | None, Field(ge=1)] = None
    level_min: Annotated[int | None, Field(ge=1)] = None
    level_max: Annotated[int | None, Field(ge=1)] = None
    include_inactive: bool = False
    is_active: bool | None = None


def node_filters(query: Annotated[NodesQuery, Query()]) -> NodeFilters:
    """Read the filters of the tree; an upper bound under the lower one is refused (422).

    ``is_active`` keeps one state and prevails over ``include_inactive``, which only adds the
    deactivated nodes to the active ones (WF-IHM-0130, WF-REF-0150).
    """
    low, high = query.level_min, query.level_max
    if low is not None and high is not None and high < low:
        refuse_query([FieldError("/query/level_max", VALUE_OUT_OF_RANGE, {"minimum": low})])
    if query.is_active is None:
        states = frozenset({True, False}) if query.include_inactive else ACTIVE_ONLY
    else:
        states = frozenset({query.is_active})
    return NodeFilters(query.search, query.code, query.level, low, high, states)


@router.get(
    "/reference/org-nodes",
    operation_id="listOrgNodes",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_org_nodes(
    actor: Acting, session: Transaction, filters: Annotated[NodeFilters, Depends(node_filters)]
) -> list[OrgNode]:
    """Give the tree whole, depth first, the nodes the filters keep with their ancestors.

    Neither paged nor sorted: a page would cut a node from its descendants (WF-REF-0070).
    """
    views = list_nodes(session, filters, may_change=CHANGE in actor.permissions)
    return described(session, views)


@router.post(
    "/reference/org-nodes",
    operation_id="createOrgNode",
    dependencies=WRITE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_org_node(body: OrgNodeWrite, account: Caller, session: Transaction) -> OrgNode:
    """Create a node under an active parent, or a root (WF-REF-0070)."""
    parent_id = None if body.parent_id is None else body.parent_id.root
    write = NodeWrite(body.code, body.label, parent_id)
    created = create_node(session, write, Act(account.user_id, utc_now()))
    return described(session, [created])[0]


@router.patch(
    "/reference/org-nodes/{org_node_id}",
    operation_id="updateOrgNode",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_org_node(
    org_node_id: UUID, body: OrgNodeUpdate, account: Caller, session: Transaction
) -> OrgNode:
    """Change a node, and move it with its descendants and its roles (WF-REF-0070)."""
    parent_id = None if body.parent_id is None else body.parent_id.root
    write = NodeWrite(body.code, body.label, parent_id)
    act = Act(account.user_id, utc_now())
    changed = update_node(session, org_node_id, write, body.lock_version.root, act)
    return described(session, [changed])[0]


@router.put(
    "/reference/org-nodes/{org_node_id}/activation",
    operation_id="setOrgNodeActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_org_node_activation(
    org_node_id: UUID, body: OrgNodeActivation, account: Caller, session: Transaction
) -> OrgNodeActivationChanged:
    """Deactivate a node with its descendants and their roles, or reactivate it alone (WF-REF-0080).

    The answer gives the nodes and the roles whose state changed; the commands of the others —
    the reactivation of a child or of a role — the client reads again in the lists.
    """
    act = Act(account.user_id, utc_now())
    changed = set_activation(
        session, org_node_id, is_active=body.is_active, lock_version=body.lock_version.root, act=act
    )
    roles = read_roles(session, changed.resource_role_ids, may_change=True)
    return OrgNodeActivationChanged(
        org_nodes=described(session, changed.nodes),
        resource_roles=described_roles(session, roles),
    )
