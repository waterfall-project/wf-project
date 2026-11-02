# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit: one row per irreversible or structuring action (WF-SEC-0030).

An action is inscribed by ``record``, in the transaction that does it: the inscription is kept if
the action is, and lost with it if it is rolled back. An inscription is a code and data, never a
sentence (WF-ARC-0110): the front words it in the language of each reader. It never carries a
secret, the token of a link to set a password least of all (WF-ADM-0140).

The author, the object and the project are named as they were at the moment of the action, by
their identifier and their label — and its code for a project —, so that the journal reads
without joining the tables of the other modules and stays readable when what it names no longer
exists: none of these identifiers is a foreign key (WF-SEC-0030, WF-DAT-0090). The database
refuses to update or delete an inscription: the role of the service has only ``INSERT`` and
``SELECT`` on the table, and a trigger refuses any update, deletion or truncation whoever asks
(migration ``0003``) — but one. The anonymisation of an account makes null the label that names
it in every inscription, as its author or as its object, and nothing else: their number, their
dates and their actions do not change (``forget_account``, WF-SEC-0030, WF-ADM-0060). The role of
the service may update those two columns alone, and the trigger of the journal admits that update
alone, one label at least made null; that the account is anonymised, the module of the accounts
checks, by a trigger of its own on this table, for the platform reads no table of a module
(migration ``0011``).

The texts that the journal sorts on are compared code point by code point, as the contract
sorts them: their collation is ``C``, which the indexes share. A search that lowers one of them
names the collation it lowers in. The action and the nature of the object sort in the order of
their enumerations in the contract, not as texts: by their rank, an expression an index of its own
serves (``ACTION_RANK``, ``OBJECT_KIND_RANK``).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, get_args
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, Text, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from structlog.contextvars import get_contextvars

from waterfall.platform.database import CODE_POINTS, Base, UtcDateTime
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import names_a_secret

# The actions and the natures of objects of the contract (``AuditAction``, ``AuditObjectKind``),
# in its order; a new one is a change of the contract, then a migration of the constraint. The
# actions lag behind the contract until EP-04 (#1577, K-04): test_audit_journal.py names the gaps.
type AuditAction = Literal[
    "revision_mark",
    "reference_designate",
    "amendment_merge",
    "risk_occurrence",
    "project_exit",
    "cost_line_exclude",
    "cost_line_reinstate",
    "import_apply",
    "user_create",
    "user_update",
    "user_deactivate",
    "user_reactivate",
    "user_anonymize",
    "password_link_create",
    "access_role_create",
    "access_role_update",
    "access_role_delete",
    "user_access_roles_set",
    "backup",
    "restore",
]
type AuditObjectKind = Literal[
    "project",
    "revision",
    "cost_structure",
    "risk",
    "cost_line",
    "import",
    "user",
    "access_role",
    "backup",
    "external_backup_upload",
]
ACTIONS: tuple[str, ...] = get_args(AuditAction.__value__)
# The natures of objects an inscription may name without a label: a backup, which has none, and an
# account, whose name an anonymisation forgets (WF-ADM-0060).
UNLABELED_KINDS = ("backup", "user")
OBJECT_KINDS: tuple[str, ...] = get_args(AuditObjectKind.__value__)

# What the data of an inscription may hold: codes, identifiers in text, numbers, never a float.
type AuditValue = str | int | bool | Sequence[AuditValue] | Mapping[str, AuditValue] | None


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _rank(column: str, values: tuple[str, ...]) -> str:
    """Give the expression of the rank of a column's value in an enumeration, from 1."""
    array = ", ".join(f"{value!r}::text" for value in values)
    return f"array_position(ARRAY[{array}], {column})"


# The orders of the contract (``AuditAction``, ``AuditObjectKind``), as the journal sorts them and
# their indexes hold them: a query names the very expression an index holds, or the index is not
# used. A new value is a migration of the constraint and of the index.
ACTION_RANK = _rank("action", ACTIONS)
OBJECT_KIND_RANK = _rank("object_kind", OBJECT_KINDS)
# The order of the author, which its index holds: an account before the platform, then by its name,
# an account anonymised, which has lost it, after the names.
ACTOR_ORDER = ("(actor_user_id IS NULL)", "actor_display_name")


class AuditEntry(Base):
    """An inscription of the journal: what was done, when, by whom, on what, in which project."""

    __tablename__ = "audit_entry"
    __table_args__ = (
        CheckConstraint(_in("action", ACTIONS), name="action_known"),
        CheckConstraint(_in("object_kind", OBJECT_KINDS), name="object_kind_known"),
        # The platform has no name; an account lost its own if it was anonymised.
        CheckConstraint(
            "actor_user_id IS NOT NULL OR actor_display_name IS NULL", name="actor_named"
        ),
        CheckConstraint(
            "(project_id IS NULL) = (project_code IS NULL) "
            "AND (project_id IS NULL) = (project_label IS NULL)",
            name="project_named",
        ),
        CheckConstraint(
            f"object_label IS NOT NULL OR {_in('object_kind', UNLABELED_KINDS)}",
            name="object_labeled",
        ),
        CheckConstraint(
            "object_revision_id IS NOT NULL OR object_revision_label IS NULL",
            name="object_revision_named",
        ),
        CheckConstraint("jsonb_typeof(params) = 'object'", name="params_object"),
        CheckConstraint("correlation_id ~ '^[A-Za-z0-9._-]{1,64}$'", name="correlation_id_form"),
        Index("ix_audit_entry_action_rank", text(ACTION_RANK)),
        Index("ix_audit_entry_object_kind_rank", text(OBJECT_KIND_RANK)),
        Index("ix_audit_entry_actor_order", text(ACTOR_ORDER[0]), ACTOR_ORDER[1]),
    )

    # The indexes serve the filters of the consultation (listAuditEvents) — period, author,
    # action, nature and object, project, correlation — and its sorts: on the date, on the texts,
    # which share their collation — the name of the author, the label, the code of the project,
    # the correlation —, on the author, an account before the platform, and on the ranks of the
    # action and of the nature (migration ``0014``).
    # The search on the label, which compares the texts transliterated and lowered by ``strpos``,
    # no index serves: a B-tree does not find a text inside another, and a trigram index serves
    # ``LIKE``, not ``strpos``. At one instant, the order of inscription is that of the
    # identifiers, drawn in time order.
    id: Mapped[UUID] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # The account that acted, and its name at that moment; both null for the platform.
    actor_user_id: Mapped[UUID | None] = mapped_column(index=True)
    actor_display_name: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS))
    action: Mapped[str] = mapped_column(Text, index=True)
    object_kind: Mapped[str] = mapped_column(Text, index=True)
    object_id: Mapped[UUID] = mapped_column(index=True)
    # Null only for an object that has no label: a backup, whose date is that of the inscription.
    object_label: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS), index=True)
    # The revision the object lives in, for an object of a revision (EP-04).
    object_revision_id: Mapped[UUID | None]
    object_revision_label: Mapped[str | None] = mapped_column(Text)
    # The project of the object; null for an object of the platform — account, role, backup.
    project_id: Mapped[UUID | None] = mapped_column(index=True)
    project_code: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS), index=True)
    project_label: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    correlation_id: Mapped[str] = mapped_column(Text(collation=CODE_POINTS), index=True)


@dataclass(frozen=True, slots=True)
class AuditActor:
    """The account that acts, by its identifier and the name it is shown by at that moment.

    The name is null for an anonymised account, which has none.
    """

    user_id: UUID
    display_name: str | None


@dataclass(frozen=True, slots=True)
class AuditRevision:
    """The revision an object lives in, as it was: the label is null while it has none."""

    revision_id: UUID
    label: str | None


@dataclass(frozen=True, slots=True)
class AuditObject:
    """The object of an action, as it was at that moment."""

    kind: AuditObjectKind
    object_id: UUID
    label: str | None
    revision: AuditRevision | None = None


@dataclass(frozen=True, slots=True)
class AuditProject:
    """The project of the object, by its identifier, its code and its label at that moment."""

    project_id: UUID
    code: str
    label: str


@dataclass(frozen=True, slots=True)
class Inscription:
    """An action to inscribe: what, by whom — ``None`` for the platform —, on what, and when.

    ``occurred_at`` is the instant the action takes effect, which its caller knows: for a task,
    the instant it succeeds; for a backup, that of the state it copies. ``params`` are data —
    codes, identifiers, values —, never a sentence.
    """

    action: AuditAction
    actor: AuditActor | None
    audited: AuditObject
    occurred_at: datetime
    project: AuditProject | None = None
    params: Mapping[str, AuditValue] = field(default_factory=dict[str, AuditValue])


@dataclass(frozen=True, slots=True)
class Act:
    """Who acts — an account, or ``None`` for the platform — and when.

    The account by its identifier alone: the journal names it as it is when the action is
    inscribed, read in the transaction that inscribes it (``inscribed_actor`` of the accounts).
    """

    author: UUID | None
    at: datetime


class AuditError(Exception):
    """An inscription that would break a rule of the journal: a defect of its caller."""


def record(session: Session, inscription: Inscription) -> UUID:
    """Inscribe an action in the transaction of ``session``, and give the inscription's identifier.

    The correlation identifier is the one bound to the logs of the request or of the task
    (WF-OBS-0020): an action done outside any is a defect, refused. A field of ``params`` whose
    name evokes a secret is refused too, at any depth, and an object without a label but a backup
    or an account — an anonymised one has lost its name —, which the table refuses as well.
    """
    correlation_id = get_contextvars().get("correlation_id")
    if not isinstance(correlation_id, str):
        message = "an action is inscribed inside a request or a task, under its correlation"
        raise AuditError(message)
    params = dict(inscription.params)
    secret = _secret_field(params)
    if secret is not None:
        message = f"an inscription does not carry a secret: field {secret!r}"
        raise AuditError(message)
    actor, audited, project = inscription.actor, inscription.audited, inscription.project
    if audited.label is None and audited.kind not in UNLABELED_KINDS:
        message = f"an object of kind {audited.kind!r} is inscribed without its label"
        raise AuditError(message)
    identifier = new_id()
    revision = audited.revision
    session.execute(
        insert(AuditEntry).values(
            id=identifier,
            occurred_at=inscription.occurred_at,
            actor_user_id=None if actor is None else actor.user_id,
            actor_display_name=None if actor is None else actor.display_name,
            action=inscription.action,
            object_kind=audited.kind,
            object_id=audited.object_id,
            object_label=audited.label,
            object_revision_id=None if revision is None else revision.revision_id,
            object_revision_label=None if revision is None else revision.label,
            project_id=None if project is None else project.project_id,
            project_code=None if project is None else project.code,
            project_label=None if project is None else project.label,
            params=params,
            correlation_id=correlation_id,
        )
    )
    return identifier


def _secret_field(value: AuditValue) -> str | None:
    """Give the name of the first field, at any depth, whose name evokes a secret."""
    if isinstance(value, Mapping):
        for name, item in value.items():
            if names_a_secret(name):
                return name
            found = _secret_field(item)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, str):
        for item in value:
            found = _secret_field(item)
            if found is not None:
                return found
    return None


# The key of the advisory lock that orders the anonymisations, distinct from the other ones.
FORGETTING_LOCK = 1_200_060


def forget_account(session: Session, user_id: UUID) -> None:
    """Make null, in the transaction of ``session``, the label of an account the journal names.

    In every inscription that names it, as its author or as its object, and nothing else
    (WF-SEC-0030): its caller anonymises the account first, in the same transaction, and the
    database refuses to forget the name of an account that is not anonymised. Two anonymisations
    wait for each other: an inscription may name both accounts, and each would hold the row the
    other waits for.
    """
    session.execute(select(func.pg_advisory_xact_lock(FORGETTING_LOCK)))
    session.execute(
        update(AuditEntry)
        .where(AuditEntry.actor_user_id == user_id, AuditEntry.actor_display_name.is_not(None))
        .values(actor_display_name=None)
    )
    session.execute(
        update(AuditEntry)
        .where(
            AuditEntry.object_kind == "user",
            AuditEntry.object_id == user_id,
            AuditEntry.object_label.is_not(None),
        )
        .values(object_label=None)
    )
