#!/usr/bin/env python3
"""Convert one page of a .drawio file into a Mermaid diagram.

Edges drawn "by hand" in draw.io do not always carry a source/target attribute:
they only carry coordinates. Each loose end is then attached to the geometrically
nearest vertex, and the distance used is reported so that the attachment stays
verifiable.
"""

import base64
import unicodedata
import html
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import defaultdict

# Beyond this many pixels, we refuse to infer the end of an edge.
INFERENCE_THRESHOLD_PX = 20.0


def load_pages(path):
    """Return {page_name: mxGraphModel element}, compressed pages included."""
    root = ET.parse(path).getroot()
    pages = {}
    for index, diagram in enumerate(root.iter("diagram")):
        name = diagram.get("name") or f"Page-{index + 1}"
        model = diagram.find("mxGraphModel")
        if model is None and (diagram.text or "").strip():
            # Compressed page: base64 -> raw deflate -> URL encoding.
            raw = zlib.decompress(base64.b64decode(diagram.text.strip()), -15)
            model = ET.fromstring(urllib.parse.unquote(raw.decode("utf-8")))
        if model is None:
            continue
        pages[name] = model
    return pages


def label_of(cell):
    """Label of a cell, draw.io HTML tags turned into Mermaid line breaks."""
    value = cell.get("value") or ""
    # Opening <div> included: draw.io also uses it as a line separator.
    value = re.sub(r"<br\s*/?>|</?(?:div|p|li)[^>]*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    # Every caller wraps the label in quotes, so a quote of its own must be escaped.
    value = value.replace('"', "#quot;")
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.split("\n")]
    return "<br>".join(line for line in lines if line)


def style_as_dict(cell):
    style = {}
    for piece in (cell.get("style") or "").split(";"):
        if "=" in piece:
            key, _, value = piece.partition("=")
            style[key.strip()] = value.strip()
        elif piece.strip():
            style[piece.strip()] = True
    return style


def mermaid_shape(style, label):
    """Pick the Mermaid shape from the draw.io style."""
    label = label or " "
    if "rhombus" in style:
        return '{"%s"}' % label
    if "ellipse" in style:
        return '(("%s"))' % label
    if "cylinder" in style or "mxgraph.flowchart.database" in str(style.get("shape", "")):
        return '[("%s")]' % label
    if str(style.get("rounded")) == "1":
        return '("%s")' % label
    return '["%s"]' % label


def identifier(label, taken):
    """Readable Mermaid identifier derived from the label, unique in the diagram."""
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


def geometry(cell):
    geo = cell.find("mxGeometry")
    if geo is None:
        return None
    return (
        float(geo.get("x", 0)), float(geo.get("y", 0)),
        float(geo.get("width", 0)), float(geo.get("height", 0)),
    )


def distance_to_rectangle(px, py, rect):
    x, y, width, height = rect
    dx = max(x - px, 0.0, px - (x + width))
    dy = max(y - py, 0.0, py - (y + height))
    return (dx * dx + dy * dy) ** 0.5


def convert(model, direction="LR", warn=lambda message, level="warning": None):
    cells = {c.get("id"): c for c in model.iter("mxCell")}

    vertices, edge_labels, nested = {}, defaultdict(list), set()
    for cell_id, cell in cells.items():
        style = style_as_dict(cell)
        if cell.get("vertex") != "1":
            continue
        if "edgeLabel" in style:
            edge_labels[cell.get("parent")].append(label_of(cell))
            continue
        rect = geometry(cell)
        if rect is None:
            continue
        vertices[cell_id] = (label_of(cell), rect, style)
        if cell.get("parent") not in ("1", "0", None):
            nested.add(cell_id)

    if nested:
        warn(
            f"{len(nested)} vertex(es) nested in a draw.io container: coordinates are "
            "relative to the parent, so geometric attachment may be wrong. Check the "
            "diagram produced."
        )

    for parent_id, labels in edge_labels.items():
        if cells.get(parent_id) is None or cells[parent_id].get("edge") != "1":
            warn(
                "orphan edge label, attached to no edge: "
                + ", ".join(f'"{label}"' for label in labels if label)
            )

    def nearest(px, py):
        cell_id = min(vertices, key=lambda i: (
            round(distance_to_rectangle(px, py, vertices[i][1]), 1),
            vertices[i][1][2] * vertices[i][1][3],
        ))
        return cell_id, distance_to_rectangle(px, py, vertices[cell_id][1])

    edges, inferences = [], []
    for cell_id, cell in cells.items():
        if cell.get("edge") != "1":
            continue
        geo = cell.find("mxGeometry")
        points = {}
        if geo is not None:
            for point in geo.findall("mxPoint"):
                points[point.get("as")] = (float(point.get("x", 0)), float(point.get("y", 0)))

        ends = {}
        for end, attribute, point_name in (("source", "source", "sourcePoint"),
                                           ("target", "target", "targetPoint")):
            reference = cell.get(attribute)
            if reference in vertices:
                ends[end] = reference
                continue
            if point_name in points:
                candidate, distance = nearest(*points[point_name])
                if distance <= INFERENCE_THRESHOLD_PX:
                    ends[end] = candidate
                    inferences.append((cell_id, end, vertices[candidate][0], distance))

        label = "<br>".join(one for one in edge_labels.get(cell_id, []) if one)
        if "source" in ends and "target" in ends:
            dashed = str(style_as_dict(cell).get("dashed")) == "1"
            edges.append((ends["source"], ends["target"], label, dashed))
        else:
            warn(
                f"edge {cell_id} ignored (unresolved end)"
                + (f' — label "{label}"' if label else "")
            )

    for cell_id, end, name, distance in inferences:
        warn(
            f'edge {cell_id}: {end} inferred towards "{name}" ({distance:.0f} px away)',
            "info",
        )
    if inferences:
        worst = max(distance for *_, distance in inferences)
        warn(
            f"{len(inferences)} edge end(s) attached by geometry "
            f"(largest gap {worst:.0f} px of {INFERENCE_THRESHOLD_PX:.0f} tolerated)",
            "info",
        )

    taken = set()
    names = {i: identifier(vertices[i][0] or "N", taken) for i in vertices}

    # Frames: a labelled vertex whose rectangle contains other vertices. Each vertex
    # goes into the smallest frame that contains it.
    def contains(outer, inner):
        ox, oy, ow, oh = vertices[outer][1]
        ix, iy, iw, ih = vertices[inner][1]
        return (outer != inner and ox <= ix and oy <= iy and ix + iw <= ox + ow
                and iy + ih <= oy + oh and ow * oh > iw * ih)

    parent_of = {}
    for inner in vertices:
        enclosing = [outer for outer in vertices if vertices[outer][0] and contains(outer, inner)]
        if enclosing:
            parent_of[inner] = min(enclosing, key=lambda o: vertices[o][1][2] * vertices[o][1][3])
    frames = set(parent_of.values())

    lines = [f"flowchart {direction}"]

    def emit(frame, indent):
        for cell_id, (label, _, style) in vertices.items():
            if parent_of.get(cell_id) != frame:
                continue
            if cell_id in frames:
                lines.append(f'{indent}subgraph {names[cell_id]}["{label}"]')
                emit(cell_id, indent + "    ")
                lines.append(f"{indent}end")
            else:
                lines.append(f"{indent}{names[cell_id]}{mermaid_shape(style, label)}")

    emit(None, "    ")

    lines.append("")
    for source, target, label, dashed in edges:
        stroke = "-.->" if dashed else "-->"
        arrow = f'{stroke}|"{label}"|' if label else stroke
        lines.append(f"    {names[source]} {arrow} {names[target]}")

    # Fill colours become classes, to stay close to the original visual.
    by_colour = defaultdict(list)
    for cell_id, (_, _, style) in vertices.items():
        if cell_id in frames:
            continue
        fill = style.get("fillColor")
        if fill and fill != "none":
            by_colour[(fill, style.get("strokeColor", "#000000"))].append(names[cell_id])
    if by_colour:
        lines.append("")
        for n, ((fill, stroke), members) in enumerate(sorted(by_colour.items()), 1):
            lines.append(f"    classDef c{n} fill:{fill},stroke:{stroke}")
            lines.append(f"    class {','.join(sorted(members))} c{n}")

    return "\n".join(lines) + "\n"


def main(argv):
    if not 2 <= len(argv) <= 4:
        print("usage: drawio2mermaid.py <file.drawio> [page] [direction]", file=sys.stderr)
        return 2
    pages = load_pages(argv[1])
    if len(argv) < 3:
        for name in pages:
            print(name)
        return 0
    if argv[2] not in pages:
        print(f'page "{argv[2]}" not found; available pages: {", ".join(pages)}', file=sys.stderr)
        return 1
    messages = []
    output = convert(
        pages[argv[2]],
        argv[3] if len(argv) > 3 else "LR",
        lambda message, level="warning": messages.append((level, message)),
    )
    for level, message in messages:
        print(f"  {'!' if level == 'warning' else '-'} {message}", file=sys.stderr)
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
