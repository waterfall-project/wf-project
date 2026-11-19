// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import {
  parametersHref,
  perimeterQuery,
  portfolioProjectsQuery,
  PROJECTS_LIST,
  readHorizon,
  readPerimeter,
  readProjectFilters,
  readThreshold,
  statesValue,
} from "./address";

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

  it("reads any horizon and any threshold the contract takes, and those alone", () => {
    expect(readHorizon(new URLSearchParams("horizon_months=36"))).toBe("36");
    expect(readHorizon(new URLSearchParams("horizon_months=240"))).toBe("240");
    for (const refused of ["0", "241", "012", "1.5", "six"]) {
      expect(readHorizon(new URLSearchParams(`horizon_months=${refused}`))).toBeUndefined();
    }
    expect(readThreshold(new URLSearchParams("under_load_threshold=0.45"))).toBe("0.45");
    expect(readThreshold(new URLSearchParams("under_load_threshold=50%"))).toBeUndefined();
  });
});

describe("what the list of the projects of the portfolio reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const perimeter = readPerimeter(
      new URLSearchParams(
        `states=completed&from=2025-01-01&to=2025-12-31&as_of=2026-03-16&org_node_id=${DESIGN_OFFICE}`,
      ),
    );
    const query = portfolioProjectsQuery({
      perimeter,
      filters: readProjectFilters(new URLSearchParams("zones=alert")),
      offset: 50,
      query: { sort: { column: "cost_index", order: "asc" }, search: "poste", size: undefined },
    });
    const asked = Object.keys(query).filter((name) => name !== PROJECTS_LIST.page);
    expect(asked).toHaveLength(9);
    expect(PROJECTS_LIST.reads).toEqual(expect.arrayContaining(asked));
  });

  it("reads every filter of a column of the list, the bounds of both sides and the period of the last marking, and asks them under the names of the contract [WF-IHM-0130-A]", () => {
    const search = new URLSearchParams(
      [
        "code=PRJ",
        "reference_budget_min=1000.50",
        "current_estimate_max=-5",
        "win_probability_min=0.4",
        "project_manager_projection_max=20",
        "delta_to_reference_min=0",
        "cost_index_max=0.9",
        "schedule_index_min=1.1",
        "last_marked_at_from=2026-01-01T00:00:00Z",
        "last_marked_at_to=2026-04-01T00:00:00Z",
      ].join("&"),
    );
    const filters = readProjectFilters(search);
    const query = portfolioProjectsQuery({
      perimeter: readPerimeter(new URLSearchParams()),
      filters,
      offset: 0,
      query: { sort: undefined, search: undefined, size: undefined },
    });
    expect(query).toEqual({
      code: "PRJ",
      reference_budget_min: "1000.50",
      current_estimate_max: "-5",
      win_probability_min: "0.4",
      project_manager_projection_max: "20",
      delta_to_reference_min: "0",
      cost_index_max: "0.9",
      schedule_index_min: "1.1",
      last_marked_at_from: "2026-01-01T00:00:00Z",
      last_marked_at_to: "2026-04-01T00:00:00Z",
    });
    // Every one is read by the list: a filter under way reads another list.
    expect(PROJECTS_LIST.reads).toEqual(expect.arrayContaining(Object.keys(query)));
  });

  it("does not ask a bound or a text the contract would refuse", () => {
    const filters = readProjectFilters(
      new URLSearchParams(
        `reference_budget_min=abc&cost_index_max=1,5&last_marked_at_from=hier&code=${"x".repeat(51)}`,
      ),
    );
    expect(
      portfolioProjectsQuery({
        perimeter: readPerimeter(new URLSearchParams()),
        filters,
        offset: 0,
        query: { sort: undefined, search: undefined, size: undefined },
      }),
    ).toEqual({});
  });

  it("ignores an identifier of the address that is no UUID, as an absent one, by the function of the reference [WF-QUA-0010]", () => {
    expect(readPerimeter(new URLSearchParams("org_node_id=not-a-uuid")).orgNode).toBeUndefined();
    expect(readPerimeter(new URLSearchParams("org_node_id=abc_123")).orgNode).toBeUndefined();
    expect(readPerimeter(new URLSearchParams(`org_node_id=${DESIGN_OFFICE}`)).orgNode).toBe(
      DESIGN_OFFICE,
    );
  });
});
