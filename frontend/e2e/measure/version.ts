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
 * before it recomputes nothing —; the workload, the projection of expenses and the indicators of
 * the current revision (`project-screens.ts`), each screen opened by the navigation. The three
 * background tasks are read at their task, from its submission to its end. Each pass gives a value
 * per operation, the median of its samples within the pass; the median and the worst are those of
 * every sample, and the dispersion the standard deviation of the sample (n - 1) of the values of the
 * passes, which `measures.py` names so: what a difference must exceed to be a gain.
 */
import type { Refusal } from "./load-check";
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
  { id: "indicators", objective: 1 },
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
  "spending.from-workload": "workload-or-projection",
  "indicators.from-spending": "indicators",
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
      readonly note?: string;
      /** What the entry of the cache of the indicators costs (`indicators` only, US-2420). */
      readonly cache?: Cache;
    }
  | { readonly id: string; readonly objective_s: number; readonly unserved: string };

/** One size of the linear extrapolation of the cache to a number of subprojects. */
export interface Extrapolated {
  readonly subprojects: number;
  readonly cell_bytes: number;
  readonly cold_cell_s: number;
  readonly hot_cell_s: number;
  readonly all_bytes: number;
  readonly cold_all_s: number;
  readonly hot_all_s: number;
}

/** What the entries of the cache of the indicators of the day cost, as `measures.py` reads it. */
export interface Cache {
  readonly subprojects: number;
  readonly scopes: number;
  readonly cell_bytes: number;
  readonly all_bytes: number;
  readonly cold_cell_s: number;
  readonly hot_cell_s: number;
  readonly cold_all_s: number;
  readonly hot_all_s: number;
  readonly extrapolation: readonly Extrapolated[];
}

/** A finite number of 0 or more of an object of the JSON of the core measure, or a refusal. */
function figure(of: unknown, key: string): number {
  const value = (of as Record<string, unknown> | null)?.[key];
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new Error(
      `the cost of the cache: ${key} must be a number of 0 or more, not ${String(value)}`,
    );
  }
  return value;
}

/**
 * The cost of the entry of the cache of the indicators, read in the JSON of `make measure-core
 * ONLY=indicators` (US-2420): the facts and the rows of its measure "indicators cache". A JSON
 * without that measure, or with a figure that is no number, is refused: the report is never
 * written without what the chain asks of `indicators`.
 */
export function cacheOf(core: unknown): Cache {
  const measures = (core as { measures?: unknown } | null)?.measures;
  const found = Array.isArray(measures)
    ? (measures as readonly { name?: unknown; facts?: unknown; rows?: unknown }[]).find(
        ({ name }) => name === "indicators cache",
      )
    : undefined;
  if (found === undefined || !Array.isArray(found.rows)) {
    throw new Error('the JSON of make measure-core has no measure "indicators cache"');
  }
  const rows = found.rows as readonly unknown[];
  const facts = found.facts;
  return {
    subprojects: figure(facts, "subprojects"),
    scopes: figure(facts, "scopes"),
    cell_bytes: figure(facts, "cell_bytes"),
    all_bytes: figure(facts, "all_bytes"),
    cold_cell_s: figure(facts, "cold_cell_s"),
    hot_cell_s: figure(facts, "hot_cell_s"),
    cold_all_s: figure(facts, "cold_all_s"),
    hot_all_s: figure(facts, "hot_all_s"),
    extrapolation: rows.map((row) => ({
      subprojects: figure(row, "subprojects"),
      cell_bytes: figure(row, "cell_bytes"),
      cold_cell_s: figure(row, "cold_cell_s"),
      hot_cell_s: figure(row, "hot_cell_s"),
      all_bytes: figure(row, "all_bytes"),
      cold_all_s: figure(row, "cold_all_s"),
      hot_all_s: figure(row, "hot_all_s"),
    })),
  };
}

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
  /**
   * The summary of the load, as k6 wrote it (`bench/load.ts`), with its duration, the gestures
   * expected of it, and the refusals it names (`refusals`, the one tolerated among them).
   */
  readonly load: Readonly<Record<string, number | readonly Refusal[]>>;
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

/** What an operation measured over two screens says of itself, whatever its durations. */
const SCREENS_NOTE: Readonly<Record<string, string>> = {
  "workload-or-projection":
    "Two screens, one operation: the samples are those of the workload (getProjectWorkload) and " +
    "of the projection of expenses (getProjectSpending), each opened by the navigation, one of " +
    "each in every pass.",
};

/** A duration in seconds as a note writes it. */
function inSeconds(value: number): string {
  return `${String(second(value))} s`;
}

/**
 * The note of a served operation: what it measures when it joins screens, and, when its median
 * stands over its objective — or, for the indicators, one scope of the cache read cold —, that
 * the objective is exceeded, with the figures. A measure never fails on a duration: the note
 * documents, and an issue decides (US-2420).
 */
function noted(
  line: Line,
  served: { median_s: number; worst_s: number; dispersion_s: number },
  cache: Cache | undefined,
): { note?: string } {
  const parts: string[] = [];
  const own = SCREENS_NOTE[line.id];
  if (own !== undefined) {
    parts.push(own);
  }
  if (served.median_s > line.objective) {
    parts.push(
      `Objective exceeded: ${inSeconds(served.median_s)} for ${String(line.objective)} s at the ` +
        `median (worst ${inSeconds(served.worst_s)}, dispersion ${inSeconds(served.dispersion_s)}).`,
    );
  }
  if (cache !== undefined && cache.cold_cell_s > line.objective) {
    parts.push(
      `Objective exceeded by the entry of the cache: one scope read cold, ${inSeconds(cache.cold_cell_s)} ` +
        `for ${String(line.objective)} s (one entry by scope, #3628).`,
    );
  }
  return parts.length === 0 ? {} : { note: parts.join(" ") };
}

/**
 * The report of a version from what the measure measured, every operation of table 15 in it; the
 * cost of the entry of the cache goes with the indicators, which the service serves.
 */
export function versionReport(
  version: string,
  takenAt: Date,
  conditions: Conditions,
  samples: readonly Measured[],
  cache: Cache,
): VersionReport {
  if (!/^\d+\.\d+\.\d+$/.test(version)) {
    throw new Error(`a version is numbered as 0.4.0, not ${version}`);
  }
  const operations = TABLE.map((line): ReportedOperation => {
    const head = { id: line.id, objective_s: line.objective };
    if (line.unserved !== undefined) {
      return { ...head, unserved: line.unserved };
    }
    const served = durations(line.id, samples);
    const own = line.id === "indicators" ? cache : undefined;
    return { ...head, ...served, ...noted(line, served, own), ...(own ? { cache: own } : {}) };
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
