// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { globSync, readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { auditGrid } from "../audit/audit-columns";
import { accessRoleGrid, userGrid } from "../admin/admin-grids";
import { backupGrid } from "../admin/backup-columns";
import { PROJECT_GRID } from "../portfolio/portfolio-grid";
import { RISK_GRID } from "../risks/risk-grid";

import { COST_GRID } from "../costs/cost-grid";
import { BREAKDOWN_GRID, CONTRIBUTOR_GRID, SUBPROJECT_GRID } from "../projects/settings-grids";
import { PROJECT_LIST_GRID } from "../projects/project-list-grid";
import { costCategoryGrid, costTypeGrid } from "../reference/cost-grids";
import { calendarGrid, orgNodeGrid, resourceRoleGrid } from "../reference/resource-grids";
import { MAX_WIDTH, MIN_WIDTH, WIDEST } from "./columns";
import { ESTIMATE_GRID } from "./estimate";
import { PLANNING_GRID } from "./planning";
import { REMAINING_GRID } from "./remaining";
import { gridShape, initialSettings, keptPageSize, recordedPreferences } from "./settings";

describe("the settings a grid starts from", () => {
  it("are the columns the grid hides, and no width, without preferences", () => {
    expect(initialSettings(undefined, PLANNING_GRID.columns)).toEqual({
      visibility: { timelines: false },
      sizing: {},
    });
    expect(initialSettings({ column_widths: {} }, PLANNING_GRID.columns).visibility).toEqual({
      timelines: false,
    });
    expect(initialSettings(undefined, ESTIMATE_GRID.columns)).toEqual({
      visibility: { subproject: false },
      sizing: {},
    });
  });

  // aucune exigence : propre à l'US (US-0650, une colonne masquée par défaut que la grille ne
  // connaissait pas).
  it("hide a column hidden by default that the grid did not know when the account set it, and show one the account chose to show", () => {
    const planning = PLANNING_GRID.columns.map((column) => column.key);
    const estimate = ESTIMATE_GRID.columns.map((column) => column.key);
    // The grid knew every column: what the account did not hide shows, the columns hidden by
    // default the account chose to show among them.
    expect(
      initialSettings({ hidden_columns: [], known_columns: planning }, PLANNING_GRID.columns)
        .visibility,
    ).toEqual({});
    expect(
      initialSettings({ hidden_columns: ["hours"], known_columns: estimate }, ESTIMATE_GRID.columns)
        .visibility,
    ).toEqual({ hours: false });
    // Set before the sub-project was offered: hidden by default, it stays hidden.
    const before = estimate.filter((key) => key !== "subproject");
    expect(
      initialSettings({ hidden_columns: ["hours"], known_columns: before }, ESTIMATE_GRID.columns)
        .visibility,
    ).toEqual({ hours: false, subproject: false });
    // A column shown by default that the grid did not know shows.
    const unknown = planning.filter((key) => key !== "gantt" && key !== "timelines");
    expect(
      initialSettings({ hidden_columns: [], known_columns: unknown }, PLANNING_GRID.columns)
        .visibility,
    ).toEqual({ timelines: false });
  });

  // aucune exigence : propre à l'US (US-0650, des réglages écrits avant les colonnes connues).
  it("hide a column hidden by default for settings recorded before the grid kept the columns it knew, though the account had shown it", () => {
    // The contract reads the list absent as empty (`docs/api/DECISIONS.md`): the account had shown
    // the timelines, the sub-project, which it hid no more; both are hidden again, once — shown
    // anew, the grid records them as known.
    expect(initialSettings({ hidden_columns: [] }, PLANNING_GRID.columns).visibility).toEqual({
      timelines: false,
    });
    expect(
      initialSettings({ hidden_columns: ["hours"] }, ESTIMATE_GRID.columns).visibility,
    ).toEqual({ hours: false, subproject: false });
  });

  it("hide the columns the account hid, and never the label, which identifies a row", () => {
    const settings = initialSettings(
      {
        hidden_columns: ["hours", "label", "removed"],
        known_columns: ESTIMATE_GRID.columns.map((column) => column.key),
      },
      ESTIMATE_GRID.columns,
    );
    expect(settings.visibility).toEqual({ hours: false });
  });

  it("keep the widths of the columns the grid has, within its bounds", () => {
    const settings = initialSettings(
      { column_widths: { label: 20, hours: 5000, quantity: 90, removed: 100 } },
      ESTIMATE_GRID.columns,
    );
    expect(settings.sizing).toEqual({ label: MIN_WIDTH, hours: MAX_WIDTH, quantity: 90 });
  });

  it("keep the Gantt, pinned at the end, wider than any other column, up to what a window holds", () => {
    const wide = initialSettings(
      { column_widths: { gantt: 1200, label: 1200 } },
      PLANNING_GRID.columns,
    );
    expect(wide.sizing).toEqual({ gantt: 1200, label: MAX_WIDTH });
    const huge = initialSettings({ column_widths: { gantt: 99_999 } }, PLANNING_GRID.columns);
    expect(huge.sizing).toEqual({ gantt: WIDEST });
    // Recorded within the bounds it is read within (#1390).
    const sizing = { gantt: 1200, label: 1200 };
    const shape = gridShape(PLANNING_GRID.columns);
    expect(
      recordedPreferences(
        undefined,
        { visibility: {}, sizing },
        undefined,
        undefined,
        undefined,
        shape,
      ).column_widths,
    ).toEqual(wide.sizing);
  });
});

describe("the preferences a grid records", () => {
  const kept = {
    hidden_columns: ["quantity"],
    column_widths: { label: 400 },
    sort: { column: "hours", order: "asc" as const },
    filters: { progress: "started" },
  };
  const settings = { visibility: { quantity: true, hours: false }, sizing: { label: 412.6 } };

  it("replace its columns, widths and sort, and keep the rest as it came", () => {
    expect(
      recordedPreferences(kept, settings, { column: "budgeted_amount", order: "desc" }),
    ).toEqual({
      ...kept,
      hidden_columns: ["hours"],
      column_widths: { label: 413 },
      sort: { column: "budgeted_amount", order: "desc" },
    });
  });

  it("record the size of the pages chosen last, over the one that came, and keep the one that came otherwise [WF-IHM-0060-A]", () => {
    const sized = { ...kept, page_size: 25 as const };
    expect(recordedPreferences(sized, settings, undefined, undefined, 100).page_size).toBe(100);
    expect(recordedPreferences(sized, settings, undefined).page_size).toBe(25);
    expect(recordedPreferences(kept, settings, undefined, undefined, 10).page_size).toBe(10);
    // A size no server takes is not recorded: the API would refuse the whole grid.
    expect(recordedPreferences(kept, settings, undefined, undefined, 7)).not.toHaveProperty(
      "page_size",
    );
    expect(keptPageSize(sized)).toBe(25);
    expect(keptPageSize(undefined)).toBeUndefined();
  });

  // aucune exigence : propre à l'US (US-0650, les colonnes connues écrites avec la grille).
  it("record the columns the grid offers as those it knows, in place of those that came", () => {
    const shape = gridShape(ESTIMATE_GRID.columns);
    const before = { ...kept, known_columns: ["label", "quantity"] };
    expect(recordedPreferences(before, settings, undefined, undefined, undefined, shape)).toEqual({
      ...before,
      hidden_columns: ["hours"],
      column_widths: { label: 413 },
      known_columns: ESTIMATE_GRID.columns.map((column) => column.key),
    });
    // Without the shape of the grid, those that came go back as they came.
    expect(recordedPreferences(before, settings, undefined).known_columns).toEqual([
      "label",
      "quantity",
    ]);
  });

  it("keep no sort once it is lifted, back to the order of the plan", () => {
    expect(recordedPreferences(kept, settings, null).sort).toBeNull();
  });

  it("send back the sort as it came when the account kept none, and name none", () => {
    expect(recordedPreferences(kept, settings, undefined).sort).toEqual(kept.sort);
    expect(recordedPreferences(undefined, settings, undefined)).not.toHaveProperty("sort");
  });
});

// aucune exigence : propre à l'US (US-0650, `known_columns` borné par le contrat à 64 clés de 64
// caractères, que gridShape écrit sans les tronquer).
describe("the columns a grid records as known", () => {
  const grids = {
    estimate: ESTIMATE_GRID,
    planning: PLANNING_GRID,
    remaining: REMAINING_GRID,
    costs: COST_GRID,
    projects: PROJECT_LIST_GRID,
    portfolio: PROJECT_GRID,
    risks: RISK_GRID,
    breakdown: BREAKDOWN_GRID,
    subprojects: SUBPROJECT_GRID,
    contributors: CONTRIBUTOR_GRID,
    costTypes: costTypeGrid(true),
    costCategories: costCategoryGrid(true),
    orgNodes: orgNodeGrid(true),
    resourceRoles: resourceRoleGrid(true),
    calendars: calendarGrid(true),
    users: userGrid(),
    accessRoles: accessRoleGrid(true),
    backups: backupGrid({ marks: true, downloads: true, restores: true }),
    audit: auditGrid({ openable: [], functions: [], revision: true }),
  };

  // The grids declared by a wrapper of another, which show the same columns once the reading
  // they serve is given.
  const wrappers = ["estimateGrid", "planningGrid", "remainingGrid", "costGrid"];

  it.each(Object.entries(grids))("of the grid %s fit the bounds of the contract", (_, grid) => {
    const { known } = gridShape(grid.columns);
    expect(known.length).toBeLessThanOrEqual(64);
    expect(known.filter((key) => key.length > 64)).toEqual([]);
    expect(new Set(known).size).toBe(known.length);
  });

  it("covers every grid the components export, so that a new one is added to the list", () => {
    const declared = globSync("src/components/**/*.{ts,tsx}")
      .filter((path) => !/\.test\.tsx?$/.test(path))
      .flatMap((path) => {
        const source = readFileSync(path, "utf8");
        return [
          ...source.matchAll(/^export const (\w+): GridConfig</gm),
          ...source.matchAll(/^export function (\w+)\((?:[^()]|\([^()]*\))*\)\s*:\s*GridConfig</gm),
        ].map((found) => found[1]);
      });
    // The grids of the list are named by what they build, the wrappers apart: 19 grids, 4 wrappers.
    expect(declared.length).toBe(Object.keys(grids).length + wrappers.length);
    expect(declared).toEqual(expect.arrayContaining(wrappers));
  });
});
