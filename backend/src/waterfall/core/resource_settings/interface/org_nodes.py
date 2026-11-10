# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation.

Read whole, created, changed, moved, deactivated in cascade and reactivated (WF-REF-0070,
0080); the label of a node and whether it is active, for an account attached to it.

The nodes are read whole, depth first, their depth resolved at the reading and never stored; a
write of the tree runs under its lock, and its refusals are those the contract names. The
deactivation of a node reaches its descendants and the roles of resources attached to it or to one
of them, in the transaction and under the lock of the tree, which the creation and the activation
of a role take too (``resource_roles``); its reactivation reaches the node alone.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, SQLColumnExpression, func, or_, select, update

from waterfall.core.resource_settings.interface.readiness import lock_reference
from waterfall.core.resource_settings.org_tree import (
    Branch,
    in_tree_order,
    is_within,
    levels_of,
    with_ancestors,
)
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole
from waterfall.platform.database import contains
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The key of the advisory lock of the tree: one for every write of the nodes.
TREE_LOCK = 5_200_070
NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
ALREADY_EXISTS = "ALREADY_EXISTS"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
ORG_NODE_CYCLE = "ORG_NODE_CYCLE"
INACTIVE_REFERENCE_OBJECT = "INACTIVE_REFERENCE_OBJECT"
# The condition the reactivation of a node lacks while its parent is deactivated (WF-REF-0080).
PARENT_ACTIVE_CONDITION = "org_node_parent_active"
DEACTIVATE = "deactivate"
REACTIVATE = "reactivate"
# The states a reading keeps unless it asks for more: the active nodes alone.
ACTIVE_ONLY: frozenset[bool] = frozenset({True})


@dataclass(frozen=True, slots=True)
class NodeCommand:
    """The command that changes the state of a node, and what it lacks: nothing if available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class NodeView:
    """A node as it is read: its parent named, its depth resolved, its commands (WF-REF-0070).

    The authors are the identifiers of accounts, or ``None`` for the platform: the API names them.
    """

    node_id: UUID
    code: str
    label: str
    parent_id: UUID | None
    parent_label: str | None
    level: int
    is_active: bool
    commands: tuple[NodeCommand, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class NodeWrite:
    """What a node is created or changed with; no parent is a root."""

    code: str
    label: str
    parent_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class NodeActivation:
    """What an activation of a node changed: the nodes in the order of the tree, and the roles."""

    nodes: list[NodeView]
    resource_role_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class NodeFilters:
    """What a reading of the tree keeps; a filter absent keeps everything (WF-IHM-0130).

    ``states`` are the values of ``is_active`` kept. The levels are the depths, 1 for a root.
    """

    search: str | None = None
    code: str | None = None
    level: int | None = None
    level_min: int | None = None
    level_max: int | None = None
    states: frozenset[bool] = ACTIVE_ONLY


def lock_tree(session: Session) -> None:
    """Take the lock of the tree for the rest of the transaction: every write of it comes first."""
    session.execute(select(func.pg_advisory_xact_lock(TREE_LOCK)))


def _every_node(session: Session) -> dict[UUID, OrgNode]:
    """Read every node of the tree, fresh."""
    rows = session.scalars(select(OrgNode).execution_options(populate_existing=True))
    return {row.id: row for row in rows}


def _command(node: OrgNode, nodes: Mapping[UUID, OrgNode]) -> NodeCommand:
    if node.is_active:
        return NodeCommand(DEACTIVATE)
    parent = None if node.parent_id is None else nodes.get(node.parent_id)
    if parent is not None and not parent.is_active:
        return NodeCommand(REACTIVATE, (PARENT_ACTIVE_CONDITION,))
    return NodeCommand(REACTIVATE)


def _view(
    node: OrgNode, nodes: Mapping[UUID, OrgNode], levels: Mapping[UUID, int], *, may_change: bool
) -> NodeView:
    parent = None if node.parent_id is None else nodes.get(node.parent_id)
    return NodeView(
        node_id=node.id,
        code=node.code,
        label=node.label,
        parent_id=node.parent_id,
        parent_label=None if parent is None else parent.label,
        level=levels[node.id],
        is_active=node.is_active,
        commands=(_command(node, nodes),) if may_change else (),
        created_at=node.created_at,
        created_by=node.created_by,
        updated_at=node.updated_at,
        updated_by=node.updated_by,
        lock_version=node.lock_version,
    )


def _branches(nodes: Mapping[UUID, OrgNode]) -> list[Branch]:
    return [Branch(node.id, node.parent_id, node.label) for node in nodes.values()]


def _criteria(filters: NodeFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [OrgNode.is_active.in_(filters.states)]
    if filters.search is not None:
        criteria.append(
            or_(contains(OrgNode.label, filters.search), contains(OrgNode.code, filters.search))
        )
    if filters.code is not None:
        criteria.append(contains(OrgNode.code, filters.code))
    return criteria


def _is_deep_enough(level: int, filters: NodeFilters) -> bool:
    return (
        (filters.level is None or level == filters.level)
        and (filters.level_min is None or level >= filters.level_min)
        and (filters.level_max is None or level <= filters.level_max)
    )


def list_nodes(session: Session, filters: NodeFilters, *, may_change: bool) -> list[NodeView]:
    """Read the tree whole, depth first: the nodes the filters keep and their ancestors.

    Every node tells its depth, the children of a parent come by label in the order of the code
    points. An ancestor is rendered for the tree to read without a hole, whether or not it
    satisfies the filters.
    """
    nodes = _every_node(session)
    levels = levels_of(_branches(nodes))
    matched = session.scalars(select(OrgNode.id).where(*_criteria(filters)))
    kept = [each for each in matched if _is_deep_enough(levels[each], filters)]
    shown = with_ancestors(_branches(nodes), kept)
    ordered = in_tree_order(branch for branch in _branches(nodes) if branch.node_id in shown)
    return [_view(nodes[each.node_id], nodes, levels, may_change=may_change) for each in ordered]


def read_node(session: Session, node_id: UUID, *, may_change: bool) -> NodeView:
    """Read a node, or refuse (404)."""
    nodes = _every_node(session)
    if node_id not in nodes:
        raise NotFoundError(NOT_FOUND)
    return _view(nodes[node_id], nodes, levels_of(_branches(nodes)), may_change=may_change)


def _unprocessable(code: str) -> UnprocessableError:
    return UnprocessableError(VALIDATION_FAILED, fields=(FieldError("/parent_id", code),))


def _refuse_parent(
    nodes: Mapping[UUID, OrgNode], node_id: UUID | None, parent_id: UUID | None, *, judged: bool
) -> None:
    """Refuse the parent a node is put under, for one reason, the first in this order (422).

    Unknown, then a loop — the node itself or one of its descendants —, then deactivated, which is
    judged only when ``judged`` (a move; a creation always).
    """
    if parent_id is None:
        return
    if parent_id not in nodes:
        raise _unprocessable(UNKNOWN_ORG_NODE)
    parents = {each.id: each.parent_id for each in nodes.values()}
    if node_id is not None and is_within(parents, parent_id, node_id):
        raise _unprocessable(ORG_NODE_CYCLE)
    if judged and not nodes[parent_id].is_active:
        raise _unprocessable(INACTIVE_REFERENCE_OBJECT)


def _refuse_code_taken(nodes: Mapping[UUID, OrgNode], code: str, own: UUID | None) -> None:
    """Refuse a code another node bears, deactivated or not, naming that node (409)."""
    holder = next((each for each in nodes.values() if each.code == code and each.id != own), None)
    if holder is not None:
        params = {"conflicting_object_id": str(holder.id), "conflicting_object_label": holder.label}
        raise ConflictError(ALREADY_EXISTS, fields=(FieldError("/code", ALREADY_EXISTS, params),))


def create_node(
    session: Session, write: NodeWrite, act: Act, node_id: UUID | None = None
) -> NodeView:
    """Create an active node under its parent, or a root, under the lock of the tree.

    Refused if the parent is unknown or deactivated (422), if the code is borne by another node,
    deactivated or not (409). ``node_id`` is the identifier the witness imposes.
    """
    lock_tree(session)
    nodes = _every_node(session)
    _refuse_parent(nodes, None, write.parent_id, judged=True)
    _refuse_code_taken(nodes, write.code, None)
    created = OrgNode(
        id=new_id() if node_id is None else node_id,
        code=write.code,
        label=write.label,
        parent_id=write.parent_id,
        is_active=True,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )
    session.add(created)
    session.flush()
    return read_node(session, created.id, may_change=True)


def _stale(node: OrgNode) -> PreconditionFailedError:
    return PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version})


def _write_node(
    session: Session, node: OrgNode, values: Mapping[str, object], lock_version: int, act: Act
) -> None:
    """Write columns of a node at the version read, which the write itself tests (412)."""
    changed = session.scalars(
        update(OrgNode)
        .where(OrgNode.id == node.id, OrgNode.lock_version == lock_version)
        .values(
            **values,
            lock_version=OrgNode.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .returning(OrgNode.id)
    ).first()
    if changed is None:
        raise _stale(node)


def _locked(
    session: Session, node_id: UUID, lock_version: int
) -> tuple[dict[UUID, OrgNode], OrgNode]:
    """Lock the tree, read it, and find the node at the version read; or refuse (404, 412)."""
    lock_tree(session)
    nodes = _every_node(session)
    node = nodes.get(node_id)
    if node is None:
        raise NotFoundError(NOT_FOUND)
    if node.lock_version != lock_version:
        raise _stale(node)
    return nodes, node


def update_node(
    session: Session, node_id: UUID, write: NodeWrite, lock_version: int, act: Act
) -> NodeView:
    """Change a node, and move it under its parent or to the root, with its descendants.

    Under the lock of the tree. Refused if unknown (404), at another version (412), if the parent
    is unknown, the node or one of its descendants, or — when the parent changes — deactivated
    (422, one reason), if the code is borne by another node (409). The depth of the descendants
    follows, resolved at the reading.
    """
    nodes, node = _locked(session, node_id, lock_version)
    _refuse_parent(nodes, node_id, write.parent_id, judged=write.parent_id != node.parent_id)
    _refuse_code_taken(nodes, write.code, node_id)
    values = {"code": write.code, "label": write.label, "parent_id": write.parent_id}
    _write_node(session, node, values, lock_version, act)
    return read_node(session, node_id, may_change=True)


def _deactivate_within(
    session: Session, nodes: Mapping[UUID, OrgNode], node: OrgNode, act: Act
) -> tuple[list[UUID], list[UUID]]:
    """Deactivate the active descendants of a node and the active roles of its subtree.

    Each its counter advanced and its author the actor (WF-REF-0080); give the nodes and the roles
    written. The node itself is written by its caller, at the version read.
    """
    parents = {each.id: each.parent_id for each in nodes.values()}
    subtree = [each for each in nodes if is_within(parents, each, node.id)]
    stamp = {"updated_at": act.at, "updated_by": act.author}
    descendants = list(
        session.scalars(
            update(OrgNode)
            .where(OrgNode.id.in_(subtree), OrgNode.id != node.id, OrgNode.is_active)
            .values(is_active=False, lock_version=OrgNode.lock_version + 1, **stamp)
            .returning(OrgNode.id)
        )
    )
    roles = list(
        session.scalars(
            update(ResourceRole)
            .where(ResourceRole.org_node_id.in_(subtree), ResourceRole.is_active)
            .values(is_active=False, lock_version=ResourceRole.lock_version + 1, **stamp)
            .returning(ResourceRole.id)
        )
    )
    return descendants, roles


def set_activation(
    session: Session, node_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> NodeActivation:
    """Deactivate a node with its subtree and its roles, or reactivate it alone.

    Under the lock of the tree, in the transaction of the caller. Refused if unknown (404), at
    another version (412), or — to reactivate — while the parent is deactivated (409,
    ``org_node_parent_active``). The deactivation reaches the active descendants and the active
    roles attached to the node or to one of them; the reactivation the node alone, its descendants
    and their roles reactivated one by one. A node already in the state asked for is unchanged, and
    nothing is given.
    """
    if not is_active:
        lock_reference(session)
    nodes, node = _locked(session, node_id, lock_version)
    if node.is_active == is_active:
        return NodeActivation([], [])
    parent = None if node.parent_id is None else nodes[node.parent_id]
    if is_active and parent is not None and not parent.is_active:
        raise ConflictError(
            STATE_FORBIDS_OPERATION,
            {"missing_condition": PARENT_ACTIVE_CONDITION, "conflicting_object_id": str(parent.id)},
        )
    _write_node(session, node, {"is_active": is_active}, lock_version, act)
    descendants, roles = ([], []) if is_active else _deactivate_within(session, nodes, node, act)
    changed = {node_id, *descendants}
    fresh = _every_node(session)
    levels = levels_of(_branches(fresh))
    ordered = in_tree_order(branch for branch in _branches(fresh) if branch.node_id in changed)
    views = [_view(fresh[each.node_id], fresh, levels, may_change=True) for each in ordered]
    return NodeActivation(views, roles)


def node_labels(session: Session, node_ids: Collection[UUID]) -> dict[UUID, str]:
    """Give the labels of the nodes, at once; an identifier no node bears is left out."""
    if not node_ids:
        return {}
    rows = session.execute(select(OrgNode.id, OrgNode.label).where(OrgNode.id.in_(node_ids)))
    return dict(rows.all())


def node_is_active(session: Session, node_id: UUID) -> bool | None:
    """Tell whether a node is active; ``None`` if there is none.

    Read under a share lock of the row: a deactivation, which writes it, waits for the write that
    attaches an account to the node, or is waited for.
    """
    return session.scalars(
        select(OrgNode.is_active).where(OrgNode.id == node_id).with_for_update(read=True)
    ).first()


def within_node(node_id: UUID, attached: SQLColumnExpression[UUID | None]) -> ColumnElement[bool]:
    """Say of a column of nodes that it holds the node or one of its descendants.

    For the table of the accounts, which holds the column and does not name this table.
    """
    subtree = select(OrgNode.id).where(OrgNode.id == node_id).cte("subtree", recursive=True)
    subtree = subtree.union_all(select(OrgNode.id).where(OrgNode.parent_id == subtree.c.id))
    return attached.in_(select(subtree.c.id))


def label_of(attached: SQLColumnExpression[UUID | None]) -> SQLColumnExpression[str | None]:
    """Give, of a column of nodes, the label of the node held: a sort by the code points."""
    return select(OrgNode.label).where(OrgNode.id == attached).scalar_subquery()
