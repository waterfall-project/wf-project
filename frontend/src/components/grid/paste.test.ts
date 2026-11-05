// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { type NodeList, pasteSpan } from "./nodes";
import { localRefusal, readBlock, widest } from "./paste";
import { PLANNING_GRID } from "./planning";

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

  it("measures the width of a very tall block, which a spread would blow the stack on", () => {
    const tall = Array.from({ length: 200_000 }, (_, index) =>
      index === 137 ? ["a", "b"] : ["a"],
    );
    expect(widest(tall)).toBe(2);
    expect(widest([])).toBe(0);
  });
});

describe("the local refusal of a block", () => {
  // The grid of the planning takes no paste yet: its columns alone are tried. `is_critical` lies
  // between `total_float` and `started_on` in the order of the contract, and the grid has no column
  // for it, the criticality being a mark of the float (#1699).
  const task = (example("nodes_planning") as NodeList).items.find((node) => node.task != null);
  const paste = {
    preview: () => Promise.reject(new Error("not asked")),
    apply: () => Promise.reject(new Error("not asked")),
    span: pasteSpan,
    name: (column: string) => column,
  };
  const shown = PLANNING_GRID.columns.map((column) => column.key);
  const column = PLANNING_GRID.columns.find((each) => each.contract === "total_float");

  /** The refusal of a block pasted on the float of the first task of the planning. */
  function refusal(text: string) {
    if (task === undefined || column === undefined) {
      throw new Error("no task, or no float column");
    }
    const landed = {
      at: { row: 0, column: column.key },
      row: task,
      column,
      named: "total_float" as const,
    };
    return localRefusal(PLANNING_GRID, paste, landed, readBlock(text), shown);
  }

  it("lets through a block whose cell on a column the grid does not configure is empty", () => {
    expect(refusal("2\t\t2026-03-02")).toBeUndefined();
    expect(refusal("2\t \t2026-03-02\t")).toBeUndefined();
  });

  it("refuses a block whose cell on a column the grid does not configure is not empty", () => {
    expect(refusal("2\toui")).toEqual({
      outcome: undefined,
      hidden: { shown: "absent", name: "is_critical" },
    });
  });
});
