// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { ESTIMATE_SORT_COLUMNS } from "./estimate";
import { readGridQuery, SEARCH_LENGTH, searchHref, sortHref } from "./query";

describe("what the address asks of a grid", () => {
  it("reads the sort by a column the grid sorts, ascending unless the address says descending", () => {
    const read = (query: string) =>
      readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS).sort;
    expect(read("sort_by=budgeted_amount&sort_order=desc")).toEqual({
      column: "budgeted_amount",
      order: "desc",
    });
    expect(read("sort_by=label")).toEqual({ column: "label", order: "asc" });
    expect(read("sort_by=label&sort_order=sideways")).toEqual({ column: "label", order: "asc" });
  });

  it("asks no sort by a column the grid does not sort, nor the contract", () => {
    const read = (query: string) =>
      readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS).sort;
    expect(read("sort_by=start_date&sort_order=desc")).toBeUndefined();
    expect(read("sort_by=nothing")).toBeUndefined();
    expect(read("sort_order=desc")).toBeUndefined();
  });

  it("reads a search of the length the contract accepts, and none otherwise", () => {
    const read = (search: string) =>
      readGridQuery(new URLSearchParams({ search }), ESTIMATE_SORT_COLUMNS).search;
    expect(read("revue")).toBe("revue");
    expect(read("")).toBeUndefined();
    expect(read("x".repeat(SEARCH_LENGTH))).toHaveLength(SEARCH_LENGTH);
    expect(read("x".repeat(SEARCH_LENGTH + 1))).toBeUndefined();
  });
});

describe("the address a grid leads to", () => {
  const current = new URLSearchParams("subproject_id=unassigned&search=revue");

  it("sets the sort by the parameters of the contract, the rest of the address kept", () => {
    expect(sortHref("/p", current, { column: "hours", order: "desc" })).toBe(
      "/p?subproject_id=unassigned&search=revue&sort_by=hours&sort_order=desc",
    );
  });

  it("lifts the sort back to the order of the plan", () => {
    const sorted = new URLSearchParams("sort_by=hours&sort_order=desc");
    expect(sortHref("/p", sorted, undefined)).toBe("/p");
    expect(sortHref("/p", current, undefined)).toBe("/p?subproject_id=unassigned&search=revue");
  });

  it("sets the search, trimmed, or lifts it when empty", () => {
    expect(searchHref("/p", current, "  câblage ")).toBe(
      "/p?subproject_id=unassigned&search=c%C3%A2blage",
    );
    expect(searchHref("/p", current, "   ")).toBe("/p?subproject_id=unassigned");
  });
});
