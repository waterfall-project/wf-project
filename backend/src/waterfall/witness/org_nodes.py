# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation of the witness.

``org_nodes_with_inactive.json``: each node under its parent, then those the witness says
deactivated, in cascade.

The file lists the nodes in the order of the tree, a parent before its children: each is created
active under the node that is its parent, with the identifier the witness imposes; those the
witness says deactivated are deactivated after all are written, each in turn (WF-REF-0080).
"""

from typing import TYPE_CHECKING

from pydantic import RootModel

from waterfall.api.contract.models import OrgNode
from waterfall.core.resource_settings.interface import (
    NodeWrite,
    create_node,
    node_labels,
    read_node,
    set_activation,
)
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

FILE = "org_nodes_with_inactive.json"


class OrgNodes(RootModel[list[OrgNode]]):
    """The tree of the witness, in the form the contract reads it (``listOrgNodes``)."""


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    nodes = witness.read(FILE, OrgNodes).root
    imposed = {node.org_node_id.root for node in nodes}
    if is_loaded(imposed, set(node_labels(session, imposed))):
        return False
    for node in nodes:
        parent_id = None if node.parent_id is None else node.parent_id.root
        write = NodeWrite(node.code, node.label, parent_id)
        create_node(session, write, witness.act, node_id=node.org_node_id.root)
    for node in nodes:
        if node.is_active:
            continue
        current = read_node(session, node.org_node_id.root, may_change=False)
        if current.is_active:
            set_activation(
                session,
                current.node_id,
                is_active=False,
                lock_version=current.lock_version,
                act=witness.act,
            )
    return True
