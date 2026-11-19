# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contribution of a project to the portfolio on the current day, kept in the cache (EP-11).

The portfolio sums documents a project gives by revision; on the current day, they are computed once
and kept by the cache of the indicators of EP-10, under the fingerprint of the project (EP-11, "La
contribution d'un projet"). The entry of a project is one JSON object, a document by kind, under
the key of the day of the project (``day_key``) followed by ``portfolio``: a scope is a subproject,
``project`` or ``unassigned``, never that word, so the entry of the contribution shares no key with
the entry of a scope. The fingerprint is the one of the indicators of the day — the counters of the
risks join it with EP-08 —: a write that changes it leaves the contribution with the scopes, and an
entry is never served for a revision, a reference or a day that is no longer the project's.

The entries of every project asked are read in one exchange; those not kept, or unreadable, are
computed by the computation the caller gives (``Contribute``, that of ``core/portfolio``) and
written together, none other. A Redis that does not answer is a miss for all: each project is
computed, nothing is written. Two readings of an entry absent compute it both and write the same: no
lock, as for the scopes. What the entry holds is what the computation gives: a change of its form
is left behind by the validity period of an entry, or by ``FORM`` of the key.
"""

import json
from typing import TYPE_CHECKING, cast

from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.caching import day_key
from waterfall.core.indicators.computing import Basis
from waterfall.core.indicators.shaping import Context
from waterfall.core.projects.interface import project_facts, subproject_ids
from waterfall.platform.cache import Unavailable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.core.indicators.interface.portfolio import Contribute
    from waterfall.platform.cache import IndicatorsCache

# What follows the key of the day of a project for the entry of its contribution.
CONTRIBUTION = "portfolio"
# The status the key is read with: the key reads only the instant of the context, never its status.
DRAFT = "draft"

type Contribution = dict[IndicatorKind, Document]


class UnserializableContributionError(TypeError):
    """A computation of the contribution gave a document that is not JSON: never kept, never served.

    Raised with a cache or without, so that a fault of the computation shows at the first reading.
    """


def contribution_key(session: Session, project_id: UUID, revision_id: UUID, at: datetime) -> str:
    """Give the key of the contribution of a project on the day of ``at``, on one of its revisions.

    The fingerprint of the day of the indicators (``day_key``), on that revision and the reference
    of the project, followed by ``portfolio``. The facts of the project are read once, for the
    reference and for the fingerprint.
    """
    facts = project_facts(session, project_id)
    basis = Basis(project_id, revision_id, facts.reference_revision_id)
    context = Context(revision_id, DRAFT, at, PROJECT, is_stored=False)
    key = day_key(session, basis, context, subproject_ids(session, project_id), facts)
    return f"{key}:{CONTRIBUTION}"


def read_contribution(kept: str | None) -> Contribution | None:
    """Give the documents of an entry of a contribution, or none for one absent or unreadable.

    An entry is unreadable when it is not JSON, is not an object, or holds a value that is not an
    object (a document): it is a miss, and is written again. An object without a kind is a
    contribution that gives nothing, and is served as it is.
    """
    if kept is None:
        return None
    try:
        held: object = json.loads(kept)
    except ValueError:
        return None
    if not isinstance(held, dict):
        return None
    documents = cast("dict[str, object]", held)
    if any(not isinstance(document, dict) for document in documents.values()):
        return None
    return cast("Contribution", documents)


def _computed(
    session: Session, revisions: Mapping[UUID, UUID], at: datetime, contribute: Contribute
) -> dict[UUID, tuple[Contribution, str]]:
    """Compute the contribution of each project on its revision, in the order given, with its JSON.

    A document that is not JSON (a ``Decimal``, a ``datetime``) is refused here, whatever the cache.
    """
    computed: dict[UUID, tuple[Contribution, str]] = {}
    for project_id, revision in revisions.items():
        documents = dict(contribute(session, project_id=project_id, revision_id=revision, at=at))
        try:
            text = json.dumps(documents, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            msg = f"the contribution of project {project_id} is not JSON: {error}"
            raise UnserializableContributionError(msg) from error
        computed[project_id] = (documents, text)
    return computed


def _documents(computed: Mapping[UUID, tuple[Contribution, str]]) -> dict[UUID, Contribution]:
    """Keep the documents of what ``_computed`` gave, without their JSON."""
    return {project_id: documents for project_id, (documents, _) in computed.items()}


def contributions(
    session: Session,
    revisions: Mapping[UUID, UUID],
    at: datetime,
    contribute: Contribute,
    cache: IndicatorsCache | None,
) -> dict[UUID, Contribution]:
    """Give the contribution of each project on its revision, from its entry or computed.

    Without a cache, every project is computed. With one, the entries are read in one exchange, and
    those missing computed then written, in one pass of writes.
    """
    if cache is None or not revisions:
        return _documents(_computed(session, revisions, at, contribute))
    keys = {
        project_id: contribution_key(session, project_id, revision, at)
        for project_id, revision in revisions.items()
    }
    found = cache.lookup_many(list(keys.values()))
    if isinstance(found, Unavailable):
        # Redis fails: the write would fail too.
        return _documents(_computed(session, revisions, at, contribute))
    held: dict[UUID, Contribution] = {}
    for project_id, kept in zip(keys, found, strict=True):
        entry = read_contribution(kept)
        if entry is not None:
            held[project_id] = entry
    missing = {each: revision for each, revision in revisions.items() if each not in held}
    computed = _computed(session, missing, at, contribute)
    if computed:
        cache.write_many({keys[project_id]: text for project_id, (_, text) in computed.items()})
    held.update(_documents(computed))
    return {project_id: held[project_id] for project_id in revisions}
