// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of the measures of a version (US-2300, `make measure-version`), in the form the chain
 * confronts (`tools/src/wftools/measures.py`, US-2300/L1): each operation of table 15 of §4.6.2,
 * in its order, with its objective; a served one with its median, its worst duration and its
 * dispersion, in seconds; one the service does not serve yet named with the epic that will measure
 * it, and no duration. Pure, so that its unit tests try it without a platform (`version.test.ts`).
 *
 * The operations of a screen are the steps of the journey of the grids a browser played
 * (`steps.ts`), and the workload of the project after them (`workload.ts`): to open a grid, the four
 * openings of the journey — the planning by its address, then the estimate, the remaining to commit
 * and the planning again by the navigation —; to filter, sort or search, the three gestures on the
 * estimate; to recompute after an entry, the duration that redates its task — the label entered
 * before it recomputes nothing —; the workload, its screen opened by the navigation. The three
 * background tasks are read at their task, from its submission to its end. Each pass gives a value
 * per operation, the median of its samples within the pass; the median and the worst are those of
 * every sample, and the dispersion the standard deviation of the sample (n - 1) of the values of the
 * passes, which `measures.py` names so: what a difference must exceed to be a gain.
 */
import { median } from "./report";

/** An operation of table 15: its identifier in the reports, its objective in seconds. */
interface Line {
  readonly id: string;
  readonly objective: number;
  /** The epic that will measure it, while the service does not serve it. */
  readonly unserved?: string;
}

/** Table 15, in its order: the identifiers and objectives of `measures.py`. */
export const TABLE: readonly Line[] = [
  { id: "open-grid", objective: 1 },
  { id: "recompute-after-entry", objective: 1 },
  { id: "indicators", objective: 1, unserved: "EP-10" },
  { id: "portfolio-view", objective: 2, unserved: "EP-11" },
  { id: "open-compared-grid", objective: 2, unserved: "EP-27" },
  { id: "filter-sort-search", objective: 2 },
  { id: "recompute-compared", objective: 2, unserved: "EP-27" },
  { id: "workload-or-projection", objective: 2 },
  { id: "mark-revision", objective: 60 },
  { id: "import-costs", objective: 300 },
  { id: "export-planning", objective: 30 },
];

/** The operation each step of the browser measures, by the name of the step. */
export const OPERATION_OF_STEP: Readonly<Record<string, string>> = {
  "planning.by-address": "open-grid",
  "estimate.from-planning": "open-grid",
  "remaining.from-estimate": "open-grid",
  "planning.from-remaining": "open-grid",
  "estimate.filter": "filter-sort-search",
  "estimate.sort": "filter-sort-search",
  "estimate.search": "filter-sort-search",
  "planning.duration": "recompute-after-entry",
  "workload.from-planning": "workload-or-projection",
};

/** A duration measured: the operation, the pass, in seconds. */
export interface Measured {
  readonly operation: string;
  readonly pass: number;
  readonly seconds: number;
}

/** An operation of a report: served, with its durations, or named for the epic to serve it. */
export type ReportedOperation =
  | {
      readonly id: string;
      readonly objective_s: number;
      readonly median_s: number;
      readonly worst_s: number;
      readonly dispersion_s: number;
    }
  | { readonly id: string; readonly objective_s: number; readonly unserved: string };

/** What the measure was taken under: the load, the passes, the platform. */
export interface Conditions {
  readonly project: string;
  readonly revision: string;
  /** The users of the load, beside the browser that measures. */
  readonly users: number;
  /** The tasks and the estimate lines of the revision, read at the preparation (§4.6.2). */
  readonly tasks: number;
  readonly estimate_lines: number;
  /** The passes of the operations of a screen, and of the background tasks. */
  readonly passes: number;
  readonly task_passes: number;
  /** The summary of the load, as k6 wrote it (`bench/load.ts`), with its duration and the gestures expected of it. */
  readonly load: Readonly<Record<string, number>>;
}

/** The report of a version, as `measures.py` reads it, with what the measure was taken under. */
export interface VersionReport {
  readonly version: string;
  readonly taken_at: string;
  readonly conditions: Conditions;
  readonly operations: readonly ReportedOperation[];
}

/** A duration in seconds, to the millisecond. */
function second(value: number): number {
  return Math.round(value * 1000) / 1000;
}

/** The standard deviation of a sample (n - 1); 0 for fewer than two values. */
export function sampleDeviation(values: readonly number[]): number {
  if (values.length < 2) {
    return 0;
  }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const squares = values.reduce((sum, value) => sum + (value - mean) ** 2, 0);
  return Math.sqrt(squares / (values.length - 1));
}

/**
 * The durations of a served operation: the median and the worst of its samples, the standard
 * deviation of the medians of its passes. An operation with a sample in fewer than two passes has
 * no dispersion to give, and is refused: the measure is played again, never reported short.
 */
function durations(id: string, samples: readonly Measured[]) {
  const own = samples.filter((sample) => sample.operation === id);
  const passes = [...new Set(own.map(({ pass }) => pass))].map((pass) =>
    median(own.filter((sample) => sample.pass === pass).map(({ seconds }) => seconds)),
  );
  if (passes.length < 2) {
    throw new Error(`${id}: measured in ${String(passes.length)} pass(es), two at least`);
  }
  const all = own.map(({ seconds }) => seconds);
  return {
    median_s: second(median(all)),
    worst_s: second(Math.max(...all)),
    dispersion_s: second(sampleDeviation(passes)),
  };
}

/** The report of a version from what the measure measured, every operation of table 15 in it. */
export function versionReport(
  version: string,
  takenAt: Date,
  conditions: Conditions,
  samples: readonly Measured[],
): VersionReport {
  if (!/^\d+\.\d+\.\d+$/.test(version)) {
    throw new Error(`a version is numbered as 0.4.0, not ${version}`);
  }
  const operations = TABLE.map((line): ReportedOperation => {
    const head = { id: line.id, objective_s: line.objective };
    return line.unserved === undefined
      ? { ...head, ...durations(line.id, samples) }
      : { ...head, unserved: line.unserved };
  });
  return { version, taken_at: takenAt.toISOString(), conditions, operations };
}

/** A background task as the API answers it (`BackgroundTaskRef`), as far as the measure reads it. */
export interface TaskRead {
  readonly task_id: string;
  readonly status: string;
  readonly submitted_at: string;
  readonly finished_at: string | null;
}

/** How long a background task took, from its submission to its end, in seconds, read at the task. */
export function taskSeconds(task: TaskRead, moment: (stamp: string) => number): number {
  if (task.status !== "succeeded" || task.finished_at === null) {
    throw new Error(`the task ${task.task_id} did not succeed: ${task.status}`);
  }
  return (moment(task.finished_at) - moment(task.submitted_at)) / 1000;
}
