#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Convert one page of a .drawio file into a Mermaid diagram.

Edges drawn "by hand" in draw.io do not always carry a source/target attribute:
they only carry coordinates. Each loose end is then attached to the geometrically
nearest vertex, and the distance used is reported so that the attachment stays
verifiable.
"""

import base64
import html
import re
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Beyond this many pixels, we refuse to infer the end of an edge.
INFERENCE_THRESHOLD_PX = 20.0

Rectangle = tuple[float, float, float, float]
Style = dict[str, str | bool]
Element = ET.Element


class Warn(Protocol):
    """What receives the warnings of a conversion, with their level."""

    def __call__(self, message: str, level: str = "warning") -> None:
        """Receive one warning; ``info`` for what is only reported."""


@dataclass(frozen=True, slots=True)
class Vertex:
    """A vertex of the page: its label, its rectangle and its style."""

    label: str
    rectangle: Rectangle
    style: Style

    @property
    def area(self) -> float:
        """Return the area of the rectangle."""
        return self.rectangle[2] * self.rectangle[3]


@dataclass(frozen=True, slots=True)
class Edge:
    """An edge between two vertices, with its label and its stroke."""

    source: str
    target: str
    label: str
    dashed: bool


@dataclass(frozen=True, slots=True)
class Inference:
    """An end of an edge attached by geometry, and the distance that decided it."""

    edge: str
    end: str
    towards: str
    distance: float


def load_pages(path: str | Path) -> dict[str, Element]:
    """Return {page_name: mxGraphModel element}, compressed pages included."""
    root = ET.parse(path).getroot()
    pages: dict[str, Element] = {}
    for index, diagram in enumerate(root.iter("diagram")):
        name = diagram.get("name") or f"Page-{index + 1}"
        model = diagram.find("mxGraphModel")
        text = (diagram.text or "").strip()
        if model is None and text:
            # Compressed page: base64 -> raw deflate -> URL encoding.
            raw = zlib.decompress(base64.b64decode(text), -15)
            model = ET.fromstring(urllib.parse.unquote(raw.decode("utf-8")))
        if model is None:
            continue
        pages[name] = model
    return pages


def label_of(cell: Element) -> str:
    """Return the label of a cell, draw.io HTML tags turned into Mermaid line breaks."""
    value = cell.get("value") or ""
    # Opening <div> included: draw.io also uses it as a line separator.
    value = re.sub(r"<br\s*/?>|</?(?:div|p|li)[^>]*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    # Every caller wraps the label in quotes, so a quote of its own must be escaped.
    value = value.replace('"', "#quot;")
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
    return "<br>".join(line for line in lines if line)


def style_as_dict(cell: Element) -> Style:
    """Return the draw.io style of a cell, a flag for each key without a value."""
    style: Style = {}
    for piece in (cell.get("style") or "").split(";"):
        if "=" in piece:
            key, _, value = piece.partition("=")
            style[key.strip()] = value.strip()
        elif piece.strip():
            style[piece.strip()] = True
    return style


def mermaid_shape(style: Style, label: str) -> str:
    """Pick the Mermaid shape from the draw.io style."""
    label = label or " "
    if "rhombus" in style:
        return f'{{"{label}"}}'
    if "ellipse" in style:
        return f'(("{label}"))'
    if "cylinder" in style or "mxgraph.flowchart.database" in str(style.get("shape", "")):
        return f'[("{label}")]'
    if str(style.get("rounded")) == "1":
        return f'("{label}")'
    return f'["{label}"]'


def identifier(label: str, taken: set[str]) -> str:
    """Return a readable Mermaid identifier derived from the label, unique in the diagram."""
    unaccented = unicodedata.normalize("NFKD", label.replace("<br>", " "))
    unaccented = "".join(c for c in unaccented if not unicodedata.combining(c))
    base = re.sub(r"[^0-9A-Za-z]+", "_", unaccented)
    base = base.strip("_") or "N"
    if base[0].isdigit():
        base = "N" + base
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    taken.add(candidate)
    return candidate


def geometry(cell: Element) -> Rectangle | None:
    """Return the rectangle of a cell, or None when it has no geometry."""
    geo = cell.find("mxGeometry")
    if geo is None:
        return None
    return (
        float(geo.get("x", 0)),
        float(geo.get("y", 0)),
        float(geo.get("width", 0)),
        float(geo.get("height", 0)),
    )


def distance_to_rectangle(px: float, py: float, rect: Rectangle) -> float:
    """Return the distance from a point to a rectangle, zero inside it."""
    x, y, width, height = rect
    dx = max(x - px, 0.0, px - (x + width))
    dy = max(y - py, 0.0, py - (y + height))
    return (dx * dx + dy * dy) ** 0.5


def _ignore(message: str, level: str = "warning") -> None:
    del message, level


def _vertices(
    cells: dict[str | None, Element], warn: Warn
) -> tuple[dict[str, Vertex], dict[str | None, list[str]]]:
    """Return the vertices of the page and the labels of its edges, by edge."""
    vertices: dict[str, Vertex] = {}
    edge_labels: dict[str | None, list[str]] = defaultdict(list)
    nested: set[str] = set()
    for cell_id, cell in cells.items():
        style = style_as_dict(cell)
        if cell.get("vertex") != "1":
            continue
        if "edgeLabel" in style:
            edge_labels[cell.get("parent")].append(label_of(cell))
            continue
        rect = geometry(cell)
        if rect is None or cell_id is None:
            continue
        vertices[cell_id] = Vertex(label_of(cell), rect, style)
        if cell.get("parent") not in ("1", "0", None):
            nested.add(cell_id)
    if nested:
        warn(
            f"{len(nested)} vertex(es) nested in a draw.io container: coordinates are "
            "relative to the parent, so geometric attachment may be wrong. Check the "
            "diagram produced."
        )
    for parent_id, labels in edge_labels.items():
        parent = cells.get(parent_id)
        if parent is None or parent.get("edge") != "1":
            warn(
                "orphan edge label, attached to no edge: "
                + ", ".join(f'"{label}"' for label in labels if label)
            )
    return vertices, edge_labels


def _nearest(vertices: dict[str, Vertex], px: float, py: float) -> tuple[str, float]:
    def rank(i: str) -> tuple[float, float]:
        return (round(distance_to_rectangle(px, py, vertices[i].rectangle), 1), vertices[i].area)

    cell_id = min(vertices, key=rank)
    return cell_id, distance_to_rectangle(px, py, vertices[cell_id].rectangle)


def _points(cell: Element) -> dict[str | None, tuple[float, float]]:
    geo = cell.find("mxGeometry")
    if geo is None:
        return {}
    return {
        point.get("as"): (float(point.get("x", 0)), float(point.get("y", 0)))
        for point in geo.findall("mxPoint")
    }


def _ends(
    cell: Element, cell_id: str, vertices: dict[str, Vertex], inferences: list[Inference]
) -> dict[str, str]:
    """Return the resolved ends of an edge, inferring loose ones by geometry."""
    points = _points(cell)
    ends: dict[str, str] = {}
    for end, point_name in (("source", "sourcePoint"), ("target", "targetPoint")):
        reference = cell.get(end)
        if reference in vertices:
            ends[end] = reference
            continue
        if point_name in points:
            candidate, distance = _nearest(vertices, *points[point_name])
            if distance <= INFERENCE_THRESHOLD_PX:
                ends[end] = candidate
                inferences.append(Inference(cell_id, end, vertices[candidate].label, distance))
    return ends


def _edges(
    cells: dict[str | None, Element],
    vertices: dict[str, Vertex],
    edge_labels: dict[str | None, list[str]],
    warn: Warn,
) -> list[Edge]:
    """Return the edges whose two ends resolve, and report how they were resolved."""
    edges: list[Edge] = []
    inferences: list[Inference] = []
    for cell_id, cell in cells.items():
        if cell.get("edge") != "1":
            continue
        # An edge without an id is still drawn, or reported, under the name "None".
        ends = _ends(cell, str(cell_id), vertices, inferences)
        label = "<br>".join(one for one in edge_labels.get(cell_id, []) if one)
        if "source" in ends and "target" in ends:
            dashed = str(style_as_dict(cell).get("dashed")) == "1"
            edges.append(Edge(ends["source"], ends["target"], label, dashed))
        else:
            warn(
                f"edge {cell_id} ignored (unresolved end)"
                + (f' — label "{label}"' if label else "")
            )
    for inference in inferences:
        warn(
            f"edge {inference.edge}: {inference.end} inferred towards "
            f'"{inference.towards}" ({inference.distance:.0f} px away)',
            "info",
        )
    if inferences:
        worst = max(inference.distance for inference in inferences)
        warn(
            f"{len(inferences)} edge end(s) attached by geometry "
            f"(largest gap {worst:.0f} px of {INFERENCE_THRESHOLD_PX:.0f} tolerated)",
            "info",
        )
    return edges


def _contains(outer: Vertex, inner: Vertex) -> bool:
    ox, oy, ow, oh = outer.rectangle
    ix, iy, iw, ih = inner.rectangle
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh and ow * oh > iw * ih


def _frames(vertices: dict[str, Vertex]) -> dict[str, str]:
    """Return the frame of each framed vertex: the smallest labelled vertex containing it."""
    parent_of: dict[str, str] = {}
    for inner, vertex in vertices.items():
        enclosing = [
            outer
            for outer, candidate in vertices.items()
            if candidate.label and outer != inner and _contains(candidate, vertex)
        ]
        if enclosing:
            parent_of[inner] = min(enclosing, key=lambda o: vertices[o].area)
    return parent_of


@dataclass(frozen=True, slots=True)
class _Layout:
    vertices: dict[str, Vertex]
    names: dict[str, str]
    parent_of: dict[str, str]
    frames: set[str]


def _emit(layout: _Layout, frame: str | None, indent: str, lines: list[str]) -> None:
    for cell_id, vertex in layout.vertices.items():
        if layout.parent_of.get(cell_id) != frame:
            continue
        if cell_id in layout.frames:
            lines.append(f'{indent}subgraph {layout.names[cell_id]}["{vertex.label}"]')
            _emit(layout, cell_id, indent + "    ", lines)
            lines.append(f"{indent}end")
        else:
            lines.append(
                f"{indent}{layout.names[cell_id]}{mermaid_shape(vertex.style, vertex.label)}"
            )


def _classes(layout: _Layout) -> list[str]:
    """Return the classes that give the vertices their fill colours."""
    by_colour: dict[tuple[str, str], list[str]] = defaultdict(list)
    for cell_id, vertex in layout.vertices.items():
        if cell_id in layout.frames:
            continue
        fill = vertex.style.get("fillColor")
        if fill and fill != "none":
            stroke = vertex.style.get("strokeColor", "#000000")
            by_colour[(str(fill), str(stroke))].append(layout.names[cell_id])
    if not by_colour:
        return []
    lines = [""]
    for n, ((fill, stroke), members) in enumerate(sorted(by_colour.items()), 1):
        lines.append(f"    classDef c{n} fill:{fill},stroke:{stroke}")
        lines.append(f"    class {','.join(sorted(members))} c{n}")
    return lines


def convert(model: Element, direction: str = "LR", warn: Warn = _ignore) -> str:
    """Return the Mermaid flowchart of a page, warnings reported through ``warn``."""
    cells = {c.get("id"): c for c in model.iter("mxCell")}
    vertices, edge_labels = _vertices(cells, warn)
    edges = _edges(cells, vertices, edge_labels, warn)
    taken: set[str] = set()
    names = {i: identifier(vertices[i].label or "N", taken) for i in vertices}
    parent_of = _frames(vertices)
    layout = _Layout(vertices, names, parent_of, set(parent_of.values()))
    lines = [f"flowchart {direction}"]
    _emit(layout, None, "    ", lines)
    lines.append("")
    for edge in edges:
        stroke = "-.->" if edge.dashed else "-->"
        arrow = f'{stroke}|"{edge.label}"|' if edge.label else stroke
        lines.append(f"    {names[edge.source]} {arrow} {names[edge.target]}")
    # Fill colours become classes, to stay close to the original visual.
    lines += _classes(layout)
    return "\n".join(lines) + "\n"


USAGE = "usage: drawio2mermaid.py <file.drawio> [page] [direction]"
LEAST_ARGUMENTS, MOST_ARGUMENTS = 1, 3


def main(arguments: list[str]) -> int:
    """List the pages of a .drawio file, or print one of them as Mermaid.

    The arguments are read by position, so that a page may be named anything, even
    something that starts with a dash.
    """
    if not LEAST_ARGUMENTS <= len(arguments) <= MOST_ARGUMENTS:
        print(USAGE, file=sys.stderr)
        return 2
    file, page, direction = [*arguments, None, None][:MOST_ARGUMENTS]
    pages = load_pages(str(file))
    if page is None:
        for name in pages:
            print(name)
        return 0
    if page not in pages:
        print(f'page "{page}" not found; available pages: {", ".join(pages)}', file=sys.stderr)
        return 1
    messages: list[tuple[str, str]] = []

    def collect(message: str, level: str = "warning") -> None:
        messages.append((level, message))

    output = convert(pages[page], direction or "LR", collect)
    for level, message in messages:
        print(f"  {'!' if level == 'warning' else '-'} {message}", file=sys.stderr)
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
