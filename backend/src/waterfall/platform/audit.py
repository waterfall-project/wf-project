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
(migration ``0003``).

The texts that the journal sorts on are compared code point by code point, as the contract
sorts them: their collation is ``C``, which the indexes share. A search that lowers one of them
names the collation it lowers in.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, get_args
from uuid import UUID

from sqlalchemy import CheckConstraint, Text, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from structlog.contextvars import get_contextvars

from waterfall.platform.database import Base, UtcDateTime
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import names_a_secret

# The actions and the natures of objects of the contract (``AuditAction``, ``AuditObjectKind``),
# in its order; a new one is a change of the contract, then a migration of the constraint.
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
OBJECT_KINDS: tuple[str, ...] = get_args(AuditObjectKind.__value__)

# What the data of an inscription may hold: codes, identifiers in text, numbers, never a float.
type AuditValue = str | int | bool | Sequence[AuditValue] | Mapping[str, AuditValue] | None

# The collation of the texts the journal sorts on: the order of the code points.
CODE_POINTS = "C"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class AuditEntry(Base):
    """An inscription of the journal: what was done, when, by whom, on what, in which project."""

    __tablename__ = "audit_entry"
    __table_args__ = (
        CheckConstraint(_in("action", ACTIONS), name="action_known"),
        CheckConstraint(_in("object_kind", OBJECT_KINDS), name="object_kind_known"),
        CheckConstraint(
            "(actor_user_id IS NULL) = (actor_display_name IS NULL)", name="actor_named"
        ),
        CheckConstraint(
            "(project_id IS NULL) = (project_code IS NULL) "
            "AND (project_id IS NULL) = (project_label IS NULL)",
            name="project_named",
        ),
        CheckConstraint(
            "object_revision_id IS NOT NULL OR object_revision_label IS NULL",
            name="object_revision_named",
        ),
        CheckConstraint("jsonb_typeof(params) = 'object'", name="params_object"),
        CheckConstraint("correlation_id ~ '^[A-Za-z0-9._-]{1,64}$'", name="correlation_id_form"),
    )

    # Every column the consultation sorts or filters on is indexed (listAuditEvents): at one
    # instant, the order of inscription is that of the identifiers, drawn in time order.
    id: Mapped[UUID] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # The account that acted, and its name at that moment; both null for the platform.
    actor_user_id: Mapped[UUID | None] = mapped_column(index=True)
    actor_display_name: Mapped[str | None] = mapped_column(Text(collation=CODE_POINTS), index=True)
    action: Mapped[str] = mapped_column(Text, index=True)
    object_kind: Mapped[str] = mapped_column(Text, index=True)
    object_id: Mapped[UUID] = mapped_column(index=True)
    # Null for an object that has no label: a backup, whose date is that of the inscription.
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
    """The account that acts, by its identifier and the name it is shown by at that moment."""

    user_id: UUID
    display_name: str


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


class AuditError(Exception):
    """An inscription that would break a rule of the journal: a defect of its caller."""


def record(session: Session, inscription: Inscription) -> UUID:
    """Inscribe an action in the transaction of ``session``, and give the inscription's identifier.

    The correlation identifier is the one bound to the logs of the request or of the task
    (WF-OBS-0020): an action done outside any is a defect, refused. A field of ``params`` whose
    name evokes a secret is refused too, at any depth.
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
    identifier = new_id()
    actor, audited, project = inscription.actor, inscription.audited, inscription.project
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
