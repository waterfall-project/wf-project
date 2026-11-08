# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exporter ``task_tree_image``: the image of the tree of the summary tasks of a structure.

Registered at the import of the interface in the registry of the exchanges
(``register_exporter``): it reads the summary tasks of a structure down to the depth asked, and
draws them by the pure rendering of ``core/planning/task_tree_image.py`` (US-1440/L1), a PNG
(EP-06, "Les exports").

Declared by US-1380/L1; its method raises ``NotImplementedError`` until US-1440/L2 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ExportedFile, ExportOrder


class TaskTreeExporter:
    """The exporter of the image of a task tree, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Draw the tree of the summary tasks of a structure, in PNG."""
        msg = "export is filled by US-1440/L2"
        raise NotImplementedError(msg)


TASK_TREE_EXPORTER = TaskTreeExporter()
