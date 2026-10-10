// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { alignment, formatCell, sortColumns } from "./columns";
import { ESTIMATE_GRID } from "./estimate";
import { NODE_COLUMNS, type NodeList, pasteSpan } from "./nodes";
import { REMAINING_GRID } from "./remaining";

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

describe("the sort of a grid of the tree", () => {
  it.each([
    ["estimate", ESTIMATE_GRID],
    ["remaining to commit", REMAINING_GRID],
  ] as const)(
    "of the %s is by each column of the lines it shows, and by none of the task alone (#526)",
    (_, grid) => {
      // The server sorts the lines under each task, the tasks in the order of the tree: a column of
      // the task alone, from the description to the work breakdown, would sort nothing.
      const columns = contractEnum("NodeColumn");
      const taskAlone = columns.slice(
        columns.indexOf("description"),
        columns.indexOf("cost_category"),
      );
      const shown = grid.columns.flatMap((column) => column.contract ?? []);
      expect(sortColumns(grid)).toEqual(shown.filter((column) => !taskAlone.includes(column)));
    },
  );

  it("is by no column whose own say is no, whatever the grid says", () => {
    const columns = [{ contract: "a" }, { contract: "b", sorts: false as const }, {}];
    expect(sortColumns({ columns })).toEqual(["a"]);
    expect(sortColumns({ sorts: true, columns })).toEqual(["a"]);
    expect(sortColumns({ sorts: false, columns })).toEqual([]);
  });
});

describe("the columns of the grid of the estimate", () => {
  it("each sort by the column of the contract of the same name, but the signal of a deactivated object", () => {
    const sorted = ESTIMATE_GRID.columns.filter((column) => column.key !== "inactive_object");
    expect(sortColumns(ESTIMATE_GRID)).toEqual(sorted.map((column) => column.key));
  });

  it("present the sub-project and the payment delay of a line between its unit disbursement and its amounts, named by the server", () => {
    expect(ESTIMATE_GRID.columns.map((column) => column.key)).toEqual([
      "label",
      "cost_category",
      "resource_role",
      "quantity",
      "hours",
      "unit_disbursement",
      "subproject",
      "payment_delay_days",
      "inactive_object",
      "base_amount",
      "inflated_amount",
    ]);
  });

  it("present neither a budgeted amount nor a re-estimated amount, but the amount at the year of reference and the amount corrected for inflation [WF-DEV-0050-A]", () => {
    const amounts = ESTIMATE_GRID.columns.filter((column) => column.format === "money");
    expect(amounts.map((column) => [column.key, column.label])).toEqual([
      ["unit_disbursement", "unitDisbursement"],
      ["base_amount", "referenceAmount"],
      ["inflated_amount", "inflatedAmount"],
    ]);
    const shown = ESTIMATE_GRID.columns.map((column) => column.contract);
    expect(shown).not.toContain("budgeted_amount");
    expect(shown).not.toContain("reestimated_amount");
  });

  // The Vérif of WF-DEV-0050: the grid shows the amount corrected for inflation the server
  // computes, never its own — a line of the volume whose task is two years after the year of
  // reference, 2026, at the inflation of the witness project, 3 % a year (the Vérif says 2 %, and
  // 4.04 %: the rate is the project's, the rule the server's, WF-DEV-0030).
  it("show a line two years after the year of reference at its amount and at its amount corrected for inflation, as the server gives them [WF-DEV-0050-A]", () => {
    const volume = example("volume/nodes_thousand") as NodeList;
    const later = volume.items.find((node) => node.estimate_line?.consumption_year === 2028);
    if (later === undefined) {
      throw new Error("the volume has no line two years after the year of reference");
    }
    const shown = (key: string) => {
      const column = ESTIMATE_GRID.columns.find((each) => each.key === key);
      return column === undefined ? undefined : formatCell("money", column.value(later), "fr");
    };
    expect([shown("base_amount"), shown("inflated_amount")]).toEqual(["5 080,00", "5 389,37"]);
  });

  it("show a summary, a task and the totals at their amount and at their amount corrected for inflation, as the server sums them [WF-DEV-0050-A]", () => {
    const volume = example("volume/nodes_thousand") as NodeList;
    const amounts = (node: (typeof volume.items)[number] | undefined) =>
      ["base_amount", "inflated_amount"].map((key) => {
        const column = ESTIMATE_GRID.columns.find((each) => each.key === key);
        return node === undefined ? undefined : formatCell("money", column?.value(node), "fr");
      });
    // Found by their labels, never by a number written here (#400).
    const row = (label: string) => volume.items.find((node) => node.task?.label === label);
    // « Génie civil », a summary whose lines run past the year of reference, and « Reprise
    // 2.1.22 », a task of 2027: each shows two different amounts.
    expect(row("Génie civil")?.task?.is_summary).toBe(true);
    expect(amounts(row("Génie civil"))).toEqual([
      "7\u202f828\u202f839,16",
      "7\u202f847\u202f988,93",
    ]);
    expect(row("Reprise 2.1.22")?.task?.start?.date).toBe("2027-01-06");
    expect(amounts(row("Reprise 2.1.22"))).toEqual(["40\u202f758,82", "41\u202f981,58"]);
    const totals = ESTIMATE_GRID.columns
      .filter((column) => column.key === "base_amount" || column.key === "inflated_amount")
      .map((column) => column.total?.(volume.totals));
    expect(totals).toEqual(["66105223.89", "68923691.06"]);
  });

  it("have the label alone pinned, the two amounts computed whole, and the figures of a line where its node says so", () => {
    const keys = (keep: (column: (typeof ESTIMATE_GRID.columns)[number]) => boolean) =>
      ESTIMATE_GRID.columns.filter(keep).map((column) => column.key);
    expect(keys((column) => column.pinned === true)).toEqual(["label"]);
    expect(keys((column) => column.computed?.whole === true)).toEqual([
      "base_amount",
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
      "base_amount",
      "budgeted_amount",
      "reestimated_amount",
      "inflated_amount",
      "previous_quantity",
      "previous_hours",
      "previous_unit_disbursement",
      "previous_reestimated_amount",
    ]);
    expect(pasteSpan(labour, "label")?.slice(0, 3)).toEqual([
      "label",
      "cost_category",
      "resource_role",
    ]);
    expect(pasteSpan(task, "total_float")).toEqual([
      "total_float",
      "is_critical",
      "predecessors",
      "work_breakdown",
    ]);
    // A column out of the facet of the node: the contract does not range it, the server judges.
    expect(pasteSpan(summary, "quantity")).toBeUndefined();
  });
});
