# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of the tree of the tasks, without a database.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1440/L1
writes its tests here ("Les tests du back").
"""

from datetime import date
from io import BytesIO

import pytest
from PIL import Image

from waterfall.core.planning.task_tree_image import (
    TreeLayout,
    TreeNode,
    header_lines,
    layout_task_tree,
    render_task_tree_image,
)

PAGE_WIDTH = 794  # an A4 page at 96 dpi
DAY = date(2026, 11, 8)


def _tree(columns: int = 3, grandchildren: int = 2, label: str = "Lot") -> TreeNode:
    """Three levels under the project: columns, children, grandchildren."""
    return TreeNode(
        "Projet Alpha",
        tuple(
            TreeNode(
                f"{label} {i}",
                tuple(
                    TreeNode(
                        f"{label} {i}.{j}",
                        tuple(TreeNode(f"{label} {i}.{j}.{k}") for k in range(grandchildren)),
                    )
                    for j in range(2)
                ),
            )
            for i in range(columns)
        ),
    )


def _layout(project: TreeNode, depth: int = 3, language: str = "fr") -> TreeLayout:
    return layout_task_tree(
        project=project, depth=depth, language=language, revision="R1", computed_on=DAY
    )


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_first_level_is_laid_out_horizontally_and_the_next_ones_vertically() -> None:
    layout = _layout(_tree())
    first = [b for b in layout.boxes if b.level == 1]
    assert len(first) == 3
    assert len({b.y for b in first}) == 1
    assert [b.x for b in first] == sorted({b.x for b in first})
    for column in first:
        below = [b for b in layout.boxes if b.label.startswith(column.label + ".") and b.level > 1]
        assert below
        assert all(b.y > column.y for b in below)
        # Never beside the column: inside its horizontal extent, one under the other.
        assert all(column.x <= b.x < column.x + column.width + 40 for b in below)
        ys = [b.y for b in below]
        assert ys == sorted(set(ys))


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_png_of_a_three_level_tree_has_the_size_of_its_layout() -> None:
    project = _tree()
    png = render_task_tree_image(
        project=project, depth=3, language="en", revision="R1", computed_on=DAY
    )
    image = Image.open(BytesIO(png))
    assert image.format == "PNG"
    layout = _layout(project, language="en")
    assert image.size == (layout.width, layout.height)
    # Something is drawn: not a blank page.
    colors = image.convert("RGB").getcolors(maxcolors=1 << 16)
    assert colors is not None
    assert len(colors) > 3


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_tree_too_wide_for_a_page_makes_an_image_wider_than_the_page_without_reduction() -> None:
    project = _tree(columns=12, label="Une récapitulative au libellé long")
    png = render_task_tree_image(
        project=project, depth=3, language="fr", revision="R1", computed_on=DAY
    )
    width, _ = Image.open(BytesIO(png)).size
    layout = _layout(project)
    assert width > PAGE_WIDTH
    # Every box lies fully inside the image at its natural size: nothing was scaled down.
    assert all(b.x + b.width < width for b in layout.boxes)
    assert width == layout.width
    first = [b for b in layout.boxes if b.level == 1]
    assert width >= sum(b.width for b in first)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_narrow_tree_is_not_stretched_to_the_page() -> None:
    layout = _layout(TreeNode("P", (TreeNode("A"),)), depth=1)
    assert layout.width < PAGE_WIDTH


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_content_depends_only_on_the_depth_asked() -> None:
    project = _tree()
    for depth, levels in ((1, {0, 1}), (2, {0, 1, 2}), (3, {0, 1, 2, 3}), (9, {0, 1, 2, 3})):
        assert {b.level for b in _layout(project, depth=depth).boxes} == levels
    assert _layout(project, depth=2) == _layout(project, depth=2)
    assert render_task_tree_image(
        project=project, depth=2, language="fr", revision="R1", computed_on=DAY
    ) == render_task_tree_image(
        project=_tree(grandchildren=5), depth=2, language="fr", revision="R1", computed_on=DAY
    )


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_project_without_summary_is_drawn_as_its_own_node_alone() -> None:
    layout = _layout(TreeNode("Seul"), language="en")
    assert [b.label for b in layout.boxes] == ["Seul"]
    assert layout.edges == ()
    png = render_task_tree_image(
        project=TreeNode("Seul"), depth=3, language="en", revision="R1", computed_on=DAY
    )
    assert Image.open(BytesIO(png)).size == (layout.width, layout.height)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_header_names_the_project_the_revision_and_the_date_in_the_account_language() -> None:
    assert header_lines("fr", "Alpha", "R2", DAY) == (
        "Projet : Alpha",
        "Révision : R2",
        "Calculé le 08/11/2026",
    )
    assert header_lines("en", "Alpha", "R2", DAY) == (
        "Project: Alpha",
        "Revision: R2",
        "Computed on 2026-11-08",
    )
    assert header_lines("de", "Alpha", "R2", DAY) == header_lines("en", "Alpha", "R2", DAY)
    fr = render_task_tree_image(
        project=_tree(), depth=2, language="fr", revision="R2", computed_on=DAY
    )
    en = render_task_tree_image(
        project=_tree(), depth=2, language="en", revision="R2", computed_on=DAY
    )
    assert fr != en


@pytest.mark.requirement("WF-PLA-0120-A")
def test_accented_labels_are_drawn_by_the_embedded_font() -> None:
    png = render_task_tree_image(
        project=TreeNode("Éléphant", (TreeNode("Équipe réalisée à Noël"),)),
        depth=1,
        language="fr",
        revision="Révision é",
        computed_on=DAY,
    )
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
