// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { type FilterChip, liftedHref } from "./filter-chips";
import { recordedPreferences } from "./settings";

const ORIGIN: FilterChip = { key: "origins", name: "Origin", value: "Local", params: ["origins"] };
const STATE: FilterChip = {
  key: "is_active",
  name: "State",
  value: "Active",
  params: ["is_active", "include_inactive"],
};

describe("the filters of a flat table lifted by their chips", () => {
  it("removes the parameters of a chip and the page, the rest of the address kept [WF-IHM-0130-A]", () => {
    const query = new URLSearchParams("sort_by=email&origins=local&is_active=true&offset=50");
    expect(liftedHref("/admin/users", query, [ORIGIN], "offset")).toBe(
      "/admin/users?sort_by=email&is_active=true",
    );
  });

  it("removes every parameter of every chip, up to the bare path [WF-IHM-0130-A]", () => {
    const query = new URLSearchParams("origins=local&is_active=false&include_inactive=true");
    expect(liftedHref("/admin/users", query, [ORIGIN, STATE], "offset")).toBe("/admin/users");
  });
});

describe("whether the panel of the filters is open, kept with the settings of the grid", () => {
  const settings = { visibility: {}, sizing: {} };

  it("is recorded as set, and goes back as the account kept it when the grid sets none [WF-IHM-0060-A]", () => {
    expect(
      recordedPreferences(undefined, settings, undefined, undefined, undefined, undefined, true),
    ).toMatchObject({ filters_open: true });
    expect(recordedPreferences({ filters_open: true }, settings, undefined)).toMatchObject({
      filters_open: true,
    });
    expect(recordedPreferences(undefined, settings, undefined)).not.toHaveProperty("filters_open");
  });
});
