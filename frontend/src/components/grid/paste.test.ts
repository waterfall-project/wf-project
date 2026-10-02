// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { readBlock } from "./paste";

describe("the block a spreadsheet copies", () => {
  it("is read as rows of cells, separated by tabs and line ends, the last one closing it", () => {
    expect(readBlock("Heures\t1\nMatériel\t24\n")).toEqual([
      ["Heures", "1"],
      ["Matériel", "24"],
    ]);
    expect(readBlock("a\tb\r\nc\td\r\n")).toEqual([
      ["a", "b"],
      ["c", "d"],
    ]);
    expect(readBlock("a\rb")).toEqual([["a"], ["b"]]);
  });

  it("keeps the empty cells, at the end of a row and on a row left blank", () => {
    expect(readBlock("Matériel\t\t24\t\n\nfin")).toEqual([
      ["Matériel", "", "24", ""],
      [""],
      ["fin"],
    ]);
  });

  it("reads a quoted cell, its tabs, line ends and doubled quotes within, as one", () => {
    expect(readBlock('"Câble ""5 m""\tgainé\nrouge"\t3\n')).toEqual([
      ['Câble "5 m"\tgainé\nrouge', "3"],
    ]);
  });

  it("keeps as it is a cell whose quotes do not enclose it", () => {
    expect(readBlock('Tube 5"\t"a"b\n')).toEqual([['Tube 5"', '"a"b']]);
  });

  it("reads a single cell copied alone", () => {
    expect(readBlock("Heures de câblage")).toEqual([["Heures de câblage"]]);
  });
});
