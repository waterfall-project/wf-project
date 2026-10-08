// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { ESTIMATE_SORT_COLUMNS } from "./estimate";
import { prefixedAddress, readGridQuery, SEARCH_LENGTH, searchHref, sortHref } from "./query";

describe("what the address asks of a grid", () => {
  it("reads the sort by a column the grid sorts, ascending unless the address says descending", () => {
    const read = (query: string) =>
      readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS).sort;
    expect(read("sort_by=inflated_amount&sort_order=desc")).toEqual({
      column: "inflated_amount",
      order: "desc",
    });
    expect(read("sort_by=label")).toEqual({ column: "label", order: "asc" });
    expect(read("sort_by=label&sort_order=sideways")).toEqual({ column: "label", order: "asc" });
  });

  it("asks no sort by a column the grid does not sort, nor the contract", () => {
    const read = (query: string) =>
      readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS).sort;
    expect(read("sort_by=start&sort_order=desc")).toBeUndefined();
    expect(read("sort_by=budgeted_amount")).toBeUndefined();
    expect(read("sort_by=nothing")).toBeUndefined();
    expect(read("sort_order=desc")).toBeUndefined();
  });

  it("sorts by the sort the account keeps when the address asks none, the address winning", () => {
    const read = (query: string, kept: { column: string; order: string } | null) =>
      readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS, kept).sort;
    const hours = { column: "hours", order: "desc" };
    expect(read("", hours)).toEqual({ column: "hours", order: "desc" });
    expect(read("sort_by=label", hours)).toEqual({ column: "label", order: "asc" });
    expect(read("", { column: "start", order: "asc" })).toBeUndefined();
    expect(read("", { column: "hours", order: "up" })).toEqual({ column: "hours", order: "asc" });
    expect(read("", null)).toBeUndefined();
  });

  it("asks no sort, and falls back on none, when the address lifted it", () => {
    const kept = { column: "hours", order: "desc" };
    expect(
      readGridQuery(new URLSearchParams("sort_by=&sort_order=desc"), ESTIMATE_SORT_COLUMNS, kept)
        .sort,
    ).toBeUndefined();
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

  it("lifts the sort back to the order of the plan, by an empty sort_by", () => {
    const sorted = new URLSearchParams("sort_by=hours&sort_order=desc");
    expect(sortHref("/p", sorted, undefined)).toBe("/p?sort_by=");
    expect(sortHref("/p", current, undefined)).toBe(
      "/p?subproject_id=unassigned&search=revue&sort_by=",
    );
  });

  it("sets the search, trimmed, or lifts it when empty", () => {
    expect(searchHref("/p", current, "  câblage ")).toBe(
      "/p?subproject_id=unassigned&search=c%C3%A2blage",
    );
    expect(searchHref("/p", current, "   ")).toBe("/p?subproject_id=unassigned");
  });

  it("starts a list the server pages again from its first page, on a sort or a search changed", () => {
    const paged = new URLSearchParams("in_tracked_scope=false&offset=50");
    expect(sortHref("/p", paged, { column: "amount", order: "asc" })).toBe(
      "/p?in_tracked_scope=false&sort_by=amount&sort_order=asc",
    );
    expect(searchHref("/p", paged, "pièce")).toBe("/p?in_tracked_scope=false&search=pi%C3%A8ce");
  });

  it("reads and writes the sort and the search of a grid among several under its own names, the others' kept", () => {
    const roles = prefixedAddress("role_");
    const address = new URLSearchParams(
      "sort_by=hours&search=other&role_sort_by=label&role_sort_order=desc&role_search=Ing",
    );
    expect(readGridQuery(address, ESTIMATE_SORT_COLUMNS, null, roles)).toEqual({
      sort: { column: "label", order: "desc" },
      search: "Ing",
    });
    expect(sortHref("/r", address, { column: "hours", order: "asc" }, roles)).toBe(
      "/r?sort_by=hours&search=other&role_search=Ing&role_sort_by=hours&role_sort_order=asc",
    );
    expect(searchHref("/r", address, "", roles)).toBe(
      "/r?sort_by=hours&search=other&role_sort_by=label&role_sort_order=desc",
    );
  });

  it("takes back to its first page only the list of the grid whose sort or search changed", () => {
    const roles = prefixedAddress("role_");
    const paged = new URLSearchParams("offset=50&role_offset=20&calendar_offset=10");
    expect(sortHref("/r", paged, { column: "label", order: "asc" }, roles)).toBe(
      "/r?offset=50&calendar_offset=10&role_sort_by=label&role_sort_order=asc",
    );
    expect(searchHref("/r", paged, "Ing", roles)).toBe(
      "/r?offset=50&calendar_offset=10&role_search=Ing",
    );
  });
});
