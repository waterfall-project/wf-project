// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A workbook written by hand, for the paths that import a file of a user: the first tab of a zip
 * archive of five parts, its cells inline — texts or numbers — and the parts stored without
 * compression. The frontend holds no library of workbooks, and the service reads this one as it
 * reads the file of the ERP (openpyxl, in values).
 */
import { crc32 } from "node:zlib";

type Cell = string | number | null;

const XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
const SHEETS = "http://schemas.openxmlformats.org/officeDocument/2006";

function escape(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** The name of a column of a tab, from its rank (0 is « A »): the extractions have a few. */
function column(rank: number): string {
  return String.fromCharCode("A".charCodeAt(0) + rank);
}

function sheet(rows: readonly (readonly Cell[])[]): string {
  const lines = rows.map((row, line) => {
    const cells = row.map((cell, rank) => {
      const at = `${column(rank)}${String(line + 1)}`;
      if (cell === null) {
        return "";
      }
      return typeof cell === "number"
        ? `<c r="${at}"><v>${String(cell)}</v></c>`
        : `<c r="${at}" t="inlineStr"><is><t>${escape(cell)}</t></is></c>`;
    });
    return `<row r="${String(line + 1)}">${cells.join("")}</row>`;
  });
  return `${XML}<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${lines.join("")}</sheetData></worksheet>`;
}

/** Pack parts into a zip archive, each stored as it is. */
function zip(parts: readonly (readonly [name: string, content: string])[]): Buffer {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;
  for (const [name, content] of parts) {
    const label = Buffer.from(name);
    const data = Buffer.from(content);
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(label.length, 26);
    locals.push(local, label, data);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(label.length, 28);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, label);
    offset += local.length + label.length + data.length;
  }
  const directory = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(parts.length, 8);
  end.writeUInt16LE(parts.length, 10);
  end.writeUInt32LE(directory.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, directory, end]);
}

/** Write a workbook of one tab, « Extraction »: the rows given, the first being the headers. */
export function workbook(rows: readonly (readonly Cell[])[]): Buffer {
  return zip([
    [
      "[Content_Types].xml",
      `${XML}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`,
    ],
    [
      "_rels/.rels",
      `${XML}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${SHEETS}/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
    ],
    [
      "xl/workbook.xml",
      `${XML}<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="${SHEETS}/relationships"><sheets><sheet name="Extraction" sheetId="1" r:id="rId1"/></sheets></workbook>`,
    ],
    [
      "xl/_rels/workbook.xml.rels",
      `${XML}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${SHEETS}/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`,
    ],
    ["xl/worksheets/sheet1.xml", sheet(rows)],
  ]);
}
