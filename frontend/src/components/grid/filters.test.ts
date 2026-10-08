// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { filterHref, readValues, valuesHref } from "./filters";

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

  it("set one filter, or lift it, the page of a list the server does not page kept as it is", () => {
    const query = new URLSearchParams("org_node_id=a&offset=2");
    expect(filterHref("/x", query, "org_node_id", undefined)).toBe("/x?offset=2");
    expect(filterHref("/x", query, "org_node_id", "b", "offset")).toBe("/x?org_node_id=b");
    expect(filterHref("/x", new URLSearchParams("offset=2"), "org_node_id", "", "offset")).toBe(
      "/x",
    );
  });
});
