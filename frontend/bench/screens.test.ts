// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { ESTIMATE_FIELDS } from "@/components/grid/estimate";
import { nodeFieldNames } from "@/components/grid/nodes";
import { PLANNING_FIELDS, PLANNING_KINDS } from "@/components/grid/planning";
import { REMAINING_FIELDS } from "@/components/grid/remaining";
import { readProgress } from "@/components/remaining/address";

import {
  ENTRIES,
  ESTIMATE,
  fieldNames,
  PLANNING,
  PLANNING_KINDS as LOAD_PLANNING_KINDS,
  query,
  READINGS,
  refusedByState,
  REMAINING,
  REMAINING_PROGRESS,
  taskPath,
} from "./screens";

const PLACE = {
  project: "01926f3a-7c00-7000-8000-000000000001",
  revision: "01926f3a-7c00-7000-8000-000000000102",
  structure: "s",
  workPackage: "w",
};

/** The query of the nodes a reading asks, its parameters by name. */
function nodesQuery(name: string): URLSearchParams {
  const reading = READINGS.find((one) => one.name === name);
  const asked = reading?.asks(PLACE).find((one) => one.name === "listNodes");
  return new URLSearchParams(asked?.path.split("?")[1] ?? "");
}

describe("the readings of the load", () => {
  it("ask the fields the pages of the grids ask, so that the load reads what a user reads [WF-QUA-0060-A]", () => {
    expect(fieldNames(PLANNING)).toEqual(nodeFieldNames(PLANNING_FIELDS));
    expect(fieldNames(ESTIMATE)).toEqual(nodeFieldNames(ESTIMATE_FIELDS));
    expect(fieldNames(REMAINING)).toEqual(nodeFieldNames(REMAINING_FIELDS));
    expect(LOAD_PLANNING_KINDS).toEqual(PLANNING_KINDS);
    expect(REMAINING_PROGRESS).toEqual(readProgress(new URLSearchParams()));
  });

  it("read each screen of the journey of the grids on its structure [WF-QUA-0060-A]", () => {
    expect(READINGS.map(({ name }) => name)).toEqual([
      "planning",
      "estimate",
      "estimate.filter",
      "estimate.sort",
      "estimate.search",
      "remaining",
      "workload",
    ]);
    expect(nodesQuery("planning").get("kinds")).toBe("task");
    expect(nodesQuery("planning").get("fields")?.split(",")).toEqual(
      nodeFieldNames(PLANNING_FIELDS),
    );
    expect(nodesQuery("estimate.filter").get("work_package_id")).toBe("w");
    expect(nodesQuery("estimate.sort").get("sort_by")).toBe("base_amount");
    expect(nodesQuery("estimate.search").get("search")).toBe("revue");
    expect(nodesQuery("remaining").get("progress")).toBe("started");
    const [structures, nodes] = READINGS[0]?.asks(PLACE) ?? [];
    expect(structures?.path).toBe(
      `/projects/${PLACE.project}/revisions/${PLACE.revision}/structures`,
    );
    expect(nodes?.path).toMatch(/\/structures\/s\/nodes\?/);
    const workload = READINGS.at(-1)
      ?.asks(PLACE)
      .map(({ name }) => name);
    expect(workload).toEqual(["getProjectWorkload", "listOrgNodes", "listRevisions"]);
  });
});

describe("query", () => {
  it("joins a list by commas under its name, as the contract declares it, and escapes each value", () => {
    expect(query({ fields: ["a", "task.b"], search: "revue de projet" })).toBe(
      "?fields=a,task.b&search=revue%20de%20projet",
    );
    expect(query({})).toBe("");
  });
});

describe("refusedByState", () => {
  it("tells the 409 of a state from any other refusal [WF-QUA-0060-A]", () => {
    const state = { code: "STATE_FORBIDS_OPERATION", status: 409, params: { state: "pricing" } };
    expect(refusedByState(409, state)).toBe(true);
    expect(refusedByState(409, { ...state, code: "ALREADY_EXISTS" })).toBe(false);
    expect(refusedByState(409, null)).toBe(false);
    expect(refusedByState(409, "STATE_FORBIDS_OPERATION")).toBe(false);
    expect(refusedByState(412, state)).toBe(false);
    expect(refusedByState(500, state)).toBe(false);
  });
});

describe("the entries of the load", () => {
  it("write the label of the task, then its duration, seven or eight days in turn", () => {
    const task = { node: "n", label: "Câblage" };
    expect(ENTRIES.map(({ name }) => name)).toEqual(["label", "duration"]);
    expect(ENTRIES[0]?.body(task, 3)).toEqual({ label: "Câblage · 3" });
    expect(ENTRIES[1]?.body(task, 2)).toEqual({ duration: { value: "7", unit: "d" } });
    expect(ENTRIES[1]?.body(task, 3)).toEqual({ duration: { value: "8", unit: "d" } });
    expect(taskPath(PLACE, task)).toBe(
      `/projects/${PLACE.project}/revisions/${PLACE.revision}/structures/s/nodes/n/task`,
    );
  });
});
