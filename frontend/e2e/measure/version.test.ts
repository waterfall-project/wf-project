// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { momentOf } from "./report";
import { STEPS } from "./steps";
import {
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
    const report = versionReport("0.4.0", new Date("2026-11-20T10:00:00Z"), CONDITIONS, SAMPLES);
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
    const report = versionReport("0.4.0", new Date(), CONDITIONS, samples);
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

  it("names an operation the service does not serve with its epic, and no duration [WF-QUA-0060-A]", () => {
    const report = versionReport("0.4.0", new Date(), CONDITIONS, SAMPLES);
    const unserved = report.operations.filter((operation) => "unserved" in operation);
    expect(unserved).toEqual([
      { id: "indicators", objective_s: 1, unserved: "EP-10" },
      { id: "portfolio-view", objective_s: 2, unserved: "EP-11" },
    ]);
  });

  it("refuses an operation measured in a single pass, which has no dispersion to give", () => {
    const short = SAMPLES.filter(
      ({ operation, pass }) => operation !== "mark-revision" || pass === 0,
    );
    expect(() => versionReport("0.4.0", new Date(), CONDITIONS, short)).toThrow(
      /mark-revision: measured in 1 pass\(es\)/,
    );
  });

  it("refuses a version that is not numbered as the reports are named", () => {
    expect(() => versionReport("v0.4", new Date(), CONDITIONS, SAMPLES)).toThrow(/0\.4\.0/);
  });
});

describe("the steps of the browser", () => {
  it("measure each operation of a screen that the service serves [WF-QUA-0060-A]", () => {
    const measured = new Set(Object.values(OPERATION_OF_STEP));
    expect([...measured].toSorted()).toEqual([
      "filter-sort-search",
      "open-compared-grid",
      "open-grid",
      "recompute-after-entry",
      "recompute-compared",
      "workload-or-projection",
    ]);
    expect(Object.keys(OPERATION_OF_STEP)).not.toContain("planning.label");
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
