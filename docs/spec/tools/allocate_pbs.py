# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# -*- coding: utf-8 -*-
"""Write the PBS field of every requirement into the Word document, replacing "TBD"."""
import pathlib, re, shutil, sys, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pbs

DOCX = str(pathlib.Path(__file__).resolve().parent.parent / 'stb-waterfall.docx')
RE_TABLE = re.compile(r'<w:tbl>.*?</w:tbl>', re.S)
RE_ROW = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
RE_CELL = re.compile(r'<w:tc>.*?</w:tc>', re.S)
RE_TEXT = re.compile(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', re.S)


def text_of(xml):
    return ''.join(RE_TEXT.findall(xml)).replace('\xa0', ' ').strip()


def update_table(table, log):
    """Replace "TBD" with the wanted value on the PBS row; None when there is nothing to do."""
    fields = {}
    for row in RE_ROW.finditer(table):
        cells = list(RE_CELL.finditer(row.group(0)))
        if len(cells) >= 2:
            fields[text_of(cells[0].group(0))] = (row, cells[1], text_of(cells[1].group(0)))
    if 'ID' not in fields or 'PBS' not in fields:
        return None
    identifier = fields['ID'][2]
    if not re.fullmatch(r'WF-[A-Z]+-\d{4}-[A-Z#]', identifier):
        log.append(f'unexpected identifier: {identifier!r}')
        return None
    row, cell, current = fields['PBS']
    if current != 'TBD':
        return None
    wanted = pbs.value(identifier)
    cell_xml = cell.group(0)
    if len(RE_TEXT.findall(cell_xml)) != 1:
        log.append(f'{identifier}: {len(RE_TEXT.findall(cell_xml))} runs in the PBS cell, left alone')
        return None
    new_cell = RE_TEXT.sub(
        lambda m: m.group(0).replace('>TBD</w:t>', f'>{wanted}</w:t>'), cell_xml, count=1)
    # `cell` offsets are relative to the row, `row` offsets to the table.
    row_xml = row.group(0)
    new_row = row_xml[:cell.start()] + new_cell + row_xml[cell.end():]
    log.append(f'{identifier} -> {wanted}')
    return table[:row.start()] + new_row + table[row.end():]


def main():
    shutil.copy2(DOCX, DOCX + '.before-pbs')
    with zipfile.ZipFile(DOCX) as archive:
        names = archive.namelist()
        parts = {name: archive.read(name) for name in names}
    xml = parts['word/document.xml'].decode('utf-8')
    log, pieces, end = [], [], 0
    for table in RE_TABLE.finditer(xml):
        updated = update_table(table.group(0), log)
        if updated is not None:
            pieces.append(xml[end:table.start()])
            pieces.append(updated)
            end = table.end()
    pieces.append(xml[end:])
    parts['word/document.xml'] = ''.join(pieces).encode('utf-8')
    with zipfile.ZipFile(DOCX, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, parts[name])
    written = [line for line in log if '->' in line]
    print(f'{len(written)} requirement(s) updated')
    for line in log:
        if '->' not in line:
            print('  !', line)
    return written


if __name__ == '__main__':
    main()
