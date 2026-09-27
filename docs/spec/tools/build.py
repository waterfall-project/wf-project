#!/usr/bin/env python3
"""Project the Word + draw.io specification into Markdown an agent can read.

Word and draw.io remain the sources; this script regenerates `waterfall-spec.md`,
which must never be edited by hand. The Markdown it produces adds two things the
.docx does not carry and reviews cannot do without: the section number on every
heading, and an explicit anchor — section plus identifier — on every requirement.

The document is written in French; this program and its console output are in
English, and every literal that lands in the document is kept verbatim.
"""

import argparse
import html
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import drawio2mermaid  # noqa: E402

# Word table label -> field name emitted in the projection. Both sides are part of
# the document: the left as Word writes it, the right as agents read it.
REQUIREMENT_FIELDS = {
    "ID": "id",
    "Titre": "titre",
    "Flex": "flexibilite",
    "FBS": "fbs",
    "PBS": "pbs",
    "Corp": "corps",
    "Motif": "motif",
    "Vérif": "verification",
}

MERMAID_KEYWORDS = (
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
    "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie", "mindmap",
    "timeline", "quadrantChart", "requirementDiagram", "C4Context",
)

RE_TOC_ENTRY = re.compile(
    r"^\[(?:(\d+(?:\.\d+)*)\.\s+)?(.+?)\s+\[\d+\]\(#[^)]*\)\]\(#[^)]*\)$"
)
RE_ANCHOR = re.compile(r'<span id="[^"]*" class="anchor"></span>')
RE_CAPTION = re.compile(r"^(Figure|Tableau)\s*(\d+)?\s*[:–—-]?\s*(.*)$")
RE_IMG = re.compile(r'^<img\s+(?P<attrs>.*?)\s*/?>$', re.S)
RE_ATTR = re.compile(r'(\w+)="([^"]*)"')
RE_ARROW = re.compile(r"(-{2,3}>|={2,3}>|-\.->|-{3,}|={3,}|--[ox])")


class BuildLog:
    """Keeps what calls for a decision apart from what is mere traceability."""

    def __init__(self, verbose=False):
        self.warnings = []
        self.traces = []
        self.verbose = verbose

    def warn(self, message, level="warning"):
        (self.traces if level == "info" else self.warnings).append(message)

    def report(self):
        for message in self.warnings:
            print(f"  ! {message}", file=sys.stderr)
        if self.verbose:
            for message in self.traces:
                print(f"  - {message}", file=sys.stderr)
        elif self.traces:
            print(f"  - {len(self.traces)} traceability message(s) "
                  f"(run again with --verbose)", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Step 1: pandoc extraction
# --------------------------------------------------------------------------- #

def unwrap_simple_fields(docx, target):
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


def extract_docx(docx, media_folder):
    result = subprocess.run(
        ["pandoc", str(docx), "-t", "gfm", "--wrap=none",
         f"--extract-media={media_folder}"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


# --------------------------------------------------------------------------- #
# Step 2: table of contents, anchors, heading numbers
# --------------------------------------------------------------------------- #

def normalise(heading):
    heading = heading.replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", heading).strip().rstrip(":").lower()


def read_table_of_contents(lines):
    """Section numbers as Word froze them, indexed by normalised heading.

    Only used to spot unnumbered headings and to detect a stale Word table of
    contents; the numbering actually emitted is recomputed from the structure.
    """
    numbers, unnumbered = {}, set()
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


def drop_table_of_contents(lines):
    """Remove the entries and their own headings: an agent reads the headings themselves."""
    own_headings = {"sommaire", "liste des figures", "liste des tables",
                    "liste des tableaux", "table des matières"}
    kept = []
    for line in lines:
        stripped = line.strip()
        if RE_TOC_ENTRY.match(stripped):
            continue
        if normalise(stripped) in own_headings:
            continue
        kept.append(line)
    return kept


def number_headings(lines, word_numbers, unnumbered, log):
    """Prefix every heading with its section number, recomputed from the structure."""
    counters, output = [], []
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
            log.warn(
                f'stale Word table of contents: "{title}" is numbered {expected} there, '
                f"the document structure gives {number}"
            )
        output.append(f"{'#' * level} {number}. {title}")
    return output


def current_section(lines, index):
    for line in reversed(lines[:index]):
        heading = re.match(r"^#{1,6}\s+(\d+(?:\.\d+)*)\.", line)
        if heading:
            return heading.group(1)
    return ""


# --------------------------------------------------------------------------- #
# Step 3: figures -> Mermaid
# --------------------------------------------------------------------------- #

def resegment_mermaid(source):
    """Restore a Mermaid source written on a single line (a Word alt text).

    Word stores the diagram without line breaks; Mermaid wants one statement per
    line. We resegment while respecting quotes and brackets.
    """
    tokens, current, depth, in_quotes = [], [], 0, False
    for character in source:
        if character == '"':
            in_quotes = not in_quotes
        elif not in_quotes:
            if character in "[{(":
                depth += 1
            elif character in "]})":
                depth -= 1
            elif character.isspace() and depth == 0:
                if current:
                    tokens.append("".join(current))
                    current = []
                continue
        current.append(character)
    if current:
        tokens.append("".join(current))

    if not tokens:
        return ""

    header, tokens = tokens[0], tokens[1:]
    if header in MERMAID_KEYWORDS and tokens and re.fullmatch(r"[A-Z]{2}", tokens[0]):
        header, tokens = f"{header} {tokens[0]}", tokens[1:]

    if header.startswith("classDiagram"):
        return resegment_class_diagram(header, tokens)

    fixed_arity = {"classDef": 3, "class": 3, "style": 3, "linkStyle": 3, "direction": 2}
    statements, i = [], 0
    while i < len(tokens):
        token = tokens[i]
        if token in fixed_arity:
            n = fixed_arity[token]
            statements.append(" ".join(tokens[i:i + n]))
            i += n
            continue
        if token in ("subgraph", "end"):
            statements.append(token if token == "end" else " ".join(tokens[i:i + 2]))
            i += 1 if token == "end" else 2
            continue
        statement = [token]
        i += 1
        while i < len(tokens) and RE_ARROW.search(tokens[i]):
            statement.append(tokens[i])
            i += 1
            if i < len(tokens):
                statement.append(tokens[i])
                i += 1
        # Transition label in the stateDiagram manner ("A --> B : text"): it runs
        # until the next token followed by an arrow, which opens the next statement.
        if i < len(tokens) and tokens[i].startswith(":"):
            while i < len(tokens):
                next_is_arrow = i + 1 < len(tokens) and RE_ARROW.search(tokens[i + 1])
                if tokens[i] in fixed_arity or (next_is_arrow and statement[-1] != ":"):
                    break
                statement.append(tokens[i])
                i += 1
        statements.append(" ".join(statement))

    return "\n".join([header] + [f"    {s}" for s in statements]) + "\n"


RE_CLASS_ARROW = re.compile(
    r"^(<\|--|--\|>|\*--|--\*|o--|--o|<--|-->|--|<\|\.\.|\.\.\|>|<\.\.|\.\.>|\.\.)$"
)


def resegment_class_diagram(header, tokens):
    """Resegment a classDiagram written on a single line.

    A relation reads `A "1" --> "*" B : label`, with optional cardinalities in
    quotes. Its label runs until the beginning of the next statement: an identifier
    followed by an arrow, possibly preceded by a cardinality, or a keyword.
    """
    arity = {"class": 2, "direction": 2, "style": 3, "classDef": 3, "cssClass": 3}
    arrow = lambda j: j < len(tokens) and RE_CLASS_ARROW.match(tokens[j]) is not None
    quoted = lambda j: j < len(tokens) and tokens[j].startswith('"')

    def starts_a_relation(j):
        return (not quoted(j) and not arrow(j) and tokens[j] != ":"
                and (arrow(j + 1) or (quoted(j + 1) and arrow(j + 2))))

    statements, i = [], 0
    while i < len(tokens):
        if tokens[i] in arity:
            n = arity[tokens[i]]
            statements.append(" ".join(tokens[i:i + n]))
            i += n
            continue
        statement = [tokens[i]]
        i += 1
        # Cardinality, arrow, cardinality, target.
        while i < len(tokens) and (quoted(i) or arrow(i)) and len(statement) < 4:
            statement.append(tokens[i])
            i += 1
        if len(statement) > 1 and i < len(tokens):
            statement.append(tokens[i])
            i += 1
        if i < len(tokens) and tokens[i].startswith(":"):
            while i < len(tokens) and tokens[i] not in arity and not (
                    statement[-1] != ":" and starts_a_relation(i)):
                statement.append(tokens[i])
                i += 1
        statements.append(" ".join(statement))

    return "\n".join([header] + [f"    {s}" for s in statements]) + "\n"


def mermaid_from_alt_text(alt):
    """Return the Mermaid source when the alt text is one, None otherwise."""
    text = html.unescape(alt or "").strip()
    if not text:
        return None
    first = text.split(None, 1)[0]
    if first not in MERMAID_KEYWORDS:
        return None
    return resegment_mermaid(text)


def load_figure_config(path):
    if not path.exists():
        return []
    return tomllib.loads(path.read_text(encoding="utf-8")).get("figure", [])


def convert_figures(lines, drawio, config, images_folder, log):
    """Replace every <img> with a Mermaid block, or keep the image when there is none."""
    pages = drawio2mermaid.load_pages(drawio) if drawio.exists() else {}
    output, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        image = RE_IMG.match(line)
        if not image:
            output.append(lines[i])
            i += 1
            continue

        attributes = dict(RE_ATTR.findall(image.group("attrs")))
        caption, next_index = read_caption(lines, i + 1)

        if caption and not re.search(r"\d", caption.split("—")[0]):
            log.warn(
                f'"{caption}": caption without a number in Word — a review finding will '
                "only be able to name this figure by its title"
            )
        mermaid = mermaid_from_alt_text(attributes.get("alt"))
        origin = "texte alternatif Word"
        if mermaid is None:
            entry = find_config_entry(config, caption)
            if entry and entry.get("source"):
                # Mermaid source held in the repository: no resegmentation at all, so
                # every kind of diagram is allowed, sequences included.
                path = ROOT / entry["source"]
                if path.exists():
                    mermaid = path.read_text(encoding="utf-8")
                    origin = entry["source"]
                else:
                    log.warn(
                        f'{caption}: Mermaid source "{entry["source"]}" not found'
                    )
            elif entry and entry.get("page") in pages:
                mermaid = drawio2mermaid.convert(
                    pages[entry["page"]],
                    entry.get("direction", "LR"),
                    lambda message, level="warning", name=caption: log.warn(
                        f"{name}: {message}", level
                    ),
                )
                origin = f"{drawio.name}, page « {entry['page']} »"
            elif entry:
                log.warn(
                    f'{caption}: draw.io page "{entry.get("page")}" not found'
                )

        if mermaid is None:
            if not caption:
                log.warn(
                    "figure with no usable caption: a draw.io page is matched by the "
                    "caption, so no match can be made. The image is kept as it is."
                )
            else:
                log.warn(
                    f"{caption}: no Mermaid source (neither an alt text nor a matching "
                    f"entry in tools/figures.toml) — the image is kept as it is"
                )
            output.extend(keep_image(attributes, caption, images_folder))
        else:
            output.append(f"<!-- source : {origin} — régénéré par tools/build.py -->")
            output.append("")
            output.append("```mermaid")
            output.append(mermaid.rstrip("\n"))
            output.append("```")

        if caption:
            output.append("")
            output.append(f"*{caption}*")
        i = next_index
    return output


def read_caption(lines, start):
    """The "Figure n …" / "Tableau n …" caption following the image; returns (caption, next index)."""
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


def find_config_entry(config, caption):
    """The entry whose caption fragment matches; the longest one wins.

    Several captions may share a prefix ("Arborescence fonctionnelle" and
    "Arborescence fonctionnelle de la planification"): the order of the entries in
    figures.toml must not decide in place of the meaning.
    """
    if not caption:
        return None
    candidates = [e for e in config if normalise(e.get("legende", "")) in normalise(caption)]
    return max(candidates, key=lambda e: len(e.get("legende", "")), default=None)


def keep_image(attributes, caption, images_folder):
    source = pathlib.Path(attributes.get("src", ""))
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

def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def unescape_cell(value):
    value = value.strip()
    # A cell entirely in bold in Word arrives as **…**: formatting has no meaning
    # inside a requirement value.
    whole = re.fullmatch(r"\*\*(.+)\*\*", value)
    if whole:
        value = whole.group(1).strip()
    value = re.sub(r"\\(.)", r"\1", value)
    return "" if value in ("", "-") else value


def yaml_scalar(value):
    if not value:
        return '""'
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def html_tables_to_pipe(lines):
    """Rewrite as Markdown tables the HTML tables that carry a requirement.

    Pandoc produces an HTML table as soon as a cell holds several paragraphs (a
    Motif in two paragraphs, say). Without this step the requirement would escape
    the conversion, the index and the duplicate check.
    """
    text = "\n".join(lines)

    def rewrite(match):
        block = match.group(0)
        pairs = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S):
            html_cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
            if len(html_cells) != 2:
                return block
            values = []
            for cell in html_cells:
                cell = re.sub(r"</p>\s*<p>", " ", cell)
                cell = re.sub(r"<[^>]+>", "", cell)
                values.append(re.sub(r"\s+", " ", html.unescape(cell)).strip())
            pairs.append(values)
        if [key for key, _ in pairs] != list(REQUIREMENT_FIELDS):
            return block
        pipe = [f"| {pairs[0][0]} | {pairs[0][1]} |", "|---|---|"]
        pipe += [f"| {key} | {value.replace('|', '/')} |" for key, value in pairs[1:]]
        return "\n".join(pipe)

    text = re.sub(r"<table>.*?</table>", rewrite, text, flags=re.S)
    return text.split("\n")


def convert_requirements(lines, log):
    """Turn requirement tables into YAML blocks carrying their section."""
    output, requirements, i = [], [], 0
    while i < len(lines):
        if not lines[i].strip().startswith("| ID "):
            output.append(lines[i])
            i += 1
            continue

        end = i
        while end < len(lines) and lines[end].strip().startswith("|"):
            end += 1
        body = [l for l in lines[i:end] if not re.match(r"^\|[\s|:-]+\|$", l.strip())]
        pairs = [cells(l) for l in body]
        if any(len(p) != 2 for p in pairs) or [p[0] for p in pairs] != list(REQUIREMENT_FIELDS):
            output.extend(lines[i:end])
            i = end
            continue

        values = {REQUIREMENT_FIELDS[key]: unescape_cell(value) for key, value in pairs}
        values["section"] = current_section(output, len(output))
        # The example in chapter 1 ("Forme des exigences") is rendered like the
        # others, but counts neither in the total nor in the index.
        if not (values["section"] or "").startswith("1."):
            requirements.append(values)

        output.append("```yaml exigence")
        output.append(f"section: {yaml_scalar(values['section'])}")
        for field in REQUIREMENT_FIELDS.values():
            output.append(f"{field}: {yaml_scalar(values[field])}")
        output.append("```")
        i = end

    duplicates = {}
    for requirement in requirements:
        duplicates.setdefault(requirement["id"], []).append(requirement["section"])
    for identifier, sections in duplicates.items():
        if len(sections) > 1:
            log.warn(
                f"identifier {identifier} carried by {len(sections)} requirements "
                f"(sections {', '.join(s or '?' for s in sections)})"
            )
    return output, requirements


def replace_requirement_index(lines, requirements):
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
    for requirement in sorted(requirements, key=lambda r: (r["id"], r["section"])):
        table.append(
            f"| {requirement['id'] or '—'} | {requirement['section'] or '—'} "
            f"| {requirement['titre'] or '—'} | {requirement['flexibilite'] or '—'} |"
        )
    table.append("")
    return lines[:start + 1] + table + lines[end:]


# --------------------------------------------------------------------------- #
# Step 5: assembly
# --------------------------------------------------------------------------- #

def tidy(lines):
    output, blanks = [], 0
    for line in lines:
        line = RE_ANCHOR.sub("", line).rstrip()
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


def front_matter(docx, drawio, requirement_count):
    return [
        "---",
        "genere_par: tools/build.py",
        f"source_texte: {docx.name}",
        f"source_diagrammes: {drawio.name}",
        f"nombre_exigences: {requirement_count}",
        "---",
        "",
        "<!-- FICHIER GÉNÉRÉ — NE PAS ÉDITER.",
        f"     Les sources sont {docx.name} (Word) et {drawio.name} (draw.io).",
        "     Toute correction se fait dans ces fichiers, puis ./build.sh. -->",
        "",
        # The logo is not in the Word document: it belongs to the repository, and the
        # projection is where a reader meets the product. The path is relative to this
        # file, so it follows branches and forks.
        '<p align="center">',
        '  <picture>',
        '    <source media="(prefers-color-scheme: dark)" srcset="../assets/waterfall_logo-dark.svg">',
        '    <img src="../assets/waterfall_logo.svg" alt="Waterfall" width="280">',
        '  </picture>',
        "</p>",
        "",
    ]


def validate_mermaid(lines, log):
    """Compile every Mermaid block produced, so the build fails before the agent does."""
    if shutil.which("mmdc") is None:
        log.warn("mmdc missing: Mermaid diagrams are not validated", "info")
        return
    blocks, current = [], None
    for line in lines:
        if current is None and line.strip() == "```mermaid":
            current = []
        elif current is not None and line.strip() == "```":
            blocks.append("\n".join(current))
            current = None
        elif current is not None:
            current.append(line)

    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        for n, block in enumerate(blocks, 1):
            source = folder / f"d{n}.mmd"
            source.write_text(block + "\n", encoding="utf-8")
            result = subprocess.run(
                ["mmdc", "-i", str(source), "-o", str(folder / f"d{n}.svg")],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                first_lines = (result.stderr or result.stdout).strip().split("\n")
                log.warn(
                    f"Mermaid diagram no. {n} does not compile: "
                    + " ".join(first_lines[:3])
                )
    log.warn(f"{len(blocks)} Mermaid diagram(s) validated by mmdc", "info")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", default="stb-waterfall.docx")
    parser.add_argument("--drawio", default="waterfall.visuels.drawio")
    parser.add_argument("--output", default="waterfall-spec.md")
    parser.add_argument("--config", default="tools/figures.toml")
    parser.add_argument("--strict", action="store_true",
                        help="fail if any warning is emitted")
    parser.add_argument("--verbose", action="store_true",
                        help="also print the traceability messages")
    arguments = parser.parse_args()

    docx = ROOT / arguments.docx
    drawio = ROOT / arguments.drawio
    output_path = ROOT / arguments.output
    if not docx.exists():
        print(f"Word source not found: {docx}", file=sys.stderr)
        return 1

    log = BuildLog(arguments.verbose)
    config = load_figure_config(ROOT / arguments.config)

    with tempfile.TemporaryDirectory() as temporary:
        readable = pathlib.Path(temporary) / docx.name
        unwrapped = unwrap_simple_fields(docx, readable)
        if unwrapped:
            log.warn(f"{unwrapped} simple field(s) unwrapped so that pandoc keeps "
                     "their result — caption numbers, mostly", "info")
        raw = extract_docx(readable, pathlib.Path(temporary) / "media")
        lines = raw.replace("\r\n", "\n").split("\n")

        word_numbers, unnumbered = read_table_of_contents(lines)
        lines = drop_table_of_contents(lines)
        lines = [RE_ANCHOR.sub("", line) for line in lines]
        lines = number_headings(lines, word_numbers, unnumbered, log)
        lines = convert_figures(lines, drawio, config, ROOT / "images", log)

    lines = html_tables_to_pipe(lines)
    lines, requirements = convert_requirements(lines, log)
    lines = replace_requirement_index(lines, requirements)
    lines = tidy(lines)
    validate_mermaid(lines, log)

    output_path.write_text(
        "\n".join(front_matter(docx, drawio, len(requirements)) + lines) + "\n",
        encoding="utf-8",
    )
    print(f"{output_path.relative_to(ROOT)} — {len(lines)} lines, "
          f"{len(requirements)} requirements")
    log.report()
    if log.warnings and arguments.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
