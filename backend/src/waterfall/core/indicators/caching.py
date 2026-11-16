# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the current day, kept in the cache under a versioned key (WF-DAT-0130-A).

The key of the entry of a project is the fingerprint of what its indicators of the day depend on,
read at each reading by the interfaces of the modules (EP-10, "Le cache"): the state, the current
revision, the reference and the counter of the project; the revision computed and its reference;
the counter and the instant of the dates of its main structure; the number of its nodes, of its
tasks, of its links and of its lines, and the last instant one was written; the number of the
imports of the actual costs of the project and the last, the number of its lines of cost, the
last one written and the sum of their counters; its subprojects; the day, in the time zone of the
installation. A write any entry depends on changes the key — an entry, a marking, an abandonment,
a designation, an import, an exclusion or a reinstatement of a line of cost, a subproject created,
the next day —: an entry is never served for a key that is no longer the project's, and no write
calls the cache. The counter of a line of cost advances under the lock of the project at each of
its writes, so that two exclusions that overlap each change the sum (#3629). A change of the
thresholds escapes it: the zones are classified at each reading.

The entry is one document by project and by key: for each scope — the project, each subproject,
the lines of the project alone —, the indicators and the three curves, computed in one pass, the
zones null. The key is read before the computation: a write that comes between them changes the
key, and what was computed is kept under a key no reading asks for any longer. Two readings of an
entry absent compute it both and write the same: no lock. A Redis that does not answer is a miss,
and the computation is answered (``IndicatorsCache``); the scopes asked alone are computed, for
no entry is written.
"""

import hashlib
import json
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from waterfall.core.costs.interface import PROJECT, UNASSIGNED, costs_stamp
from waterfall.core.estimate.interface import lines_stamp
from waterfall.core.indicators.computing import LinesRead, amounts_from
from waterfall.core.indicators.curving import (
    cost_curve_document,
    curves_of_scope,
    earned_value_curves_document,
    read_curve_sources,
)
from waterfall.core.indicators.formulas import indicators_of
from waterfall.core.indicators.shaping import indicators_document
from waterfall.core.planning.interface import revision_content_stamp
from waterfall.core.projects.interface import (
    current_day,
    project_facts,
    stored_lock_version,
    subproject_ids,
)
from waterfall.core.revisions.interface import aimed_structure, structure_facts
from waterfall.platform.cache import Unavailable

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.computing import Basis
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.shaping import Context
    from waterfall.platform.cache import IndicatorsCache

# The form of an entry: a change of what an entry holds changes it, and the entries of the form
# before are no longer read, without waiting for their validity to end.
FORM = "1"
# The length of the fingerprint kept in the key: 128 bits of the SHA-256 of the canonical text.
FINGERPRINT_LENGTH = 32

# What an entry holds for a scope: a document by kind (``IndicatorKind``), the indicators of the
# project under ``project``.
type ScopeEntry = dict[str, Document]


def _text(value: object) -> str:
    """Write a value of the key: ``-`` for none, an instant or a day in ISO 8601."""
    if value is None:
        return "-"
    isoformat = getattr(value, "isoformat", None)
    return str(isoformat()) if callable(isoformat) else str(value)


def day_key(session: Session, basis: Basis, context: Context, subprojects: Sequence[UUID]) -> str:
    """Give the key of the entry of the day of a project: its identifier, then the fingerprint.

    ``subprojects`` are those of the project, as the entry draws them.
    """
    project_id, revision_id = basis.project_id, basis.revision_id
    facts = project_facts(session, project_id)
    main = aimed_structure(session, project_id, revision_id, None)
    structure = None if main is None else structure_facts(session, project_id, main, lock=False)
    content = revision_content_stamp(session, project_id, revision_id)
    lines = lines_stamp(session, project_id, revision_id)
    costs = costs_stamp(session, project_id)
    # The instants are those of the start of each act, not of its commit: a write that started
    # first and commits last leaves their maximum where it was. The key holds by the counters
    # that grow in the transaction of each write, in the order of the commits: every write of the
    # tree, a line and its remaining to commit included, advances the counter of its structure
    # under its lock (``structure_rescheduled``) — the main one is the only structure until EP-08 —;
    # an import adds its entry; a change of state, a marking, an abandonment, a designation
    # advance the counter of the project; an exclusion, a reinstatement or an imputation advances
    # the counter of the lines of cost, whose sum the key reads (``costs_stamp``); a line an import
    # finds unchanged leaves its counter, and the number of the imports moves the key.
    parts: list[tuple[str, tuple[object, ...]]] = [
        ("form", (FORM,)),
        ("project", (facts.state, facts.current_revision_id, facts.reference_revision_id)),
        ("counter", (stored_lock_version(session, project_id),)),
        ("revision", (revision_id, basis.reference_id)),
        (
            "structure",
            (None, None) if structure is None else (structure.lock_version, structure.scheduled_at),
        ),
        ("content", (content.nodes, content.tasks, content.links, content.updated_at)),
        ("lines", (lines.count, lines.updated_at)),
        (
            "costs",
            (costs.imports, costs.imported_at, costs.lines, costs.updated_at, costs.versions),
        ),
        ("subprojects", (len(subprojects), *sorted(str(each) for each in subprojects))),
        ("day", (current_day(context.computed_at),)),
    ]
    canonical = "\n".join(f"{name}={','.join(_text(v) for v in values)}" for name, values in parts)
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()[:FINGERPRINT_LENGTH]
    return f"{project_id}:{fingerprint}"


def day_entry(
    session: Session, basis: Basis, context: Context, scopes: Collection[CostScope]
) -> dict[str, ScopeEntry]:
    """Compute the indicators and the three curves of the scopes given, in one pass, zones null.

    Each document bears the context given, its own scope; the entry is by the scope as the
    contract writes it.
    """
    project_id = basis.project_id
    day = current_day(context.computed_at)
    sources = read_curve_sources(session, basis)
    read = LinesRead(sources.reference, sources.lines, sources.remaining, sources.completed)
    amounts = amounts_from(session, project_id, read, day, scopes)
    entry: dict[str, ScopeEntry] = {}
    for scope in scopes:
        here = replace(context, scope=scope)
        curves = curves_of_scope(session, project_id, sources, day, scope)
        entry[str(scope)] = {
            "project": indicators_document(indicators_of(amounts[scope], None), here),
            "cost_curve": cost_curve_document(curves, here, payment_delays=False),
            "cost_curve_payment_delays": cost_curve_document(curves, here, payment_delays=True),
            "earned_value_curves": earned_value_curves_document(curves, here),
        }
    return entry


def _read_entry(kept: str | None) -> dict[str, ScopeEntry] | None:
    """Give the scopes of an entry kept, or none for an entry absent or that cannot be read.

    An entry is unreadable when it is not JSON, holds no scopes, or a scope that lacks the
    indicators of the project: it is a miss, and is written again.
    """
    if kept is None:
        return None
    try:
        held: object = json.loads(kept)
    except ValueError:
        return None
    if not isinstance(held, dict):
        return None
    scopes = cast("dict[str, object]", held).get("scopes")
    if not isinstance(scopes, dict):
        return None
    for each in cast("dict[str, object]", scopes).values():
        if not isinstance(each, dict) or "project" not in each:
            return None
    return cast("dict[str, ScopeEntry]", scopes)


def cached_scopes(
    session: Session,
    basis: Basis,
    context: Context,
    scopes: Collection[CostScope],
    cache: IndicatorsCache,
) -> dict[CostScope, ScopeEntry]:
    """Give the documents of the day of the scopes asked, by kind, from the entry of the key.

    Served by the entry when it is kept; otherwise every scope of the project is computed, the
    entry written, and the scopes asked taken from it; when Redis does not answer, the scopes asked
    alone are computed. A scope the entry lacks — a subproject created between the reading of the
    key and the refusal of the scope — is computed alone.
    """
    subprojects = subproject_ids(session, basis.project_id)
    key = day_key(session, basis, context, subprojects)
    found = cache.lookup(key)
    if isinstance(found, Unavailable):
        # Redis fails: the write would fail too, and the other scopes would be computed for nothing.
        entry = day_entry(session, basis, context, scopes)
        return {scope: entry[str(scope)] for scope in scopes}
    entry = _read_entry(found)
    if entry is None:
        drawn: list[CostScope] = [PROJECT, *subprojects, UNASSIGNED]
        entry = day_entry(session, basis, context, drawn)
        cache.write(key, json.dumps({"scopes": entry}, separators=(",", ":")))
    missing: list[CostScope] = [scope for scope in scopes if str(scope) not in entry]
    if missing:
        entry = {**entry, **day_entry(session, basis, context, missing)}
    return {scope: entry[str(scope)] for scope in scopes}
