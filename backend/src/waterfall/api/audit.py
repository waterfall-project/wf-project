# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The family ``audit``: the journal of audit read, never written (FBS-1.5, WF-ADM-0190).

Both operations ask for the permission to consult the journal alone (WF-ADM-0100): without it,
the journal does not exist for the caller (404). The journal is the whole of it — every account,
the platform, every project —, read as it keeps itself: an inscription is a code and data, never a
sentence, that the front words in the language of each reader (WF-ARC-0110). No operation
inscribes, changes or deletes an inscription: only the action itself inscribes (WF-SEC-0030).
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy.orm import Session

from waterfall.api.authentication import Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import (
    AuditAction,
    AuditActorKind,
    AuditEvent,
    AuditFacets,
    AuditObjectKind,
    PaginationMeta,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import Offset, listed
from waterfall.core.projects.interface import Viewer, openable, projects_named, projects_present
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import AuditEntry, AuditProject
from waterfall.platform.audit_consultation import (
    AuditColumn,
    AuditFilters,
    AuditSort,
    by_code,
    journal_actors,
    journal_projects,
    list_entries,
)
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError

router = APIRouter(tags=["audit"])

CONSULTATION = "audit_log.read"
READ = [Depends(Requires(CONSULTATION))]
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
# The form of a correlation identifier (WF-OBS-0020), as the contract writes it.
CORRELATION = r"^[A-Za-z0-9._-]{1,64}$"


class JournalQuery(BaseModel):
    """The filters of the journal, as the query names them."""

    since: AwareDatetime | None = Field(default=None, alias="from")
    to: AwareDatetime | None = None
    user_id: UUID | None = None
    actor_kind: AuditActorKind | None = None
    actions: Text | None = None
    project_id: UUID | None = None
    object_kind: AuditObjectKind | None = None
    object_id: UUID | None = None
    search: Annotated[Text | None, Field(min_length=1, max_length=200)] = None
    correlation_id: Annotated[Text | None, Field(pattern=CORRELATION)] = None


def audit_filters(query: Annotated[JournalQuery, Query()]) -> AuditFilters:
    """Read the filters of the journal; the actions are separated by commas.

    A period whose end precedes its start is refused at its end, the start named (422): no empty
    list stands for a refusal.
    """
    since, until = query.since, query.to
    if since is not None and until is not None and until < since:
        fault = FieldError("/query/to", VALUE_OUT_OF_RANGE, {"minimum": since.astimezone(UTC)})
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    actions = listed("actions", query.actions, AuditAction)
    return AuditFilters(
        since=since,
        until=until,
        user_id=query.user_id,
        actor_kind=None if query.actor_kind is None else query.actor_kind.value,
        actions=None if actions is None else frozenset(actions),
        project_id=query.project_id,
        object_kind=None if query.object_kind is None else query.object_kind.value,
        object_id=query.object_id,
        correlation_id=query.correlation_id,
        search=query.search,
    )


def audit_sort(
    sort_by: AuditColumn | None = None, sort_order: SortOrder | None = None
) -> AuditSort:
    """Read the sort the journal asks for; its direction absent, the column's own."""
    return AuditSort(sort_by, None if sort_order is None else sort_order is SortOrder.desc)


@dataclass(frozen=True, slots=True)
class Window:
    """The page asked for: how many inscriptions, after how many."""

    limit: int
    offset: int


def audit_window(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT, offset: Offset = 0
) -> Window:
    """Read the page the journal asks for: fifty inscriptions from the first by default."""
    return Window(limit, offset)


def opened_by(session: Session, actor: Acting, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give those of the projects an inscription cites that the caller opens (WF-ADM-0190).

    A project the caller opens is one that exists and that they read as the list of the projects
    gives it (WF-ADM-0110, WF-PRJ-0060): a reader of them all, or a contributor. A project that
    no longer exists — deleted, or created after the backup a restoration brought back — is
    named by its inscription and led to by nothing. Two reads for the whole page.
    """
    present = projects_present(session, project_ids)
    return openable(session, present, Viewer(actor.user_id, actor.permissions))


def audit_event(entry: AuditEntry, opens: frozenset[UUID]) -> AuditEvent:
    """Describe an inscription as the contract does, as it was at the moment of the action."""
    actor: dict[str, Any] = (
        {"kind": "platform"}
        if entry.actor_user_id is None
        else {
            "kind": "user",
            "user_id": entry.actor_user_id,
            "display_name": entry.actor_display_name,
        }
    )
    revision = (
        None
        if entry.object_revision_id is None
        else {"revision_id": entry.object_revision_id, "label": entry.object_revision_label}
    )
    project = (
        None
        if entry.project_id is None
        else {
            "project_id": entry.project_id,
            "code": entry.project_code,
            "label": entry.project_label,
            "can_open": entry.project_id in opens,
        }
    )
    return AuditEvent.model_validate(
        {
            "audit_event_id": entry.id,
            "occurred_at": entry.occurred_at,
            "actor": actor,
            "action": entry.action,
            "object": {
                "kind": entry.object_kind,
                "object_id": entry.object_id,
                "label": entry.object_label,
                "revision": revision,
            },
            "project": project,
            "params": entry.params,
            "correlation_id": entry.correlation_id,
        }
    )


# The platform as an author has no account, and a parameter an action does not carry is absent:
# both stay absent, not null.
@router.get("/audit-events", operation_id="listAuditEvents", dependencies=READ)
def get_audit_events(
    session: Transaction,
    actor: Acting,
    filters: Annotated[AuditFilters, Depends(audit_filters)],
    sort: Annotated[AuditSort, Depends(audit_sort)],
    window: Annotated[Window, Depends(audit_window)],
) -> dict[str, Any]:
    """Give a page of the journal, filtered and sorted by the server (WF-ADM-0190)."""
    limit, offset = window.limit, window.offset
    page = list_entries(session, filters, sort, limit, offset)
    cited = {entry.project_id for entry in page.entries if entry.project_id is not None}
    opens = opened_by(session, actor, cited)
    return {
        "items": [
            audit_event(entry, opens).model_dump(mode="json", exclude_unset=True)
            for entry in page.entries
        ],
        "meta": PaginationMeta(limit=limit, offset=offset, total=page.total).model_dump(),
    }


def _projects_today(session: Session) -> list[AuditProject]:
    """Name each project of the journal as it is today, as it was inscribed if it is gone (#927).

    A project that exists but bears no code today keeps the code of its latest inscription, if
    that one held a code; a project that never bore one is named without code, after the codes
    (#2166). The label, never null in the project, is read as it is. The projects are read
    together, in one grouped query, not one by one.
    """
    named = journal_projects(session)
    present = projects_named(session, [project.project_id for project in named])
    today: list[AuditProject] = []
    for project in named:
        if project.project_id in present:
            code, label = present[project.project_id]
            today.append(AuditProject(project.project_id, code or project.code, label))
        else:
            today.append(project)
    return sorted(today, key=by_code)


@router.get("/audit-events/facets", operation_id="listAuditFacets", dependencies=READ)
def get_audit_facets(session: Transaction, caller: Acting) -> AuditFacets:
    """Give the accounts and the projects the whole journal names, to choose one in its filters.

    An account by the name it shows today, read from the accounts — by the name its latest
    inscription keeps if none bears it any longer —, in the order of the names compared code point
    by code point, then of the identifiers; an account anonymised, which has lost its name, after
    the names, as the sort of the journal puts it. A project by the code and the label it bears
    today, read through the module of the projects — by those of its latest inscription if it no
    longer exists (#927) —, in the order of the codes compared code point by code point, then of
    the identifiers; a project without code after the codes (#2166).
    """
    named = journal_actors(session)
    projects = _projects_today(session)
    opens = opened_by(session, caller, [project.project_id for project in projects])
    today = read_authors(session, [actor.user_id for actor in named])
    actors = sorted(
        (
            (actor.user_id, today[actor.user_id].display_name)
            if actor.user_id in today
            else (actor.user_id, actor.display_name)
            for actor in named
        ),
        key=lambda actor: (actor[1] is None, actor[1] or "", actor[0]),
    )
    return AuditFacets.model_validate(
        {
            "actors": [{"user_id": user_id, "display_name": name} for user_id, name in actors],
            "projects": [
                {
                    "project_id": project.project_id,
                    "code": project.code,
                    "label": project.label,
                    "can_open": project.project_id in opens,
                }
                for project in projects
            ],
        }
    )
