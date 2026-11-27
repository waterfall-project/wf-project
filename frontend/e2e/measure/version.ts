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
 * before it recomputes nothing —; to open a grid compared to a marked revision (EP-27), the four
 * openings of the grids compared to the reference — the planning by the base chosen in the banner,
 * then the estimate, the remaining to commit and the planning again by the navigation —; to
 * recompute in a grid compared, the duration entered anew there, until its marks are read anew;
 * the estimate compared is opened sorted, as the account keeps the sort of the step before
 * (`steps.ts`);
 * the workload, the projection of expenses and the indicators of the current revision
 * (`project-screens.ts`), each screen opened by the navigation. The three background tasks are read
 * at their task, from its submission to its end. Each pass gives a value per operation, the median
 * of its samples within the pass; the median and the worst are those of every sample, and the
 * dispersion the standard deviation of the sample (n - 1) of the values of the passes, which
 * `measures.py` names so: what a difference must exceed to be a gain.
 */
import type { Refusal } from "./load-check";
import { median } from "./report";
import type { PortfolioReading, ReadingSummary } from "./scale";

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
  { id: "portfolio-view", objective: 2 },
  { id: "open-compared-grid", objective: 2 },
  { id: "filter-sort-search", objective: 2 },
  { id: "recompute-compared", objective: 2 },
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
  "planning.compared": "open-compared-grid",
  "estimate.compared-from-planning": "open-compared-grid",
  "remaining.compared-from-estimate": "open-compared-grid",
  "planning.compared-from-remaining": "open-compared-grid",
  "planning.compared-duration": "recompute-compared",
  "workload.from-planning": "workload-or-projection",
  "spending.from-workload": "workload-or-projection",
  "indicators.from-spending": "indicators",
  "portfolio.view": "portfolio-view",
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
  /** What documents the scope read cold past the objective (`measures.py`: optional). */
  readonly note?: string;
}

/** The scopes of the entries of the cache beyond the subprojects: the project and its own lines. */
export const FIXED_SCOPES = 2;

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

/** A whole number of 0 or more of the JSON of the core measure, or a refusal. */
function count(of: unknown, key: string): number {
  const value = figure(of, key);
  if (!Number.isInteger(value)) {
    throw new Error(`the cost of the cache: ${key} must be a whole number, not ${String(value)}`);
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
  const read = {
    subprojects: figure(facts, "subprojects"),
    scopes: count(facts, "scopes"),
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
  if (read.extrapolation.length === 0) {
    throw new Error("the cost of the cache: extrapolation holds one size at least");
  }
  if (read.scopes !== read.subprojects + FIXED_SCOPES) {
    throw new Error(
      "the cost of the cache: scopes are the subprojects, the project and its own lines",
    );
  }
  if (read.all_bytes < read.cell_bytes) {
    throw new Error(
      "the cost of the cache: the entries of every scope weigh at least the one of the project",
    );
  }
  const sizes = read.extrapolation.map(({ subprojects }) => subprojects);
  if (sizes.some((size, index) => index > 0 && size <= (sizes[index - 1] ?? -Infinity))) {
    throw new Error(
      "the cost of the cache: the rows of extrapolation are sorted by subprojects, strictly ascending, one row per size",
    );
  }
  return read;
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
  /** The portfolio read cold then hot, and the decision on warming the cache (US-2970). */
  readonly portfolio?: PortfolioReading;
  /** The readings kept at a past date, on the platform measured (WF-DAT-0040, US-2970). */
  readonly kept?: readonly ReadingSummary[];
}

/** What a report of a version holds beside its operations, taken on a platform at volumes. */
export interface Beside {
  readonly portfolio?: PortfolioReading;
  readonly kept?: readonly ReadingSummary[];
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

/** A duration in seconds as a note writes it. */
function inSeconds(value: number): string {
  return `${String(second(value))} s`;
}

/**
 * The note of a served operation: only that its median stands over its objective, with the
 * figures — nothing otherwise, so that a note means a finding documented. A measure never fails on
 * a duration: the note documents, and an issue decides (US-2420). The scope read cold past the
 * objective is documented by the `note` of the cache, not here (`withNote`).
 */
function noted(
  line: Line,
  served: { median_s: number; worst_s: number; dispersion_s: number },
): { note?: string } {
  return served.median_s > line.objective
    ? {
        note:
          `Objective exceeded: ${inSeconds(served.median_s)} for ${String(line.objective)} s at the ` +
          `median (worst ${inSeconds(served.worst_s)}, dispersion ${inSeconds(served.dispersion_s)}).`,
      }
    : {};
}

/** The issue that decides the calculation of one scope read cold (the author's, 2026-11-17). */
const COLD_CELL_ISSUE = "#3802";

/** The cache, with the note that documents the scope read cold when it is past the objective. */
function withNote(cache: Cache, objective: number): Cache {
  if (cache.cold_cell_s <= objective) {
    return cache;
  }
  return {
    ...cache,
    note:
      `Objective exceeded by the entry of the cache: one scope read cold, ${inSeconds(cache.cold_cell_s)} ` +
      `for ${String(objective)} s (one entry by scope, #3628); the calculation of one scope cold is ` +
      `decided in ${COLD_CELL_ISSUE}.`,
  };
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
  beside: Beside = {},
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
    const own = line.id === "indicators" ? withNote(cache, line.objective) : undefined;
    return { ...head, ...served, ...noted(line, served), ...(own ? { cache: own } : {}) };
  });
  return {
    version,
    taken_at: takenAt.toISOString(),
    conditions,
    operations,
    ...(beside.portfolio ? { portfolio: beside.portfolio } : {}),
    ...(beside.kept ? { kept: beside.kept } : {}),
  };
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
