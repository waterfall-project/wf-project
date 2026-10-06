#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Project the Word + draw.io specification into Markdown an agent can read.

Word, draw.io and the Mermaid files of figures/ remain the sources; this script
regenerates `waterfall-spec.md`, which must never be edited by hand. The Markdown
it produces adds two things the .docx does not carry and reviews cannot do
without: the section number on every heading, and an explicit anchor — section
plus identifier — on every requirement.

The document is written in French; this program and its console output are in
English, and every literal that lands in the document is kept verbatim.
"""

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import drawio2mermaid

# The directory of this script is on Python's import path when it runs, so its
# neighbour drawio2mermaid imports as a module.
ROOT = Path(__file__).resolve().parent.parent

# Word table label -> field name emitted in the projection. Both sides are part of
# the document: the left as Word writes it, the right as agents read it.
REQUIREMENT_FIELDS: dict[str, str] = {
    "ID": "id",
    "Titre": "titre",
    "Flex": "flexibilite",
    "FBS": "fbs",
    "PBS": "pbs",
    "Corp": "corps",
    "Motif": "motif",
    "Vérif": "verification",
}

# A table-of-contents entry as pandoc renders it: the heading, then its page number as a
# link. Word writes the entry's own hyperlink either as a w:hyperlink, which pandoc wraps
# around the whole entry, or as a HYPERLINK field, which pandoc drops; and it escapes the
# dot of a leading number so that the line does not read as a list item.
RE_TOC_ENTRY = re.compile(
    r"^\[?(?:(\d+(?:\.\d+)*)\\?\.\s+)?(.+?)\s+\[\d+\]\(#[^)]*\)(?:\]\(#[^)]*\))?$"
)
RE_ANCHOR = re.compile(r'<span id="[^"]*" class="anchor"></span>')
RE_CAPTION = re.compile(r"^(Figure|Tableau)\s*(\d+)?\s*[:–—-]?\s*(.*)$")
RE_IMG = re.compile(r"^<img\s+(?P<attrs>.*?)\s*/?>$", re.DOTALL)
RE_ATTR = re.compile(r'(\w+)="([^"]*)"')
# A revision mark of Word: an insertion, a deletion, a move, a change of properties, or
# the insertion, deletion or merge of a table cell — the requirement tables carry those.
# The word boundary keeps w:delText and w:instrText out.
RE_TRACKED_CHANGE = re.compile(
    r"<w:(?:ins|del|moveFrom|moveTo|cellIns|cellDel|cellMerge|\w+Change)\b"
)
RE_COMMENT_THREAD = re.compile(r"<w15:commentEx\b[^>]*>")
PAIR = 2
"""A requirement table has two columns: the label, and the value."""

Requirement = dict[str, str]
FigureEntry = dict[str, str]


class BuildNotes:
    """Keeps what calls for a decision apart from what is mere traceability."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.warnings: list[str] = []
        self.traces: list[str] = []
        self.verbose = verbose

    def warn(self, message: str, level: str = "warning") -> None:
        """Note a message: a warning, or ``info`` for mere traceability."""
        (self.traces if level == "info" else self.warnings).append(message)

    def report(self) -> None:
        """Print the warnings, and the traces when asked to."""
        for message in self.warnings:
            print(f"  ! {message}", file=sys.stderr)
        if self.verbose:
            for message in self.traces:
                print(f"  - {message}", file=sys.stderr)
        elif self.traces:
            print(
                f"  - {len(self.traces)} traceability message(s) (run again with --verbose)",
                file=sys.stderr,
            )


# --------------------------------------------------------------------------- #
# Step 1: pandoc extraction
# --------------------------------------------------------------------------- #


def pending_review_marks(docx: Path) -> list[str]:
    """Return what the Word document still holds under review, one message per kind.

    Pandoc accepts every tracked change silently and drops the comments: a
    projection built from a document under review would present as adopted what
    its author has not accepted yet. Each message is a warning, so that --strict
    refuses to publish until the changes are accepted or rejected and the comment
    threads resolved in Word. A thread is a comment without a parent; Word marks
    it done in commentsExtended.xml, and a document that has comments but no such
    part has them all open.
    """
    with zipfile.ZipFile(docx) as archive:
        names = set(archive.namelist())

        def part(name: str) -> str:
            return archive.read(name).decode("utf-8") if name in names else ""

        document = part("word/document.xml")
        comments = part("word/comments.xml")
        extended = part("word/commentsExtended.xml")
    messages: list[str] = []
    changes = len(RE_TRACKED_CHANGE.findall(document))
    if changes:
        messages.append(
            f"{changes} tracked change(s) pending in the Word document: accept or reject "
            "them in Word before publishing — pandoc accepts them all silently"
        )
    if extended:
        threads = [
            mark.group(0)
            for mark in RE_COMMENT_THREAD.finditer(extended)
            if "w15:paraIdParent" not in mark.group(0)
        ]
        open_threads = sum('w15:done="1"' not in thread for thread in threads)
    else:
        open_threads = comments.count("<w:comment ")
    if open_threads:
        messages.append(
            f"{open_threads} open comment thread(s) in the Word document: resolve them "
            "in Word before publishing — pandoc drops the comments"
        )
    return messages


def unwrap_simple_fields(docx: Path, target: Path) -> int:
    """Copy the document with every w:fldSimple unwrapped, its cached result kept.

    Word writes an updated field in one of two shapes: a complex field — begin,
    instrText, separate, result, end — or a single w:fldSimple that nests its
    result. Pandoc drops the second shape whole, which silently strips the number
    from every figure and table caption; updating the fields in Word (Ctrl+A, F9)
    is precisely what produces that shape. Unwrapping keeps the number and changes
    nothing else, and the source document is never touched.
    """
    with zipfile.ZipFile(docx) as archive:
        names = archive.namelist()
        parts = {name: archive.read(name) for name in names}
    xml = parts["word/document.xml"].decode("utf-8")
    count = xml.count("<w:fldSimple")
    xml = re.sub(r"<w:fldSimple[^>]*>", "", xml).replace("</w:fldSimple>", "")
    parts["word/document.xml"] = xml.encode("utf-8")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, parts[name])
    return count


def extract_docx(docx: Path, media_folder: Path) -> str:
    """Return the Word document as GitHub Markdown, its media extracted to a folder."""
    result = subprocess.run(
        ["pandoc", str(docx), "-t", "gfm", "--wrap=none", f"--extract-media={media_folder}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# --------------------------------------------------------------------------- #
# Step 2: table of contents, anchors, heading numbers
# --------------------------------------------------------------------------- #


def normalise(heading: str) -> str:
    """Return a heading as the table of contents and the figure entries compare it."""
    heading = heading.replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", heading).strip().rstrip(":").lower()


def read_table_of_contents(lines: list[str]) -> tuple[dict[str, str], set[str]]:
    """Return the section numbers as Word froze them, indexed by normalised heading.

    Only used to spot unnumbered headings and to detect a stale Word table of
    contents; the numbering actually emitted is recomputed from the structure.
    """
    numbers: dict[str, str] = {}
    unnumbered: set[str] = set()
    for line in lines:
        entry = RE_TOC_ENTRY.match(line.strip())
        if not entry:
            continue
        number, heading = entry.group(1), normalise(entry.group(2))
        if heading.startswith(("figure ", "tableau ")):
            continue
        if number:
            numbers.setdefault(heading, number)
        else:
            unnumbered.add(heading)
    return numbers, unnumbered


def drop_table_of_contents(lines: list[str]) -> list[str]:
    """Remove the entries and their own headings: an agent reads the headings themselves."""
    own_headings = {
        "sommaire",
        "liste des figures",
        "liste des tables",
        "liste des tableaux",
        "table des matières",
    }
    return [
        line
        for line in lines
        if not RE_TOC_ENTRY.match(line.strip()) and normalise(line.strip()) not in own_headings
    ]


def number_headings(
    lines: list[str], word_numbers: dict[str, str], unnumbered: set[str], notes: BuildNotes
) -> list[str]:
    """Prefix every heading with its section number, recomputed from the structure."""
    counters: list[int] = []
    output: list[str] = []
    for line in lines:
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not heading:
            output.append(line)
            continue
        level, title = len(heading.group(1)), heading.group(2).strip()
        key = normalise(title)
        if key in unnumbered:
            output.append(f"{'#' * level} {title}")
            continue
        del counters[level:]
        while len(counters) < level:
            counters.append(0)
        counters[level - 1] += 1
        number = ".".join(str(c) for c in counters)
        expected = word_numbers.get(key)
        if expected and expected != number:
            notes.warn(
                f'stale Word table of contents: "{title}" is numbered {expected} there, '
                f"the document structure gives {number}"
            )
        output.append(f"{'#' * level} {number}. {title}")
    return output


def current_section(lines: list[str], index: int) -> str:
    """Return the number of the section a line belongs to."""
    for line in reversed(lines[:index]):
        heading = re.match(r"^#{1,6}\s+(\d+(?:\.\d+)*)\.", line)
        if heading:
            return heading.group(1)
    return ""


# --------------------------------------------------------------------------- #
# Step 3: figures -> Mermaid
# --------------------------------------------------------------------------- #


def load_figure_config(path: Path) -> list[FigureEntry]:
    """Return the entries of figures.toml: which caption takes which Mermaid source."""
    if not path.exists():
        return []
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("figure", [])
    return cast("list[FigureEntry]", entries)


@dataclass(frozen=True, slots=True)
class _Figures:
    """What every figure of the document is converted with."""

    drawio: Path
    pages: dict[str, drawio2mermaid.Element]
    images_folder: Path
    notes: BuildNotes


def _mermaid_of(
    caption: str, entry: FigureEntry | None, figures: _Figures
) -> tuple[str | None, str]:
    """Return the Mermaid source of a figure, and where it comes from.

    The source is never read from the Word document: an alt text is one line of
    text that Word rewrites at will, and a diagram does not survive it. It lives
    in the repository, as a Mermaid file or as a page of the draw.io file, and
    tools/figures.toml says which one a caption takes.
    """
    if entry and entry.get("source"):
        path = ROOT / entry["source"]
        if path.exists():
            return path.read_text(encoding="utf-8"), entry["source"]
        figures.notes.warn(f'{caption}: Mermaid source "{entry["source"]}" not found')
    elif entry and entry.get("page") in figures.pages:

        def warn(message: str, level: str = "warning") -> None:
            figures.notes.warn(f"{caption}: {message}", level)

        page = entry["page"]
        converted = drawio2mermaid.convert(figures.pages[page], entry.get("direction", "LR"), warn)
        return converted, f"{figures.drawio.name}, page « {page} »"
    elif entry:
        figures.notes.warn(f'{caption}: draw.io page "{entry.get("page")}" not found')
    return None, ""


def _figure(
    mermaid: str | None, origin: str, caption: str, attributes: dict[str, str], figures: _Figures
) -> list[str]:
    """Return the lines of a figure: its Mermaid block, or the image kept as it is."""
    if mermaid is not None:
        return [
            f"<!-- source : {origin} — régénéré par tools/build.py -->",
            "",
            "```mermaid",
            mermaid.rstrip("\n"),
            "```",
        ]
    if not caption:
        figures.notes.warn(
            "figure with no usable caption: a draw.io page is matched by the "
            "caption, so no match can be made. The image is kept as it is."
        )
    else:
        figures.notes.warn(
            f"{caption}: no Mermaid source (no matching entry in tools/figures.toml) "
            "— the image is kept as it is"
        )
    return keep_image(attributes, caption, figures.images_folder)


def convert_figures(
    lines: list[str],
    drawio: Path,
    config: list[FigureEntry],
    images_folder: Path,
    notes: BuildNotes,
) -> list[str]:
    """Replace every <img> with a Mermaid block, or keep the image when there is none."""
    pages = drawio2mermaid.load_pages(drawio) if drawio.exists() else {}
    figures = _Figures(drawio, pages, images_folder, notes)
    output: list[str] = []
    i = 0
    while i < len(lines):
        image = RE_IMG.match(lines[i].strip())
        if not image:
            output.append(lines[i])
            i += 1
            continue
        attributes = dict(RE_ATTR.findall(image.group("attrs")))
        caption, next_index = read_caption(lines, i + 1)
        if caption and not re.search(r"\d", caption.split("—")[0]):
            notes.warn(
                f'"{caption}": caption without a number in Word — a review finding will '
                "only be able to name this figure by its title"
            )
        entry = find_config_entry(config, caption)
        mermaid, origin = _mermaid_of(caption, entry, figures)
        output.extend(_figure(mermaid, origin, caption, attributes, figures))
        if caption:
            output.append("")
            output.append(f"*{caption}*")
        i = next_index
    return output


def read_caption(lines: list[str], start: int) -> tuple[str, int]:
    """Return the "Figure n …" / "Tableau n …" caption after an image, and the next index."""
    i = start
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        candidate = RE_ANCHOR.sub("", lines[i]).strip()
        caption = RE_CAPTION.match(candidate)
        if caption:
            kind, number, title = caption.groups()
            head = f"{kind} {number}" if number else kind
            return (f"{head} — {title.strip()}" if title.strip() else head), i + 1
    return "", start


def find_config_entry(config: list[FigureEntry], caption: str) -> FigureEntry | None:
    """Return the entry whose caption fragment matches; the longest one wins.

    Several captions may share a prefix ("Arborescence fonctionnelle" and
    "Arborescence fonctionnelle de la planification"): the order of the entries in
    figures.toml must not decide in place of the meaning.
    """
    if not caption:
        return None
    candidates = [e for e in config if normalise(e.get("legende", "")) in normalise(caption)]
    return max(candidates, key=lambda e: len(e.get("legende", "")), default=None)


def keep_image(attributes: dict[str, str], caption: str, images_folder: Path) -> list[str]:
    """Copy an image beside the projection, and return the Markdown that shows it."""
    source = Path(attributes.get("src", ""))
    if not source.exists():
        return [f"<!-- image manquante : {source} -->"]
    images_folder.mkdir(parents=True, exist_ok=True)
    destination = images_folder / source.name
    shutil.copy2(source, destination)
    path = destination.relative_to(ROOT).as_posix()
    return [f"![{caption or source.name}]({path})"]


# --------------------------------------------------------------------------- #
# Step 4: requirement tables -> anchored YAML blocks
# --------------------------------------------------------------------------- #


def cells(line: str) -> list[str]:
    """Return the cells of a Markdown table row."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def unescape_cell(value: str) -> str:
    """Return the value of a requirement cell, without Markdown escapes or whole bold."""
    value = value.strip()
    # A cell entirely in bold in Word arrives as **…**: formatting has no meaning
    # inside a requirement value.
    whole = re.fullmatch(r"\*\*(.+)\*\*", value)
    if whole:
        value = whole.group(1).strip()
    value = re.sub(r"\\(.)", r"\1", value)
    return "" if value in ("", "-") else value


def yaml_scalar(value: str) -> str:
    """Return a value as a double-quoted YAML scalar."""
    if not value:
        return '""'
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def html_tables_to_pipe(lines: list[str]) -> list[str]:
    """Rewrite as Markdown tables the HTML tables that carry a requirement.

    Pandoc produces an HTML table as soon as a cell holds several paragraphs (a
    Motif in two paragraphs, say). Without this step the requirement would escape
    the conversion, the index and the duplicate check.
    """
    text = "\n".join(lines)

    def text_of(cell: str) -> str:
        cell = re.sub(r"</p>\s*<p>", " ", cell)
        cell = re.sub(r"<[^>]+>", "", cell)
        return re.sub(r"\s+", " ", html.unescape(cell)).strip()

    def rewrite(match: re.Match[str]) -> str:
        block = match.group(0)
        pairs: list[list[str]] = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.DOTALL):
            html_cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.DOTALL)
            if len(html_cells) != PAIR:
                return block
            pairs.append([text_of(cell) for cell in html_cells])
        if [key for key, _ in pairs] != list(REQUIREMENT_FIELDS):
            return block
        pipe = [f"| {pairs[0][0]} | {pairs[0][1]} |", "|---|---|"]
        pipe += [f"| {key} | {value.replace('|', '/')} |" for key, value in pairs[1:]]
        return "\n".join(pipe)

    text = re.sub(r"<table>.*?</table>", rewrite, text, flags=re.DOTALL)
    return text.split("\n")


def _duplicates(requirements: list[Requirement], notes: BuildNotes) -> None:
    sections_of: dict[str, list[str]] = {}
    for requirement in requirements:
        sections_of.setdefault(requirement["id"], []).append(requirement["section"])
    for identifier, sections in sections_of.items():
        if len(sections) > 1:
            notes.warn(
                f"identifier {identifier} carried by {len(sections)} requirements "
                f"(sections {', '.join(s or '?' for s in sections)})"
            )


def convert_requirements(
    lines: list[str], notes: BuildNotes
) -> tuple[list[str], list[Requirement]]:
    """Turn requirement tables into YAML blocks carrying their section."""
    output: list[str] = []
    requirements: list[Requirement] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip().startswith("| ID "):
            output.append(lines[i])
            i += 1
            continue

        end = i
        while end < len(lines) and lines[end].strip().startswith("|"):
            end += 1
        body = [row for row in lines[i:end] if not re.match(r"^\|[\s|:-]+\|$", row.strip())]
        pairs = [cells(row) for row in body]
        if any(len(p) != PAIR for p in pairs) or [p[0] for p in pairs] != list(REQUIREMENT_FIELDS):
            output.extend(lines[i:end])
            i = end
            continue

        values = {REQUIREMENT_FIELDS[key]: unescape_cell(value) for key, value in pairs}
        values["section"] = current_section(output, len(output))
        # The example in chapter 1 ("Forme des exigences") is rendered like the
        # others, but counts neither in the total nor in the index.
        if not values["section"].startswith("1."):
            requirements.append(values)

        output.append("```yaml exigence")
        output.append(f"section: {yaml_scalar(values['section'])}")
        output.extend(
            f"{field}: {yaml_scalar(values[field])}" for field in REQUIREMENT_FIELDS.values()
        )
        output.append("```")
        i = end

    _duplicates(requirements, notes)
    return output, requirements


def replace_requirement_index(lines: list[str], requirements: list[Requirement]) -> list[str]:
    """Rewrite "Index des exigences": Word page numbers mean nothing here."""
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+(?:\d+(?:\.\d+)*\.\s+)?Index des exigences\s*$", line):
            start = i
            break
    if start is None:
        return lines

    end = start + 1
    while end < len(lines) and not lines[end].startswith("#"):
        end += 1

    table = ["", "| Exigence | Section | Titre | Flex |", "|---|---|---|---|"]
    table.extend(
        f"| {requirement['id'] or '—'} | {requirement['section'] or '—'} "
        f"| {requirement['titre'] or '—'} | {requirement['flexibilite'] or '—'} |"
        for requirement in sorted(requirements, key=lambda r: (r["id"], r["section"]))
    )
    table.append("")
    return lines[: start + 1] + table + lines[end:]


# --------------------------------------------------------------------------- #
# Step 5: assembly
# --------------------------------------------------------------------------- #


def tidy(lines: list[str]) -> list[str]:
    """Remove Word anchors, trailing spaces and repeated blank lines."""
    output: list[str] = []
    blanks = 0
    for raw in lines:
        line = RE_ANCHOR.sub("", raw).rstrip()
        if not line.strip():
            blanks += 1
            if blanks > 1:
                continue
        else:
            blanks = 0
        output.append(line)
    while output and not output[0].strip():
        output.pop(0)
    return output


def front_matter(docx: Path, drawio: Path, requirement_count: int) -> list[str]:
    """Return the head of the projection: its front matter, the warning, the logo."""
    return [
        "---",
        "genere_par: tools/build.py",
        f"source_texte: {docx.name}",
        f"source_diagrammes: {drawio.name}",
        f"nombre_exigences: {requirement_count}",
        "---",
        "",
        "<!-- FICHIER GÉNÉRÉ — NE PAS ÉDITER.",
        f"     Les sources sont {docx.name} (Word), {drawio.name} (draw.io)",
        "     et les fichiers Mermaid de figures/.",
        "     Toute correction se fait dans ces fichiers, puis ./build.sh. -->",
        "",
        # The logo is not in the Word document: it belongs to the repository, and the
        # projection is where a reader meets the product. The path is relative to this
        # file, so it follows branches and forks.
        '<p align="center">',
        "  <picture>",
        (
            '    <source media="(prefers-color-scheme: dark)" '
            'srcset="../assets/waterfall_logo-dark.svg">'
        ),
        '    <img src="../assets/waterfall_logo.svg" alt="Waterfall" width="280">',
        "  </picture>",
        "</p>",
        "",
    ]


def _mermaid_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] | None = None
    for line in lines:
        if current is None and line.strip() == "```mermaid":
            current = []
        elif current is not None and line.strip() == "```":
            blocks.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(line)
    return blocks


def validate_mermaid(lines: list[str], notes: BuildNotes) -> None:
    """Compile every Mermaid block produced, so the build fails before the agent does."""
    if shutil.which("mmdc") is None:
        notes.warn("mmdc missing: Mermaid diagrams are not validated", "info")
        return
    blocks = _mermaid_blocks(lines)
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        for n, block in enumerate(blocks, 1):
            source = folder / f"d{n}.mmd"
            source.write_text(block + "\n", encoding="utf-8")
            result = subprocess.run(
                ["mmdc", "-i", str(source), "-o", str(folder / f"d{n}.svg")],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                first_lines = (result.stderr or result.stdout).strip().split("\n")
                notes.warn(
                    f"Mermaid diagram no. {n} does not compile: " + " ".join(first_lines[:3])
                )
    notes.warn(f"{len(blocks)} Mermaid diagram(s) validated by mmdc", "info")


def main() -> int:
    """Regenerate the projection; with --strict, fail on any warning."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", default="stb-waterfall.docx")
    parser.add_argument("--drawio", default="waterfall.visuels.drawio")
    parser.add_argument("--output", default="waterfall-spec.md")
    parser.add_argument("--config", default="tools/figures.toml")
    parser.add_argument("--strict", action="store_true", help="fail if any warning is emitted")
    parser.add_argument(
        "--verbose", action="store_true", help="also print the traceability messages"
    )
    arguments = parser.parse_args()

    docx = ROOT / arguments.docx
    drawio = ROOT / arguments.drawio
    output_path = ROOT / arguments.output
    if not docx.exists():
        print(f"Word source not found: {docx}", file=sys.stderr)
        return 1

    notes = BuildNotes(verbose=arguments.verbose)
    config = load_figure_config(ROOT / arguments.config)
    marks = pending_review_marks(docx)
    for message in marks:
        notes.warn(message)
    if marks and arguments.strict:
        # The previous projection stays as it is: it was built from an accepted document,
        # and the one pandoc would build now would present as adopted what is not yet.
        notes.report()
        print(
            f"{arguments.output} left untouched: the Word document is still under review",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as temporary:
        readable = Path(temporary) / docx.name
        unwrapped = unwrap_simple_fields(docx, readable)
        if unwrapped:
            notes.warn(
                f"{unwrapped} simple field(s) unwrapped so that pandoc keeps "
                "their result — caption numbers, mostly",
                "info",
            )
        raw = extract_docx(readable, Path(temporary) / "media")
        lines = raw.replace("\r\n", "\n").split("\n")

        word_numbers, unnumbered = read_table_of_contents(lines)
        lines = drop_table_of_contents(lines)
        lines = [RE_ANCHOR.sub("", line) for line in lines]
        lines = number_headings(lines, word_numbers, unnumbered, notes)
        lines = convert_figures(lines, drawio, config, ROOT / "images", notes)

    lines = html_tables_to_pipe(lines)
    lines, requirements = convert_requirements(lines, notes)
    lines = replace_requirement_index(lines, requirements)
    lines = tidy(lines)
    validate_mermaid(lines, notes)

    output_path.write_text(
        "\n".join(front_matter(docx, drawio, len(requirements)) + lines) + "\n",
        encoding="utf-8",
    )
    print(f"{output_path.relative_to(ROOT)} — {len(lines)} lines, {len(requirements)} requirements")
    notes.report()
    if notes.warnings and arguments.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
