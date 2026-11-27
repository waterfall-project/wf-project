// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of the measures of a version (US-2300, `make measure-version`): each operation of
 * table 15 of §4.6.2 that the service serves, measured on PRJ-001 of the witness freshly loaded —
 * a thousand tasks, five lines of estimate each — under the load of fifty users, then written in
 * the form the chain confronts (`version.ts`, `tools/src/wftools/measures.py`).
 *
 * The preparation, outside the measure, makes the accounts by the operations of the contract
 * (`accounts.ts`) — fifty for the load, one for the browser —, registers them on PRJ-001, chooses
 * the tasks they write, gives the users of the load their tokens and signs the user of the browser
 * in. Then k6 plays the load (`bench/load.ts`, `load-users.ts`), and under it the browser plays the
 * journey of the grids (`steps.ts`) and opens the workload of the project, the projection of
 * expenses and the indicators of the current revision (`project-screens.ts`): one pass
 * unmeasured, as `make measure` plays one, then `E2E_MEASURE_PASSES`, each from the default
 * settings of the grids of its account. Under the same load, the background tasks: the export of
 * the planning, the import of eighteen thousand lines of actual costs, the marking of the
 * revision, `E2E_MEASURE_TASK_PASSES` times each, read at their tasks (`background.ts`); the
 * marking last, which freezes the revision the load writes — its entries are then refused, and its
 * readings go on. The load is stopped, its summary read, and the report written where `make
 * measure-version` says, with the cost of the entry of the cache of the indicators that `make
 * measure-core ONLY=indicators` wrote (`E2E_MEASURE_CACHE`).
 *
 * The measure fails on no duration: an operation past its objective is the report's to document,
 * once versioned (US-2300/L3). Only a measure that did not happen fails it: an account it cannot
 * make, a step of the journey the browser does not reach the end of — the browser is the only user
 * that measures —, a background task that fails, data below the volumes of §4.6.2, or a load that
 * did not run as asked (`load-check.ts`: no summary, readings refused, too few gestures, entries
 * refused as frozen before any marking or beyond the share of the load the revision stood
 * frozen). Not a path: it plays alone, in its project `measure-version` (`playwright.config.ts`),
 * which no goal of the chain plays.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import { type APIRequestContext, type Browser, test } from "@playwright/test";

import { LOADED } from "../bounds";
import { type LocalPerson, resetGridPreferences } from "../service/realm";
import { settle } from "../usable";
import { administratorReady, contributorsOf, measureUsers, renewedToken } from "./accounts";
import { cacheRead } from "./cache-read";
import { type Caller, caller, exportPlanning, importCosts, markRevision } from "./background";
import {
  gesturesExpected,
  type LoadSummary,
  loadFailures,
  type Refusal,
  type Volumes,
} from "./load-check";
import { placeAndTasks, prepareLoad, startLoad, stopLoad } from "./load-users";
import type { Interval } from "./report";
import { openPortfolio, PORTFOLIO_STEP } from "./portfolio-screen";
import { scaleRead } from "./scale-read";
import { portfolioReading, type PortfolioReading, type ReadingSummary } from "./scale";
import {
  journey,
  measuredRevision,
  type Player,
  PROJECT,
  signedIn,
  type Target,
  targets,
} from "./steps";
import { type Measured, OPERATION_OF_STEP, type VersionReport, versionReport } from "./version";
import { currentOf, keptReads, markedOf, type RevisionRef, revisionsOf, spread } from "./volumes";
import {
  INDICATORS_STEP,
  indicatorsFromSpending,
  SPENDING_STEP,
  spendingFromWorkload,
  WORKLOAD_STEP,
  workloadFromPlanning,
} from "./project-screens";

/** A whole number of 1 or more the environment names, or its default. */
function whole(variable: string, own: number): number {
  const named = process.env[variable];
  const chosen = named === undefined || named === "" ? own : Number(named);
  if (!Number.isInteger(chosen) || chosen < 1) {
    throw new Error(`${variable} must be a whole number of 1 or more: ${String(named)}`);
  }
  return chosen;
}

/**
 * The users of the load, beside the browser: the fifty users active of §4.6.2. Another number is
 * for a trial of the measure (the guide, "Commandes"): a report of a version is taken at fifty,
 * and says its `users` in its conditions.
 */
const USERS = whole("E2E_LOAD_USERS", 50);
/** The measured passes of the operations of a screen, and of the background tasks. */
const PASSES = whole("E2E_MEASURE_PASSES", 5);
const TASK_PASSES = whole("E2E_MEASURE_TASK_PASSES", 3);
if (PASSES < 2 || TASK_PASSES < 2) {
  throw new Error("two passes at least: a single one gives no dispersion");
}

/** A screen opened after the journey, settled after; none when it is not reached. */
async function screen(
  player: Player,
  step: string,
  open: (page: Player["page"]) => Promise<Interval>,
): Promise<{ step: string; span: Interval | undefined }> {
  try {
    const span = await open(player.page);
    await settle(player.requests, LOADED);
    return { step, span };
  } catch (error) {
    const [why = ""] = (error instanceof Error ? error.message : String(error)).split("\n");
    console.log(`${step}: not reached at ${player.page.url()} (${why})`);
    return { step, span: undefined };
  }
}

/** A background task timed in each of its passes, logged as it goes. */
async function passes(
  operation: string,
  timed: (pass: number) => Promise<number>,
): Promise<Measured[]> {
  const measured: Measured[] = [];
  for (let pass = 0; pass < TASK_PASSES; pass += 1) {
    const seconds = await timed(pass);
    console.log(`${operation}, pass ${String(pass + 1)}: ${seconds.toFixed(1)} s`);
    measured.push({ operation, pass, seconds });
  }
  return measured;
}

/** The marked revisions whose kept indicators are read at their past date. */
const KEPT_READS = 5;

/** The reads of a kept reading after its first, which is read cold apart. */
const KEPT_PASSES = 5;

/** The user of the browser, ready: signed in, its task found, the API under its token. */
interface Measurer {
  readonly person: LocalPerson;
  readonly player: Player;
  readonly target: Target;
  readonly api: Caller;
  /** The current revision of PRJ-001, which the grids open on and the load writes. */
  readonly revision: string;
  /** The marked revisions of PRJ-001, the oldest first, whose kept indicators are read. */
  readonly marked: readonly RevisionRef[];
}

/**
 * Prepare the measure, outside it: the accounts made and registered on PRJ-001, the user of the
 * browser signed in and its task found, the file of the load written.
 */
async function prepared(
  browser: Browser,
  calls: APIRequestContext,
  origin: string,
): Promise<{ measurer: Measurer; users: number; volumes: Volumes }> {
  await administratorReady(browser);
  const { users } = await measureUsers(browser, calls, USERS + 1);
  await contributorsOf(browser, calls, PROJECT, users);
  const [person, ...loaders] = users;
  if (person === undefined) {
    throw new Error("no user for the browser");
  }
  const api = caller(calls, renewedToken(browser, person));
  const revisions = await revisionsOf(api, PROJECT);
  const revision = currentOf(revisions);
  measuredRevision(revision);
  const { place, tasks, volumes } = await placeAndTasks(api, PROJECT, revision, loaders.length);
  const [player] = await signedIn(browser, [person], origin);
  const [target] = player === undefined ? [] : await targets(player, 1);
  if (player === undefined || target === undefined) {
    throw new Error("the user of the browser is not signed in, or has no task to write");
  }
  await prepareLoad(browser, loaders, place, tasks);
  console.log(
    `Prepared: ${String(loaders.length)} users of the load, the browser at ${String(target.position)}`,
  );
  const marked = markedOf(revisions);
  return {
    measurer: { person, player, target, api, revision, marked },
    users: loaders.length,
    volumes,
  };
}

/**
 * The operations of a screen, one pass unmeasured then the measured ones, each from the default
 * settings of the grids of the account; the steps the browser did not reach the end of beside.
 */
async function screens(
  browser: Browser,
  calls: APIRequestContext,
  { person, player, target }: Measurer,
): Promise<{ samples: Measured[]; unreached: Set<string> }> {
  const samples: Measured[] = [];
  const unreached = new Set<string>();
  for (let pass = -1; pass < PASSES; pass += 1) {
    console.log(`Screens, pass ${pass < 0 ? "unmeasured" : String(pass + 1)}`);
    await resetGridPreferences(browser, calls, person);
    const timed = await journey(player, target, `v${String(pass)}`);
    const steps = [
      ...timed,
      await screen(player, WORKLOAD_STEP, workloadFromPlanning),
      await screen(player, SPENDING_STEP, spendingFromWorkload),
      await screen(player, INDICATORS_STEP, indicatorsFromSpending),
      await screen(player, PORTFOLIO_STEP, openPortfolio),
    ];
    for (const { step, span } of pass < 0 ? [] : steps) {
      const operation = OPERATION_OF_STEP[step];
      if (span === undefined) {
        unreached.add(step);
      } else if (operation !== undefined) {
        samples.push({ operation, pass, seconds: (span.end - span.start) / 1000 });
      }
    }
  }
  return { samples, unreached };
}

/**
 * The background tasks, each in its passes: the export, the import, the marking last; and when the
 * first marking was asked, which froze the revision for the entries of the load (none if it never
 * did): the back refuses them from the submission of the task (409 `no_background_task_running`),
 * then once the revision is marked.
 */
async function backgroundTasks(
  { api, revision }: Measurer,
  version: string,
): Promise<{ tasks: Measured[]; frozenAt: number | undefined }> {
  let frozenAt: number | undefined;
  const exported = await passes("export-planning", () => exportPlanning(api, PROJECT, revision));
  const imported = await passes("import-costs", (pass) => importCosts(api, PROJECT, pass));
  const marked = await passes("mark-revision", async (pass) => {
    frozenAt ??= Date.now();
    return markRevision(api, PROJECT, version, pass);
  });
  return { tasks: [...exported, ...imported, ...marked], frozenAt };
}

/** How many openings of the portfolio, after the cold one, give its hot duration. */
const HOT_OPENINGS = 5;

/**
 * The portfolio opened before anything else reads it, then again: the first opening computes what
 * the cache of the indicators lacks, the others find it. Outside the load, so that the figure is
 * the cache's and not the contention's. The decision on warming it is `portfolioReading`'s.
 */
async function portfolioColdAndHot({ player }: Measurer): Promise<PortfolioReading> {
  const seconds = async () => {
    const { start, end } = await openPortfolio(player.page);
    return (end - start) / 1000;
  };
  const cold = await seconds();
  const hot: number[] = [];
  for (let opening = 0; opening < HOT_OPENINGS; opening += 1) {
    hot.push(await seconds());
  }
  const total = await player.page
    .getByRole("main")
    .getByText(/\d+ projets/)
    .first()
    .innerText();
  const projects = Number(/(\d+) projets/.exec(total)?.[1] ?? "0");
  console.log(
    `Portfolio, ${String(projects)} projects: cold ${cold.toFixed(2)} s, hot ${hot.map((value) => value.toFixed(2)).join(" ")} s`,
  );
  return portfolioReading(projects, 2, cold, hot);
}

/** The indicators kept at the past dates of marked revisions spread over the history of PRJ-001. */
async function keptAtPastDates({ api, marked }: Measurer): Promise<ReadingSummary[]> {
  return keptReads(api, PROJECT, spread(marked, KEPT_READS), KEPT_PASSES);
}

/** Write the report, and its lines in the log of the run. */
function written(report: string, measured: VersionReport): void {
  for (const operation of measured.operations) {
    console.log(
      "unserved" in operation
        ? `${operation.id}: unserved, ${operation.unserved}`
        : `${operation.id}: ${String(operation.median_s)} s (worst ${String(operation.worst_s)},` +
            ` dispersion ${String(operation.dispersion_s)}; objective ${String(operation.objective_s)} s)`,
    );
  }
  mkdirSync(dirname(report), { recursive: true });
  writeFileSync(report, `${JSON.stringify(measured, null, 2)}\n`);
  console.log(`The report of the version: ${report}`);
}

test("measures each operation of table 15 the service serves under the load of fifty users, and writes the report of the version [WF-QUA-0060-A]", async ({
  browser,
  playwright,
}, testInfo) => {
  // A bound of its working alone: an hour to prepare and to play the screens, and twenty minutes
  // for each background task of each pass.
  test.setTimeout(60 * 60_000 + 3 * TASK_PASSES * 20 * 60_000);
  const report = process.env.E2E_MEASURE_VERSION_REPORT ?? "";
  const version = process.env.E2E_MEASURE_VERSION ?? "";
  if (report === "" || version === "") {
    throw new Error(
      "E2E_MEASURE_VERSION_REPORT and E2E_MEASURE_VERSION are given by make measure-version: run it",
    );
  }
  const cache = cacheRead(process.env.E2E_MEASURE_CACHE ?? "");
  const origin = new URL(String(testInfo.project.use.baseURL)).origin;
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const { measurer, users, volumes } = await prepared(browser, calls, origin);
    const portfolio = await portfolioColdAndHot(measurer);
    const kept = await keptAtPastDates(measurer);
    console.log(`Portfolio: ${portfolio.decision}`);
    let summary: LoadSummary | undefined;
    let refusals: readonly Refusal[] = [];
    let measured: Awaited<ReturnType<typeof screens>>;
    let tasks: Measured[];
    let frozenAt: number | undefined;
    const started = Date.now();
    let stopped = started;
    let durationSeconds = 0;
    try {
      startLoad();
      measured = await screens(browser, calls, measurer);
      ({ tasks, frozenAt } = await backgroundTasks(measurer, version));
      stopped = Date.now();
      durationSeconds = (stopped - started) / 1000;
    } finally {
      ({ summary, refusals } = stopLoad());
    }
    console.log(`The load: ${JSON.stringify(summary)}, ${durationSeconds.toFixed(0)} s`);
    if (measured.unreached.size > 0) {
      const steps = [...measured.unreached].join(", ");
      throw new Error(`The journey no longer works: the browser did not reach the end of ${steps}`);
    }
    // The marking, last of the background tasks, froze the revision
    // from the asking of its first pass.
    const frozenSeconds = frozenAt === undefined ? 0 : (stopped - frozenAt) / 1000;
    const failures = loadFailures(
      summary,
      { users, duration_s: durationSeconds, frozen_s: frozenSeconds },
      refusals,
    );
    if (summary === undefined || failures.length > 0) {
      throw new Error(`The load did not run as asked: ${failures.join("; ")}`);
    }
    const conditions = {
      project: PROJECT,
      revision: measurer.revision,
      users,
      tasks: volumes.tasks,
      estimate_lines: volumes.estimate_lines,
      passes: PASSES,
      task_passes: TASK_PASSES,
      load: {
        ...summary,
        duration_s: Math.round(durationSeconds),
        gestures_expected: Math.round(gesturesExpected(users, durationSeconds)),
        refusals,
      },
    };
    written(
      report,
      versionReport(version, new Date(), conditions, [...measured.samples, ...tasks], cache, {
        portfolio,
        kept,
        scale: scaleRead(process.env.E2E_MEASURE_SCALE ?? ""),
      }),
    );
  } finally {
    await calls.dispose();
  }
});
