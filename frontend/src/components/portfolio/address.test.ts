// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { parametersHref, perimeterQuery, readPerimeter, statesValue } from "./address";

/** A node of organisation of the reference, as the contract identifies it. */
const [, NODE] = example("org_nodes") as components["schemas"]["OrgNode"][];
const DESIGN_OFFICE = NODE?.org_node_id ?? "";

describe("the address of a view of the portfolio", () => {
  it("reads the states of a portfolio in their order, and the dates and the node the API may take", () => {
    const perimeter = readPerimeter(
      new URLSearchParams(
        "states=completed,lost,in_progress&from=2025-02-30&to=2026-03-31&org_node_id=a/b",
      ),
    );
    expect(perimeter).toEqual({
      states: ["in_progress", "completed"],
      from: undefined,
      to: "2026-03-31",
      asOf: undefined,
      orgNode: undefined,
    });
    expect(perimeterQuery(perimeter)).toEqual({
      states: ["in_progress", "completed"],
      to: "2026-03-31",
    });
  });

  it("asks nothing the address does not name: the server chooses", () => {
    expect(perimeterQuery(readPerimeter(new URLSearchParams()))).toEqual({});
  });

  it("asks of the perimeter what a view takes alone", () => {
    const perimeter = readPerimeter(
      new URLSearchParams(`from=2025-01-01&as_of=2026-03-16&org_node_id=${DESIGN_OFFICE}`),
    );
    expect(perimeterQuery(perimeter)).toEqual({
      from: "2025-01-01",
      as_of: "2026-03-16",
      org_node_id: DESIGN_OFFICE,
    });
    expect(perimeterQuery(perimeter, { period: false, node: false })).toEqual({
      as_of: "2026-03-16",
    });
  });

  it("changes parameters back to the first page of the list, the rest kept", () => {
    const query = new URLSearchParams("sort_by=label&offset=50&from=2025-01-01");
    expect(
      parametersHref("/portfolio/projects", query, { states: "pricing", from: undefined }),
    ).toBe("/portfolio/projects?sort_by=label&states=pricing");
    expect(parametersHref("/portfolio/projects", new URLSearchParams("offset=50"), {})).toBe(
      "/portfolio/projects",
    );
  });

  it("writes the states in the order of the portfolio, none for none", () => {
    expect(statesValue(["completed", "in_progress"])).toBe("in_progress,completed");
    expect(statesValue([])).toBeUndefined();
  });
});
