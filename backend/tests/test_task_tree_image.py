# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of the tree of the tasks, without a database.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1440/L1
writes its tests here ("Les tests du back").
"""

from datetime import date
from io import BytesIO
from itertools import pairwise

import pytest
from PIL import Image

from waterfall.core.planning.task_tree_image import (
    FONT_SIZE,
    INDENT,
    PADDING,
    Box,
    TreeLayout,
    TreeNode,
    header_lines,
    layout_task_tree,
    render_task_tree_image,
)

PAGE_WIDTH = 794  # an A4 page at 96 dpi
DAY = date(2026, 11, 8)
FILL = (239, 246, 255)  # the fill of a frame
OUTLINE = (107, 114, 128)  # the outline of a frame
ROOT_FILL = (219, 234, 254)  # the fill of the project's frame


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


def _png(project: TreeNode, depth: int = 3, language: str = "fr") -> Image.Image:
    png = render_task_tree_image(
        project=project, depth=depth, language=language, revision="R1", computed_on=DAY
    )
    return Image.open(BytesIO(png)).convert("RGB")


def _frame_tops(image: Image.Image, x: int) -> set[int]:
    """Return the y of the first fill row of each frame crossing the column ``x`` + 2 of the PNG.

    A frame's top is its outline over its fill, which text and connecting lines never reproduce.
    """
    return {
        y + 1
        for y in range(image.height - 1)
        if image.getpixel((x + 2, y)) == OUTLINE
        and image.getpixel((x + 2, y + 1)) in (FILL, ROOT_FILL)
    }


def _assert_frames_in_png(image: Image.Image, boxes: tuple[Box, ...]) -> None:
    """Every frame of the layout is where the PNG has it: filled inside, and nothing else there."""
    for box in boxes:
        fill = ROOT_FILL if box.level == 0 else FILL
        assert image.getpixel((box.x + 2, box.y + 2)) == fill
        assert image.getpixel((box.x + box.width - 2, box.y + box.height - 2)) == fill
    for x in {b.x for b in boxes}:
        assert _frame_tops(image, x) == {b.y + 1 for b in boxes if b.x <= x + 2 < b.x + b.width}


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_first_level_is_laid_out_horizontally_and_the_next_ones_vertically() -> None:
    project = _tree()
    layout = _layout(project)
    image = _png(project)
    first = [b for b in layout.boxes if b.level == 1]
    assert len(first) == 3
    assert len({b.y for b in first}) == 1
    assert [b.x for b in first] == sorted({b.x for b in first})
    _assert_frames_in_png(image, layout.boxes)
    assert {min(_frame_tops(image, b.x)) for b in first} == {first[0].y + 1}
    for column in first:
        below = [b for b in layout.boxes if b.label.startswith(column.label + ".") and b.level > 1]
        assert below
        assert all(b.y > column.y for b in below)
        # Never beside the column: at the indent of its level, one under the other.
        assert all(b.x == column.x + INDENT * (b.level - 1) for b in below)
        for level in (2, 3):
            ys = [b.y for b in below if b.level == level]
            assert ys == sorted(set(ys))
        # Each frame lies under the one before it, the PNG's own pixels agreeing.
        ordered = [column, *below]
        assert all(p.y + p.height < n.y for p, n in pairwise(ordered))


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_png_of_a_three_level_tree_has_its_frames_where_the_layout_puts_them() -> None:
    project = _tree()
    image = _png(project, language="en")
    layout = _layout(project, language="en")
    assert image.size == (layout.width, layout.height)
    _assert_frames_in_png(image, layout.boxes)
    # Something is drawn: the header's ink above the first frame.
    assert any(
        image.getpixel((x, y)) != (255, 255, 255)
        for x in range(layout.width)
        for y in range(layout.boxes[0].y)
    )
    png = render_task_tree_image(
        project=project, depth=3, language="en", revision="R1", computed_on=DAY
    )
    assert Image.open(BytesIO(png)).format == "PNG"


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_tree_too_wide_for_a_page_makes_an_image_wider_than_the_page_without_reduction() -> None:
    project = _tree(columns=12, label="Une récapitulative au libellé long")
    image = _png(project)
    layout = _layout(project)
    first = [b for b in layout.boxes if b.level == 1]
    assert image.width > PAGE_WIDTH
    assert image.width == layout.width
    assert image.width >= sum(b.width for b in first)
    # Natural size: every frame is as high as one line of the unreduced font and its padding.
    assert {b.height for b in layout.boxes} == {FONT_SIZE + 2 * PADDING}
    assert all(b.x + b.width < image.width for b in layout.boxes)
    _assert_frames_in_png(image, layout.boxes)
    # The frames of the first level do not overlap, side by side in the PNG.
    assert all(p.x + p.width < n.x for p, n in pairwise(first))


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
def test_a_depth_below_one_draws_only_the_node_of_the_project() -> None:
    layout = _layout(_tree(), depth=0)
    assert [b.label for b in layout.boxes] == ["Projet Alpha"]
    assert layout.edges == ()
    _assert_frames_in_png(_png(_tree(), depth=0), layout.boxes)


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
    for tagged in ("fr-FR", "fr_FR", "FR-fr"):
        assert header_lines(tagged, "Alpha", "R2", DAY) == header_lines("fr", "Alpha", "R2", DAY)
    assert header_lines("en-GB", "Alpha", "R2", DAY) == header_lines("en", "Alpha", "R2", DAY)
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
