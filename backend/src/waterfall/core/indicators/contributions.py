# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contribution of a project to the portfolio on the current day, kept in the cache (EP-11).

The portfolio sums documents a project gives by revision; on the current day, they are computed once
and kept by the cache of the indicators of EP-10, under the fingerprint of the project (EP-11, "La
contribution d'un projet"). The entry of a project is one JSON object, a document by kind, under
the key of the day of the project (``day_key``) followed by ``portfolio`` and a fingerprint of its
own: a scope is a subproject, ``project`` or ``unassigned``, never that word, so the entry of the
contribution shares no key with the entry of a scope. The fingerprint of the day is the one of the
indicators, the counters of the risks in it (US-2630/L1): a write that changes it leaves the
contribution with the scopes, and an entry is never served for a revision, a reference or a day
that is no longer the project's.

The entries of every project asked are read in one exchange; those not kept, or unreadable, are
computed by the computation the caller gives (``Contributing``, that of ``core/portfolio``) and
written together, none other. A Redis that does not answer is a miss for all: each project is
computed, nothing is written. Two readings of an entry absent compute it both and write the same: no
lock, as for the scopes.

The key covers, beyond the fingerprint of the day, what the contribution reads and the indicators of
the day do not (#4158, decision of the author of 2026-11-19; WF-DAT-0130-A): the probability of
winning of the project, which weighs an offer, and the stamp of the roles and of the calendars of
the platform (``roles_stamp``) — the calendar of a role and its hours, which spread the workload —,
read once for all the projects of a reading. The part of the risks (US-2680/L3) needs nothing more:
what it reads is in the fingerprint of the day already — the number of the risks and the sum of
their counters, which a declaration, a deletion, a review, an occurrence, a change of the identity
or of the provision of a risk, or of its own estimate, moves; the counters of the structures of the
revision, own estimates included, the lines and the reference, from which its severity, the
re-estimated amount of an occurred one, its share and the base are read. ``FORM`` of the key
changes with what an entry holds, so that an entry of a form before is never read again.

The key covers the stamp of the hourly rates of the reference too (``rates_stamp``, #4283, US-2720),
read once for all the projects: on the current day, the structure of the costs of a revision not
marked names the rates its labour lacks, and the document ``estimate`` of an offer is not computed
without them (WF-DEV-0010), so a rate set leaves the entry (WF-DAT-0130-A). The rates a revision
keeps need nothing more: they are written at its opening, which moves its counters, and at its
marking.

The key does not cover the label of a nature of cost, which the structure of the costs of a
revision not marked reads on the reference as it stands: a nature renamed is served under its former
label until the entry expires, within the validity of the cache (``IndicatorsCache``).

An entry answers every kind the caller names (``Contributing.kinds``), a document or ``null`` for a
kind the state of the project does not call for: an entry that lacks one of them is partial —
written by a computation that gave fewer kinds, or by a form before — and is a miss, computed and
written again, never served as complete (#4193). A document that is not JSON — a ``Decimal``, a
``datetime``, a ``NaN`` or an infinity — is refused (``UnserializableContributionError``, #4166).
"""

import hashlib
import json
from typing import TYPE_CHECKING, cast

from waterfall.core.cost_settings.interface import rates_stamp
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.caching import day_key
from waterfall.core.indicators.computing import Basis
from waterfall.core.indicators.shaping import Context
from waterfall.core.projects.interface import project_facts, subproject_ids
from waterfall.core.resource_settings.interface import roles_stamp
from waterfall.platform.cache import Unavailable

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import RatesStamp
    from waterfall.core.indicators.interface.documents import Document, IndicatorKind
    from waterfall.core.indicators.interface.portfolio import Contributing
    from waterfall.core.resource_settings.interface import RolesStamp
    from waterfall.platform.cache import IndicatorsCache

# What follows the key of the day of a project for the entry of its contribution.
CONTRIBUTION = "portfolio"
# The status the key is read with: the key reads only the instant of the context, never its status.
DRAFT = "draft"
# The form of an entry of a contribution: a change of what an entry holds changes it. "2" since
# US-2680/L2: every kind named, ``null`` for one the project does not give (#4193); "3" since
# US-2680/L3, which adds ``portfolio_risks``; "4" since US-2720, whose structure of the costs names
# the rates missing.
FORM = "4"
# The length of what the key adds to the fingerprint of the day: 128 bits of a SHA-256.
FINGERPRINT_LENGTH = 32

type Contribution = dict[IndicatorKind, Document]
# What the key of every contribution of a reading reads once: the stamp of the roles and of the
# calendars, and that of the hourly rates.
type Stamps = tuple[RolesStamp, RatesStamp]


class UnserializableContributionError(TypeError):
    """A computation of the contribution gave a document that is not JSON: never kept, never served.

    Raised with a cache or without, so that a fault of the computation shows at the first reading.
    """


def contribution_key(
    session: Session,
    project_id: UUID,
    revision_id: UUID,
    at: datetime,
    stamps: Stamps,
) -> str:
    """Give the key of the contribution of a project on the day of ``at``, on one of its revisions.

    The fingerprint of the day of the indicators (``day_key``), on that revision and the reference
    of the project, followed by ``portfolio`` and the fingerprint of what the contribution reads
    besides: the form of an entry, the probability of winning of the project, ``stamps`` — the stamp
    of the roles and of the calendars, and that of the hourly rates, read once by the caller for all
    the projects (``stamps_of``). The facts of the project are read once, for the reference, the
    probability and the fingerprint. The label of a nature of cost is not covered: a nature renamed
    is served under its former label until the entry expires.
    """
    roles, rates = stamps
    facts = project_facts(session, project_id)
    basis = Basis(project_id, revision_id, facts.reference_revision_id)
    context = Context(revision_id, DRAFT, at, PROJECT, is_stored=False)
    key = day_key(session, basis, context, subproject_ids(session, project_id), facts)
    besides = (
        f"form={FORM}\n"
        f"win_probability={facts.win_probability}\n"
        f"roles={roles.count},{roles.versions},{_instant(roles.updated_at)}\n"
        f"calendars={roles.calendar_count},{roles.calendar_versions},"
        f"{_instant(roles.calendar_updated_at)}\n"
        f"rates={rates.count},{rates.versions},{_instant(rates.updated_at)}"
    )
    fingerprint = hashlib.sha256(besides.encode()).hexdigest()[:FINGERPRINT_LENGTH]
    return f"{key}:{CONTRIBUTION}:{fingerprint}"


def stamps_of(session: Session) -> Stamps:
    """Read what the key of every contribution of a reading reads once: two statements."""
    return roles_stamp(session), rates_stamp(session)


def _instant(written: datetime | None) -> str:
    """Write the last instant a row was written, ``-`` for none."""
    return "-" if written is None else written.isoformat()


def read_contribution(kept: str | None, kinds: Collection[IndicatorKind]) -> Contribution | None:
    """Give the documents of an entry of a contribution; none for one absent, unreadable or partial.

    An entry is unreadable when it is not JSON, is not an object, or holds a value that is neither
    an object (a document) nor ``null``; partial when one of ``kinds`` is not a key of it. Either is
    a miss, and is written again. The kinds ``null`` are left out of what is served: an object of
    every kind, all ``null``, is a contribution that gives nothing, served as it is.
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
    if any(each is not None and not isinstance(each, dict) for each in documents.values()):
        return None
    if any(kind not in documents for kind in kinds):
        return None
    return cast(
        "Contribution", {kind: each for kind, each in documents.items() if each is not None}
    )


def _computed(
    session: Session, revisions: Mapping[UUID, UUID], at: datetime, contributing: Contributing
) -> dict[UUID, tuple[Contribution, str]]:
    """Compute the contribution of each project on its revision, in the order given, with its entry.

    The entry names every kind of ``contributing``, ``null`` for one not given. A document that is
    not JSON (a ``Decimal``, a ``datetime``, a ``NaN``) is refused here, whatever the cache. The
    documents given are read back from the entry, so that a contribution computed and one read from
    the cache are alike, to their types (a tuple a list, for one).
    """
    computed: dict[UUID, tuple[Contribution, str]] = {}
    for project_id, revision in revisions.items():
        documents = dict(
            contributing.compute(session, project_id=project_id, revision_id=revision, at=at)
        )
        entry: dict[str, Document | None] = {**dict.fromkeys(contributing.kinds), **documents}
        try:
            text = json.dumps(entry, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as error:
            msg = f"the contribution of project {project_id} is not JSON: {error}"
            raise UnserializableContributionError(msg) from error
        # Served as the cache would serve it, after a round trip through JSON: the same types.
        computed[project_id] = (_served(text), text)
    return computed


def _served(text: str) -> Contribution:
    """Give the documents of an entry just written, its kinds ``null`` left out."""
    held = cast("dict[IndicatorKind, Document | None]", json.loads(text))
    return {kind: each for kind, each in held.items() if each is not None}


def _documents(computed: Mapping[UUID, tuple[Contribution, str]]) -> dict[UUID, Contribution]:
    """Keep the documents of what ``_computed`` gave, without their entry."""
    return {project_id: documents for project_id, (documents, _) in computed.items()}


def contributions(
    session: Session,
    revisions: Mapping[UUID, UUID],
    at: datetime,
    contributing: Contributing,
    cache: IndicatorsCache | None,
) -> dict[UUID, Contribution]:
    """Give the contribution of each project on its revision, from its entry or computed.

    Without a cache, every project is computed. With one, the stamps of the roles and of the rates
    are read once, the entries in one exchange, and those missing — absent, unreadable or partial —
    computed then written, in one pass of writes.
    """
    if cache is None or not revisions:
        return _documents(_computed(session, revisions, at, contributing))
    stamps = stamps_of(session)
    keys = {
        project_id: contribution_key(session, project_id, revision, at, stamps)
        for project_id, revision in revisions.items()
    }
    found = cache.lookup_many(list(keys.values()))
    if isinstance(found, Unavailable):
        # Redis fails: the write would fail too.
        return _documents(_computed(session, revisions, at, contributing))
    held: dict[UUID, Contribution] = {}
    for project_id, kept in zip(keys, found, strict=True):
        entry = read_contribution(kept, contributing.kinds)
        if entry is not None:
            held[project_id] = entry
    missing = {each: revision for each, revision in revisions.items() if each not in held}
    computed = _computed(session, missing, at, contributing)
    if computed:
        cache.write_many({keys[project_id]: text for project_id, (_, text) in computed.items()})
    held.update(_documents(computed))
    return {project_id: held[project_id] for project_id in revisions}
