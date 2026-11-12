// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workbook written by hand (`workbook.ts`), read back from the archive it produces: the paths
 * that import a file hand it to the service, which answers a 4xx the path can only read as a refusal
 * of its import (#2827). Read here as a reader of the format does — the end of the central directory,
 * the entries, their checksums, the parts the format expects, the cells of the tab — it fails on its
 * own, naming what is wrong with the archive.
 *
 * This tests a tool of the harness: it proves no requirement of the specification.
 */
import { crc32 } from "node:zlib";

import { expect, test } from "@playwright/test";

import { workbook } from "./workbook";

/** A part of the archive, as the central directory lists it, with the bytes its local header points to. */
interface Entry {
  readonly name: string;
  readonly method: number;
  readonly crc: number;
  readonly content: Buffer;
}

/** Read the archive as a zip reader does: from the end of the central directory to each part. */
function entries(archive: Buffer): readonly Entry[] {
  const end = archive.length - 22;
  expect(archive.readUInt32LE(end), "signature of the end of the central directory").toBe(
    0x06054b50,
  );
  const count = archive.readUInt16LE(end + 10);
  expect(archive.readUInt16LE(end + 8), "entries of this disk and in all").toBe(count);
  let at = archive.readUInt32LE(end + 16);
  expect(at + archive.readUInt32LE(end + 12), "the directory ends where its end begins").toBe(end);
  const found: Entry[] = [];
  for (let each = 0; each < count; each += 1) {
    expect(archive.readUInt32LE(at), `signature of the entry ${String(each)}`).toBe(0x02014b50);
    const method = archive.readUInt16LE(at + 10);
    const crc = archive.readUInt32LE(at + 16);
    const size = archive.readUInt32LE(at + 24);
    const label = archive.readUInt16LE(at + 28);
    const local = archive.readUInt32LE(at + 42);
    const name = archive.subarray(at + 46, at + 46 + label).toString();
    expect(archive.readUInt32LE(local), `signature of the local header of ${name}`).toBe(
      0x04034b50,
    );
    expect(archive.readUInt16LE(local + 26), `name length of the local header of ${name}`).toBe(
      label,
    );
    expect(archive.subarray(local + 30, local + 30 + label).toString()).toBe(name);
    expect(archive.readUInt32LE(local + 18), `stored size of ${name}`).toBe(size);
    const from = local + 30 + label;
    found.push({ name, method, crc, content: archive.subarray(from, from + size) });
    at += 46 + label;
  }
  return found;
}

const PARTS = [
  "[Content_Types].xml",
  "_rels/.rels",
  "xl/workbook.xml",
  "xl/_rels/workbook.xml.rels",
  "xl/worksheets/sheet1.xml",
];

/** A part of the archive, its text. */
function part(found: readonly Entry[], name: string): string {
  const entry = found.find((each) => each.name === name);
  expect(entry, `the part ${name}`).toBeDefined();
  return entry?.content.toString() ?? "";
}

test("the workbook of the paths is a zip archive of the five parts a reader of xlsx expects, each stored whole and its checksum right", () => {
  const found = entries(workbook([["Poste"], ["FA-1"]]));
  expect(found.map((each) => each.name)).toEqual(PARTS);
  for (const each of found) {
    expect(each.method, `${each.name} stored, not compressed`).toBe(0);
    expect(crc32(each.content), `checksum of ${each.name}`).toBe(each.crc);
  }
});

test("the parts of the workbook name each other: the types, the relation to the workbook, its tab, and the tab itself", () => {
  const found = entries(workbook([["Poste"]]));
  const types = part(found, "[Content_Types].xml");
  expect(types).toContain('PartName="/xl/workbook.xml"');
  expect(types).toContain('PartName="/xl/worksheets/sheet1.xml"');
  expect(part(found, "_rels/.rels")).toContain('Target="xl/workbook.xml"');
  expect(part(found, "xl/workbook.xml")).toContain(
    '<sheet name="Extraction" sheetId="1" r:id="rId1"/>',
  );
  expect(part(found, "xl/_rels/workbook.xml.rels")).toContain('Target="worksheets/sheet1.xml"');
  for (const name of PARTS) {
    expect(part(found, name).startsWith("<?xml"), `${name} is XML`).toBe(true);
  }
});

test("the tab holds the rows given, the first row their headers: numbers as values, texts inline and escaped, a null cell left out", () => {
  const found = entries(
    workbook([
      ["Elément d'OTP", "Montant"],
      ["A&B <1>", 250.5],
      [null, 10],
    ]),
  );
  const sheet = part(found, "xl/worksheets/sheet1.xml");
  expect(sheet).toContain('<row r="1"><c r="A1" t="inlineStr"><is><t>Elément d\'OTP</t></is></c>');
  expect(sheet).toContain('<c r="B1" t="inlineStr"><is><t>Montant</t></is></c></row>');
  expect(sheet).toContain('<c r="A2" t="inlineStr"><is><t>A&amp;B &lt;1&gt;</t></is></c>');
  expect(sheet).toContain('<c r="B2"><v>250.5</v></c>');
  expect(sheet).toContain('<row r="3"><c r="B3"><v>10</v></c></row>');
  expect(sheet).not.toContain("A3");
});
