# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the current day, kept in the cache under a versioned key (WF-DAT-0130-A).

The key of the day of a project is the fingerprint of what its indicators of the day depend on,
read at each reading by the interfaces of the modules (EP-10, "Le cache"): the state, the current
revision, the reference and the counter of the project; the revision computed and its reference;
the counter and the instant of the dates of its main structure, and the counter of every structure
of the revision; the number of the risks of the project and the sum of their counters (a review,
an occurrence, a change of the provision of a risk, US-2630/L1); the number of its nodes, of its
tasks, of its links and of its lines, and the last instant one was written; the number of the
imports of the actual costs of the project and the last, the number of its lines of cost, the
last one written and the sum of their counters; its subprojects; the day, in the time zone of the
installation. A write any entry depends on changes the key — an entry, a marking, an abandonment,
a designation, an import, an exclusion or a reinstatement of a line of cost, a subproject created,
the next day —: an entry is never served for a key that is no longer the project's, and no write
calls the cache. The counter of a line of cost advances under the lock of the project at each of
its writes, so that two exclusions that overlap each change the sum (#3629). A change of the
thresholds escapes it: the zones are classified at each reading.

The entry is one document by scope and by key (decision of the author of 2026-11-16, #3628; the
measure of US-2420): for a scope — the project, a subproject, the lines of the project alone —, its
indicators and its three curves, the zones null, under the key of the project followed by the scope.
A reading computes and writes only the scopes it asks that are not kept, in one pass: one scope for
the indicators and the curves, every scope for the evolution of the indices without a scope. The
fingerprint is the project's, shared by its scopes: a write that changes it leaves every scope of
the project at once. The key is read before the computation: a write that comes between them
changes the key, and what was computed is kept under a key no reading asks for any longer. Two
readings of an entry absent compute it both and write the same: no lock. A Redis that does not
answer is a miss, and the computation is answered (``IndicatorsCache``); nothing is written.
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
from waterfall.core.revisions.interface import aimed_structure, structure_counters, structure_facts
from waterfall.core.risks.interface import risks_stamp
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
FORM = "3"
# The length of the fingerprint kept in the key: 128 bits of the SHA-256 of the canonical text.
FINGERPRINT_LENGTH = 32

# What an entry holds for a scope: a document by kind (``IndicatorKind``), the indicators of the
# project under ``project``.
type ScopeEntry = dict[str, Document]
# The kinds an entry of a scope holds, each a document: an entry that lacks one is a miss.
KINDS = ("project", "cost_curve", "cost_curve_payment_delays", "earned_value_curves")


def _text(value: object) -> str:
    """Write a value of the key: ``-`` for none, an instant or a day in ISO 8601."""
    if value is None:
        return "-"
    isoformat = getattr(value, "isoformat", None)
    return str(isoformat()) if callable(isoformat) else str(value)


def day_key(session: Session, basis: Basis, context: Context, subprojects: Sequence[UUID]) -> str:
    """Give the key of the day of a project: its identifier, then the fingerprint.

    ``subprojects`` are those of the project, as its scopes are drawn. The entry of a scope is kept
    under this key followed by the scope (``scope_key``).
    """
    project_id, revision_id = basis.project_id, basis.revision_id
    facts = project_facts(session, project_id)
    main = aimed_structure(session, project_id, revision_id, None)
    structure = None if main is None else structure_facts(session, project_id, main, lock=False)
    content = revision_content_stamp(session, project_id, revision_id)
    lines = lines_stamp(session, project_id, revision_id)
    costs = costs_stamp(session, project_id)
    counters = structure_counters(session, project_id, revision_id)
    risks = risks_stamp(session, project_id)
    # The instants are those of the start of each act, not of its commit: a write that started
    # first and commits last leaves their maximum where it was. The key holds by the counters
    # that grow in the transaction of each write, in the order of the commits: every write of the
    # tree, a line and its remaining to commit included, advances the counter of its structure
    # under its lock (``structure_rescheduled``), whatever the structure — the main one, a
    # differential, the own estimate of a risk —, every one of which the key reads;
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
        ("structures", tuple(f"{each}:{counter}" for each, counter in counters)),
        ("risks", (risks.count, risks.versions)),
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


def scope_key(key: str, scope: CostScope) -> str:
    """Give the key of the entry of a scope: the key of the day of its project, then the scope."""
    return f"{key}:{scope}"


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


def _read_entry(kept: str | None) -> ScopeEntry | None:
    """Give the documents of the entry of a scope, or none for an entry absent or unreadable.

    An entry is unreadable when it is not JSON, is not an object, or lacks a kind or holds one that
    is not a document: it is a miss, and is written again.
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
    if any(not isinstance(documents.get(kind), dict) for kind in KINDS):
        return None
    return cast("ScopeEntry", documents)


def cached_scopes(
    session: Session,
    basis: Basis,
    context: Context,
    scopes: Collection[CostScope],
    cache: IndicatorsCache,
) -> dict[CostScope, ScopeEntry]:
    """Give the documents of the day of the scopes asked, by kind, from their entries for the key.

    The entries of the scopes asked are read in one exchange; those not kept are computed together,
    in one pass, and written, none other. When Redis does not answer, the scopes asked are computed
    and nothing is written. A scope that is not one of the key — a subproject the reading of the
    scopes did not see — is computed and not written: the key does not cover it.
    """
    project_id = basis.project_id
    subprojects = subproject_ids(session, project_id)
    key = day_key(session, basis, context, subprojects)
    asked: list[CostScope] = list(dict.fromkeys(scopes))
    found = cache.lookup_many([scope_key(key, scope) for scope in asked])
    if isinstance(found, Unavailable):
        # Redis fails: the write would fail too.
        computed = day_entry(session, basis, context, asked)
        return {scope: computed[str(scope)] for scope in asked}
    held: dict[CostScope, ScopeEntry] = {}
    for scope, kept in zip(asked, found, strict=True):
        entry = _read_entry(kept)
        if entry is not None:
            held[scope] = entry
    missing: list[CostScope] = [scope for scope in asked if scope not in held]
    if missing:
        computed = day_entry(session, basis, context, missing)
        drawn: set[CostScope] = {PROJECT, UNASSIGNED, *subprojects}
        cache.write_many(
            {
                scope_key(key, scope): json.dumps(computed[str(scope)], separators=(",", ":"))
                for scope in missing
                if scope in drawn
            }
        )
        held.update({scope: computed[str(scope)] for scope in missing})
    return {scope: held[scope] for scope in asked}
