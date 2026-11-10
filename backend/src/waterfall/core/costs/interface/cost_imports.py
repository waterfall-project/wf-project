# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The log of the imports of the actual costs of a project (WF-CRE-0050; US-1610).

``list_cost_imports`` reads the entries of a project, the most recent first, each with its author,
its period and its four counts (``listCostImports``, US-1610/L2, whose application writes them);
``load_cost_import`` writes the entry of an import of the witness, at the identifier, the instant
and the author it imposes (US-1610/L3, for the tests and the witness of US-1650/L2).

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def list_cost_imports(session: Session, project_id: UUID) -> None:
    """Give the entries of the log of the imports of a project (``listCostImports``)."""
    msg = "list_cost_imports is filled by US-1610/L2"
    raise NotImplementedError(msg)


def load_cost_import(session: Session, project_id: UUID) -> None:
    """Write the entry of an import of the witness, at the identifier and the instant imposed."""
    msg = "load_cost_import is filled by US-1610/L3"
    raise NotImplementedError(msg)
