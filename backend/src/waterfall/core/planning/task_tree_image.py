# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of the tree of the summary tasks, drawn with Pillow (WF-PLA-0120, US-1440/L1).

Pure: the tree arrives in memory and the PNG leaves as bytes, with no database and no clock (the
date of the computation is an argument). The first level is laid out horizontally under the node
of the project, the next ones vertically under their parent. The image has the size of its
content: a tree too wide for a page makes an image wider than the page, never reduced. The font,
DejaVu Sans, is embedded in ``core/exchanges/fonts`` so that the image does not depend on the
fonts of the worker's image; the header, in the language of the account, comes from the small
catalogue below (WF-ARC-0110).
"""

from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from io import BytesIO
from typing import TYPE_CHECKING, Final

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from datetime import date

    from PIL.ImageFont import FreeTypeFont

FONT_SIZE: Final = 16
HEADER_FONT_SIZE: Final = 20
PADDING: Final = 8
GAP: Final = 24
ROW_GAP: Final = 12
INDENT: Final = 28
MARGIN: Final = 24
HEADER_GAP: Final = 24
# The most pixels (width times height) an image has: beyond, the export fails and says so, never
# reduces the image (WF-PLA-0120, #2481).
MAX_PIXELS: Final = 100_000_000

_BACKGROUND: Final = (255, 255, 255)
_INK: Final = (31, 41, 55)
_LINE: Final = (107, 114, 128)
_FILL: Final = (239, 246, 255)
_ROOT_FILL: Final = (219, 234, 254)

DEFAULT_LANGUAGE: Final = "en"
_HEADER: Final = {
    "fr": ("Projet : {project}", "Révision : {revision}", "Calculé le {date}"),
    "en": ("Project: {project}", "Revision: {revision}", "Computed on {date}"),
}
_DATE_FORMAT: Final = {"fr": "%d/%m/%Y", "en": "%Y-%m-%d"}
# What names the current revision, which bears no version name yet.
_CURRENT_REVISION: Final = {"fr": "révision courante", "en": "current revision"}


@dataclass(frozen=True)
class TreeNode:
    """A summary task to draw: its label and its summary children, in order."""

    label: str
    children: tuple[TreeNode, ...] = ()


@dataclass(frozen=True)
class Box:
    """A node placed in the image: its level (0 is the project) and its rectangle, in pixels."""

    label: str
    level: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class TreeLayout:
    """Where each node goes, the lines of the header (and their y) and the size of the whole image.

    ``edges`` are (parent, child) indexes into ``boxes``; ``boxes[0]`` is the project node.
    """

    header: tuple[str, ...]
    header_ys: tuple[int, ...]
    boxes: tuple[Box, ...]
    edges: tuple[tuple[int, int], ...]
    width: int
    height: int


def one_line(label: str) -> str:
    """Give a label on one line: each run of blanks and line breaks is a single space (#2482).

    The rendering measures and draws one line; a label with a line break would be measured wider
    than the text drawn.
    """
    return " ".join(label.split())


def language_of(language: str) -> str:
    """Give the language of the catalogue a language stands for: its primary subtag, or English."""
    primary = language.replace("_", "-").split("-")[0].lower()
    return primary if primary in _HEADER else DEFAULT_LANGUAGE


def revision_label(language: str, version_name: str | None) -> str:
    """Give how the header names a revision: its version name, or the current revision."""
    return version_name if version_name is not None else _CURRENT_REVISION[language_of(language)]


def header_lines(language: str, project: str, revision: str, computed_on: date) -> tuple[str, ...]:
    """Return the three lines of the header (project, revision, date of the computation).

    A language with a region (``fr-FR``, ``fr_FR``) is read as its primary subtag; a language the
    catalogue does not know falls back to English.
    """
    lang = language_of(language)
    day = computed_on.strftime(_DATE_FORMAT[lang])
    return tuple(
        line.format(project=project, revision=revision, date=day) for line in _HEADER[lang]
    )


@cache
def _font_bytes() -> bytes:
    return files("waterfall.core.exchanges").joinpath("fonts", "DejaVuSans.ttf").read_bytes()


def own_font(size: int) -> FreeTypeFont:
    """Give a font of its own: Pillow does not promise a ``FreeTypeFont`` safe between threads.

    Only the bytes of the file are cached, shared and read-only (#2486).
    """
    return ImageFont.truetype(BytesIO(_font_bytes()), size)


def _header_line_height() -> int:
    return round(HEADER_FONT_SIZE * 1.3)


def _cut(node: TreeNode, depth: int, level: int = 1) -> tuple[TreeNode, ...]:
    """Return the children of ``node`` that the depth asked keeps (level 1 is under the project)."""
    if level > depth:
        return ()
    return tuple(TreeNode(c.label, _cut(c, depth, level + 1)) for c in node.children)


def layout_task_tree(
    *,
    project: TreeNode,
    depth: int,
    language: str,
    revision: str,
    computed_on: date,
) -> TreeLayout:
    """Place the project node, its children side by side, and their descendants below them.

    ``depth`` is the number of levels under the project that are drawn (1 draws the first level
    only); below 1 only the project node is drawn.
    """
    body_font = own_font(FONT_SIZE)
    head_font = own_font(HEADER_FONT_SIZE)
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    header = header_lines(language, project.label, revision, computed_on)

    def text_width(label: str, font: FreeTypeFont) -> int:
        return round(scratch.textlength(label, font=font))

    def box_size(label: str) -> tuple[int, int]:
        return text_width(label, body_font) + 2 * PADDING, FONT_SIZE + 2 * PADDING

    header_width = max(text_width(line, head_font) for line in header)
    header_ys = tuple(MARGIN + i * _header_line_height() for i in range(len(header)))
    top = MARGIN + len(header) * _header_line_height() + HEADER_GAP

    root_w, root_h = box_size(project.label)
    columns = _cut(project, depth)
    boxes: list[Box] = [Box(project.label, 0, 0, top, root_w, root_h)]
    edges: list[tuple[int, int]] = []

    def place(node: TreeNode, level: int, x: int, y: int, parent: int) -> int:
        """Stack ``node`` and its subtree from ``y`` down; return the y after the subtree."""
        w, h = box_size(node.label)
        boxes.append(Box(node.label, level, x, y, w, h))
        index = len(boxes) - 1
        edges.append((parent, index))
        end = y + h + ROW_GAP
        for child in node.children:
            end = place(child, level + 1, x + INDENT, end, index)
        return end

    row_y = top + root_h + GAP
    x = MARGIN
    bottom = top + root_h + ROW_GAP
    for child in columns:
        first = len(boxes)
        bottom = max(bottom, place(child, 1, x, row_y, 0))
        x = max(b.x + b.width for b in boxes[first:]) + GAP
    content_right = x - GAP if columns else MARGIN + root_w
    width = max(content_right + MARGIN, header_width + 2 * MARGIN, root_w + 2 * MARGIN)
    boxes[0] = Box(project.label, 0, (width - root_w) // 2, top, root_w, root_h)
    height = bottom - ROW_GAP + MARGIN
    return TreeLayout(header, header_ys, tuple(boxes), tuple(edges), width, height)


def render_task_tree_image(
    *,
    project: TreeNode,
    depth: int,
    language: str,
    revision: str,
    computed_on: date,
) -> bytes:
    """Draw the tree of the summary tasks under ``project`` down to ``depth``; the PNG's bytes."""
    layout = layout_task_tree(
        project=project,
        depth=depth,
        language=language,
        revision=revision,
        computed_on=computed_on,
    )
    return draw_task_tree(layout)


def draw_task_tree(layout: TreeLayout) -> bytes:
    """Draw a layout; the PNG's bytes. The size of the layout is the caller's to bound."""
    image = Image.new("RGB", (layout.width, layout.height), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    head_font = own_font(HEADER_FONT_SIZE)
    body_font = own_font(FONT_SIZE)
    for line, line_y in zip(layout.header, layout.header_ys, strict=True):
        draw.text((MARGIN, line_y), line, fill=_INK, font=head_font)
    for parent, child in layout.edges:
        p, c = layout.boxes[parent], layout.boxes[child]
        if c.level == 1:
            bus = p.y + p.height + GAP // 2
            p_mid, c_mid = p.x + p.width // 2, c.x + c.width // 2
            draw.line([(p_mid, p.y + p.height), (p_mid, bus), (c_mid, bus), (c_mid, c.y)], _LINE)
        else:
            stem = p.x + INDENT // 2
            mid = c.y + c.height // 2
            draw.line([(stem, p.y + p.height), (stem, mid), (c.x, mid)], _LINE)
    for box in layout.boxes:
        draw.rectangle(
            (box.x, box.y, box.x + box.width, box.y + box.height),
            fill=_ROOT_FILL if box.level == 0 else _FILL,
            outline=_LINE,
        )
        draw.text((box.x + PADDING, box.y + PADDING), box.label, fill=_INK, font=body_font)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
