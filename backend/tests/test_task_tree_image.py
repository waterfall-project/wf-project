# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of the tree of the tasks, without a database.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1440/L1
writes its tests here ("Les tests du back").
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from io import BytesIO
from itertools import pairwise

import pytest
from PIL import Image

from waterfall.core.planning.task_tree_image import (
    FONT_SIZE,
    HEADER_FONT_SIZE,
    INDENT,
    MARGIN,
    MAX_PIXELS,
    PADDING,
    Box,
    TreeLayout,
    TreeNode,
    draw_task_tree,
    header_lines,
    language_of,
    layout_task_tree,
    one_line,
    own_font,
    render_task_tree_image,
    revision_label,
)

PAGE_WIDTH = 794  # an A4 page at 96 dpi
DAY = date(2026, 11, 8)
FILL = (239, 246, 255)  # the fill of a frame
OUTLINE = (107, 114, 128)  # the outline of a frame
ROOT_FILL = (219, 234, 254)  # the fill of the project's frame
# The two tolerances of the ink read back from the image, each with its reason (#2539). A glyph
# does not touch the top of its line: the font keeps its ascent above the capitals and the accents,
# so the first row of ink of a header line lies a few rows below the y it is drawn at; 8 pixels hold
# the header font with its accents, and are fewer than the step of a line, so a line drawn a band
# too low is still seen.
INK_TOP_SLACK = 8
# The ink of a label is measured by its first and last columns that differ from the fill, while the
# font measures its advance: the side bearings of the first and last glyphs and the half-covered
# columns of the anti-aliasing, a pixel or so at each end, make the two differ by up to 3 pixels.
INK_SIDE_SLACK = 3


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
    The probe sits two pixels in from the left edge, where the top edge is flat only because the
    frames are drawn with square corners (``draw.rectangle``): rounded corners would move the
    probe off the outline and fail every test on the pixels, as they should be adjusted with it.
    The middle of the edge is no better, a connecting line entering the frame there.
    """
    return {
        y + 1
        for y in range(image.height - 1)
        if image.getpixel((x + 2, y)) == OUTLINE
        and image.getpixel((x + 2, y + 1)) in (FILL, ROOT_FILL)
    }


def _ink_in(image: Image.Image, top: int, bottom: int) -> bool:
    """Tell whether anything but the background lies in the rows from ``top`` to ``bottom``."""
    return any(
        image.getpixel((x, y)) != (255, 255, 255)
        for x in range(image.width)
        for y in range(top, bottom)
    )


def _first_ink_row(image: Image.Image, top: int, bottom: int) -> int:
    """Give the first row from ``top`` to ``bottom`` that holds anything but the background."""
    return next(
        y
        for y in range(top, bottom)
        if any(image.getpixel((x, y)) != (255, 255, 255) for x in range(image.width))
    )


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
        # Each frame lies under the one before it, in the layout (the PNG is checked above).
        ordered = [column, *below]
        assert all(p.y + p.height < n.y for p, n in pairwise(ordered))


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_png_of_a_three_level_tree_has_its_frames_where_the_layout_puts_them() -> None:
    project = _tree()
    image = _png(project, language="en")
    layout = _layout(project, language="en")
    assert image.size == (layout.width, layout.height)
    _assert_frames_in_png(image, layout.boxes)
    assert _ink_in(image, 0, layout.boxes[0].y)
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


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_three_lines_of_the_header_are_placed_one_under_the_other_each_with_its_ink() -> None:
    layout = _layout(_tree())
    image = _png(_tree())
    step = round(HEADER_FONT_SIZE * 1.3)
    assert layout.header_ys == (MARGIN, MARGIN + step, MARGIN + 2 * step)
    assert len(layout.header) == 3
    assert layout.boxes[0].y >= layout.header_ys[-1] + step
    # Each line of the header leaves its ink in its own band, and none lies between the header
    # and the first frame.
    for line_y in layout.header_ys:
        assert _ink_in(image, line_y, line_y + step)
        # The ink of a line begins at its own y: a few rows below at most, never above.
        top = _first_ink_row(image, line_y - 2, line_y + step)
        assert line_y <= top <= line_y + INK_TOP_SLACK
    assert not _ink_in(image, layout.header_ys[-1] + step, layout.boxes[0].y)


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_label_of_each_frame_is_drawn_inside_it() -> None:
    layout = _layout(_tree())
    image = _png(_tree())
    background = {FILL, ROOT_FILL}
    for box in layout.boxes:
        inside = [
            image.getpixel((x, y))
            for x in range(box.x + 1, box.x + box.width)
            for y in range(box.y + 1, box.y + box.height)
        ]
        assert any(pixel not in background for pixel in inside), box.label
        # The ink is that of this label: as wide as the font measures it, from the padding.
        columns = [
            x
            for x in range(box.x + 2, box.x + box.width - 2)
            if any(
                image.getpixel((x, y)) not in background
                for y in range(box.y + 2, box.y + box.height - 2)
            )
        ]
        wanted = round(own_font(FONT_SIZE).getlength(box.label))
        assert abs((columns[-1] - columns[0] + 1) - wanted) <= INK_SIDE_SLACK, box.label
        assert abs(columns[0] - (box.x + PADDING)) <= INK_SIDE_SLACK, box.label
    # The check discriminates: a frame without label has nothing but its fill.
    empty = _layout(TreeNode("", (TreeNode(""),)), depth=1)
    blank = _png(TreeNode("", (TreeNode(""),)), depth=1)
    for box in empty.boxes:
        inside = {
            blank.getpixel((x, y))
            for x in range(box.x + 1, box.x + box.width)
            for y in range(box.y + 1, box.y + box.height)
        }
        assert inside <= background


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_label_is_brought_to_one_line_blanks_and_line_breaks_alike() -> None:
    assert one_line("Études\net\r\n  essais\t\u2028finaux ") == "Études et essais finaux"
    assert one_line("Simple") == "Simple"
    assert one_line(" \n ") == ""


@pytest.mark.requirement("WF-PLA-0120-A")
def test_the_language_and_the_name_of_the_revision_follow_the_catalogue() -> None:
    assert [language_of(each) for each in ("fr", "fr-FR", "EN", "de")] == ["fr", "fr", "en", "en"]
    assert revision_label("fr", None) == "révision courante"
    assert revision_label("en-GB", None) == "current revision"
    assert revision_label("fr", "v1.0") == "v1.0"


@pytest.mark.requirement("WF-PLA-0120-A")
def test_renders_in_parallel_threads_give_the_png_of_a_render_alone() -> None:
    assert own_font(FONT_SIZE) is not own_font(FONT_SIZE)
    # The fonts are not shared between threads (#2486): the same bytes however many render at once.
    projects = [_tree(columns=3 + i % 3, label=f"Lot{i % 3}") for i in range(24)]

    def render(project: TreeNode) -> bytes:
        return render_task_tree_image(
            project=project, depth=3, language="fr", revision="R1", computed_on=DAY
        )

    alone = [render(project) for project in projects]
    with ThreadPoolExecutor(max_workers=8) as pool:
        together = list(pool.map(render, projects * 4))
    assert together == alone * 4


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_layout_beyond_the_ceiling_of_a_hundred_million_pixels_is_known_from_its_size() -> None:
    assert MAX_PIXELS == 100_000_000
    # 300 columns of 40 nested summaries: about 18,000 by 8,000 pixels, laid out in a blink.
    column = TreeNode("Lot récapitulatif")
    for _ in range(40):
        column = TreeNode("Lot récapitulatif", (column,))
    project = TreeNode("Projet", tuple(column for _ in range(300)))
    layout = _layout(project, depth=40)
    assert layout.width * layout.height > MAX_PIXELS
    # The size is known from the layout alone: nothing was drawn to measure it.
    small = _layout(_tree())
    assert small.width * small.height < MAX_PIXELS
    assert draw_task_tree(small).startswith(b"\x89PNG")
