// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { ESTIMATE_SORT_COLUMNS } from "./estimate";
import {
  asked,
  CONTRACT_ADDRESS,
  pagedList,
  pageSizeOf,
  prefixedAddress,
  readGridQuery,
  SEARCH_LENGTH,
  searchHref,
  sortHref,
} from "./query";
import { REMAINING_SORT_COLUMNS } from "./remaining";

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

  it("asks no sort by a column of the task alone of a grid of the tree, in the address or kept, as by one it does not know (#526)", () => {
    // The remaining to commit sorts the lines under each task: its progress and its finish, of the
    // task alone, are not asked — a preference kept before them is passed over, without error.
    const read = (query: string, kept: { column: string; order: string } | null = null) =>
      readGridQuery(new URLSearchParams(query), REMAINING_SORT_COLUMNS, kept).sort;
    expect(read("sort_by=progress&sort_order=desc")).toBeUndefined();
    expect(read("sort_by=finish")).toBeUndefined();
    expect(read("", { column: "progress", order: "desc" })).toBeUndefined();
    expect(read("", { column: "finish", order: "asc" })).toBeUndefined();
    // Passed over as an unknown sort is: the address that asks it falls back on the sort kept.
    const kept = { column: "budgeted_amount", order: "desc" };
    expect(read("sort_by=finish", kept)).toEqual({ column: "budgeted_amount", order: "desc" });
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
      size: 50,
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

describe("the size of the pages of a flat table", () => {
  const size = (query: string, kept?: number | null, names = CONTRACT_ADDRESS) =>
    readGridQuery(new URLSearchParams(query), ESTIMATE_SORT_COLUMNS, null, names, kept).size;

  it("is one of 10, 25, 50 and 100 as the contract admits them, a text of the address or a number of the settings", () => {
    expect([10, 25, 50, 100].map(pageSizeOf)).toEqual([10, 25, 50, 100]);
    expect(["10", "25", "50", "100"].map(pageSizeOf)).toEqual([10, 25, 50, 100]);
    for (const refused of ["", "0", "7", "500", "-25", "25.5", "x", " 25", null, undefined, 25.5]) {
      expect(pageSizeOf(refused)).toBeUndefined();
    }
  });

  it("is read from the address, else from the settings of the grid, else 50, whatever the address holds that no server takes [WF-IHM-0060-A]", () => {
    expect(size("")).toBe(50);
    expect(size("", 25)).toBe(25);
    expect(size("limit=100", 25)).toBe(100);
    expect(size("limit=7", 25)).toBe(25);
    expect(size("limit=7")).toBe(50);
    expect(size("", 7)).toBe(50);
    expect(size("", null)).toBe(50);
  });

  it("is carried by a grid among several under its own name, the others' kept [WF-IHM-0060-A]", () => {
    const roles = prefixedAddress("role_");
    expect(roles.limit).toBe("role_limit");
    expect(size("limit=10&role_limit=25", undefined, roles)).toBe(25);
    expect(size("limit=10", undefined, roles)).toBe(50);
  });

  it("is asked of the server by every reading, under the name of the contract [WF-IHM-0060-A]", () => {
    const query = readGridQuery(new URLSearchParams("limit=25"), ESTIMATE_SORT_COLUMNS);
    expect(asked(query, 50)).toEqual({ limit: 25, offset: 50 });
    expect(asked({ sort: undefined, search: undefined })).toEqual({});
  });

  it("is read by the list of its pages, which a sort, a search or a size changed reads otherwise", () => {
    const roles = prefixedAddress("role_");
    expect(pagedList(roles)).toEqual({
      page: "role_offset",
      size: "role_limit",
      reads: ["role_search", "role_sort_by", "role_sort_order", "role_limit"],
    });
  });

  it("is kept by a sort or a search that changes, back to its first page", () => {
    const paged = new URLSearchParams("limit=25&offset=50");
    expect(sortHref("/r", paged, { column: "label", order: "asc" })).toBe(
      "/r?limit=25&sort_by=label&sort_order=asc",
    );
    expect(searchHref("/r", paged, "Ing")).toBe("/r?limit=25&search=Ing");
  });
});
