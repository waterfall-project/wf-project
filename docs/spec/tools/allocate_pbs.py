# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# -*- coding: utf-8 -*-
"""Write the PBS field of every requirement into the Word document, replacing "TBD".

Every field is allocated today; the tool serves again when a requirement arrives with
"TBD" in its PBS field. It keeps a copy of the document beside it before writing.
"""

import re
import shutil
import zipfile
from pathlib import Path

import pbs

DOCX = Path(__file__).resolve().parent.parent / "stb-waterfall.docx"
RE_TABLE = re.compile(r"<w:tbl>.*?</w:tbl>", re.DOTALL)
RE_ROW = re.compile(r"<w:tr\b.*?</w:tr>", re.DOTALL)
RE_CELL = re.compile(r"<w:tc>.*?</w:tc>", re.DOTALL)
RE_TEXT = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.DOTALL)
RE_IDENTIFIER = re.compile(r"WF-[A-Z]+-\d{4}-[A-Z#]")
TO_ALLOCATE = "TBD"
FIELDS_PER_ROW = 2


def text_of(xml: str) -> str:
    """Return the visible text of a piece of WordprocessingML."""
    return "".join(RE_TEXT.findall(xml)).replace("\xa0", " ").strip()


def _fields(table: str) -> dict[str, tuple[re.Match[str], re.Match[str], str]]:
    fields: dict[str, tuple[re.Match[str], re.Match[str], str]] = {}
    for row in RE_ROW.finditer(table):
        cells = list(RE_CELL.finditer(row.group(0)))
        if len(cells) >= FIELDS_PER_ROW:
            fields[text_of(cells[0].group(0))] = (row, cells[1], text_of(cells[1].group(0)))
    return fields


def update_table(table: str, log: list[str]) -> str | None:
    """Return the table with "TBD" replaced on its PBS row; None when there is nothing to do."""
    fields = _fields(table)
    if "ID" not in fields or "PBS" not in fields:
        return None
    identifier = fields["ID"][2]
    if not RE_IDENTIFIER.fullmatch(identifier):
        log.append(f"unexpected identifier: {identifier!r}")
        return None
    row, cell, current = fields["PBS"]
    if current != TO_ALLOCATE:
        return None
    wanted = pbs.value(identifier)
    cell_xml = cell.group(0)
    runs = len(RE_TEXT.findall(cell_xml))
    if runs != 1:
        log.append(f"{identifier}: {runs} runs in the PBS cell, left alone")
        return None
    new_cell = cell_xml.replace(f">{TO_ALLOCATE}</w:t>", f">{wanted}</w:t>", 1)
    # `cell` offsets are relative to the row, `row` offsets to the table.
    row_xml = row.group(0)
    new_row = row_xml[: cell.start()] + new_cell + row_xml[cell.end() :]
    log.append(f"{identifier} -> {wanted}")
    return table[: row.start()] + new_row + table[row.end() :]


def allocate(xml: str, log: list[str]) -> str:
    """Return the document body with every PBS field to allocate filled in."""
    pieces: list[str] = []
    end = 0
    for table in RE_TABLE.finditer(xml):
        updated = update_table(table.group(0), log)
        if updated is not None:
            pieces.append(xml[end : table.start()])
            pieces.append(updated)
            end = table.end()
    pieces.append(xml[end:])
    return "".join(pieces)


def main(docx: Path = DOCX) -> list[str]:
    """Allocate the PBS fields of the Word document, and return what was written."""
    shutil.copy2(docx, docx.with_name(docx.name + ".before-pbs"))
    with zipfile.ZipFile(docx) as archive:
        names = archive.namelist()
        parts = {name: archive.read(name) for name in names}
    log: list[str] = []
    parts["word/document.xml"] = allocate(parts["word/document.xml"].decode("utf-8"), log).encode(
        "utf-8"
    )
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, parts[name])
    written = [line for line in log if "->" in line]
    print(f"{len(written)} requirement(s) updated")
    for line in log:
        if "->" not in line:
            print("  !", line)
    return written


if __name__ == "__main__":
    main()
