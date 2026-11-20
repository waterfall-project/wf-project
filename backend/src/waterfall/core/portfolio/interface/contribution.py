# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a project gives the portfolio, by revision (EP-11, "La contribution d'un projet").

At the marking, ``store_contribution`` keeps, by ``keep_document`` of the indicators, the documents
of the kinds the state of the project calls for: a project In progress the workload, the cost
structure, the risks and the milestones; an offer the same but what asks for a reference — the
milestones —, and its curves. A project in another state keeps none. An exception reaches the
marking, which fails whole (the policy of EP-10, WF-DAT-0040). Registered at
``register_indicators`` of the revisions, after ``store_indicators``, at the import of this
interface (US-2680/L2). On the current day, the same computation gives the same documents for the
current revision of the project — or, without one, its last marked —, kept by the cache of the
indicators under the fingerprint of the project. A revision marked before EP-11 keeps none, and is
given none after (decision of the author of 2026-11-17).

The forms, which the views read (US-2700 to US-2750); every identifier and every date a string, an
amount or hours a decimal in a string, to the cent or the hundredth, never weighted:

- ``portfolio_workload`` (US-2700): ``{"roles": [{"resource_role_id", "months": [{"month":
  "2026-03", "hours": "8.00"}]}]}`` — the hours of each role loaded, by month loaded in order, on
  the remaining to commit of the revision (``getProjectWorkload``: from the day of the computation
  for the current revision, from the day of its marking for a marked one), the estimate being all
  the remaining of an offer. A role without load is absent; a month without load too.
- ``portfolio_cost_structure`` (US-2720): ``{"budget_revision_id", "budget_by_cost_type":
  [{"cost_type_id", "label", "amount"}], "remaining_by_cost_type": [same],
  "budget_labour_by_role": [{"resource_role_id", "amount"}], "remaining_labour_by_role": [same]}``
  — the reference budget by cost type, provision lines left out, read on ``budget_revision_id``,
  the reference of the project or the revision itself for an offer, whose estimate stands for it;
  the remaining to commit of the revision, provisions included; the labour of each by role, which
  the view groups by the current node of the role (WF-PTF-0080, WF-REF-0070). Each list in the
  order of its identifiers, an entry without an amount absent; ``label`` names the cost type as the
  revision read it.
- ``portfolio_milestones`` (US-2750): ``{"milestones": [{"lineage_id", "label", "reference_date",
  "completed_on"}]}`` — the milestones of the revision inscribed in the time/time tracking, in the
  order of the plan, their date in the reference, none when the reference does not hold them, and
  the day each was completed, none while it is not (WF-PTF-0110). A project In progress only.
- ``portfolio_offer_curves`` (US-2740): ``{"cost_curve": CurveSeries, "cost_curve_payment_delays":
  CurveSeries}`` — the curves of the estimate of an offer, the reference budget without the
  provision lines and the projection provisions included, without and with the payment delays
  (``offer_curves`` of the indicators), their context that of the marking (``marked``,
  ``is_stored`` true) or of the day. An offer only.

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L2, the risks by US-2680/L3.
"""

from typing import TYPE_CHECKING

from waterfall.core.indicators.interface import keep_document
from waterfall.core.portfolio.contributing import portfolio_documents
from waterfall.core.revisions.interface import revision_project

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def store_contribution(session: Session, revision_id: UUID, act: Act) -> None:
    """Keep the documents of the portfolio of a revision, in the transaction of its marking.

    Computed at the instant of ``act``, the act of the marking, on the state of the project then;
    every document is computed before the first is kept, each kept at that instant by its requester
    (``keep_document``). Nothing is caught.
    """
    project_id = revision_project(session, revision_id)
    documents = portfolio_documents(session, project_id, revision_id, act.at, marking=True)
    for kind, document in documents.items():
        keep_document(session, revision_id, kind, document, act)
