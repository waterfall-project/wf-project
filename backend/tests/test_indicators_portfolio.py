# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the indicators offer the portfolio: keep, read kept, read of the day (US-2680/L1).

``keep_document`` writes a document of the portfolio at the act of the marking, in its transaction,
and nowhere else; what it wrote is never written again. ``kept_documents_of`` reads the documents of
several marked revisions in one statement. ``day_documents_of`` gives the documents of the day of
several projects from the cache of the indicators, under the fingerprint of each project, against
the Redis of the tests ("Un test contre Redis"): one exchange for all, a project computed once, a
write or a day that changes the key computed again, a Redis out of reach computed and not written.
The projects are those of the fabrics of the portfolio (``portfolio_support``); the computation of
the day stands for that of ``core/portfolio``, which US-2680/L2 writes.
"""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from portfolio_support import OFFER, READ_ON, REVIEW, Portfolio, portfolio
from projects_support import MANAGING, PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import event, select
from sqlalchemy.exc import DBAPIError, IntegrityError

from waterfall.core.indicators.contributions import (
    UnserializableContributionError,
    contribution_key,
    read_contribution,
    stamps_of,
)
from waterfall.core.indicators.interface import (
    PORTFOLIO_KINDS,
    Contributing,
    day_documents_of,
    keep_document,
    kept_documents_of,
)
from waterfall.core.indicators.interface.portfolio import (
    STATEMENTS_PER_PROJECT,
    STATEMENTS_PER_READING,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import (
    ProjectChange,
    Viewer,
    stored_lock_version,
    update_project,
)
from waterfall.core.revisions.interface import mark_revision, register_indicators
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.cache import PREFIX, IndicatorsCache, forget_reports
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping, Sequence

    from realm import TestRealm
    from redis import Redis
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.platform.cache import Unavailable
    from waterfall.platform.database import Database

# The validity of an entry in these tests, in seconds.
TTL = 300
# A Redis no one listens on.
CLOSED_PORT = "redis://127.0.0.1:1/0"
# What the triggers of the table say when they refuse a row (migration 0032).
OUTSIDE = "the indicators of a revision are written by its marking alone"
ROW_REFUSED = "a row of a marked revision is never written"
# A document of the workload, as the computation of the portfolio would give it.
WORKLOAD: Document = {"months": [{"month": "2026-03", "hours": "8.00"}]}


# --- Keeping at the marking --------------------------------------------------------------------


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def open_revision(api: ContractClient, stage: Scene) -> UUID:
    """Open the current revision of the project of the stage, as its manager does; give it."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return UUID(response.json()["revision_id"])


def marked_keeping(
    stage: Scene, revision_id: UUID, act: Act, keep: Mapping[IndicatorKind, Document], kept_at: Act
) -> None:
    """Mark a revision at ``act``, a computation registered keeping ``keep`` at ``kept_at``."""

    def keeping(session: Session, marked: UUID, _act: Act) -> None:
        for kind, document in keep.items():
            keep_document(session, marked, kind, document, kept_at)

    withdraw = register_indicators(keeping)
    try:
        with logging_context(correlation_id="marking"), stage.database.transaction() as session:
            mark_revision(session, revision_id, "v1.0", None, act)
    finally:
        withdraw()


def rows_of(owner: Engine, revision_id: UUID) -> list[tuple[object, ...]]:
    """Read the documents of the portfolio a revision kept, as the base holds them."""
    with owner.connect() as connection:
        rows = connection.execute(
            select(
                RevisionIndicator.kind,
                RevisionIndicator.scope,
                RevisionIndicator.computed_at,
                RevisionIndicator.created_at,
                RevisionIndicator.created_by,
                RevisionIndicator.document,
            )
            .where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind.in_(sorted(PORTFOLIO_KINDS)),
            )
            .order_by(RevisionIndicator.kind)
        )
        return [tuple(row) for row in rows]


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_document_of_the_portfolio_is_kept_at_the_act_of_the_marking_in_its_transaction(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # Propre à l'US : the documents of the portfolio are computed at the instant of the marking and
    # written in its transaction, under the kinds of the portfolio: the scope of the project, the
    # instant of the marking its ``computed_at``, its requester the author, the document as given.
    # The kind is one the marking of an offer does not keep itself (``store_contribution``): the
    # milestones, which ask for a reference.
    revision_id = open_revision(api, stage)
    act = Act(stage.manager.user_id, utc_now())
    milestones: Document = {"milestones": []}
    marked_keeping(stage, revision_id, act, {"portfolio_milestones": milestones}, act)
    with stage.database.transaction() as session:
        marked_at = session.scalar(select(Revision.marked_at).where(Revision.id == revision_id))
    assert marked_at == act.at
    author = stage.manager.user_id
    kept = [row for row in rows_of(owner, revision_id) if row[0] == "portfolio_milestones"]
    assert kept == [("portfolio_milestones", "project", act.at, act.at, author, milestones)]


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_document_kept_at_another_instant_than_the_marking_fails_the_marking_whole(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # Propre à l'US : the document is computed at the instant of the marking (#3549); one that says
    # another instant is refused at the end of the transaction, which the marking with it.
    revision_id = open_revision(api, stage)
    act = Act(stage.manager.user_id, utc_now())
    later = Act(act.author, act.at + timedelta(seconds=1))
    with pytest.raises(DBAPIError, match=OUTSIDE):
        marked_keeping(stage, revision_id, act, {"portfolio_milestones": WORKLOAD}, later)
    with stage.database.transaction() as session:
        revision = session.get(Revision, revision_id)
        assert revision is not None
        assert (revision.status, revision.marked_at) == ("draft", None)
    assert rows_of(owner, revision_id) == []


def test_a_document_kept_outside_a_marking_is_refused_at_the_end_of_its_transaction(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # Covers no requirement: the trigger of #3549, reached through ``keep_document``. A
    # transaction that keeps a document and does not mark its revision is refused at its end.
    revision_id = open_revision(api, stage)
    with pytest.raises(DBAPIError, match=OUTSIDE), stage.database.transaction() as session:
        keep_document(session, revision_id, "portfolio_workload", WORKLOAD, Act(None, utc_now()))
    assert rows_of(owner, revision_id) == []


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_document_of_the_portfolio_is_never_kept_again_once_its_revision_is_marked(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # Propre à l'US : the documents follow the immutability of the revision. Once marked, a second
    # document of a kind kept, or one of a kind not kept, is refused by the guard of the table, at
    # once: what the marking kept stays as it was.
    revision_id = open_revision(api, stage)
    act = Act(None, utc_now())
    marked_keeping(stage, revision_id, act, {"portfolio_milestones": WORKLOAD}, act)
    before = rows_of(owner, revision_id)
    for kind in ("portfolio_workload", "portfolio_risks"):
        refused = pytest.raises(IntegrityError, match=ROW_REFUSED)
        with refused, stage.database.transaction() as session:
            keep_document(session, revision_id, kind, {"changed": True}, act)
    assert rows_of(owner, revision_id) == before


@pytest.mark.parametrize("kind", ["project", "estimate", "cost_curve"])
def test_a_kind_of_the_marking_of_ep10_is_not_kept_for_another_module(
    stage: Scene, kind: IndicatorKind
) -> None:
    # Covers no requirement: the documents of EP-10 are the marking's own (``store_indicators``);
    # ``keep_document`` writes the kinds of the portfolio alone, a fault of its caller otherwise.
    with stage.database.transaction() as session, pytest.raises(ValueError, match=kind):
        keep_document(session, uuid4(), kind, WORKLOAD, Act(None, utc_now()))


# --- Reading what was kept -----------------------------------------------------------------------


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    return portfolio(api, make_scene(api, owner, database, realm))


@contextmanager
def statements_on(session: Session) -> Generator[list[str]]:
    """Record the statements of ``session`` that read the indicators kept, while in the block."""
    seen: list[str] = []

    def capture(*call: Any) -> None:
        statement = call[2]
        if "FROM revision_indicator" in statement:
            seen.append(statement)

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", capture)
    try:
        yield seen
    finally:
        event.remove(bind, "before_cursor_execute", capture)


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_documents_several_marked_revisions_kept_are_read_in_one_statement(
    fabrics: Portfolio,
) -> None:
    # Propre à l'US : a view at a past date reads, for every project of its scope, the documents its
    # retained revision kept, in one statement. The review of the project In progress kept the
    # indicators of the project, its estimate and its milestones; an offer, its estimate and its
    # curves, no indicator of a project; a revision that kept none of the kinds, or that does not
    # exist, has its entry, empty.
    review = fabrics.in_progress.marked[REVIEW][0]
    offer = fabrics.offer.marked[OFFER][0]
    unknown = uuid4()
    kinds: list[IndicatorKind] = [
        "project",
        "estimate",
        "portfolio_milestones",
        "portfolio_offer_curves",
    ]
    with fabrics.stage.database.transaction() as session, statements_on(session) as seen:
        kept = kept_documents_of(session, [review, offer, unknown], kinds)
    assert set(kept) == {review, offer, unknown}
    assert set(kept[review]) == {"project", "estimate", "portfolio_milestones"}
    assert set(kept[offer]) == {"estimate", "portfolio_offer_curves"}
    assert kept[unknown] == {}
    assert kept[review]["estimate"]["context"]["revision_id"] == str(review)
    assert kept[review]["estimate"]["context"]["scope"] == "project"
    assert len(seen) == 1


def test_no_revision_or_no_kind_reads_nothing(fabrics: Portfolio) -> None:
    # Covers no requirement: a scope without a project at the date, or a view that asks no kind,
    # costs no statement.
    review = fabrics.in_progress.marked[REVIEW][0]
    with fabrics.stage.database.transaction() as session, statements_on(session) as seen:
        assert kept_documents_of(session, [], ["project"]) == {}
        assert kept_documents_of(session, [review], []) == {review: {}}
    assert seen == []


# --- The documents of the day --------------------------------------------------------------------

# The instant of the readings of the day: the date of the witness, after every fact of the fabrics.
AT = datetime(READ_ON.year, READ_ON.month, READ_ON.day, 9, 0, tzinfo=UTC)
# The kinds every entry of these readings answers.
KINDS: tuple[IndicatorKind, ...] = ("portfolio_workload",)


@dataclass
class Counted:
    """The computation of the day of the portfolio, which records each project it computes.

    It gives a document of the workload that names the project, the revision and the instant.
    """

    calls: list[tuple[UUID, UUID]] = field(default_factory=list[tuple[UUID, UUID]])

    def __call__(
        self, session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
    ) -> Mapping[IndicatorKind, Document]:
        del session
        self.calls.append((project_id, revision_id))
        workload = {"project": str(project_id), "revision": str(revision_id), "at": at.isoformat()}
        return {"portfolio_workload": workload}


class Exchanges(IndicatorsCache):
    """The cache of the indicators, which counts its exchanges of reading and its writes."""

    def __init__(self, client: Redis, ttl: int) -> None:
        """Count nothing yet."""
        super().__init__(client, ttl)
        self.lookups = 0
        self.writes: list[list[str]] = []

    def lookup_many(self, keys: Sequence[str]) -> list[str | None] | Unavailable:
        """Count the exchange, then read."""
        self.lookups += 1
        return super().lookup_many(keys)

    def write_many(self, documents: Mapping[str, str]) -> None:
        """Count the keys written, then write."""
        self.writes.append(list(documents))
        super().write_many(documents)


@pytest.fixture(autouse=True)
def fresh_reports() -> None:
    """Forget the causes the process has logged: each test sees the first of them."""
    forget_reports()


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[Exchanges]:
    """Give the cache of the indicators beside the queue of the test; the entries it wrote deleted.

    Those alone: another test may share the Redis of the tests.
    """
    opened = Exchanges.of(queue, TTL)
    yield opened
    written = {PREFIX + key for keys in opened.writes for key in keys}
    if written:
        opened.client.delete(*written)
    opened.close()


def of_the_day(fabrics: Portfolio) -> dict[UUID, UUID]:
    """Give the revision of the day of each project of the fabrics: its last marked one.

    None is current: the project In progress and the completed one give their review, the offers
    their offer.
    """
    return {
        project.project_id: max(project.marked.values(), key=lambda each: each[1])[0]
        for project in fabrics.projects
    }


def read_day(
    fabrics: Portfolio, at: datetime, counted: Counted, cache: IndicatorsCache | None
) -> dict[UUID, dict[IndicatorKind, Document]]:
    """Read the documents of the day of the four projects, at an instant."""
    with fabrics.stage.database.transaction() as session:
        contributing = Contributing(counted, KINDS)
        return day_documents_of(session, of_the_day(fabrics), at, contributing, cache)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_documents_of_the_day_are_computed_once_then_read_from_the_cache_in_one_exchange(
    fabrics: Portfolio, cache: Exchanges
) -> None:
    # Propre à l'US : the contribution of a project on the current day is computed once and kept by
    # the cache of EP-10, under the fingerprint of the project. The first reading computes the four
    # and writes them together; the second, later the same day, computes none and serves what the
    # first computed. Each reads the entries of the four in one exchange.
    revisions = of_the_day(fabrics)
    counted = Counted()
    first = read_day(fabrics, AT, counted, cache)
    assert counted.calls == list(revisions.items())
    assert list(first) == list(revisions)
    for project_id, documents in first.items():
        assert documents == {
            "portfolio_workload": {
                "project": str(project_id),
                "revision": str(revisions[project_id]),
                "at": AT.isoformat(),
            }
        }
    assert (cache.lookups, [len(keys) for keys in cache.writes]) == (1, [4])
    second = read_day(fabrics, AT + timedelta(hours=3), counted, cache)
    assert second == first
    assert len(counted.calls) == len(revisions)
    assert (cache.lookups, len(cache.writes)) == (2, 1)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_write_of_a_project_leaves_its_entry_alone_and_the_next_day_every_entry(
    fabrics: Portfolio, cache: Exchanges
) -> None:
    # Propre à l'US : the key is the fingerprint of the indicators of the day: a change of the
    # project In progress advances its counter, and its contribution alone is computed again; the
    # next day, every one is.
    revisions = of_the_day(fabrics)
    counted = Counted()
    read_day(fabrics, AT, counted, cache)
    running = fabrics.in_progress.project_id
    manager = fabrics.stage.manager.user_id
    with fabrics.stage.database.transaction() as session:
        counter = stored_lock_version(session, running)
        change = ProjectChange({"label": "Rénovation de la ligne 4"}, counter)
        update_project(session, running, change, Act(manager, AT), Viewer(manager, MANAGING))
    counted.calls.clear()
    changed = read_day(fabrics, AT + timedelta(minutes=5), counted, cache)
    assert counted.calls == [(running, revisions[running])]
    assert changed[running]["portfolio_workload"]["at"] == (AT + timedelta(minutes=5)).isoformat()
    counted.calls.clear()
    read_day(fabrics, AT + timedelta(days=1), counted, cache)
    assert counted.calls == list(revisions.items())


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.parametrize("damage", ["not JSON", "[]", '{"portfolio_workload": "1"}'])
def test_an_entry_unreadable_is_a_miss_computed_and_written_again(
    fabrics: Portfolio, cache: Exchanges, damage: str
) -> None:
    # Propre à l'US : an entry that is not an object of documents is no contribution: the project
    # is computed again, alone, and its entry written again.
    revisions = of_the_day(fabrics)
    offer = fabrics.offer.project_id
    counted = Counted()
    first = read_day(fabrics, AT, counted, cache)
    with fabrics.stage.database.transaction() as session:
        key = contribution_key(session, offer, revisions[offer], AT, stamps_of(session))
    cache.client.set(PREFIX + key, damage, ex=TTL)
    counted.calls.clear()
    again = read_day(fabrics, AT, counted, cache)
    assert counted.calls == [(offer, revisions[offer])]
    assert again == first
    assert json.loads(cache.read(key) or "null") == first[offer]


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_out_of_reach_or_no_cache_computes_every_project_and_writes_nothing(
    fabrics: Portfolio,
) -> None:
    # « L'indisponibilité du cache des indicateurs n'empêche aucune lecture […] » : a Redis that
    # answers nowhere is a miss for every project, each computed and none written; without a cache,
    # every reading computes them all.
    revisions = of_the_day(fabrics)
    closed = TaskQueue.connect(CLOSED_PORT, timeout=WORKER_TIMEOUT)
    unreachable = Exchanges.of(closed, TTL)
    try:
        counted = Counted()
        found = read_day(fabrics, AT, counted, unreachable)
        assert counted.calls == list(revisions.items())
        assert (unreachable.lookups, unreachable.writes) == (1, [])
    finally:
        unreachable.close()
        closed.close()
    counted = Counted()
    assert read_day(fabrics, AT, counted, None) == found
    assert read_day(fabrics, AT, counted, None) == found
    assert counted.calls == [*revisions.items(), *revisions.items()]


def statements_of_day(
    fabrics: Portfolio, revisions: dict[UUID, UUID], cache: IndicatorsCache
) -> int:
    """Count the SQL statements of a reading of the day of ``revisions``."""
    seen: list[str] = []

    def capture(*call: Any) -> None:
        seen.append(call[2])

    with fabrics.stage.database.transaction() as session:
        bind = session.get_bind()
        event.listen(bind, "before_cursor_execute", capture)
        try:
            day_documents_of(session, revisions, AT, Contributing(Counted(), KINDS), cache)
        finally:
            event.remove(bind, "before_cursor_execute", capture)
    return len(seen)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_statements_of_a_warm_reading_of_the_day_are_bounded_per_project(
    fabrics: Portfolio, cache: Exchanges
) -> None:
    # Propre à l'US : the fingerprint of a project is read by statements, project after project,
    # even when Redis answers all; the cost per project is bounded (STATEMENTS_PER_PROJECT,
    # documented by ``day_documents_of``), the stamp of the roles once by reading, and the
    # exchanges with Redis do not grow with them.
    revisions = of_the_day(fabrics)
    read_day(fabrics, AT, Counted(), cache)
    lookups = cache.lookups
    counts = {
        size: statements_of_day(fabrics, dict(list(revisions.items())[:size]), cache)
        for size in (1, len(revisions))
    }
    assert cache.lookups == lookups + 2
    assert len(cache.writes) == 1
    for size, count in counts.items():
        assert count <= STATEMENTS_PER_PROJECT * size + STATEMENTS_PER_READING


@pytest.mark.requirement("WF-DAT-0130-A")
@pytest.mark.parametrize("with_cache", [True, False])
@pytest.mark.parametrize("value", [AT, Decimal("1.00"), float("nan"), float("inf")])
def test_a_document_that_is_not_json_is_refused_with_a_cache_or_without(
    fabrics: Portfolio, cache: Exchanges, value: object, *, with_cache: bool
) -> None:
    # Propre à l'US : a datetime, a Decimal, a NaN or an infinity in a document fails the same way
    # in both paths: never kept as a JSON that is not standard (#4166).
    def contribute(
        session: Session, *, project_id: UUID, revision_id: UUID, at: datetime
    ) -> Mapping[IndicatorKind, Document]:
        del session, project_id, revision_id, at
        return {"portfolio_workload": {"x": value}}

    revisions = of_the_day(fabrics)
    contributing = Contributing(contribute, KINDS)
    with (
        fabrics.stage.database.transaction() as session,
        pytest.raises(UnserializableContributionError),
    ):
        day_documents_of(session, revisions, AT, contributing, cache if with_cache else None)
    assert cache.writes == []


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_that_lacks_a_kind_is_a_miss_computed_and_written_whole(
    fabrics: Portfolio, cache: Exchanges
) -> None:
    # Propre à l'US : an entry written by a computation that gave fewer kinds — the list of US-2690
    # before this lot, its ``project`` alone (#4193) — is not served as complete: the project is
    # computed again and its entry written with every kind, ``null`` for one it does not give.
    revisions = of_the_day(fabrics)
    offer = fabrics.offer.project_id
    with fabrics.stage.database.transaction() as session:
        key = contribution_key(session, offer, revisions[offer], AT, stamps_of(session))
    cache.client.set(PREFIX + key, '{"estimate": {"total": "1"}}', ex=TTL)
    counted = Counted()
    with fabrics.stage.database.transaction() as session:
        kinds: tuple[IndicatorKind, ...] = ("portfolio_workload", "portfolio_milestones")
        found = day_documents_of(session, revisions, AT, Contributing(counted, kinds), cache)
    assert (offer, revisions[offer]) in counted.calls
    assert set(found[offer]) == {"portfolio_workload"}
    entry = json.loads(cache.read(key) or "null")
    assert entry["portfolio_milestones"] is None
    assert entry["portfolio_workload"] == found[offer]["portfolio_workload"]


def test_no_project_asks_no_exchange(fabrics: Portfolio, cache: Exchanges) -> None:
    # Covers no requirement: a scope without a project of the day computes nothing and asks Redis
    # nothing.
    counted = Counted()
    with fabrics.stage.database.transaction() as session:
        assert day_documents_of(session, {}, AT, Contributing(counted, KINDS), cache) == {}
    assert (counted.calls, cache.lookups, cache.writes) == ([], 0, [])


@pytest.mark.parametrize(
    ("kept", "read"),
    [
        (None, None),
        ("not JSON", None),
        ('["portfolio_workload"]', None),
        ('{"portfolio_workload": []}', None),
        ("{}", None),
        ('{"project": {"rows": []}}', None),
        ('{"portfolio_workload": null}', {}),
        ('{"portfolio_workload": {"rows": []}}', {"portfolio_workload": {"rows": []}}),
        (
            '{"portfolio_workload": {"rows": []}, "estimate": null}',
            {"portfolio_workload": {"rows": []}},
        ),
    ],
)
def test_an_entry_of_a_contribution_is_read_when_it_answers_every_kind(
    kept: str | None, read: dict[str, object] | None
) -> None:
    # Covers no requirement: the form of an entry, without Redis (#4193). An entry that answers
    # every kind asked, a document or ``null``, is served without its ``null``; one that lacks a
    # kind is partial, and a miss, as anything that is not an object of documents.
    assert read_contribution(kept, KINDS) == read
