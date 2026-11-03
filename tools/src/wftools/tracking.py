# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Change one line of the tracking table of an epic's issue, under a lock (US-1120).

Usage: ``python -m wftools.tracking --issue N --lot ID [--state S] [--pr P] [--model M]``,
``--issue N --us ID --status S``, or ``--issue N --finding F [--attached A] [--decision D]``.

The body of the issue is read, changed and written again by ``gh`` while the tool holds
``$XDG_RUNTIME_DIR/waterfall-tracking-<issue>.lock`` (``/tmp`` by default): two deliverers that
change two lines of the same table each keep their change, the second reading the body the first
wrote. The tool touches the cell or the line it is asked for and nothing else: the rest of the
body is written back byte for byte. A line it does not find is refused, the body unchanged.

The table « Ordre de réalisation » is read by the names of its columns (« Pas avec » exists in
the epics from EP-19 on only). A story of one lot has the cell « Lot » ``lot unique`` and is named
by its identifier (``US-1080``); the lots of a story of several are named ``US-1120/L2`` and are
the rows from the story's own down to the next story's, the cells ``#``, ``US`` and « Statut »
empty. The table « Constats ouverts » takes a finding added (the title of its issue, whose
``[EP-nn]`` prefix is dropped), changed when it is there, or removed when its issue is closed;
where the section has the sentence « Aucun constat… » and no table, the table replaces it.
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn, cast

from wftools.slots import runtime_directory

ORDER_TITLE = "## Ordre de réalisation"
FINDINGS_TITLE = "## Constats ouverts"
SINGLE_LOT = "lot unique"
TO_DECIDE = "à trancher"
PIPE = re.compile(r"(?<!\\)\|")
HEADING = re.compile(r"#{1,6} ")
LOT_LABEL = re.compile(r"L\d+(?!\w)")
TITLE_PREFIX = re.compile(r"^\[[^\]]*\]\s*")
FINDINGS_COLUMNS = ["Constat", "Rattaché à", "Décision"]


class TrackingError(Exception):
    """A change the tool refuses, or a call of ``gh`` that fails, said to the user."""


def refuse(message: str) -> NoReturn:
    """Refuse the change, saying why."""
    raise TrackingError(message)


def lock_path(environment: Mapping[str, str], issue: int) -> Path:
    """Return the lock file of an issue, in the runtime directory of the workstation."""
    return runtime_directory(environment) / f"waterfall-tracking-{issue}.lock"


@contextmanager
def locked(path: Path) -> Generator[None]:
    """Hold the exclusive lock of an issue, waiting for whoever has it."""
    try:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    except OSError as error:
        message = f"cannot open the lock {path}: {error.strerror}"
        raise TrackingError(message) from error
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def gh(arguments: list[str], stdin: str | None = None) -> str:
    """Run ``gh`` and return its output; a failure is said with what ``gh`` wrote."""
    try:
        result = subprocess.run(
            ["gh", *arguments], input=stdin, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as error:
        message = "gh is not installed or not on the PATH"
        raise TrackingError(message) from error
    if result.returncode != 0:
        refuse(f"gh {' '.join(arguments[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def answer(arguments: list[str], *keys: str) -> dict[str, object]:
    """Run ``gh`` and return its JSON answer; an unexpected one is refused, not left as a trace."""
    name = " ".join(arguments[:2])
    try:
        data: object = json.loads(gh(arguments))
    except json.JSONDecodeError as error:
        message = f"gh {name} did not answer JSON"
        raise TrackingError(message) from error
    if not isinstance(data, dict):
        refuse(f"gh {name} did not answer an object")
    result = cast("dict[str, object]", data)
    if any(key not in result for key in keys):
        refuse(f"gh {name} answered without {' and '.join(keys)}")
    return result


def read_body(issue: int) -> str:
    """Return the body of an issue, exactly."""
    return str(answer(["issue", "view", str(issue), "--json", "body"], "body")["body"])


def write_body(issue: int, body: str) -> None:
    """Replace the body of an issue."""
    gh(["issue", "edit", str(issue), "--body-file", "-"], stdin=body)


def read_finding(number: int) -> tuple[str, bool]:
    """Return the title of the issue of a finding, and whether it is closed."""
    data = answer(["issue", "view", str(number), "--json", "title,state"], "title", "state")
    return str(data["title"]), str(data["state"]).upper() == "CLOSED"


def split_ending(line: str) -> tuple[str, str]:
    """Return a line without its line ending, and that ending."""
    text = line.rstrip("\r\n")
    return text, line[len(text) :]


def cells(line: str) -> list[str]:
    """Return the stripped cells of a row of a table."""
    return [cell.strip() for cell in PIPE.split(split_ending(line)[0].strip())[1:-1]]


def escape(value: str) -> str:
    """Return a value as a cell holds it: a pipe is escaped, so it adds no column."""
    return PIPE.sub(r"\\|", value)


def set_cell(line: str, index: int, value: str) -> str:
    """Return the row with one cell replaced; the other cells keep their bytes."""
    text, ending = split_ending(line)
    pieces = PIPE.split(text)
    if index + 1 >= len(pieces) - 1:
        refuse(f"the row is shorter than the header of its table: {text.strip()}")
    pieces[index + 1] = f" {escape(value)} "
    return "|".join(pieces) + ending


def section(lines: list[str], title: str) -> tuple[int, int]:
    """Return the first line after the heading of a section, and the end of the section."""
    for index, line in enumerate(lines):
        if split_ending(line)[0].strip() == title:
            end = next(
                (i for i in range(index + 1, len(lines)) if HEADING.match(lines[i])), len(lines)
            )
            return index + 1, end
    refuse(f"the body has no section « {title[3:]} »")


def table(lines: list[str], start: int, end: int) -> tuple[int, int] | None:
    """Return the first run of rows of a table between two lines, if there is one."""
    first = next((i for i in range(start, end) if lines[i].lstrip().startswith("|")), None)
    if first is None:
        return None
    last = first
    while last < end and lines[last].lstrip().startswith("|"):
        last += 1
    return first, last


def columns(lines: list[str], span: tuple[int, int], names: list[str]) -> dict[str, int]:
    """Return the index of each wanted column, by the header of the table."""
    header = cells(lines[span[0]])
    for name in names:
        if name not in header:
            refuse(f"the table has no column « {name} »")
    return {name: header.index(name) for name in names}


def order_table(lines: list[str]) -> tuple[int, int]:
    """Return the rows of the table « Ordre de réalisation »."""
    start, end = section(lines, ORDER_TITLE)
    span = table(lines, start, end)
    if span is None:
        refuse("the section « Ordre de réalisation » has no table")
    return span


def story_rows(lines: list[str], span: tuple[int, int], story: str) -> list[int]:
    """Return the rows of a story: its own, then the continuation rows below it."""
    us = columns(lines, span, ["US"])["US"]
    rows: list[int] = []
    for index in range(span[0] + 2, span[1]):
        row = cells(lines[index])
        if us >= len(row):
            continue
        if rows:
            if row[us]:
                break
            rows.append(index)
        elif row[us].split(" ")[0] == story:
            rows.append(index)
    if not rows:
        refuse(f"no row for the story {story} in the table « Ordre de réalisation »")
    return rows


def change_lot(lines: list[str], lot: str, changes: dict[str, str]) -> None:
    """Change the cells of the row of a lot."""
    span = order_table(lines)
    story, _, label = lot.partition("/")
    names = columns(lines, span, ["Lot", *changes])
    for index in story_rows(lines, span, story):
        row = cells(lines[index])
        if len(row) <= max(names.values()):
            refuse(f"the row is shorter than the header of its table: {lines[index].strip()}")
        cell = row[names["Lot"]]
        found = LOT_LABEL.match(cell)
        if (label and found and found.group() == label) or (not label and cell == SINGLE_LOT):
            for name, value in changes.items():
                lines[index] = set_cell(lines[index], names[name], value)
            return
    refuse(f"no row for the lot {lot} in the table « Ordre de réalisation »")


def change_story(lines: list[str], story: str, status: str) -> None:
    """Change the status of a story, on its first row."""
    span = order_table(lines)
    names = columns(lines, span, ["Statut"])
    first = story_rows(lines, span, story)[0]
    lines[first] = set_cell(lines[first], names["Statut"], status)


def finding_cell(number: int, title: str) -> str:
    """Return the first cell of a finding: its number, then its title without the epic's prefix."""
    return escape(f"#{number} {TITLE_PREFIX.sub('', title).strip()}")


def emphasize(decision: str) -> str:
    """Return a decision as the table writes it: « à trancher » in bold."""
    return f"**{decision}**" if decision == TO_DECIDE else decision


def finding_row(lines: list[str], span: tuple[int, int], number: int) -> int | None:
    """Return the row of a finding, if the table has it."""
    for index in range(span[0] + 2, span[1]):
        row = cells(lines[index])
        if row and (row[0] == f"#{number}" or row[0].startswith(f"#{number} ")):
            return index
    return None


def add_finding(lines: list[str], span: tuple[int, int] | None, start: int, row: str) -> None:
    """Add a row to the table of findings; with no table, make one where the sentence was."""
    if span is not None:
        columns(lines, span, FINDINGS_COLUMNS)
        ending = split_ending(lines[span[1] - 1])[1]
        if not ending:
            lines[span[1] - 1] += "\n"
        lines.insert(span[1], row + ending)
        return
    row += "\n"
    header = "| Constat | Rattaché à | Décision |\n|---|---|---|\n"
    sentence = next(
        (i for i in range(start, len(lines)) if lines[i].lstrip().startswith("Aucun constat")),
        None,
    )
    if sentence is None:
        lines.insert(start, f"\n{header}{row}")
    else:
        lines[sentence] = f"{header}{row}"


def change_finding(
    lines: list[str],
    number: int,
    finding: tuple[str, bool],
    cells_given: tuple[str | None, str | None],
) -> None:
    """Add a finding, change it where it is, or remove it when its issue is closed."""
    title, closed = finding
    attached, decision = cells_given
    start, end = section(lines, FINDINGS_TITLE)
    span = table(lines, start, end)
    row = None if span is None else finding_row(lines, span, number)
    if closed:
        if row is None:
            refuse(f"no row for the finding #{number} in the table « Constats ouverts »")
        del lines[row]
    elif span is not None and row is not None:
        names = columns(lines, span, FINDINGS_COLUMNS)
        if attached is not None:
            lines[row] = set_cell(lines[row], names["Rattaché à"], attached)
        if decision is not None:
            lines[row] = set_cell(lines[row], names["Décision"], emphasize(decision))
    elif attached is None or decision is None:
        refuse(f"the finding #{number} is not in the table: give ATTACHED and DECISION")
    else:
        new = (
            f"| {finding_cell(number, title)} | {escape(attached)} | "
            f"{escape(emphasize(decision))} |"
        )
        add_finding(lines, span, start, new)


def apply(body: str, options: argparse.Namespace) -> str:
    """Return the body changed as asked."""
    lines = body.splitlines(keepends=True)
    if options.lot:
        changes = {
            name: value
            for name, value in (
                ("État du lot", options.state),
                ("PR", options.pr),
                ("Modèle", options.model),
            )
            if value is not None
        }
        change_lot(lines, options.lot, changes)
    elif options.us:
        change_story(lines, options.us, options.status)
    else:
        change_finding(
            lines, options.finding, options.finding_issue, (options.attached, options.decision)
        )
    return "".join(lines)


def parser() -> argparse.ArgumentParser:
    """Return the parser of the command line."""
    result = argparse.ArgumentParser(
        prog="wftools.tracking", description="Change the tracking table."
    )
    result.add_argument("--issue", type=int, required=True, help="the issue of the epic")
    result.add_argument("--lot", help="a lot: US-1080, or US-1120/L2")
    result.add_argument("--state", help="the cell « État du lot »")
    result.add_argument("--pr", help="the cell « PR »")
    result.add_argument("--model", help="the cell « Modèle »")
    result.add_argument("--us", help="a story: US-1120")
    result.add_argument("--status", help="the cell « Statut » of the story")
    result.add_argument("--finding", type=int, help="the issue of a finding")
    result.add_argument("--attached", help="the cell « Rattaché à »")
    result.add_argument("--decision", help="the cell « Décision »")
    return result


def validate(options: argparse.Namespace) -> None:
    """Refuse a call that does not name exactly one thing to change, and what to change."""
    targets = [name for name in ("lot", "us", "finding") if getattr(options, name) is not None]
    if len(targets) != 1:
        refuse("give exactly one of LOT, US or FINDING")
    if options.lot and options.state is None and options.pr is None and options.model is None:
        refuse("give at least one of STATE, PR or MODEL with LOT")
    if options.us and options.status is None:
        refuse("give STATUS with US")
    for name in ("state", "pr", "model", "status", "attached", "decision"):
        value = getattr(options, name)
        if value is not None and ("\n" in value or "\r" in value):
            refuse(f"{name.upper()} holds a line break: a cell is one line")


def main(arguments: list[str]) -> int:
    """Change the table; return 1 and say why when it cannot."""
    options = parser().parse_args(arguments)
    try:
        validate(options)
        if options.finding is not None:
            # Read before the lock on purpose: the title and the state of the finding's issue
            # do not depend on the body of the epic's issue.
            options.finding_issue = read_finding(options.finding)
        with locked(lock_path(os.environ, options.issue)):
            body = read_body(options.issue)
            changed = apply(body, options)
            if changed != body:
                write_body(options.issue, changed)
    except TrackingError as error:
        print(f"tracking: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
