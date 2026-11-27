// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { momentOf } from "./report";
import { compareScale, portfolioReading, summary } from "./scale";
import { STEPS } from "./steps";
import {
  type Cache,
  cacheOf,
  type Conditions,
  type Measured,
  OPERATION_OF_STEP,
  sampleDeviation,
  TABLE,
  taskSeconds,
  versionReport,
} from "./version";

const CONDITIONS: Conditions = {
  project: "01926f3a-7c00-7000-8000-000000000001",
  revision: "01926f3a-7c00-7000-8000-000000000102",
  users: 50,
  tasks: 1000,
  estimate_lines: 5000,
  passes: 2,
  task_passes: 2,
  load: { gestures: 600, reads_refused: 0, unauthorised: 0, duration_s: 600 },
};

/** The cost of the entry of the cache of the indicators, one scope read cold under the objective. */
const CACHE: Cache = {
  subprojects: 2,
  scopes: 4,
  cell_bytes: 15000,
  all_bytes: 48000,
  cold_cell_s: 0.4,
  hot_cell_s: 0.02,
  cold_all_s: 1.1,
  hot_all_s: 0.05,
  extrapolation: [
    {
      subprojects: 100,
      cell_bytes: 15000,
      cold_cell_s: 0.4,
      hot_cell_s: 0.02,
      all_bytes: 1100000,
      cold_all_s: 15,
      hot_all_s: 0.4,
    },
  ],
};

/** The JSON of `make measure-core ONLY=indicators`, as far as the report reads it. */
const CORE = {
  measures: [
    { name: "indicators cache, one scope, cold", facts: { entry_bytes: 1 }, rows: [] },
    {
      name: "indicators cache",
      facts: {
        subprojects: 2,
        scopes: 4,
        cell_bytes: 15000,
        all_bytes: 48000,
        cold_cell_s: 0.4,
        hot_cell_s: 0.02,
        cold_all_s: 1.1,
        hot_all_s: 0.05,
      },
      rows: [CACHE.extrapolation[0]],
    },
  ],
};

/** A duration of an operation in a pass. */
function measured(operation: string, pass: number, seconds: number): Measured {
  return { operation, pass, seconds };
}

/** Two passes of every served operation, the first a second faster than the second. */
const SAMPLES: readonly Measured[] = TABLE.filter((line) => line.unserved === undefined).flatMap(
  ({ id }) => [measured(id, 0, 1), measured(id, 1, 2)],
);

describe("versionReport", () => {
  it("names every operation of table 15 once, in its order, with its objective [WF-QUA-0060-A]", () => {
    const report = versionReport(
      "0.4.0",
      new Date("2026-11-20T10:00:00Z"),
      CONDITIONS,
      SAMPLES,
      CACHE,
    );
    expect(report.operations.map(({ id }) => id)).toEqual([
      "open-grid",
      "recompute-after-entry",
      "indicators",
      "portfolio-view",
      "open-compared-grid",
      "filter-sort-search",
      "recompute-compared",
      "workload-or-projection",
      "mark-revision",
      "import-costs",
      "export-planning",
    ]);
    expect(report.operations.map(({ objective_s: objective }) => objective)).toEqual([
      1, 1, 1, 2, 2, 2, 2, 2, 60, 300, 30,
    ]);
    expect(report.version).toBe("0.4.0");
    expect(report.taken_at).toBe("2026-11-20T10:00:00.000Z");
    expect(report.conditions.users).toBe(50);
  });

  it("gives a served operation its median, its worst and the deviation of its passes, in seconds [WF-QUA-0060-A]", () => {
    const samples = [
      measured("open-grid", 0, 0.8),
      measured("open-grid", 0, 1.2),
      measured("open-grid", 0, 0.9),
      measured("open-grid", 1, 1.4),
      measured("open-grid", 1, 1.0),
      measured("open-grid", 2, 0.7),
      ...SAMPLES.filter(({ operation }) => operation !== "open-grid"),
    ];
    const report = versionReport("0.4.0", new Date(), CONDITIONS, samples, CACHE);
    const [open] = report.operations;
    // Medians by pass: 0.9, 1.2 and 0.7; of every sample, 0.9.
    expect(open).toEqual({
      id: "open-grid",
      objective_s: 1,
      median_s: 0.95,
      worst_s: 1.4,
      dispersion_s: 0.252,
    });
  });

  it("serves the portfolio view since EP-11: a duration, no operation left unserved [US-2970]", () => {
    const report = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE);
    expect(report.operations.filter((operation) => "unserved" in operation)).toEqual([]);
    expect(report.operations.find(({ id }) => id === "portfolio-view")).toMatchObject({
      objective_s: 2,
      median_s: 1.5,
    });
  });

  it("carries the portfolio read cold and hot and the readings kept beside its operations, and nothing without them [US-2970]", () => {
    const portfolio = portfolioReading(300, 2, 1.5, [0.4, 0.5]);
    const kept = [summary("kept", 0.3, [0.2, 0.25])];
    const plain = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE);
    expect(plain).not.toHaveProperty("portfolio");
    expect(plain).not.toHaveProperty("kept");
    const beside = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE, {
      portfolio,
      kept,
    });
    expect(beside.portfolio).toEqual(portfolio);
    expect(beside.kept).toEqual(kept);
    expect(beside).not.toHaveProperty("scale");
    const platform = { projects: 5, reads: [summary("read", 0.5, [0.02, 0.03])] };
    const scale = {
      taken_at: "2026-11-27T14:16:32.913Z",
      passes: 2,
      ...compareScale(platform, { ...platform, projects: 393 }),
    };
    const compared = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE, { scale });
    expect(compared.scale).toEqual(scale);
  });

  it("carries the cost of the cache on the indicators, which the service serves, and on no other [WF-QUA-0060-A]", () => {
    const report = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE);
    const carrying = report.operations.filter((operation) => "cache" in operation);
    expect(carrying.map(({ id }) => id)).toEqual(["indicators"]);
    expect(carrying[0]).toMatchObject({ cache: CACHE, median_s: 1.5, worst_s: 2 });
  });

  it("documents in a note an objective exceeded, and says nothing of one held [WF-QUA-0060-A]", () => {
    const report = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES, CACHE);
    const notes = Object.fromEntries(
      report.operations.map((operation) => [
        operation.id,
        "note" in operation ? operation.note : undefined,
      ]),
    );
    // Every served operation of SAMPLES has a median of 1.5 s: over the second of the indicators,
    // under the 60 s of the marking.
    expect(notes.indicators).toMatch(/Objective exceeded: 1\.5 s for 1 s at the median/);
    expect(notes["mark-revision"]).toBeUndefined();
    // The operation shared by two screens has no note of its own: a median under its objective
    // documents nothing, and a standing note would document every finding of the operation.
    expect(notes["workload-or-projection"]).toBeUndefined();
  });

  it("writes no note on an operation whose median holds, whatever the screens it joins [WF-QUA-0060-A]", () => {
    const quick = TABLE.filter((line) => line.unserved === undefined).flatMap(({ id }) => [
      measured(id, 0, 0.4),
      measured(id, 1, 0.6),
    ]);
    const report = versionReport("0.4.0", new Date(), CONDITIONS, quick, CACHE);
    expect(report.operations.filter((operation) => "note" in operation)).toEqual([]);
    const indicators = report.operations.find(({ id }) => id === "indicators");
    expect(indicators !== undefined && "cache" in indicators ? indicators.cache : null).toEqual(
      CACHE,
    );
  });

  it("documents a scope read cold over the objective in the note of the cache, not of the operation [WF-QUA-0060-A]", () => {
    const quick = TABLE.filter((line) => line.unserved === undefined).flatMap(({ id }) => [
      measured(id, 0, 0.4),
      measured(id, 1, 0.6),
    ]);
    const report = versionReport("0.4.0", new Date(), CONDITIONS, quick, {
      ...CACHE,
      cold_cell_s: 1.13,
    });
    const indicators = report.operations.find(({ id }) => id === "indicators");
    expect(indicators).toBeDefined();
    expect(indicators).not.toHaveProperty("note");
    const cache = indicators !== undefined && "cache" in indicators ? indicators.cache : undefined;
    expect(cache?.note).toMatch(/one scope read cold, 1\.13 s for 1 s/);
    expect(cache?.note).toMatch(/#3802/);
  });

  it("counts a step not reached at its bound, marks it unreached and documents it, without refusing the report [US-2970]", () => {
    const quick = TABLE.filter((line) => line.unserved === undefined).flatMap(({ id }) => [
      measured(id, 0, 0.4),
      measured(id, 1, 0.6),
      measured(id, 2, 0.5),
    ]);
    // portfolio.view is missed in one pass of three: counted at its bound of 180 s, the median holds.
    const missed = quick.map((sample) =>
      sample.operation === "portfolio-view" && sample.pass === 1
        ? { ...sample, seconds: 180, unreached: "portfolio.view" }
        : sample,
    );
    const report = versionReport("0.4.0", new Date(), CONDITIONS, missed, CACHE);
    const view = report.operations.find(({ id }) => id === "portfolio-view");
    expect(view).toMatchObject({
      worst_s: 180,
      median_s: 0.5,
      unreached: [{ step: "portfolio.view", passes: 1, bound_s: 180 }],
    });
    expect(view !== undefined && "note" in view ? view.note : "").toMatch(
      /Not reached, counted at their bound: portfolio\.view in 1 pass\(es\), 180 s\./,
    );
    // The other operations say nothing of it.
    expect(
      report.operations.filter((operation) => "unreached" in operation).map(({ id }) => id),
    ).toEqual(["portfolio-view"]);
  });

  it("publishes a step not reached in any pass: its median is its bound, over its objective [US-2970]", () => {
    const quick = TABLE.filter((line) => line.unserved === undefined).flatMap(({ id }) => [
      measured(id, 0, 0.4),
      measured(id, 1, 0.6),
    ]);
    const never = [0, 1].map((pass) => ({
      operation: "workload-or-projection",
      pass,
      seconds: 180,
      unreached: "spending.from-workload",
    }));
    const samples = [
      ...quick.filter(({ operation }) => operation !== "workload-or-projection"),
      ...never,
      measured("workload-or-projection", 0, 0.5),
      measured("workload-or-projection", 1, 0.7),
    ];
    const report = versionReport("0.4.0", new Date(), CONDITIONS, samples, CACHE);
    const own = report.operations.find(({ id }) => id === "workload-or-projection");
    expect(own).toMatchObject({
      worst_s: 180,
      unreached: [{ step: "spending.from-workload", passes: 2, bound_s: 180 }],
    });
    const note = own !== undefined && "note" in own ? own.note : "";
    expect(note).toMatch(/Objective exceeded: .* for 2 s at the median/);
    expect(note).toMatch(/spending\.from-workload in 2 pass\(es\), 180 s/);
  });

  it("refuses an operation measured in a single pass, which has no dispersion to give", () => {
    const short = SAMPLES.filter(
      ({ operation, pass }) => operation !== "mark-revision" || pass === 0,
    );
    expect(() => versionReport("0.4.0", new Date(), CONDITIONS, short, CACHE)).toThrow(
      /mark-revision: measured in 1 pass\(es\)/,
    );
  });

  it("refuses a version that is not numbered as the reports are named", () => {
    expect(() => versionReport("v0.4", new Date(), CONDITIONS, SAMPLES, CACHE)).toThrow(/0\.4\.0/);
  });
});

describe("the steps of the browser", () => {
  it("measure each operation of a screen that the service serves [WF-QUA-0060-A]", () => {
    const measured = new Set(Object.values(OPERATION_OF_STEP));
    expect([...measured].toSorted()).toEqual([
      "filter-sort-search",
      "indicators",
      "open-compared-grid",
      "open-grid",
      "portfolio-view",
      "recompute-after-entry",
      "recompute-compared",
      "workload-or-projection",
    ]);
    expect(Object.keys(OPERATION_OF_STEP)).not.toContain("planning.label");
  });

  it("measure the workload and the projection of expenses as one operation, the indicators as another [WF-QUA-0060-A]", () => {
    expect(OPERATION_OF_STEP).toMatchObject({
      "workload.from-planning": "workload-or-projection",
      "spending.from-workload": "workload-or-projection",
      "indicators.from-spending": "indicators",
    });
  });

  it("measure the grids compared to a marked revision: the four openings, and the entry until its marks are read anew [WF-QUA-0060-A]", () => {
    const of = (operation: string) => STEPS.filter((step) => OPERATION_OF_STEP[step] === operation);
    expect(of("open-compared-grid")).toEqual([
      "planning.compared",
      "estimate.compared-from-planning",
      "remaining.compared-from-estimate",
      "planning.compared-from-remaining",
    ]);
    expect(of("recompute-compared")).toEqual(["planning.compared-duration"]);
  });

  it("give every step of the journey an operation of table 15, but the label, which recomputes nothing [WF-QUA-0060-A]", () => {
    const ids = new Set(TABLE.map(({ id }) => id));
    for (const step of STEPS.filter((one) => one !== "planning.label")) {
      expect(ids.has(OPERATION_OF_STEP[step] ?? "")).toBe(true);
    }
  });
});

describe("cacheOf", () => {
  it("reads the facts and the rows of the measure of the cache in the JSON of the core measure [WF-QUA-0060-A]", () => {
    expect(cacheOf(CORE)).toEqual(CACHE);
  });

  it("refuses a JSON without the measure of the cache, or with a figure that is no number [WF-QUA-0060-A]", () => {
    expect(() => cacheOf({ measures: [] })).toThrow(/indicators cache/);
    expect(() => cacheOf(null)).toThrow(/indicators cache/);
    expect(() => cacheOf(coreWith({ facts: { cold_cell_s: "1" } }))).toThrow(/cold_cell_s/);
  });

  it("refuses, as the chain does, an extrapolation that is empty [WF-QUA-0060-A]", () => {
    expect(() => cacheOf(coreWith({ rows: [] }))).toThrow(/one size at least/);
  });

  it("refuses scopes that are not the subprojects and the two of the project [WF-QUA-0060-A]", () => {
    expect(() => cacheOf(coreWith({ facts: { scopes: 5 } }))).toThrow(/scopes are the subprojects/);
  });

  it("refuses scopes that are not a whole number [WF-QUA-0060-A]", () => {
    expect(() => cacheOf(coreWith({ facts: { scopes: 4.5 } }))).toThrow(/scopes must be a whole/);
  });

  it("refuses entries of every scope that weigh less than the one of the project [WF-QUA-0060-A]", () => {
    expect(() => cacheOf(coreWith({ facts: { all_bytes: 14999 } }))).toThrow(/weigh at least/);
  });

  it("refuses rows of extrapolation that are not sorted by subprojects [WF-QUA-0060-A]", () => {
    const row = CACHE.extrapolation[0];
    expect(() =>
      cacheOf(
        coreWith({
          rows: [
            { ...row, subprojects: 200 },
            { ...row, subprojects: 100 },
          ],
        }),
      ),
    ).toThrow(/sorted by subprojects/);
  });

  it("refuses two rows of extrapolation of the same size [WF-QUA-0060-A]", () => {
    const row = CACHE.extrapolation[0];
    expect(() =>
      cacheOf(
        coreWith({
          rows: [
            { ...row, subprojects: 100 },
            { ...row, subprojects: 100 },
          ],
        }),
      ),
    ).toThrow(/strictly ascending, one row per size/);
  });
});

/** The JSON of the core measure with some of the facts, or the rows, of the cache changed. */
function coreWith(change: { facts?: Record<string, unknown>; rows?: readonly unknown[] }) {
  return {
    measures: [
      {
        name: "indicators cache",
        facts: { ...CORE.measures[1]?.facts, ...change.facts },
        rows: change.rows ?? CORE.measures[1]?.rows,
      },
    ],
  };
}

describe("sampleDeviation", () => {
  it("is the standard deviation of a sample, n - 1, and 0 for a single value", () => {
    expect(sampleDeviation([2, 4, 4, 4, 5, 5, 7, 9])).toBeCloseTo(2.138, 3);
    expect(sampleDeviation([3])).toBe(0);
  });
});

describe("taskSeconds", () => {
  const task = {
    task_id: "01926f3a-7c00-7000-8000-000000000944",
    status: "succeeded",
    submitted_at: "2026-05-04T08:25:00Z",
    finished_at: "2026-05-04T08:26:00.250000+00:00",
  };

  it("reads a background task from its submission to its end [WF-QUA-0060-A]", () => {
    expect(taskSeconds(task, momentOf)).toBe(60.25);
  });

  it("refuses a task that did not succeed", () => {
    expect(() => taskSeconds({ ...task, status: "failed" }, momentOf)).toThrow(/did not succeed/);
  });
});
