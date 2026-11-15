// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Permission } from "@/session/request";
import { example, type Problem } from "@/test/fixtures";

import { identifierOf, keptState, shownPage, stateOf, stateQuery } from "./address";

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

describe("the state a list of the reference data shows", () => {
  const WRITES: readonly Permission[] = ["cost_settings.read", "cost_settings.write"];
  const state = (address: string, kept?: string, permissions = WRITES) =>
    stateOf(
      new URLSearchParams(address),
      "type_is_active",
      kept,
      permissions,
      "cost_settings.write",
    );

  it("is the active objects alone by default, the deactivated ones alone, or every one, the address prevailing over the account [WF-REF-0150-A]", () => {
    expect(state("")).toBe(true);
    expect(state("type_is_active=false")).toBe(false);
    expect(state("type_is_active=all")).toBeUndefined();
    // The account's when the address names none; the address's otherwise.
    expect(state("", "false")).toBe(false);
    expect(state("", "all")).toBeUndefined();
    expect(state("type_is_active=true", "all")).toBe(true);
    // A text of no state is the default; `include_inactive` is not read (#3076).
    expect(state("type_is_active=maybe")).toBe(true);
    expect(state("include_inactive=true")).toBe(true);
  });

  it("is nothing to a session that may not read the deactivated objects, offered no filter [WF-REF-0150-A]", () => {
    expect(state("type_is_active=false", "all", ["cost_settings.read"])).toBeUndefined();
    expect(stateQuery(undefined, false)).toEqual({});
  });

  it("is asked by `is_active`, every one by `include_inactive` alone [WF-REF-0150-A]", () => {
    expect(stateQuery(true, true)).toEqual({ is_active: true });
    expect(stateQuery(false, true)).toEqual({ is_active: false });
    expect(stateQuery(undefined, true)).toEqual({ include_inactive: true });
  });

  it("is kept with the settings of its grid once it differs from the active ones, the search not kept [WF-IHM-0060-A]", () => {
    expect(keptState("type_is_active")).toEqual({
      filters: ["type_is_active"],
      defaulted: { type_is_active: "true" },
      searchKept: false,
    });
  });
});
