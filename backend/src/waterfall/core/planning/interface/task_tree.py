# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exporter ``task_tree_image``: the image of the tree of the summary tasks of a structure.

Registered at the import of the interface in the registry of the exchanges
(``register_exporter``): it reads the summary tasks of a structure down to the depth asked, and
draws them by the pure rendering of ``core/planning/task_tree_image.py`` (US-1440/L1), a PNG
(EP-06, "Les exports"). The header names the project, the revision and the date the structure was
last computed, in the language of the account that asks (WF-ARC-0110). The labels are brought to
one line before the tree is built (#2482), and the layout is measured before anything is drawn: an
image of more than 100 million pixels is not drawn, the export fails with
``TASK_TREE_IMAGE_TOO_LARGE`` (WF-PLA-0120, #2481).

Declared by US-1380/L1; filled by US-1440/L2.
"""

import re
from typing import TYPE_CHECKING

from waterfall.core.exchanges.interface import ExportedFile
from waterfall.core.planning import task_tree_image
from waterfall.core.planning.task_tree_image import (
    TreeNode,
    draw_task_tree,
    layout_task_tree,
    one_line,
    revision_label,
)
from waterfall.core.planning.tree import read_tree
from waterfall.core.projects.interface import Viewer, project_code, project_label
from waterfall.core.revisions.interface import read_revision, structure_facts
from waterfall.core.users.interface import read_account
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.installation import FOLLOWED, read_settings

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ExportOrder
    from waterfall.core.planning.tree import Tree

TOO_LARGE = "TASK_TREE_IMAGE_TOO_LARGE"
MEDIA_TYPE = "image/png"
_NOT_IN_A_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _summaries(tree: Tree, parent: UUID | None, depth: int) -> tuple[TreeNode, ...]:
    """Give the summary tasks under a parent, down to ``depth`` levels, their labels on one line.

    A milestone or a leaf is not a summary and is left out, whatever the depth (WF-PLA-0110).
    """
    if depth < 1:
        return ()
    return tuple(
        TreeNode(one_line(tree.tasks[each].label), _summaries(tree, each, depth - 1))
        for each in tree.subtasks(parent)
        if tree.is_summary(each)
    )


def _language(session: Session, requested_by: UUID) -> str:
    """Give the language of the account that asks, the installation's if it follows the default."""
    chosen = read_account(session, requested_by).display_preferences.get("language")
    if isinstance(chosen, str) and chosen != FOLLOWED:
        return chosen
    return read_settings(session).default_language


class TaskTreeExporter:
    """The exporter of the image of a task tree, as the exchanges ask it (``Exporter``)."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Draw the tree of the summary tasks of a structure, in PNG.

        Read in the transaction of the task, nothing written. ``depth`` null keeps the whole depth.
        """
        project_id = order.project_id
        tree = read_tree(session, project_id, order.structure_id)
        facts = structure_facts(session, project_id, order.structure_id, lock=False)
        language = _language(session, order.requested_by)
        revision = read_revision(
            session, project_id, order.revision_id, Viewer(order.requested_by, ())
        )
        depth = len(tree.tasks) if order.depth is None else order.depth
        layout = layout_task_tree(
            project=TreeNode(
                one_line(project_label(session, project_id) or ""),
                _summaries(tree, None, depth),
            ),
            depth=depth,
            language=language,
            revision=one_line(revision_label(language, revision.version_name)),
            computed_on=facts.scheduled_at.date(),
        )
        if layout.width * layout.height > task_tree_image.MAX_PIXELS:
            raise UnprocessableError(TOO_LARGE)
        code = _NOT_IN_A_NAME.sub("_", project_code(session, project_id) or "")
        name = f"task-tree-{code}.png" if code.strip("_") else "task-tree.png"
        return ExportedFile(draw_task_tree(layout), MEDIA_TYPE, name)


TASK_TREE_EXPORTER = TaskTreeExporter()
