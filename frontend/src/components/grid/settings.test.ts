// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { MAX_WIDTH, MIN_WIDTH } from "./columns";
import { ESTIMATE_GRID } from "./estimate";
import { initialSettings, recordedPreferences } from "./settings";

describe("the settings a grid starts from", () => {
  it("are none without preferences", () => {
    expect(initialSettings(undefined, ESTIMATE_GRID.columns)).toEqual({
      visibility: {},
      sizing: {},
    });
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
});

describe("the preferences a grid records", () => {
  it("replace its columns and widths, and keep the rest as it came", () => {
    const kept = {
      hidden_columns: ["quantity"],
      column_widths: { label: 400 },
      sort: { column: "hours", order: "asc" as const },
      filters: { progress: ["started"] },
    };
    expect(
      recordedPreferences(kept, {
        visibility: { quantity: true, hours: false },
        sizing: { label: 412.6 },
      }),
    ).toEqual({ ...kept, hidden_columns: ["hours"], column_widths: { label: 413 } });
  });
});
