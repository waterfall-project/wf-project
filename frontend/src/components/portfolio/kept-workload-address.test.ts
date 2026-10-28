// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { spokenHref } from "@/components/grid/kept-address";

import { restoredWorkload, WORKLOAD_KEPT } from "./kept-workload-address";

const KEPT = { horizon_months: "12", under_load_threshold: "0.5", org_node_id: "node-1" };

/** The address a consultation of the workload leads to, at the query given. */
function at(query: string, kept: Record<string, string> | null = KEPT) {
  return restoredWorkload(new URLSearchParams(query), kept);
}

describe("the address the aggregated workload leads to", () => {
  it("finds the horizon, the threshold and the node kept when the address names none of them [WF-PTF-0060-A]", () => {
    const query = new URLSearchParams(at("")?.split("?")[1]);
    expect(Object.fromEntries(query)).toEqual(KEPT);
  });

  it("carries the states and the dates of the perimeter over, and keeps none of them [WF-PTF-0060-A]", () => {
    const query = new URLSearchParams(at("states=completed&as_of=2026-06-01")?.split("?")[1]);
    expect(Object.fromEntries(query)).toEqual({
      ...KEPT,
      states: "completed",
      as_of: "2026-06-01",
    });
  });

  it("leaves an address that names one of the three as it is [WF-PTF-0060-A]", () => {
    expect(at("horizon_months=24")).toBeUndefined();
    expect(at("under_load_threshold=0.3")).toBeUndefined();
    expect(at("org_node_id=node-2")).toBeUndefined();
  });

  it("leaves the address alone when nothing is kept, or when the reading was lifted [WF-PTF-0060-A]", () => {
    expect(at("", null)).toBeUndefined();
    expect(at("", {})).toBeUndefined();
    expect(at("horizon_months=")).toBeUndefined();
  });

  it("says the horizon lifted when a change would leave the address naming none, so that the default can be chosen [WF-PTF-0060-A]", () => {
    expect(spokenHref("/portfolio/workload?states=completed", WORKLOAD_KEPT)).toBe(
      "/portfolio/workload?states=completed&horizon_months=",
    );
    expect(spokenHref("/portfolio/workload?org_node_id=n", WORKLOAD_KEPT)).toBe(
      "/portfolio/workload?org_node_id=n",
    );
  });
});
