# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks and the coverage of a project (``getProjectRiskCoverage``; US-2610).

The reserve is the sum of the shares the risks bear in the reference (``risk_reference_share``,
M-01), written when a revision becomes the reference, by designation or by merge; the coverage
compares it with the provisions of the risks identified in the revision read and the costs at
occurrence of the occurred ones (WF-RIS-0050), the re-estimated amount of the lines that came from
them beside, outside the variance (#1761). The estimate reads it in its indicators of the remaining
to commit, by the registry it declares (``register_coverage``), which this answers.

The reserve is the one the reference of the project conserves, whichever revision is read; none
without a reference. A marked revision is read as its marking kept it (EP-10) for the figures of
its risks, with the reserve of the reference (``kept_coverage``): this computes the coverage of a
revision the marking has not kept, and what the marking keeps.

Declared by US-2550/L1, the socle of EP-08; filled by US-2610/L1.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.risks.covering import conserved_coverage, coverage_of

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import Coverage


def risk_coverage_of(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project: its reserve, provisions, costs."""
    return coverage_of(session, project_id, revision_id)


def kept_coverage(
    session: Session, project_id: UUID, kept: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """Give the coverage a marked revision kept, with the reserve the reference conserves now.

    None when the marking kept no coverage (``kept`` absent or without its figures): the reading
    computes it then.
    """
    return conserved_coverage(session, project_id, kept)
