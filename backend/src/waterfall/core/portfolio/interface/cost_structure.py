# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of the costs of the portfolio (``getPortfolioCostStructure``; US-2720).

The documents ``portfolio_cost_structure``, weighted: the reference budget by cost type, provisions
left out, the remaining to commit by cost type, provisions included, their shares summing to one,
and the labour grouped by the current node of its role (WF-PTF-0080).

- **Who contributes.** The projects In progress, those Completed in the period — the default one
  included —, and the offers In pricing when asked, each by the revision the scope retains for it
  (``resolve_scope``); a project In progress or Completed for all it holds, an offer for its
  estimate weighted by its probability of winning (WF-PTF-0020, M-07). A project that kept no
  document — a marking before EP-11 — or an offer without a probability adds nothing.
- **The sums.** Each amount of a project is weighted and rounded once, to the cent, a half away from
  nought (``sum_by_nature``), and the portfolio sums those parts, never rounding a sum again; only
  the shares are rounded, to four decimals, the largest carrying the remainder (``shares_of``). The
  document has already left the provision lines out of the budget and kept them in the remaining:
  a provision line is told by its category, by ``core/estimate`` alone (EP-08).
- **The labour by node** is the labour of the budget, by role, grouped by the node the role is
  attached to **now**, whatever the date read (WF-REF-0070): summed by node within a project, then
  weighted once. ``org_node_id`` restricts it to the roles of the node and of its descendants; the
  breakdowns by cost type are not restricted (the parameter ``PortfolioOrgNode``).
- **A rate missing** (#4283, decision of the author of 2026-11-20). On the current day, a document
  whose labour lines lack an hourly rate names the rates instead of an amount: its part enters no
  sum, as an estimate not computed enters none in the list (US-2690/L2). The key it falls under is
  not computed — its share ``hourly_rate_missing``, ``params.missing_rates`` naming the categories
  and the years, its amount the parts computed of the other projects —, and every other share of
  the same breakdown is not computed either, ``hourly_rate_missing`` without ``params``: their total
  is not computed (WF-DEV-0010, as ``getEstimateIndicators`` says it of the shares of a total).
- **The labels**, those of the cost types and of the nodes as they stand when read
  (``AmountByKey.label``); a cost type the reference no longer has keeps the label a document gave.

A past date reads what the revisions marked by then kept (US-2680), no line of an estimate being
read (WF-DAT-0040); the node of a role is the current one at any date.

Declared by US-2670/L1, the socle of EP-11; filled by US-2720.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.cost_settings.interface import category_label_of, cost_type_labels
from waterfall.core.portfolio.aggregation import (
    CostLine,
    shares_of,
    sum_by_key,
    sum_by_nature,
)
from waterfall.core.portfolio.contributing import COST_STRUCTURE
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import PeriodRule, resolve_scope
from waterfall.core.portfolio.shaping import computable, money, scope_document
from waterfall.core.portfolio.states import COMPLETED, IN_PROGRESS, PRICING
from waterfall.core.resource_settings.interface import (
    RoleFilters,
    RoleSort,
    RoleWindow,
    list_roles,
    read_roles,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document, IndicatorKind
    from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading
    from waterfall.core.projects.interface import ProjectState
    from waterfall.core.resource_settings.interface import RoleView

# The states the view counts: the projects In progress, the offers In pricing when asked, those
# Completed in the period.
COUNTED: frozenset[ProjectState] = frozenset({IN_PROGRESS, PRICING, COMPLETED})
KINDS: tuple[IndicatorKind, ...] = (COST_STRUCTURE,)
HOURLY_RATE_MISSING = "hourly_rate_missing"
# Every role there is: the window of the list of the roles, wider than any installation.
EVERY_ROLE = RoleWindow(limit=10**9, offset=0)
EVERY_STATE = frozenset({True, False})
ZERO = Decimal("0.00")

type Entry = Mapping[str, Any]


@dataclass(slots=True)
class Breakdown:
    """The sums of one breakdown of the portfolio, by key: weighted parts, labels, rates missing.

    ``parts`` holds what each project adds, weighted and rounded once; ``lacking`` the keys a
    project could not compute, with the rates missing, by category and year.
    """

    parts: list[dict[str, Decimal]] = field(default_factory=list[dict[str, Decimal]])
    labels: dict[str, str | None] = field(default_factory=dict[str, str | None])
    lacking: dict[str, dict[tuple[str, int], Entry]] = field(
        default_factory=dict[str, dict[tuple[str, int], Entry]]
    )

    def add(self, amounts: Mapping[str, Decimal], weight: Decimal) -> None:
        """Add the amounts of a project, by key, each weighted and rounded once."""
        lines = [CostLine(key, amount) for key, amount in amounts.items()]
        # The document already chose its provision lines (``core/estimate``): every line is kept.
        self.parts.append(sum_by_nature(lines, weight, with_provisions=True))

    def lack(self, key: str, missing: Iterable[Entry]) -> None:
        """Note that a project could not compute a key, for the rates it names."""
        held = self.lacking.setdefault(key, {})
        for each in missing:
            held[each["cost_category_id"], each["year"]] = each

    def keys(self) -> list[str]:
        """Give the keys of the breakdown, those not computed included, by their identifiers."""
        summed = {key for part in self.parts for key in part}
        return sorted(summed | set(self.lacking))

    def entries(self, labels: Mapping[str, str | None]) -> list[Document]:
        """Write the breakdown (``AmountByKey``): each key, its amount and its share."""
        keys = self.keys()
        sums = sum_by_key(self.parts)
        amounts = [sums.get(key, ZERO) for key in keys]
        shares = (
            [self._not_computed(key) for key in keys]
            if self.lacking
            else [computable(each) for each in shares_of(amounts)]
        )
        return [
            {"key": key, "label": labels.get(key), "amount": money(amount), "share": share}
            for key, amount, share in zip(keys, amounts, shares, strict=True)
        ]

    def _not_computed(self, key: str) -> Document:
        """Write the share of a key in a total a rate missing prevents, its own rates named."""
        share: dict[str, Any] = {
            "is_computable": False,
            "value": None,
            "reason": HOURLY_RATE_MISSING,
        }
        missing = self.lacking.get(key)
        if missing:
            rates = sorted(
                missing.values(),
                key=lambda each: (each["label"], each["cost_category_id"], each["year"]),
            )
            share["params"] = {"missing_rates": rates}
        return share


def _amounts(entries: Iterable[Entry], name: str, breakdown: Breakdown) -> dict[str, Decimal]:
    """Read the amounts of a document by key; a key not computed is noted, and adds nothing."""
    found: dict[str, Decimal] = {}
    for entry in entries:
        key = entry[name]
        breakdown.labels.setdefault(key, entry.get("label"))
        if entry["amount"] is None:
            breakdown.lack(key, entry["missing_rates"])
        else:
            found[key] = Decimal(entry["amount"])
    return found


def _roles(
    session: Session, documents: Iterable[Document], node_id: UUID | None
) -> dict[str, RoleView]:
    """Give each role of the labour kept, as it stands now, those under the node asked alone.

    Every role, deactivated ones too: a document keeps the labour of a role deactivated since. A
    role is never deleted.
    """
    identifiers = {
        UUID(entry["resource_role_id"])
        for document in documents
        for entry in document["budget_labour_by_role"]
    }
    roles = read_roles(session, identifiers, may_change=False)
    if node_id is not None:
        filters = RoleFilters(org_node_id=node_id, states=EVERY_STATE)
        sort = RoleSort(category_label_of)
        within = list_roles(session, filters, sort, EVERY_ROLE, may_change=False).roles
        allowed = {each.resource_role_id for each in within}
        roles = [each for each in roles if each.resource_role_id in allowed]
    return {str(each.resource_role_id): each for each in roles}


def _labour(
    document: Document, roles: Mapping[str, RoleView], breakdown: Breakdown
) -> dict[str, Decimal]:
    """Sum the labour of a project by the node of its roles, exactly; a role outside is left out.

    A role whose labour is not computed leaves its node not computed, for the rates it names.
    """
    found: list[dict[str, Decimal]] = []
    for entry in document["budget_labour_by_role"]:
        role = roles.get(entry["resource_role_id"])
        if role is None:
            continue
        node = str(role.org_node_id)
        if entry["amount"] is None:
            breakdown.lack(node, entry["missing_rates"])
        else:
            found.append({node: Decimal(entry["amount"])})
    return sum_by_key(found)


def read_portfolio_cost_structure(
    session: Session, asked: PortfolioAsked, reading: PortfolioReading
) -> Document:
    """Give the structure of the costs of the scope read by ``reading``.

    Refuses a period inverted and an unknown node as every view of the portfolio does (422,
    ``resolve_scope``).
    """
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=PeriodRule())
    documents = documents_of(session, resolved, reading, KINDS)
    weighed = [
        (weight, held[COST_STRUCTURE])
        for project_id, held in documents.items()
        if COST_STRUCTURE in held and (weight := resolved.projects[project_id].weight) is not None
    ]
    budget, remaining, labour = Breakdown(), Breakdown(), Breakdown()
    roles = _roles(session, (document for _, document in weighed), asked.org_node_id)
    for weight, document in weighed:
        budget.add(_amounts(document["budget_by_cost_type"], "cost_type_id", budget), weight)
        remaining.add(
            _amounts(document["remaining_by_cost_type"], "cost_type_id", remaining), weight
        )
        labour.add(_labour(document, roles, labour), weight)
    types = {UUID(key) for key in (*budget.keys(), *remaining.keys())}
    current = {str(key): label for key, label in cost_type_labels(session, types).items()}
    node_labels = {str(each.org_node_id): each.org_node_label for each in roles.values()}
    return {
        "scope": scope_document(resolved.scope),
        "budget_by_cost_type": budget.entries({**budget.labels, **current}),
        "remaining_by_cost_type": remaining.entries({**remaining.labels, **current}),
        "labor_by_org_node": labour.entries(node_labels),
    }
