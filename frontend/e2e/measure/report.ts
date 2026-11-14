// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The arithmetic of the measure of the journey of the grids against the service (US-2210): where
 * the time of a step went, read from the requests the browser saw and from the log of the API, and
 * the report of the passes. Pure, so that its unit tests try it without a platform
 * (`report.test.ts`).
 *
 * A step lasts from its gesture to the grid drawn and hydrated (`usable.ts`). Its time splits in
 * three parts:
 *
 * - **the API**: the time during which at least one request of the user's account was under way at
 *   the API within the step, read in the log of the API — each request writes, once answered, its
 *   `duration_ms` and its actor, the account that asked —: the front sends no identifier of
 *   correlation, and each user of the measure has an account of its own, so that the account and
 *   the window of the step tie a request to its step;
 * - **Next**, by difference: the time during which the server of Next was answering the browser —
 *   a document, a component tree of the server, a server action, as the browser saw them, a
 *   prefetch asked before the step too: the menu of a filter prefetches the reading its choice
 *   leads to, which a choice made before it is answered waits for — or the API was answering Next,
 *   less the part of the API;
 * - **the browser**: the rest of the step, from the gesture to the grid usable.
 *
 * The weight of the answer is what the server of Next sent the browser for the step, the bodies
 * of its answers as they came over the network. Its time and its weight count the same requests of
 * Next: those under way within the step, but a prefetch the step started itself — the links of a
 * grid hydrated prefetch the screens they lead to —, which serves a step to come, and which the step
 * does not wait for: its time is the browser's, at work meanwhile. The requests of the API such a
 * prefetch makes stay in the part of the API all the same: the log ties a request to an account and
 * a moment, not to the request of Next that made it — a limit the guide states.
 *
 * Five passes give the dispersion: for each step, the median and the worst of every sample of the
 * passes, and the spread, the gap between the highest and the lowest median of a pass — what a
 * difference must exceed to be told a gain or a loss, which this report never says.
 */

/** A span of time, in milliseconds since the epoch, on the clock of the workstation. */
export interface Interval {
  readonly start: number;
  readonly end: number;
}

/** A request the browser made of the server of Next, and the bytes of its answer. */
export interface FrontRequest extends Interval {
  readonly bytes: number;
  /** Whether the router asked it ahead of a navigation (`Next-Router-Prefetch`). */
  readonly prefetch: boolean;
}

/**
 * A request of Next the browser gave up — a navigation that took the place of another, a prefetch
 * it left behind —, waited for until it failed, and none of its bytes. Its timing gives its start
 * only once an answer came: for one that failed before any, it is 0, and the start is the moment
 * the page asked it, as the measure kept it — failing that, the failure itself, so that it covers
 * nothing rather than every step before it.
 */
export function failedRequest(
  timedStart: number,
  asked: number | undefined,
  failed: number,
  prefetch: boolean,
): FrontRequest {
  const start = timedStart > 0 ? timedStart : (asked ?? failed);
  return { start, end: failed, bytes: 0, prefetch };
}

/** A request the API answered, as its log writes it. */
export interface ApiRequest extends Interval {
  /** The account that asked: its identifier in Waterfall, or `anonymous`, or `platform`. */
  readonly actor: string;
  readonly method: string;
  readonly path: string;
  readonly status: number;
}

/** How the time of a step splits, in milliseconds, and what the server of Next sent. */
export interface StepParts {
  readonly usable: number;
  readonly api: number;
  readonly next: number;
  readonly browser: number;
  readonly bytes: number;
  /** How many requests of the account the API answered within the step. */
  readonly apiRequests: number;
}

/** Whether two spans of time meet. */
function meets(one: Interval, other: Interval): boolean {
  return one.start < other.end && other.start < one.end;
}

/** How long some spans cover within a window, each instant counted once. */
export function covered(spans: readonly Interval[], window: Interval): number {
  const clipped = spans
    .map(({ start, end }) => ({
      start: Math.max(start, window.start),
      end: Math.min(end, window.end),
    }))
    .filter(({ start, end }) => end > start)
    .toSorted((a, b) => a.start - b.start);
  let total = 0;
  let reached = Number.NEGATIVE_INFINITY;
  for (const { start, end } of clipped) {
    if (end > reached) {
      total += end - Math.max(start, reached);
      reached = end;
    }
  }
  return total;
}

/**
 * Where the time of a step went: the requests the browser made of Next within it, and those the
 * API answered for the account of its user, `actor` — no other's, the client of `getMe` included.
 */
export function partsOf(
  step: Interval,
  front: readonly FrontRequest[],
  api: readonly ApiRequest[],
  actor: string,
): StepParts {
  const usable = step.end - step.start;
  const ownFront = front.filter((request) => meets(request, step));
  const answered = ownFront.filter((request) => !request.prefetch || request.start < step.start);
  const ownApi = api.filter((request) => request.actor === actor && meets(request, step));
  const served = covered([...answered, ...ownApi], step);
  const apiPart = covered(ownApi, step);
  return {
    usable,
    api: apiPart,
    next: served - apiPart,
    browser: usable - served,
    bytes: answered.reduce((sum, request) => sum + request.bytes, 0),
    apiRequests: ownApi.length,
  };
}

/** The structured record the API writes once it has answered a request (`request.completed`). */
interface Completed {
  readonly event?: unknown;
  readonly timestamp?: unknown;
  readonly duration_ms?: unknown;
  readonly actor?: unknown;
  readonly method?: unknown;
  readonly path?: unknown;
  readonly status?: unknown;
}

/**
 * The moment of a record of the API, in milliseconds since the epoch: its time in ISO 8601, in UTC,
 * whose fraction of a second may run to the microsecond, which `Date.parse` would cut.
 */
export function momentOf(timestamp: string): number {
  const found = /^(.+T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(?:Z|\+00:00)$/.exec(timestamp);
  if (found === null) {
    return Number.NaN;
  }
  const [, seconds = "", fraction = ""] = found;
  return Date.parse(`${seconds}Z`) + (fraction === "" ? 0 : Number(`0.${fraction}`) * 1000);
}

/**
 * The requests the API answered, read from its log: one record of JSON a line, of which only those
 * that close a request count. A record is written as its answer ends: the request spans its
 * duration before it. `offset` is how far the clock of the API is ahead of the workstation's.
 */
export function apiRequests(log: string, offset = 0): ApiRequest[] {
  const requests: ApiRequest[] = [];
  for (const line of log.split("\n")) {
    const start = line.indexOf("{");
    if (start < 0) {
      continue;
    }
    let record: Completed;
    try {
      record = JSON.parse(line.slice(start)) as Completed;
    } catch {
      continue;
    }
    const { event, timestamp, duration_ms: duration, actor, method, path, status } = record;
    if (
      event !== "request.completed" ||
      typeof timestamp !== "string" ||
      typeof duration !== "number"
    ) {
      continue;
    }
    const end = momentOf(timestamp) - offset;
    if (Number.isNaN(end)) {
      continue;
    }
    requests.push({
      start: end - duration,
      end,
      actor: typeof actor === "string" ? actor : "",
      method: typeof method === "string" ? method : "",
      path: typeof path === "string" ? path : "",
      status: typeof status === "number" ? status : 0,
    });
  }
  return requests;
}

/** The median, the worst and the spread of a quantity over the passes. */
export interface Statistic {
  readonly median: number;
  readonly worst: number;
  /** The highest median of a pass less the lowest: the dispersion of the passes. */
  readonly spread: number;
}

/**
 * The median of some values; 0 for none. The one median of the measures: that of the second
 * against the fake back (`opening.spec.ts`) is this one too.
 */
export function median(values: readonly number[]): number {
  const sorted = values.toSorted((a, b) => a - b);
  const half = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? (sorted[half] ?? 0)
    : ((sorted[half - 1] ?? 0) + (sorted[half] ?? 0)) / 2;
}

/** A value of the report, to the tenth. */
function tenth(value: number): number {
  return Math.round(value * 10) / 10;
}

/**
 * The statistic of a quantity, its samples given by pass — one for each user who completed the
 * step in that pass —; a pass without any sample has no median, and counts for nothing.
 */
export function statisticOf(byPass: readonly (readonly number[])[]): Statistic {
  const all = byPass.flat();
  const medians = byPass.filter((pass) => pass.length > 0).map((pass) => median(pass));
  return {
    median: tenth(median(all)),
    worst: tenth(all.length === 0 ? 0 : Math.max(...all)),
    spread: tenth(medians.length === 0 ? 0 : Math.max(...medians) - Math.min(...medians)),
  };
}

/** A step a user played in a pass: its parts, or none when it did not reach its end. */
export interface Sample {
  readonly step: string;
  readonly pass: number;
  readonly parts: StepParts | undefined;
}

/** What the report says of a step, at a number of users. */
export interface StepReport {
  readonly samples: number;
  /** How many times a user did not reach the end of the step: none in a sound run. */
  readonly incomplete: number;
  readonly usable_ms: Statistic;
  readonly api_ms: Statistic;
  readonly next_ms: Statistic;
  readonly browser_ms: Statistic;
  readonly bytes: Statistic;
  readonly api_requests: Statistic;
}

/** The statistic of one part of the samples of a step, by pass. */
function partStatistic(
  samples: readonly Sample[],
  passes: number,
  part: keyof StepParts,
): Statistic {
  return statisticOf(
    Array.from({ length: passes }, (_, pass) =>
      samples.flatMap((sample) =>
        sample.pass === pass && sample.parts !== undefined ? [sample.parts[part]] : [],
      ),
    ),
  );
}

/** What the report says of each step, in the order of the journey, from the samples of a level. */
export function stepReports(
  steps: readonly string[],
  samples: readonly Sample[],
  passes: number,
): Record<string, StepReport> {
  return Object.fromEntries(
    steps.map((step) => {
      const own = samples.filter((sample) => sample.step === step);
      const statistic = (part: keyof StepParts) => partStatistic(own, passes, part);
      const report: StepReport = {
        samples: own.filter((sample) => sample.parts !== undefined).length,
        incomplete: own.filter((sample) => sample.parts === undefined).length,
        usable_ms: statistic("usable"),
        api_ms: statistic("api"),
        next_ms: statistic("next"),
        browser_ms: statistic("browser"),
        bytes: statistic("bytes"),
        api_requests: statistic("apiRequests"),
      };
      return [step, report];
    }),
  );
}

/**
 * The durations of `getMe` a level saw, by pass: at the API, and as its client asked it; and how
 * many times its client got no answer of success.
 */
export interface GetMeSamples {
  readonly api: readonly (readonly number[])[];
  readonly roundTrip: readonly (readonly number[])[];
  readonly lost: number;
}

/** What the report says of `getMe` at a number of users. */
export interface GetMeReport {
  readonly samples: number;
  /** How many times the client of `getMe` got no answer of success: none in a sound run. */
  readonly lost: number;
  readonly api_ms: Statistic;
  readonly round_trip_ms: Statistic;
}

/** The report of `getMe` at a level. */
export function getMeReport({ api, roundTrip, lost }: GetMeSamples): GetMeReport {
  return {
    samples: api.flat().length,
    lost,
    api_ms: statisticOf(api),
    round_trip_ms: statisticOf(roundTrip),
  };
}

/** What the report says of a number of users playing the journey at once. */
export interface LevelReport {
  readonly users: number;
  readonly steps: Record<string, StepReport>;
  readonly get_me: GetMeReport;
}

/**
 * The steps a user alone did not complete, in the order of the journey: a journey that no longer
 * works — a link renamed, a grid that never shows —, which fails the measure once its report is
 * written. Under the load of four or eight users, a step not completed is the measure of that load,
 * counted and never failed.
 */
export function brokenSteps(levels: readonly LevelReport[]): string[] {
  return levels
    .filter((level) => level.users === 1)
    .flatMap((level) =>
      Object.entries(level.steps).flatMap(([step, report]) =>
        report.incomplete > 0 ? [step] : [],
      ),
    );
}

/** The report of a measure, written as JSON: its form, which `version` names, is this lot's. */
export interface MeasureReport {
  readonly measure: "grids-against-the-service";
  readonly version: 1;
  /** When the measure ended, in ISO 8601. */
  readonly taken_at: string;
  readonly project: string;
  readonly revision: string;
  readonly passes: number;
  /** How far the clock of the API was found ahead of the workstation's, in milliseconds. */
  readonly clock_offset_ms: number;
  readonly levels: readonly LevelReport[];
}

/** The durations of `getMe` at the API within a span, whoever asked: `GET /api/v1/me`. */
export function getMeDurations(requests: readonly ApiRequest[], span: Interval): number[] {
  return requests
    .filter(
      (request) =>
        request.method === "GET" && request.path === "/api/v1/me" && meets(request, span),
    )
    .map((request) => request.end - request.start);
}
