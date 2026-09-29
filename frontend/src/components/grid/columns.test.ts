// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { alignment, formatCell, sortColumns } from "./columns";
import { ESTIMATE_GRID } from "./estimate";

describe("a cell of a grid", () => {
  it("shows its value by its format, from the exact string of the contract", () => {
    expect(formatCell("money", "1234.5", "en")).toBe("1,234.50");
    expect(formatCell("decimal", "12.5", "fr")).toBe("12,5");
    expect(formatCell("date", "2026-06-30", "en")).toBe("30/06/2026");
    expect(formatCell("date", "2026-03-02", "fr")).toBe("02/03/2026");
    expect(formatCell("text", "Études", "en")).toBe("Études");
  });

  it("shows nothing for a value the answer does not give", () => {
    expect(formatCell("money", null, "fr")).toBe("");
    expect(formatCell("date", undefined, "fr")).toBe("");
  });

  it("aligns a text at the start and a figure at the end, unless its column says otherwise", () => {
    expect(alignment({ format: "text" })).toBe("start");
    expect(alignment({ format: "money" })).toBe("end");
    expect(alignment({ format: "date", align: "start" })).toBe("start");
  });
});

describe("the columns of the grid of the estimate", () => {
  it("each sort by the column of the contract of the same name", () => {
    expect(sortColumns(ESTIMATE_GRID)).toEqual(ESTIMATE_GRID.columns.map((column) => column.key));
  });

  it("have the label alone pinned, and the two amounts computed", () => {
    const keys = (keep: (column: (typeof ESTIMATE_GRID.columns)[number]) => boolean) =>
      ESTIMATE_GRID.columns.filter(keep).map((column) => column.key);
    expect(keys((column) => column.pinned === true)).toEqual(["label"]);
    expect(keys((column) => column.computed === true)).toEqual([
      "budgeted_amount",
      "reestimated_amount",
    ]);
  });
});
