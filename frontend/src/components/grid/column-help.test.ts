// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the definitions of the columns (US-0580/L2, #1137): each column of the grids of the
 * estimate, of the planning, of the remaining to commit and of the risks (US-0580/L3) has a
 * definition for its header, and the amount corrected of inflation, the sentence with the year and
 * the rate that correct it where the screen knows them.
 */
import { describe, expect, it } from "vitest";

import { RISK_GRID } from "@/components/risks/risk-grid";
import { estimateReference } from "@/test/reference";

import type { GridColumn } from "./columns";
import { estimateGrid, ESTIMATE_GRID } from "./estimate";
import { PLANNING_GRID, planningGrid } from "./planning";
import { REMAINING_GRID, remainingGrid } from "./remaining";

type AnyColumn = Pick<GridColumn<never, string, never>, "key" | "help">;

/** The keys of the columns of a grid that bear no definition. */
function bare(columns: readonly AnyColumn[]): string[] {
  return columns.filter((column) => column.help === undefined).map((column) => column.key);
}

describe("the definitions of the columns", () => {
  it.each([
    ["estimate", ESTIMATE_GRID.columns, estimateGrid(estimateReference()).columns],
    ["planning", PLANNING_GRID.columns, planningGrid().columns],
    ["remaining", REMAINING_GRID.columns, remainingGrid().columns],
    ["risks", RISK_GRID.columns, RISK_GRID.columns],
  ] as const)("gives every column of the grid of the %s a definition", (_grid, defined, built) => {
    expect(defined.length).toBeGreaterThan(0);
    expect(bare(defined)).toEqual([]);
    expect(bare(built)).toEqual([]);
  });

  it("gives the amount corrected of inflation a definition of its own whether or not the revision is known", () => {
    const plain = estimateGrid(estimateReference()).columns.find(
      (column) => column.key === "inflated_amount",
    );
    const corrected = estimateGrid(estimateReference(), undefined, {
      year: "2026",
      rate: "3 %",
    }).columns.find((column) => column.key === "inflated_amount");
    expect(plain?.help).toBe("estimate.inflatedAmountStatic");
    expect(plain?.helpValues).toBeUndefined();
    expect(corrected?.help).toBe("estimate.inflatedAmount");
    expect(corrected?.helpValues).toEqual({ year: "2026", rate: "3 %" });
  });
});
