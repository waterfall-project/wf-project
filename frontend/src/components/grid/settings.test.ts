// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { MAX_WIDTH, MIN_WIDTH, WIDEST } from "./columns";
import { ESTIMATE_GRID } from "./estimate";
import { PLANNING_GRID } from "./planning";
import { initialSettings, keptPageSize, recordedPreferences } from "./settings";

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

  it("show a column hidden by default once the account kept a list of hidden columns that omits it", () => {
    expect(initialSettings({ hidden_columns: [] }, PLANNING_GRID.columns).visibility).toEqual({});
    expect(
      initialSettings({ hidden_columns: ["gantt"] }, PLANNING_GRID.columns).visibility,
    ).toEqual({ gantt: false });
    expect(initialSettings({ hidden_columns: [] }, ESTIMATE_GRID.columns).visibility).toEqual({});
    expect(
      initialSettings({ hidden_columns: ["hours"] }, ESTIMATE_GRID.columns).visibility,
    ).toEqual({ hours: false });
  });

  it("hide the columns the account hid, and never the label, which identifies a row", () => {
    const settings = initialSettings(
      { hidden_columns: ["hours", "label", "removed"] },
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

  it("keep no sort once it is lifted, back to the order of the plan", () => {
    expect(recordedPreferences(kept, settings, null).sort).toBeNull();
  });

  it("send back the sort as it came when the account kept none, and name none", () => {
    expect(recordedPreferences(kept, settings, undefined).sort).toEqual(kept.sort);
    expect(recordedPreferences(undefined, settings, undefined)).not.toHaveProperty("sort");
  });
});
