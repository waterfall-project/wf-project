# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Contrôles que LibreOffice ne fait pas : totaux de tableau déclarés, formules circulaires."""
import re, sys, zipfile
from lxml import etree
from openpyxl.utils.cell import range_boundaries, coordinate_from_string, column_index_from_string

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
z = zipfile.ZipFile(sys.argv[1])
wb = etree.fromstring(z.read("xl/workbook.xml"))
rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
target = {r.get("Id"): r.get("Target") for r in rels}
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
problems = 0
for sh in wb.find("m:sheets", NS):
    name, path = sh.get("name"), "xl/" + target[sh.get(R)]
    ws = etree.fromstring(z.read(path))
    cells = {c.get("r"): c for c in ws.iter("{%s}c" % NS["m"])}
    # tables of the sheet
    srels_path = path.replace("worksheets/", "worksheets/_rels/") + ".rels"
    tables = []
    if srels_path in z.namelist():
        for r in etree.fromstring(z.read(srels_path)):
            if r.get("Target").startswith("../tables/"):
                tables.append("xl/tables/" + r.get("Target").split("/")[-1])
    for t in tables:
        tx = etree.fromstring(z.read(t))
        c1, r1, c2, r2 = range_boundaries(tx.get("ref"))
        cols = tx.find("m:tableColumns", NS)
        if tx.get("totalsRowCount") == "1":
            for i, col in enumerate(cols):
                from openpyxl.utils import get_column_letter
                ref = f"{get_column_letter(c1 + i)}{r2}"
                c = cells.get(ref)
                has_f = c is not None and c.find("m:f", NS) is not None
                declared = col.get("totalsRowFunction")
                if has_f and not declared:
                    print(f"{name}!{ref}: formule de total non déclarée ({t})"); problems += 1
                if declared and not has_f:
                    print(f"{name}!{ref}: total déclaré sans formule ({t})"); problems += 1
        # header names
        for i, col in enumerate(cols):
            from openpyxl.utils import get_column_letter
            ref = f"{get_column_letter(c1 + i)}{r1}"
    # circularity: same-sheet A1 ranges containing the cell itself
    for ref, c in cells.items():
        f = c.find("m:f", NS)
        if f is None or not f.text:
            continue
        col, row = coordinate_from_string(ref)
        ci = column_index_from_string(col)
        text = re.sub(r"'[^']*'![$A-Z0-9:]+|[A-Za-z_]+!\$?[A-Z]+\$?\d+(:\$?[A-Z]+\$?\d+)?", "", f.text)
        for m in re.finditer(r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?", text):
            a, b = column_index_from_string(m.group(1)), int(m.group(2))
            cc, d = (column_index_from_string(m.group(3)), int(m.group(4))) if m.group(3) else (a, b)
            if a <= ci <= cc and b <= row <= d:
                print(f"{name}!{ref}: lit sa propre cellule : {f.text}"); problems += 1
print("problèmes :", problems)
