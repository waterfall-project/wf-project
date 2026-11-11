// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example, type Problem } from "@/test/fixtures";

import { identifierOf, shownPage } from "./address";

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

describe("an identifier of the address", () => {
  const ID = "01926f3a-7c00-7000-8000-000000000001";

  it("is kept when it is a UUID, whatever its case", () => {
    expect(identifierOf(new URLSearchParams({ cost_type_id: ID }), "cost_type_id")).toBe(ID);
    expect(
      identifierOf(new URLSearchParams({ cost_type_id: ID.toUpperCase() }), "cost_type_id"),
    ).toBe(ID.toUpperCase());
  });

  it("is dropped like an absent one when it is not a UUID, so that no read leaves with it [US-1770]", () => {
    for (const value of ["abc", "", "01926f3a-7c00", `${ID}x`, "1; drop"]) {
      expect(identifierOf(new URLSearchParams({ cost_type_id: value }), "cost_type_id")).toBe(
        undefined,
      );
    }
    expect(identifierOf(new URLSearchParams(), "cost_type_id")).toBeUndefined();
  });
});
