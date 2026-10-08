// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  boundNames,
  boundsHref,
  filterHref,
  readBounds,
  readValues,
  refusedBounds,
  refusedSides,
  valuesHref,
} from "./filters";

const ORIGINS = ["local", "directory", "identity_provider"] as const;

describe("the filters of a list in the address", () => {
  it("read the values of the contract a parameter names, in its order, each once, and none else", () => {
    const search = new URLSearchParams("origins=identity_provider,nowhere,local,local");
    expect(readValues(search, "origins", ORIGINS)).toEqual(["local", "identity_provider"]);
    expect(readValues(new URLSearchParams(), "origins", ORIGINS)).toEqual([]);
  });

  it("write the values chosen in the order of the contract, back to the first page of a paged list, the rest kept", () => {
    const query = new URLSearchParams("sort_by=email&offset=50");
    const filter = { name: "origins", values: ORIGINS, page: "offset" };
    expect(valuesHref("/admin/users", query, filter, ["identity_provider", "local"])).toBe(
      "/admin/users?sort_by=email&origins=local%2Cidentity_provider",
    );
    expect(valuesHref("/admin/users", query, filter, [])).toBe("/admin/users?sort_by=email");
    // Every value retained is no filter: the list holds them all.
    expect(valuesHref("/admin/users", query, filter, [...ORIGINS])).toBe(
      "/admin/users?sort_by=email",
    );
  });

  it("write every value chosen of a column some rows hold none of: every zone still filters", () => {
    const zones = { name: "zones", values: ["nominal", "watch", "alert"], exhaustive: false };
    expect(valuesHref("/p", new URLSearchParams(), zones, ["alert", "nominal", "watch"])).toBe(
      "/p?zones=nominal%2Cwatch%2Calert",
    );
  });

  it("set one filter, or lift it, the page of a list the server does not page kept as it is", () => {
    const query = new URLSearchParams("org_node_id=a&offset=2");
    expect(filterHref("/x", query, "org_node_id", undefined)).toBe("/x?offset=2");
    expect(filterHref("/x", query, "org_node_id", "b", "offset")).toBe("/x?org_node_id=b");
    expect(filterHref("/x", new URLSearchParams("offset=2"), "org_node_id", "", "offset")).toBe(
      "/x",
    );
    // The pages of every list of a screen, taken back to their first.
    const pages = new URLSearchParams("role_offset=50&calendar_offset=25&sort_by=code");
    expect(
      filterHref("/x", pages, "include_inactive", "true", ["role_offset", "calendar_offset"]),
    ).toBe("/x?sort_by=code&include_inactive=true");
  });
});

describe("the bounds of a column of figures in the address", () => {
  it("are named after the column, as the contract names them for every list (#545)", () => {
    expect(boundNames("role_monthly_hours")).toEqual({
      min: "role_monthly_hours_min",
      max: "role_monthly_hours_max",
    });
  });

  it("read each bound that is a figure of the contract of its kind, and none else", () => {
    const search = new URLSearchParams(
      "rate_min=110&rate_max=150.555&hours_min=-2.75&hours_max=8,5",
    );
    expect(readBounds(search, "rate", "money")).toEqual({ min: "110", max: undefined });
    expect(readBounds(search, "hours", "decimal")).toEqual({ min: "-2.75", max: undefined });
    expect(readBounds(search, "rate", "decimal")).toEqual({ min: "110", max: "150.555" });
    expect(readBounds(new URLSearchParams(), "rate", "money")).toEqual({
      min: undefined,
      max: undefined,
    });
  });

  it("write the bounds of several columns, a side empty lifted, back to the first page, the rest kept", () => {
    const query = new URLSearchParams("sort_by=label&offset=50&a_max=9");
    const href = boundsHref(
      "/x",
      query,
      [
        { column: "a", bounds: { min: "1", max: undefined } },
        { column: "b", bounds: { min: undefined, max: "2.5" } },
      ],
      { page: "offset" },
    );
    expect(href).toBe("/x?sort_by=label&a_min=1&b_max=2.5");
    expect(
      boundsHref("/x", new URLSearchParams("a_min=1"), [
        { column: "a", bounds: { min: undefined, max: undefined } },
      ]),
    ).toBe("/x");
  });

  it("write the choice the bounds go with while a bound is, and lift it with the last", () => {
    const scope = { name: "rate_year", value: "2026" };
    expect(
      boundsHref(
        "/x",
        new URLSearchParams(),
        [{ column: "rate", bounds: { min: "110", max: undefined } }],
        {
          scope,
        },
      ),
    ).toBe("/x?rate_min=110&rate_year=2026");
    expect(
      boundsHref(
        "/x",
        new URLSearchParams("rate_year=2025&rate_min=110"),
        [{ column: "rate", bounds: { min: undefined, max: undefined } }],
        { scope },
      ),
    ).toBe("/x");
  });

  it("read the parameters the API refused, by name and code, the lower bound an upper one is refused for, and nothing of another field", () => {
    const refused = refusedBounds([
      {
        pointer: "/query/monthly_hours_max",
        code: "VALUE_OUT_OF_RANGE",
        params: { minimum: "1000" },
      },
      { pointer: "/query/rate_year", code: "VALUE_REQUIRED" },
      { pointer: "/query/monday_min", code: "NUMBER_INVALID" },
      { pointer: "/label", code: "VALUE_REQUIRED" },
      { pointer: "/query/headcount_max", code: "VALUE_TOO_LONG" },
    ]);
    expect([...refused]).toEqual([
      ["monthly_hours_max", { code: "VALUE_OUT_OF_RANGE", minimum: "1000" }],
      ["rate_year", { code: "VALUE_REQUIRED" }],
      ["monday_min", { code: "NUMBER_INVALID" }],
    ]);
    // By the two sides of a column of the contract.
    expect(refusedSides(refused, "monday")).toEqual({ min: { code: "NUMBER_INVALID" } });
    expect(refusedSides(refused, "headcount")).toBeUndefined();
  });
});
