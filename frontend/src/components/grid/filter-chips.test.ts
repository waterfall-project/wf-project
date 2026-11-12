// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { type FilterChip, liftedHref, liftedParams } from "./filter-chips";

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
    expect(liftedHref("/admin/users", query, liftedParams([ORIGIN]), "offset")).toBe(
      "/admin/users?sort_by=email&is_active=true",
    );
  });

  it("removes every parameter of every chip, up to the bare path [WF-IHM-0130-A]", () => {
    const query = new URLSearchParams("origins=local&is_active=false&include_inactive=true");
    expect(liftedHref("/admin/users", query, liftedParams([ORIGIN, STATE]), "offset")).toBe(
      "/admin/users",
    );
  });
});

describe("the parameters lifted", () => {
  it("are those of the chips, each once, and any other the reading set aside with `every` [WF-IHM-0130-A]", () => {
    expect(liftedParams([ORIGIN, STATE, ORIGIN])).toEqual([
      "origins",
      "is_active",
      "include_inactive",
    ]);
    const query = new URLSearchParams("origins=nope&sort_by=email&search=a&offset=2");
    expect(liftedHref("/admin/users", query, ["origins"], "offset")).toBe(
      "/admin/users?sort_by=email&search=a",
    );
  });
});
