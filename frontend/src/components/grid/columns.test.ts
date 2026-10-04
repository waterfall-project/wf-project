// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { alignment, formatCell, sortColumns } from "./columns";
import { ESTIMATE_GRID } from "./estimate";
import { NODE_COLUMNS, type NodeList, pasteSpan } from "./nodes";

// The schemas of the contract the nodes of a structure are written in.
const SCHEMAS = join(import.meta.dirname, "../../../../docs/api/components/schemas/revisions.yaml");

/** The values of an enumeration of the contract, in the order it writes them. */
function contractEnum(name: string): string[] {
  const lines = readFileSync(SCHEMAS, "utf-8").split("\n");
  const from = lines.indexOf(`${name}:`);
  const enumAt = lines.findIndex((line, index) => index > from && line === "  enum:");
  const values: string[] = [];
  for (const line of lines.slice(enumAt + 1)) {
    const value = /^ {4}- (\S+)$/.exec(line)?.[1];
    if (value === undefined) {
      break;
    }
    values.push(value);
  }
  return values;
}

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

  it("present the amount at the year of reference and the amount corrected for inflation, neither the budgeted nor the re-estimated amount by name [WF-DEV-0050-A]", () => {
    const amounts = ESTIMATE_GRID.columns.filter((column) => column.format === "money");
    expect(amounts.map((column) => column.label)).toEqual([
      "unitDisbursement",
      "referenceAmount",
      "inflatedAmount",
    ]);
    expect(amounts.map((column) => column.sortBy)).not.toContain("budgeted_amount");
  });

  it("have the label alone pinned, the two amounts computed whole, and the figures of a line where its node says so", () => {
    const keys = (keep: (column: (typeof ESTIMATE_GRID.columns)[number]) => boolean) =>
      ESTIMATE_GRID.columns.filter(keep).map((column) => column.key);
    expect(keys((column) => column.pinned === true)).toEqual(["label"]);
    expect(keys((column) => column.computed?.whole === true)).toEqual([
      "reestimated_amount",
      "inflated_amount",
    ]);
    expect(keys((column) => column.computed?.whole === false)).toEqual([
      "quantity",
      "hours",
      "unit_disbursement",
    ]);
  });
});

describe("the columns of the contract", () => {
  it("are those of NodeColumn, in the order the contract writes them", () => {
    expect([...NODE_COLUMNS]).toEqual(contractEnum("NodeColumn"));
  });

  it("measure a block pasted on a node on the columns of its facet, from the column of the cell", () => {
    const [summary, task, labour] = (example("nodes_estimate") as NodeList).items;
    if (summary === undefined || task === undefined || labour === undefined) {
      throw new Error("the example of the estimate lacks its first rows");
    }
    expect(pasteSpan(labour, "unit_disbursement")).toEqual([
      "unit_disbursement",
      "subproject",
      "payment_delay_days",
      "consumption_year",
      "budgeted_amount",
      "reestimated_amount",
      "inflated_amount",
      "previous_reestimated_amount",
    ]);
    expect(pasteSpan(labour, "label")?.slice(0, 3)).toEqual([
      "label",
      "cost_category",
      "resource_role",
    ]);
    expect(pasteSpan(task, "total_float")).toEqual(["total_float", "is_critical", "predecessors"]);
    // A column out of the facet of the node: the contract does not range it, the server judges.
    expect(pasteSpan(summary, "quantity")).toBeUndefined();
  });
});
