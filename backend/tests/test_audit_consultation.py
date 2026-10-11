# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The consultation of the journal of audit through the API: a flat table, filtered and sorted.

The journal is written as the actions write it (``record``), under the correlation of a request,
then read by ``listAuditEvents`` and ``listAuditFacets`` by a reader who holds the permission to
consult it and no other (FBS-1.5). Every answer is checked against the contract.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import text, update
from sqlalchemy.dialects import postgresql
from support import ContractClient, bearer

from waterfall.api.contract import models
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import (
    AuditAction,
    AuditActor,
    AuditObject,
    AuditObjectKind,
    AuditProject,
    AuditRevision,
    AuditValue,
    Inscription,
    record,
)
from waterfall.platform.audit_consultation import (
    AuditColumn,
    AuditFilters,
    AuditSort,
    journal_query,
)
from waterfall.platform.database import Database
from waterfall.platform.logs import logging_context

EVENTS = "/api/v1/audit-events"
FACETS = "/api/v1/audit-events/facets"
CONSULTATION = "audit_log.read"
CLAIRE = AuditActor(uuid4(), "Claire Martin")
BRUNO = AuditActor(uuid4(), "bruno Petit")
FIRST = AuditProject(uuid4(), "PRJ-001", "Modernisation du poste de commande")
SECOND = AuditProject(uuid4(), "PRJ-002", "Extension de la sous-station")


@dataclass(frozen=True, slots=True)
class Written:
    """An inscription a test writes: what, by whom, on what, when, under which correlation."""

    at: datetime
    actor: AuditActor | None
    action: AuditAction
    kind: AuditObjectKind
    label: str | None
    correlation: str
    project: AuditProject | None = None
    params: dict[str, AuditValue] = field(default_factory=dict[str, AuditValue])
    object_id: UUID = field(default_factory=uuid4)


def at(day: int, month: int = 10, hour: int = 9) -> datetime:
    """Give an instant of 2026 in universal time."""
    return datetime(2026, month, day, hour, tzinfo=UTC)


# The journal of the tests, in the order of inscription: two inscriptions of one request at one
# instant, the platform, an object without a label, a revision and two projects, names and labels
# whose order of code points is not that of a dictionary.
JOURNAL = (
    Written(
        at(1, 9),
        CLAIRE,
        "access_role_create",
        "access_role",
        "Auditeur",
        "req-a",
        params={"permissions": ["audit_log.read"]},
    ),
    Written(
        at(1, 9),
        CLAIRE,
        "user_access_roles_set",
        "user",
        "Élodie Zola",
        "req-a",
        params={"access_roles_granted": [], "access_roles_withdrawn": []},
    ),
    Written(
        at(15, 9), None, "user_create", "user", "Zoé Arnaud", "sync-b", params={"origin": "local"}
    ),
    Written(at(2), BRUNO, "user_deactivate", "user", "Claire Martin", "req-c"),
    Written(at(3), None, "backup", "backup", None, "task-d"),
    Written(at(4), CLAIRE, "revision_mark", "revision", "Offre v1.0", "req-e", project=SECOND),
    Written(
        at(5), BRUNO, "cost_line_exclude", "cost_line", "FA-2026-0295%", "req-f", project=FIRST
    ),
    Written(at(6), CLAIRE, "import_apply", "import", "coûts-réels-2026-05.xlsx", "req-g", FIRST),
)


def write(database: Database, journal: tuple[Written, ...] = JOURNAL) -> list[UUID]:
    """Inscribe the journal, each inscription under its correlation; give their identifiers."""
    written: list[UUID] = []
    for each in journal:
        revision = AuditRevision(uuid4(), "Offre v1.0") if each.kind == "revision" else None
        inscription = Inscription(
            each.action,
            each.actor,
            AuditObject(each.kind, each.object_id, each.label, revision),
            each.at,
            each.project,
            each.params,
        )
        with logging_context(correlation_id=each.correlation), database.transaction() as session:
            written.append(record(session, inscription))
    return written


@pytest.fixture
def reader(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write an account that may consult the journal and nothing else; give its token's header."""
    subject = f"subject-{uuid4()}"
    auditor = role(database, "Auditeur", permissions=(CONSULTATION,))
    account(database, "Lambert", "Ines", roles=(auditor,), idp_subject=subject)
    return bearer(realm.token(subject, KEY))


def read(api: ContractClient, headers: dict[str, str], **query: str) -> dict[str, Any]:
    """Read a page of the journal; fail unless it is given."""
    response = api.get(f"{EVENTS}?{urlencode(query)}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def labels(page: dict[str, Any]) -> list[str | None]:
    """Give the labels of the objects of a page, in its order."""
    return [event["object"]["label"] for event in page["items"]]


def expected(column: str | None, *, descending: bool | None) -> list[str | None]:
    """Give the labels of the journal in the order the contract sorts it, read from ``JOURNAL``.

    The journal's own order — by date, the latest first, two of one instant in the reverse order of
    their inscription — breaks the ties of any other column, whichever its direction; a column
    without a value comes last in the ascending order, first in the descending one.
    """
    journal = list(enumerate(JOURNAL))
    latest = sorted(journal, key=lambda each: (each[1].at, each[0]), reverse=True)
    if column in {None, "occurred_at"}:
        ordered = latest[::-1] if descending is False else latest
        return [each.label for _, each in ordered]
    ranks = {
        "action": [action.value for action in models.AuditAction],
        "object_kind": [kind.value for kind in models.AuditObjectKind],
    }

    def value(written: Written) -> tuple[int, str] | None:
        if column in ranks:
            named = written.action if column == "action" else written.kind
            return ranks[str(column)].index(named), ""
        text = {
            "actor": None if written.actor is None else written.actor.display_name,
            "object_label": written.label,
            "project": None if written.project is None else written.project.code,
            "correlation_id": written.correlation,
        }[str(column)]
        return None if text is None else (0, text)

    valued = [each for each in latest if value(each[1]) is not None]
    valued.sort(key=lambda each: value(each[1]) or (0, ""), reverse=bool(descending))
    empty = [each for each in latest if value(each[1]) is None]
    ordered = [*empty, *valued] if descending else [*valued, *empty]
    return [each.label for _, each in ordered]


def test_the_journal_reads_the_latest_first_two_of_one_instant_in_reverse_order_of_writing(
    api: ContractClient, database: Database, reader: dict[str, str]
) -> None:
    write(database)
    page = read(api, reader)
    assert labels(page) == expected(None, descending=None)
    assert labels(page)[-2:] == ["Élodie Zola", "Auditeur"]
    assert page["meta"] == {"limit": 50, "offset": 0, "total": len(JOURNAL)}
    second = read(api, reader, limit="3", offset="3")
    assert labels(second) == labels(page)[3:6]
    assert second["meta"] == {"limit": 3, "offset": 3, "total": len(JOURNAL)}


def test_an_inscription_is_read_as_it_was_written_by_its_codes_and_its_data(
    api: ContractClient, database: Database, reader: dict[str, str]
) -> None:
    identifiers = write(database)
    events = {event["audit_event_id"]: event for event in read(api, reader)["items"]}
    attribution = events[str(identifiers[1])]
    assert attribution == {
        "audit_event_id": str(identifiers[1]),
        "occurred_at": "2026-09-01T09:00:00Z",
        "actor": {
            "kind": "user",
            "user_id": str(CLAIRE.user_id),
            "display_name": "Claire Martin",
        },
        "action": "user_access_roles_set",
        "object": {
            "kind": "user",
            "object_id": str(JOURNAL[1].object_id),
            "label": "Élodie Zola",
            "revision": None,
        },
        "project": None,
        "params": {"access_roles_granted": [], "access_roles_withdrawn": []},
        "correlation_id": "req-a",
    }
    marked = events[str(identifiers[5])]
    assert marked["object"]["revision"]["label"] == "Offre v1.0"
    assert marked["project"] == {
        "project_id": str(SECOND.project_id),
        "code": "PRJ-002",
        "label": "Extension de la sous-station",
    }
    assert (marked["params"], events[str(identifiers[4])]["actor"]) == ({}, {"kind": "platform"})


COLUMNS = ["occurred_at", "actor", "action", "object_kind", "object_label", "project"]


@pytest.mark.requirement("WF-IHM-0060-A")
@pytest.mark.parametrize("column", [*COLUMNS, "correlation_id"])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_each_column_of_the_journal_sorts_in_both_directions(
    api: ContractClient, database: Database, reader: dict[str, str], column: str, order: str
) -> None:
    # « Chaque colonne d'une table plate se trie dans les deux sens » : the journal is one, sorted
    # by the server on each of its seven columns.
    write(database)
    page = read(api, reader, sort_by=column, sort_order=order)
    assert labels(page) == expected(column, descending=order == "desc")


@pytest.mark.parametrize("column", COLUMNS)
def test_a_column_sorted_without_a_direction_takes_its_own(
    api: ContractClient, database: Database, reader: dict[str, str], column: str
) -> None:
    # The date the latest first, any other column ascending.
    write(database)
    page = read(api, reader, sort_by=column)
    assert labels(page) == expected(column, descending=None if column == "occurred_at" else False)


@pytest.mark.parametrize(
    ("query", "kept"),
    [
        ({"from": "2026-10-03T09:00:00Z"}, [7, 6, 5, 4]),
        ({"to": "2026-10-03T09:00:00Z"}, [3, 2, 1, 0]),
        ({"from": "2026-09-15T09:00:00+00:00", "to": "2026-10-04T09:00:00Z"}, [4, 3, 2]),
        ({"user_id": str(BRUNO.user_id)}, [6, 3]),
        ({"actor_kind": "platform"}, [4, 2]),
        ({"actor_kind": "user"}, [7, 6, 5, 3, 1, 0]),
        ({"actions": "user_create,backup"}, [4, 2]),
        ({"project_id": str(FIRST.project_id)}, [7, 6]),
        ({"object_kind": "user"}, [3, 2, 1]),
        ({"object_id": str(JOURNAL[3].object_id)}, [3]),
        ({"correlation_id": "req-a"}, [1, 0]),
        ({"search": "COUTS-reels"}, [7]),
        ({"search": "élodie"}, [1]),
        ({"search": "95%"}, [6]),
        ({"search": "0295_"}, []),
        ({"actor_kind": "user", "object_kind": "user", "correlation_id": "req-a"}, [1]),
        ({"user_id": str(CLAIRE.user_id), "actor_kind": "platform"}, []),
    ],
)
def test_each_filter_keeps_what_it_says_and_the_filters_combine(
    api: ContractClient,
    database: Database,
    reader: dict[str, str],
    query: dict[str, str],
    kept: list[int],
) -> None:
    # A search finds the text whatever its case and its accents, a « % » as a letter, and no
    # label in an object that has none, a backup.
    identifiers = write(database)
    page = read(api, reader, **query)
    assert [event["audit_event_id"] for event in page["items"]] == [
        str(identifiers[rank]) for rank in kept
    ]
    assert page["meta"]["total"] == len(kept)


@pytest.mark.requirement("WF-ADM-0190-A")
def test_filtered_on_a_month_without_any_action_the_journal_presents_nothing(
    api: ContractClient, database: Database, reader: dict[str, str]
) -> None:
    # « Filtré sur un mois sans aucune action, il ne présente rien » : August, before the first
    # inscription, its last instant included and the first of September excluded.
    write(database)
    page = read(api, reader, **{"from": "2026-08-01T00:00:00Z", "to": "2026-09-01T00:00:00Z"})
    assert page == {"items": [], "meta": {"limit": 50, "offset": 0, "total": 0}}


def test_a_period_whose_end_precedes_its_start_is_refused_naming_the_start(
    api: ContractClient, reader: dict[str, str]
) -> None:
    query = urlencode({"from": "2026-06-03T16:00:00+02:00", "to": "2026-06-01T00:00:00Z"})
    response = api.get(f"{EVENTS}?{query}", headers=reader)
    assert response.status_code == 422
    assert response.json()["fields"] == [
        {
            "pointer": "/query/to",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": "2026-06-03T14:00:00Z"},
        }
    ]


@pytest.mark.parametrize(
    ("query", "pointer", "code"),
    [
        ("from=2026-06-03T14:00:00", "/query/from", "DATE_INVALID"),
        ("to=yesterday", "/query/to", "DATE_INVALID"),
        ("actions=user_create,user_erase", "/query/actions", "VALIDATION_FAILED"),
        ("actions=", "/query/actions", "VALIDATION_FAILED"),
        ("actor_kind=robot", "/query/actor_kind", "VALIDATION_FAILED"),
        ("object_kind=planet", "/query/object_kind", "VALIDATION_FAILED"),
        ("user_id=claire", "/query/user_id", "VALIDATION_FAILED"),
        ("correlation_id=req%20a", "/query/correlation_id", "VALIDATION_FAILED"),
        ("search=", "/query/search", "VALUE_REQUIRED"),
        ("search=%00", "/query/search", "VALIDATION_FAILED"),
        ("sort_by=params", "/query/sort_by", "VALIDATION_FAILED"),
        ("sort_order=up", "/query/sort_order", "VALIDATION_FAILED"),
        ("limit=501", "/query/limit", "VALUE_OUT_OF_RANGE"),
        ("offset=-1", "/query/offset", "VALUE_OUT_OF_RANGE"),
    ],
)
def test_a_parameter_out_of_its_schema_is_refused_at_its_field(
    api: ContractClient, reader: dict[str, str], query: str, pointer: str, code: str
) -> None:
    response = api.get(f"{EVENTS}?{query}", headers=reader)
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert [(each["pointer"], each["code"]) for each in body["fields"]] == [(pointer, code)]


@pytest.mark.requirement("WF-ADM-0190-A")
@pytest.mark.parametrize("path", [EVENTS, FACETS])
def test_a_user_without_the_permission_to_consult_the_journal_does_not_reach_it(
    api: ContractClient, database: Database, realm: TestRealm, path: str
) -> None:
    # « Un utilisateur sans la permission de consulter FBS-1.5 n'atteint pas la vue » : the journal
    # does not exist for him, whatever else he may do — here, everything but that.
    write(database)
    subject = f"subject-{uuid4()}"
    others = ("users.read", "users.write", "access_roles.read", "access_roles.write")
    account(database, "Roux", "Ines", roles=(role(database, "Gestion", permissions=others),))
    account(
        database,
        "Vidal",
        "Noé",
        roles=(role(database, "Presque tout", permissions=others),),
        idp_subject=subject,
    )
    response = api.get(path, headers=bearer(realm.token(subject, KEY)))
    assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")


def test_the_facets_name_each_author_as_shown_today_and_each_project_once(
    api: ContractClient, database: Database, reader: dict[str, str]
) -> None:
    # An author renamed since keeps in each inscription the name of its moment, and is chosen in
    # the filters by the name it shows today; the platform is no author. A project by the code and
    # the label of its latest inscription, in the order of the codes.
    claire = account(database, "Martin", "Claire", email="claire@example.org")
    bruno = AuditActor(
        account(database, "Petit", "bruno", email="bruno@example.org"), "bruno Petit"
    )
    renamed = AuditActor(claire, "Claire Martin")
    journal = tuple(replace_actor(each, {CLAIRE: renamed, BRUNO: bruno}) for each in JOURNAL)
    write(database, journal)
    with database.transaction() as session:
        session.execute(
            update(UserAccount).where(UserAccount.id == claire).values(last_name="Abel")
        )
    response = api.get(FACETS, headers=reader)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "actors": [
            {"user_id": str(claire), "display_name": "Claire Abel"},
            {"user_id": str(bruno.user_id), "display_name": "bruno Petit"},
        ],
        "projects": [
            {"project_id": str(FIRST.project_id), "code": "PRJ-001", "label": FIRST.label},
            {"project_id": str(SECOND.project_id), "code": "PRJ-002", "label": SECOND.label},
        ],
    }
    names = {event["actor"].get("display_name") for event in read(api, reader)["items"]}
    assert names == {"Claire Martin", "bruno Petit", None}


def replace_actor(written: Written, actors: dict[AuditActor, AuditActor]) -> Written:
    """Give the inscription written by the account that stands for its author."""
    actor = None if written.actor is None else actors[written.actor]
    return Written(
        written.at,
        actor,
        written.action,
        written.kind,
        written.label,
        written.correlation,
        written.project,
        written.params,
        written.object_id,
    )


def test_a_journal_without_any_inscription_has_no_facet(
    api: ContractClient, reader: dict[str, str]
) -> None:
    response = api.get(FACETS, headers=reader)
    assert (response.status_code, response.json()) == (200, {"actors": [], "projects": []})


@pytest.mark.parametrize(
    ("column", "index"),
    [("action", "ix_audit_entry_action_rank"), ("object_kind", "ix_audit_entry_object_kind_rank")],
)
def test_the_sorts_on_the_action_and_on_the_nature_are_served_by_their_index(
    database: Database, column: AuditColumn, index: str
) -> None:
    # The query names the very expression the index holds: the planner, a sequential reading
    # forbidden, reads the journal in its order rather than sorting it.
    query = journal_query(AuditFilters(), AuditSort(column, descending=False))
    compiled = query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    with database.transaction() as session:
        session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = session.execute(text(f"EXPLAIN {compiled}")).scalars().all()
    assert any(index in line for line in plan), plan
