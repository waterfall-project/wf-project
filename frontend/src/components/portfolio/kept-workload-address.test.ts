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

  it("restores the settings an address leaves out, and keeps the node it names [WF-PTF-0060-A]", () => {
    const query = new URLSearchParams(at("org_node_id=node-2")?.split("?")[1]);
    expect(Object.fromEntries(query)).toEqual({ ...KEPT, org_node_id: "node-2" });
    const threshold = new URLSearchParams(at("under_load_threshold=0.3")?.split("?")[1]);
    expect(Object.fromEntries(threshold)).toEqual({ ...KEPT, under_load_threshold: "0.3" });
  });

  it("leaves an address that names every setting as it is, and does not loop [WF-PTF-0060-A]", () => {
    expect(at("horizon_months=24&under_load_threshold=0.3&org_node_id=node-2")).toBeUndefined();
    const target = at("org_node_id=node-2") ?? "";
    expect(at(target.split("?")[1] ?? "")).toBeUndefined();
  });

  it("takes a setting written empty, the default, as written [WF-PTF-0060-A]", () => {
    expect(at("horizon_months=&under_load_threshold=0.3&org_node_id=n")).toBeUndefined();
    const query = new URLSearchParams(at("horizon_months=")?.split("?")[1]);
    expect(Object.fromEntries(query)).toEqual({ ...KEPT, horizon_months: "" });
  });

  it("leaves the address alone when nothing is kept for what it leaves out [WF-PTF-0060-A]", () => {
    expect(at("", null)).toBeUndefined();
    expect(at("", {})).toBeUndefined();
    expect(at("horizon_months=24", { horizon_months: "12" })).toBeUndefined();
  });

  it("writes empty each setting a change would remove, so that the default is not restored [WF-PTF-0060-A]", () => {
    expect(spokenHref("/portfolio/workload?states=completed", WORKLOAD_KEPT)).toBe(
      "/portfolio/workload?states=completed&horizon_months=&under_load_threshold=&org_node_id=",
    );
    const full = "/portfolio/workload?org_node_id=n&horizon_months=12&under_load_threshold=0.5";
    expect(spokenHref(full, WORKLOAD_KEPT)).toBe(full);
  });
});
