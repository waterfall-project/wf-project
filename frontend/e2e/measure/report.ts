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
 *   the API within the step, while a request of Next the step waits for was under way, read in the
 *   log of the API — each request writes, once answered, its `duration_ms` and its actor, the
 *   account that asked —: the front sends no identifier of correlation, and each user of the
 *   measure has an account of its own, so that the account and the window of the step tie a
 *   request to its step;
 * - **Next**, by difference: the time during which the server of Next was answering the browser —
 *   a document, a component tree of the server, a server action, as the browser saw them, a
 *   prefetch asked before the step too: the menu of a filter prefetches the reading its choice
 *   leads to, which a choice made before it is answered waits for — or the API was answering Next,
 *   less the part of the API;
 * - **the browser**: the rest of the step, from the gesture to the grid usable.
 *
 * The weight of the answer is what the server of Next sent the browser for the step, the bodies
 * of its answers as they came over the network. Its time and its weight count the same requests of
 * Next: those under way within the step, but a prefetch the step started itself for another screen
 * — the links of a grid hydrated prefetch the screens they lead to —, which serves a step to come,
 * and which the step does not wait for: its time is the browser's, at work meanwhile. One the step
 * started for the screen it ends on, a router asking again an entry gone stale, is waited for and
 * counts. The requests of the API made meanwhile for such a prefetch, outside the requests the step
 * waits for, count for none; those made within them still do — the log ties a request to an
 * account and a moment, not to the request of Next that made it — a limit the guide states.
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
  /** The screen it asks for, as `screenOf` writes it: the path and the query of the grid. */
  readonly path: string;
  /** Whether the router asked it ahead of a navigation (`Next-Router-Prefetch`). */
  readonly prefetch: boolean;
  /**
   * `false` when its bytes are not known: the router cut it short, or its sizes never came. Its
   * `bytes` is then 0, which says nothing of what Next sent. Known unless said otherwise.
   */
  readonly weighed?: boolean;
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
  path: string,
): FrontRequest {
  const start = timedStart > 0 ? timedStart : (asked ?? failed);
  return { start, end: failed, bytes: 0, path, prefetch, weighed: false };
}

/**
 * The screen an address asks for: its path, and its query without `_rsc`, the key the router adds
 * to each request of Next, the other parameters sorted — those of the grid, its filter, sort and
 * search. Two addresses of one path with other queries are two screens.
 */
export function screenOf(address: string): string {
  const { pathname, searchParams } = new URL(address, "http://screen.invalid");
  searchParams.delete("_rsc");
  searchParams.sort();
  const query = searchParams.toString();
  return query === "" ? pathname : `${pathname}?${query}`;
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
  /**
   * How many of the requests the step waits for have no known bytes (`FrontRequest.weighed`): when
   * any, `bytes` is a floor, not a weight, and the report leaves the sample out of its statistic.
   */
  readonly unweighed: number;
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
 * Whether the step waits for a request of Next: one the browser asked of it within the step — a
 * document, a tree of components, a server action —, or a prefetch asked before the step, which a
 * gesture made before it is answered waits for, or a prefetch the step asked itself for the screen
 * it ends on: a router whose entry of the prefetch cache has gone stale asks the screen anew, as a
 * prefetch, and waits for it — the step then waits for that request, whatever its header says.
 * Any other prefetch the step started serves a step to come, which this one does not wait for.
 */
function awaited(request: FrontRequest, step: Interval, destination: string): boolean {
  return !request.prefetch || request.start < step.start || request.path === destination;
}

/**
 * Where the time of a step went: the requests the browser made of Next within it, and those the
 * API answered for the account of its user, `actor` — no other's, the client of `getMe` included —,
 * during the requests of Next the step waits for and no other time: an API request that outlives
 * them, or runs while no such request does, is made for a prefetch of a screen to come — the links
 * of the grid prefetch the screens they lead to — and under the load of several users, queued, it
 * would cover the whole step and leave nothing to Next or the browser. `destination` is the screen
 * the step ends on, as `screenOf` writes it.
 */
export function partsOf(
  step: Interval,
  front: readonly FrontRequest[],
  api: readonly ApiRequest[],
  actor: string,
  destination = "",
): StepParts {
  const usable = step.end - step.start;
  const answered = front.filter(
    (request) => meets(request, step) && awaited(request, step, destination),
  );
  const pieces = api
    .filter((request) => request.actor === actor && meets(request, step))
    .map((request) => within(request, answered))
    .filter((parts) => parts.length > 0);
  const ownApi = pieces.flat();
  const served = covered(answered, step);
  const apiPart = covered(ownApi, step);
  return {
    usable,
    api: apiPart,
    next: served - apiPart,
    browser: usable - served,
    bytes: answered.reduce((sum, request) => sum + request.bytes, 0),
    unweighed: answered.filter((request) => request.weighed === false).length,
    apiRequests: pieces.length,
  };
}

/** The parts of a request that fall within some spans, each part a span of its own. */
function within(request: Interval, spans: readonly Interval[]): Interval[] {
  return spans
    .map(({ start, end }) => ({
      start: Math.max(start, request.start),
      end: Math.min(end, request.end),
    }))
    .filter(({ start, end }) => end > start);
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
  /**
   * The highest median of a pass less the lowest: the dispersion of the passes. None — `null` —
   * when fewer than two passes have a sample: a single pass would say 0, as a stable one would.
   */
  readonly spread: number | null;
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
 * step in that pass —; a pass without any sample has no median, and counts for nothing, so that the
 * spread may rest on fewer passes than were played, and on none.
 */
export function statisticOf(byPass: readonly (readonly number[])[]): Statistic {
  const all = byPass.flat();
  const medians = byPass.filter((pass) => pass.length > 0).map((pass) => median(pass));
  return {
    median: tenth(median(all)),
    worst: tenth(all.length === 0 ? 0 : Math.max(...all)),
    spread: medians.length < 2 ? null : tenth(Math.max(...medians) - Math.min(...medians)),
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
  /**
   * What Next sent, over the samples whose bytes are all known; `null` when none is, which says
   * nothing of the weight and is not the 0 of a download that never was.
   */
  readonly bytes: Statistic | null;
  /**
   * How many samples of the step waited for a request whose bytes are unknown, and are left out of
   * `bytes`: when any, `bytes` rests on fewer samples than `samples`, and may understate.
   */
  readonly unweighed: number;
  readonly api_requests: Statistic;
}

/**
 * Whether a step says what a part weighs: the bytes of a step that waited for a request whose
 * bytes are unknown are a floor, and a median of floors reads as a download that never was.
 */
function weighs(parts: StepParts, part: keyof StepParts): boolean {
  return part !== "bytes" || parts.unweighed === 0;
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
        sample.pass === pass && sample.parts !== undefined && weighs(sample.parts, part)
          ? [sample.parts[part]]
          : [],
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
        bytes: own.some((sample) => sample.parts !== undefined && weighs(sample.parts, "bytes"))
          ? statistic("bytes")
          : null,
        unweighed: own.filter((sample) => (sample.parts?.unweighed ?? 0) > 0).length,
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
