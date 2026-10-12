# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The family ``audit``: the journal of audit read, never written (FBS-1.5, WF-ADM-0190).

Both operations ask for the permission to consult the journal alone (WF-ADM-0100): without it,
the journal does not exist for the caller (404). The journal is the whole of it — every account,
the platform, every project —, read as it keeps itself: an inscription is a code and data, never a
sentence, that the front words in the language of each reader (WF-ARC-0110). No operation
inscribes, changes or deletes an inscription: only the action itself inscribes (WF-SEC-0030).
"""

from datetime import UTC
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, Field

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
from waterfall.api.evaluation import Requires
from waterfall.api.queries import listed
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import AuditEntry
from waterfall.platform.audit_consultation import (
    AuditColumn,
    AuditFilters,
    AuditSort,
    journal_actors,
    journal_projects,
    list_entries,
)
from waterfall.platform.errors import FieldError, UnprocessableError

router = APIRouter(tags=["audit"])

CONSULTATION = "audit_log.read"
READ = [Depends(Requires(CONSULTATION))]
VALIDATION_FAILED = "VALIDATION_FAILED"
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


def audit_event(entry: AuditEntry) -> AuditEvent:
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
    filters: Annotated[AuditFilters, Depends(audit_filters)],
    sort: Annotated[AuditSort, Depends(audit_sort)],
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Give a page of the journal, filtered and sorted by the server (WF-ADM-0190)."""
    page = list_entries(session, filters, sort, limit, offset)
    return {
        "items": [
            audit_event(entry).model_dump(mode="json", exclude_unset=True) for entry in page.entries
        ],
        "meta": PaginationMeta(limit=limit, offset=offset, total=page.total).model_dump(),
    }


@router.get("/audit-events/facets", operation_id="listAuditFacets", dependencies=READ)
def get_audit_facets(session: Transaction) -> AuditFacets:
    """Give the accounts and the projects the whole journal names, to choose one in its filters.

    An account by the name it shows today, read from the accounts — by the name its latest
    inscription keeps if none bears it any longer —, in the order of the names compared code point
    by code point, then of the identifiers; an account anonymised, which has lost its name, after
    the names, as the sort of the journal puts it.
    """
    named = journal_actors(session)
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
                {"project_id": project.project_id, "code": project.code, "label": project.label}
                for project in journal_projects(session)
            ],
        }
    )
