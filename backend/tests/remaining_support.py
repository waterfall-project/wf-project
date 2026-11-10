# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the remaining to commit share (EP-09, "Les tests du back"): a line reviewed.

What a review of the project writes on a line of estimate — its remaining to commit before the
review, the mark of its re-estimation and the reason sent —, valid for a line of labour of
``estimate_support`` unless a test changes it, written around the service. The stories of EP-09
add here a project In progress with its reference, its tasks and its lines written through the
interfaces, and the clock set; a story that needs another helper writes it in its own file.
"""

from decimal import Decimal

from project_rows import AT

# The six columns of a line of labour reviewed (migration 0027): its figures and its amount before
# the review — two engineers for twelve hours —, reestimated at ``AT``, and why.
REVIEWED: dict[str, object] = {
    "previous_quantity": Decimal(2),
    "previous_hours": Decimal(12),
    "previous_unit_disbursement": None,
    "previous_reestimated_amount": Decimal("1560.00"),
    "reestimated_at": AT,
    "remaining_reason": "Revue d'avril : essais reportés",
}


def reviewed(**overrides: object) -> dict[str, object]:
    """Give the columns a review writes on a line of labour, with the changes a test asks for."""
    return {**REVIEWED, **overrides}
