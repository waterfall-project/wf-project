// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the definitions of the columns (US-0580/L2, #1137): each column of the grids of the
 * estimate, of the planning, of the remaining to commit and of the risks (US-0580/L3) has a
 * definition for its header. So has each column of the tables of the administration and of the
 * portfolio, those of their commands included (US-0670/L2, #1434), in both catalogues.
 */
import { describe, expect, it } from "vitest";

import { accessRoleGrid, userGrid } from "@/components/admin/admin-grids";
import { backupGrid } from "@/components/admin/backup-columns";
import { auditGrid } from "@/components/audit/audit-columns";
import { PROJECT_GRID } from "@/components/portfolio/portfolio-grid";
import { commandColumns } from "@/components/reference/command-columns";
import { RISK_GRID } from "@/components/risks/risk-grid";
import { CATALOGUES } from "@/i18n/catalogues";
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

  it.each([
    ["accounts", userGrid({ roles: () => [], rename: undefined }).columns],
    ["accounts, read only", userGrid().columns],
    ["access roles", accessRoleGrid(true).columns],
    ["backups", backupGrid({ marks: true, downloads: true, restores: true }).columns],
    ["journal of audit", auditGrid({ openable: [], functions: [], revision: false }).columns],
    ["projects of the portfolio", PROJECT_GRID.columns],
    ["commands of the reference data", commandColumns(true, () => ({}) as never, undefined)],
  ] as const)(
    "gives every column of the table of the %s a definition, in both catalogues [WF-IHM-0140-A]",
    (_table, columns: readonly AnyColumn[]) => {
      expect(columns.length).toBeGreaterThan(0);
      expect(bare(columns)).toEqual([]);
      for (const { help } of columns) {
        const [grid = "", column = ""] = (help ?? "").split(".");
        for (const catalogue of [CATALOGUES.fr, CATALOGUES.en]) {
          const definitions: Record<string, Record<string, { help: string }>> = catalogue.columns;
          expect(definitions[grid]?.[column]?.help.trim(), help).toBeTruthy();
        }
      }
    },
  );
});
