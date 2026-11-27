// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the measure of a version says of the volumes (US-2970/L2): how long a revision takes to read
 * on a platform of one project and on one of six hundred (WF-DAT-0050-A), what the readings kept at
 * a past date cost (WF-DAT-0040), and what the portfolio costs read cold and read hot, with the
 * decision about warming the cache of the indicators (EP-11, « Pas de préchauffage du cache »).
 * Durations are those of the API as a user sees them, planning included: the time from the request
 * to the whole answer, never a plan read in an `EXPLAIN`. Pure but for `timeReads`, so that the unit
 * tests try the rest without a platform (`scale.test.ts`).
 */
import type { Caller } from "./background";
import { median } from "./report";

/** The gap above which a duration is a finding, against its witness: a quarter. */
export const GAP_FINDING = 0.25;

/** A read measured: its name, its first duration (cold), then the median and worst of the others. */
export interface ReadingSummary {
  readonly name: string;
  readonly first_s: number;
  readonly median_s: number;
  readonly worst_s: number;
  readonly passes: number;
}

/** A duration in seconds, to the millisecond. */
function second(value: number): number {
  return Math.round(value * 1000) / 1000;
}

/** A gap as a fraction, to the thousandth. */
function fraction(value: number): number {
  return Math.round(value * 1000) / 1000;
}

/**
 * Time a read once cold then `passes` times: the first duration is kept apart, the median and the
 * worst are those of the passes after it. A read that does not answer 200 is refused: nothing is
 * measured of an answer that is not the reading — but for the status `leaving`, which the first
 * read may get: the read is then left out, none (a revision that kept no indicators has none to
 * read).
 */
export async function timeReads(
  api: Caller,
  name: string,
  path: string,
  passes: number,
  leaving?: number,
): Promise<ReadingSummary | undefined> {
  const seconds: number[] = [];
  for (let pass = 0; pass <= passes; pass += 1) {
    const read = await api.timed(path);
    if (pass === 0 && read.status === leaving) {
      return undefined;
    }
    if (read.status !== 200) {
      throw new Error(`${name}: GET ${path} answered ${String(read.status)}, not 200`);
    }
    seconds.push(read.seconds);
  }
  const [first = 0, ...others] = seconds;
  return summary(name, first, others);
}

/** The summary of a first duration and of the passes after it. */
export function summary(name: string, first: number, others: readonly number[]): ReadingSummary {
  if (others.length === 0) {
    throw new Error(`${name}: no pass after the first`);
  }
  return {
    name,
    first_s: second(first),
    median_s: second(median(others)),
    worst_s: second(Math.max(...others)),
    passes: others.length,
  };
}

/** One platform of the comparison: how many projects it lists (`listProjects`), and what it read. */
export interface ScalePlatform {
  readonly projects: number;
  readonly reads: readonly ReadingSummary[];
}

/** The gap of one read between the small platform and the large one. */
export interface ReadGap {
  readonly name: string;
  readonly small_median_s: number;
  readonly large_median_s: number;
  /** (large − small) ÷ small. */
  readonly gap: number;
}

/** The comparison of the reading of the same revisions on two platforms (WF-DAT-0050-A). */
export interface ScaleComparison {
  readonly small: ScalePlatform;
  readonly large: ScalePlatform;
  readonly reads: readonly ReadGap[];
  /** The gap of the sums of the medians. */
  readonly gap: number;
  /** Whether a read, or the sum, is more than a quarter apart: a finding. */
  readonly finding: boolean;
  readonly note: string;
}

/**
 * Compare the durations of the same reads on the two platforms. A read that one platform lacks
 * refuses the comparison: the same revisions are read, or nothing is said.
 */
export function compareScale(small: ScalePlatform, large: ScalePlatform): ScaleComparison {
  const names = small.reads.map(({ name }) => name);
  if (
    names.length === 0 ||
    names.length !== large.reads.length ||
    names.some((name, index) => name !== large.reads[index]?.name)
  ) {
    throw new Error("the two platforms must read the same revisions, in the same order");
  }
  const reads = small.reads.map((own, index): ReadGap => {
    const other = large.reads[index]?.median_s ?? 0;
    return {
      name: own.name,
      small_median_s: own.median_s,
      large_median_s: other,
      gap: own.median_s === 0 ? Infinity : fraction(other / own.median_s - 1),
    };
  });
  const sum = (values: readonly number[]) => values.reduce((total, value) => total + value, 0);
  const smallSum = sum(reads.map((read) => read.small_median_s));
  const largeSum = sum(reads.map((read) => read.large_median_s));
  const gap = smallSum === 0 ? Infinity : fraction(largeSum / smallSum - 1);
  const over = reads.filter((read) => Math.abs(read.gap) > GAP_FINDING);
  const finding = Math.abs(gap) > GAP_FINDING || over.length > 0;
  const percent = (value: number) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(0)} %`;
  const note =
    `The same ${String(reads.length)} revisions read on a platform listing ${String(small.projects)} ` +
    `project(s) and on one listing ${String(large.projects)}: ${String(second(smallSum))} s against ${String(second(largeSum))} s (${percent(gap)}).` +
    (finding
      ? ` A finding: a gap of more than a quarter ` +
        `${over.length > 0 ? `on ${over.map((read) => `${read.name} (${percent(read.gap)})`).join(", ")}` : "on the sum"}.`
      : " No gap of more than a quarter.");
  return { small, large, reads, gap, finding, note };
}

/** The portfolio read cold, then hot, and what that says of warming the cache. */
export interface PortfolioReading {
  /** The projects the portfolio lists. */
  readonly projects: number;
  readonly objective_s: number;
  /** The first opening after the platform started: the cache of the indicators empty. */
  readonly cold_s: number;
  /** The openings after it, the same screen again. */
  readonly hot_median_s: number;
  readonly hot_worst_s: number;
  readonly hot_passes: number;
  /** Whether warming the cache of the indicators is retained, and why. */
  readonly warming: "retained" | "not retained";
  readonly decision: string;
}

/**
 * Whether the cache of the indicators should be warmed, from the portfolio read cold and hot. Warm
 * it when the first reader pays what the objective forbids and the cache would give it back: cold
 * over the objective, hot under it. Cold within the objective: nothing to warm. Hot over the
 * objective: the cache is not what costs, and warming it would fix nothing.
 */
export function portfolioReading(
  projects: number,
  objective: number,
  cold: number,
  hot: readonly number[],
): PortfolioReading {
  const hotMedian = median(hot);
  const base = {
    projects,
    objective_s: objective,
    cold_s: second(cold),
    hot_median_s: second(hotMedian),
    hot_worst_s: second(Math.max(...hot)),
    hot_passes: hot.length,
  };
  const figures = `cold ${String(second(cold))} s, hot ${String(second(hotMedian))} s, objective ${String(objective)} s`;
  if (cold <= objective) {
    return {
      ...base,
      warming: "not retained",
      decision: `Not retained: the first reading is within the objective (${figures}).`,
    };
  }
  if (hotMedian > objective) {
    return {
      ...base,
      warming: "not retained",
      decision:
        `Not retained: hot, the portfolio is over its objective too (${figures}); ` +
        "the cache of the indicators is not what costs, warming it would not bring it back.",
    };
  }
  return {
    ...base,
    warming: "retained",
    decision:
      `Retained: the first reading is over the objective and the cache brings it back ` +
      `(${figures}); the first reader of the day pays what warming would spare.`,
  };
}
