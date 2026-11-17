// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What makes a measure of a version a measure (US-2300): the load it was taken under ran as asked,
 * and the data it was taken on have the volumes of §4.6.2. Two pure decisions, which
 * `version.measure.ts` takes once the load is stopped and once it is prepared, and which say why
 * they refuse: a load that failed as a whole — every reading refused, no user signed in, a few
 * gestures — would otherwise give a flattering report.
 */

/** What k6 says of the load once stopped (`handleSummary` of `bench/load.ts`). */
export interface LoadSummary {
  readonly users: number;
  readonly seed: number;
  /** Every gesture, readings and entries. */
  readonly gestures: number;
  readonly reads: number;
  /**
   * The readings the marking refuses (409 `STATE_FORBIDS_OPERATION`): the workload of a project
   * left without a current revision once its revision is marked.
   */
  readonly reads_frozen: number;
  /** The readings a screen did not get a full answer to, otherwise. */
  readonly reads_refused: number;
  readonly writes: number;
  /** The entries refused on a revision the measure has marked (409, the state's): its doing. */
  readonly writes_frozen: number;
  /** The entries refused otherwise. */
  readonly writes_refused: number;
  /** The gestures refused for want of a valid token (401, 403). */
  readonly unauthorised: number;
  readonly requests: number;
}

/** How the load was run, as the measure knows it. */
export interface LoadRun {
  /** The virtual users the load played. */
  readonly users: number;
  /** How long the load lasted, in seconds, from its start to its stop. */
  readonly duration_s: number;
  /**
   * How long the revision stood frozen under the load, in seconds, from the asking of the first
   * marking the measure made — the back refuses the entries from the submission of its task, while
   * it is queued or runs, then once the revision is marked — to the stop of the load; 0 when the
   * measure marked nothing. The passes after the first mark a revision opened again, in which the
   * load, which writes in its own, never enters: they extend nothing.
   */
  readonly frozen_s: number;
}

/** The share of the readings, or of the entries, that may be refused before the load is void. */
export const REFUSED_TOLERANCE = 0.01;
/**
 * The readings, and the entries, that may be refused whatever their share: one of each, counted
 * apart. A hundredth of the seventy entries of a load tolerates none, and a single refusal at
 * random would void a measure of twenty minutes; the one tolerated is named in the report
 * (`conditions.load.refusals`), and a refusal the log does not name is not tolerated this way.
 */
export const REFUSED_LEAST = 1;
/** The most refusals the report names: a load that refused more has failed. */
export const REFUSALS_REPORTED = 50;
/**
 * The share of the entries, and of the readings, beside the share of the duration the revision
 * stood frozen, that may be refused as frozen: the gestures of a user fall at random in time.
 */
export const FROZEN_SLACK = 0.1;
/** The mean pause between two gestures of a user, in seconds (`bench/draw.ts`). */
export const PAUSE_MEAN_S = 10;
/** The share of the gestures its pauses promise below which the load did not run as asked. */
export const GESTURES_LEAST_SHARE = 0.5;

/** The gestures a load of the users promises over its duration, one every ten seconds each. */
export function gesturesExpected(users: number, durationSeconds: number): number {
  return (users * durationSeconds) / PAUSE_MEAN_S;
}

/** What the load refused otherwise than by the marking, as its log names it. */
export interface Refusal {
  readonly kind: string;
  readonly name: string;
  readonly status: number;
}

/**
 * The refusals a log of k6 names, one `msg="refused <kind> <name>: <status>"` a line
 * (`bench/load.ts`), the first of them up to what the report holds.
 */
export function refusalsOf(log: string): Refusal[] {
  const refusals: Refusal[] = [];
  for (const match of log.matchAll(/msg="refused (\S+) (.+?): (\d+)"/g)) {
    refusals.push({ kind: match[1] ?? "", name: match[2] ?? "", status: Number(match[3]) });
  }
  return refusals.slice(0, REFUSALS_REPORTED);
}

/** The log of a container as `docker logs` gives it: k6 writes to its error output, after the output. */
export function logText(output: { stdout?: string | null; stderr?: string | null }): string {
  return `${output.stdout ?? ""}\n${output.stderr ?? ""}`;
}

/**
 * The refusals tolerated of gestures: a hundredth of them, rounded down, one at least — unless
 * the load refused some its log does not name (`unnamed`), the one at least being tolerated only
 * for being named.
 */
export function refusedTolerated(gestures: number, unnamed = 0): number {
  const share = Math.floor(gestures * REFUSED_TOLERANCE);
  return unnamed > 0 ? share : Math.max(share, REFUSED_LEAST);
}

/** The reasons the load did not run as asked; none when it did. */
export function loadFailures(
  summary: LoadSummary | undefined,
  run: LoadRun,
  refusals: readonly Refusal[],
): string[] {
  if (summary === undefined) {
    return ["the load wrote no summary"];
  }
  const failures: string[] = [];
  // The log is read before the stop of the load: what it refuses during the stop is counted by
  // k6 and named nowhere. Unless the report is full, such a refusal is not tolerated as isolated.
  const counted = summary.reads_refused + summary.writes_refused;
  const unnamed = refusals.length < REFUSALS_REPORTED ? Math.max(counted - refusals.length, 0) : 0;
  const allowed = (gestures: number) => refusedTolerated(gestures, unnamed);
  const tolerated = (gestures: number) =>
    `${String(allowed(gestures))} tolerated` +
    (unnamed > 0 ? `, ${String(unnamed)} refusal(s) not named` : "");
  if (summary.unauthorised !== 0) {
    failures.push(`${String(summary.unauthorised)} gestures refused for want of a valid token`);
  }
  if (summary.reads === 0 || summary.reads_refused > allowed(summary.reads)) {
    failures.push(
      `${String(summary.reads_refused)} of ${String(summary.reads)} readings refused, ${tolerated(summary.reads)}`,
    );
  }
  if (summary.writes_refused > allowed(summary.writes)) {
    failures.push(
      `${String(summary.writes_refused)} of ${String(summary.writes)} entries refused, ${tolerated(summary.writes)}`,
    );
  }
  const frozenShare = run.duration_s > 0 ? Math.min(1, run.frozen_s / run.duration_s) : 0;
  const shares = [
    { gestures: "entries", frozen: summary.writes_frozen, of: summary.writes },
    { gestures: "readings", frozen: summary.reads_frozen, of: summary.reads },
  ];
  for (const { gestures, frozen, of } of shares) {
    if (frozen > 0 && run.frozen_s <= 0) {
      failures.push(`${String(frozen)} ${gestures} refused though the revision was never frozen`);
    }
    if (frozen > of * (frozenShare + FROZEN_SLACK)) {
      failures.push(
        `${String(frozen)} of ${String(of)} ${gestures} refused as frozen, ` +
          `the revision having stood frozen ${String(Math.round(frozenShare * 100))} % of the load`,
      );
    }
  }
  const expected = gesturesExpected(run.users, run.duration_s);
  if (summary.gestures < expected * GESTURES_LEAST_SHARE) {
    failures.push(
      `${String(summary.gestures)} gestures made, ${String(Math.round(expected))} expected ` +
        `of ${String(run.users)} users in ${String(Math.round(run.duration_s))} s`,
    );
  }
  return failures;
}

/** The tasks of the witness of §4.6.2 at least: a thousand. */
export const TASKS_LEAST = 1000;
/**
 * The estimate lines of a task of the witness of §4.6.2, on average, at least: five, less what its
 * generator rounds off (the witness carries 4,999 lines on its thousand tasks).
 */
export const LINES_PER_TASK_LEAST = 4.9;

/** The volumes of the revision as the preparation read them. */
export interface Volumes {
  readonly tasks: number;
  readonly estimate_lines: number;
}

/** The reasons the data are not those of §4.6.2; none when they are. */
export function volumeFailures({ tasks, estimate_lines: lines }: Volumes): string[] {
  const failures: string[] = [];
  if (tasks < TASKS_LEAST) {
    failures.push(`${String(tasks)} tasks, ${String(TASKS_LEAST)} at least`);
  }
  if (lines < tasks * LINES_PER_TASK_LEAST) {
    failures.push(
      `${String(lines)} estimate lines on ${String(tasks)} tasks, ` +
        `${String(LINES_PER_TASK_LEAST)} a task on average at least`,
    );
  }
  return failures;
}
