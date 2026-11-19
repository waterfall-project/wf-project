# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the list and of the value of the portfolio share (US-2690/L2).

A view read by the manager of the scene, through the service; a document a marking kept, changed
around the service as its superuser could — the table refuses it to the service, and the marking of
an exact figure would ask for a project of its own —, so that a test of the list reads the figure it
needs from the revision it names; the fabrics and their marked revisions.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from portfolio_support import OFFER, REVIEW, Portfolio
from sqlalchemy import select, text, update

from waterfall.core.indicators.tables import RevisionIndicator

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from projects_support import Person
    from sqlalchemy import Engine
    from support import ContractClient

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PORTFOLIO = "/api/v1/portfolio"
# The default period of a view read on 3 June 2026, the date of the witness.
READ = "as_of=2026-06-03"
# Every project of the fabrics counted by a view, and the states no view counts, asked all the same.
COUNTED = "in_progress,pricing,completed"
EVERY = "in_progress,pricing,completed,created,lost,abandoned"


def read(api: ContractClient, who: Person, view: str, query: str = "") -> Any:
    """Read a view of the portfolio as an account does, whatever the answer."""
    return api.get(f"{PORTFOLIO}/{view}?{query}", headers=who.headers)


def served(api: ContractClient, who: Person, view: str, query: str = "") -> Any:
    """Read a view of the portfolio that answers; give its body."""
    answer = read(api, who, view, query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def revision_of(fabrics: Portfolio, name: str) -> UUID:
    """Give the revision a project of the fabrics last marked: its review, or its offer."""
    marked = {
        "running": fabrics.in_progress.marked[REVIEW],
        "completed": fabrics.completed.marked[REVIEW],
        "offer": fabrics.offer.marked[OFFER],
        "lost": fabrics.lost.marked[OFFER],
    }
    return marked[name][0]


def kept_changed(
    owner: Engine, revision_id: UUID, kind: str, change: Callable[[dict[str, Any]], dict[str, Any]]
) -> None:
    """Change the document of a kind a marked revision kept, as a superuser around the service.

    The trigger that makes a marked revision immutable is set aside for the statement: it is a test
    of what a list reads, not of what a marking keeps.
    """
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        document = connection.scalar(
            select(RevisionIndicator.document).where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind == kind,
                RevisionIndicator.scope == "project",
            )
        )
        assert document is not None
        connection.execute(
            update(RevisionIndicator)
            .where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind == kind,
                RevisionIndicator.scope == "project",
            )
            .values(document=change(document))
        )


def with_index(name: str, value: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Give the change that sets an index of a document ``project`` to a value computed."""
    figure = {"is_computable": True, "value": value, "reason": None}
    return lambda document: {**document, name: {"value": figure, "zone": None}}


def example(key: str) -> dict[str, Any]:
    """Give the fixture that cites a numeric example of the document, as the harness loads it.

    The service replays what the tests of ``tests/examples`` replay without a database: the same
    inputs, the same expected value, read from the same fixture.
    """
    for path in sorted(FIXTURES.rglob("*.json")):
        data = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
        if key in data.get("examples", []):
            return data
    message = f"no fixture cites {key}: write one under fixtures/"
    raise LookupError(message)
