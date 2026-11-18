# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio reads of the actual costs: the last import of each project (EP-11).

The health of the control of the projects flags a project In progress that has imported no cost
since its last marked revision (WF-PTF-0110): the instant of the last import applied of each
project, up to an instant — that of a past date, read as the imports stood then —, in one query.

Declared by US-2670/L1, the socle of EP-11; filled by US-2750.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


def last_imports(
    session: Session, project_ids: Collection[UUID], before: datetime
) -> dict[UUID, datetime]:
    """Give the instant of the last import applied before ``before``, of each project with one."""
    msg = "last_imports is filled by US-2750"
    raise NotImplementedError(msg)
