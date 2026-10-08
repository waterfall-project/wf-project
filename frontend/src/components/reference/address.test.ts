// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example, type Problem } from "@/test/fixtures";

import { readingOf, shownPage } from "./address";

describe("what a list of the reference data reads of the address", () => {
  it("tells a parameter absent from one given empty, and leaves out those it does not read", () => {
    const reads = ["include_inactive", "role_search"];
    const absent = readingOf(new URLSearchParams("calendar_search=x"), reads);
    const empty = readingOf(new URLSearchParams("role_search="), reads);
    expect(absent).toBe("include_inactive&role_search");
    expect(empty).toBe("include_inactive&role_search=");
    expect(absent).not.toBe(empty);
    expect(readingOf(new URLSearchParams("role_search=Ing&include_inactive=true"), reads)).toBe(
      "include_inactive=true&role_search=Ing",
    );
  });
});

describe("what a list shows of a page whose bounds the API may refuse", () => {
  it("shows the rows of the page read, and no bound refused", () => {
    const read = example("resource_roles_bounded") as {
      items: readonly unknown[];
      meta: { limit: number; offset: number; total: number };
    };
    const shown = shownPage({ kind: "read", data: read });
    expect(shown.rows).toHaveLength(2);
    expect(shown.page.total).toBe(2);
    expect(shown.refused).toBeUndefined();
  });

  it("shows no row of a page refused, and the upper bound refused with the lower one it names", () => {
    const problem = example("resource_roles_bounds_inverted") as Problem;
    const shown = shownPage({
      kind: "refused",
      refusal: { status: 422, code: "VALIDATION_FAILED" },
      problem,
    });
    expect(shown.rows).toEqual([]);
    expect(shown.page).toEqual({ limit: 0, offset: 0, total: 0 });
    expect([...(shown.refused ?? [])]).toEqual([
      ["monthly_hours_max", { code: "VALUE_OUT_OF_RANGE", minimum: "1000" }],
    ]);
  });
});
