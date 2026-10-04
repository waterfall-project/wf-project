// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  HORIZON,
  HORIZONS,
  parametersHref,
  perimeterQuery,
  readChoice,
  readPerimeter,
  statesValue,
} from "./address";

describe("the address of a view of the portfolio", () => {
  it("reads the states of a portfolio in their order, and the dates the API may take", () => {
    const perimeter = readPerimeter(
      new URLSearchParams("states=completed,lost,in_progress&from=2025-02-30&to=2026-03-31"),
    );
    expect(perimeter).toEqual({
      states: ["in_progress", "completed"],
      from: undefined,
      to: "2026-03-31",
      asOf: undefined,
    });
    expect(perimeterQuery(perimeter)).toEqual({
      states: ["in_progress", "completed"],
      to: "2026-03-31",
    });
  });

  it("asks nothing the address does not name: the server chooses", () => {
    expect(perimeterQuery(readPerimeter(new URLSearchParams()))).toEqual({});
  });

  it("reads a parameter of a view among the values it offers alone", () => {
    expect(readChoice(new URLSearchParams("horizon_months=12"), HORIZON, HORIZONS)).toBe("12");
    expect(readChoice(new URLSearchParams("horizon_months=7"), HORIZON, HORIZONS)).toBeUndefined();
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
