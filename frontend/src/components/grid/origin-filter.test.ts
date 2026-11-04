// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { originNames, originQuery, readOriginFilter } from "./origin-filter";

const RISK = "01926f3a-7c00-7000-8000-000000000752";

/** The address of a screen with a query. */
function address(query: string): URLSearchParams {
  return new URLSearchParams(query);
}

describe("the filter of a grid on the rows a risk occurred merged", () => {
  it("reads the risk the address names, and asks the server for it alone [WF-RIS-0060-A]", () => {
    const filter = readOriginFilter(address(`origin_risk_ids=${RISK}`));
    expect(filter).toEqual({ kind: "risk", risk: RISK });
    expect(originQuery(filter)).toEqual({ origin_risk_ids: [RISK] });
  });

  it("reads any risk when the address says so, and asks the server for it [WF-RIS-0060-A]", () => {
    const filter = readOriginFilter(address("is_from_risk=true"));
    expect(filter).toEqual({ kind: "any" });
    expect(originQuery(filter)).toEqual({ is_from_risk: true });
  });

  it("reads one risk when the address names both, as its filter shows one at a time", () => {
    expect(readOriginFilter(address(`is_from_risk=true&origin_risk_ids=${RISK}`))).toEqual({
      kind: "risk",
      risk: RISK,
    });
  });

  it("asks nothing when the address names nothing, or what the contract would refuse", () => {
    for (const query of ["", "is_from_risk=false", "is_from_risk=1", "origin_risk_ids=x"]) {
      const filter = readOriginFilter(address(query));
      expect(filter).toBeUndefined();
      expect(originQuery(filter)).toEqual({});
    }
  });

  it("names the risks occurred by their identifier for the marks of the rows", () => {
    const risks = [{ id: RISK, label: "Retard" }];
    expect(originNames({ risks, filter: undefined })).toEqual({ [RISK]: "Retard" });
    expect(originNames(undefined)).toBeUndefined();
  });
});
