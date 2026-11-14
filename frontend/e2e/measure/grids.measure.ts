// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The measure of the journey of the grids against the service (US-2210, `make measure`): the
 * journey of `steps.ts` played by one, four and eight users at once, each with an account of its
 * own, five passes each, on the front built for production, which reaches the API directly — no
 * proxy of the contract between them, whose checking of each answer is the harness's cost, not the
 * users' —, on a platform whose witness was loaded afresh.
 *
 * The preparation makes the accounts through the operations of the contract (`accounts.ts`), and
 * signs each user in, in a browser context of its own: none of it is measured. Each level of users
 * plays one pass unmeasured first — the server's first load of its modules, the cache of the
 * browser warm, as for a user who has opened the application —, then five; before each pass, the
 * grids of each account find their default settings again (`resetGridPreferences`): a filter or a
 * sort is kept in the preferences of the account, and the next pass would start from it. The users
 * of a level start each pass together. Meanwhile, `getMe` is asked of the API once a second by a
 * client of its own, as the token of the first user, and every `getMe` the API answers within the
 * pass is read from its log.
 *
 * The report, a JSON whose form `report.ts` declares (`MeasureReport`), is written where `make
 * measure` says (`E2E_MEASURE_REPORT`): for each level, each step, the median, the worst and the
 * spread over the passes of its duration and of its three parts — the API, Next, the browser —,
 * of the bytes Next sent and of the requests the API answered; and `getMe`. The log of the run
 * writes the medians. The measure fails on no duration: only a journey that no longer works — an
 * account it cannot make, a user it cannot sign in — fails it, and a step that does not reach its
 * end is counted in the report, not failed.
 *
 * Not a path: it plays alone, in its project `measure-service` (`playwright.config.ts`), which no
 * goal of the chain plays.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import { type APIRequestContext, type Browser, test } from "@playwright/test";

import { API, frontToken, type LocalPerson, resetGridPreferences, signIn } from "../service/realm";
import { settle } from "../usable";
import { administratorReady, contributorsOf, measureUsers } from "./accounts";
import { apiAnswered, clockOffset } from "./api-log";
import {
  getMeDurations,
  getMeReport,
  type LevelReport,
  type MeasureReport,
  partsOf,
  type Sample,
  stepReports,
} from "./report";
import {
  journey,
  player,
  type Player,
  PROJECT,
  REVISION,
  STEPS,
  type Target,
  targets,
} from "./steps";

/** A whole number of 1 or more the environment names, or its default. */
function counted(variable: string, own: string): number[] {
  const named = process.env[variable];
  const values = (named === undefined || named === "" ? own : named).trim().split(/\s+/);
  return values.map((value) => {
    const chosen = Number(value);
    if (!Number.isInteger(chosen) || chosen < 1) {
      throw new Error(`${variable} must be whole numbers of 1 or more: ${String(named)}`);
    }
    return chosen;
  });
}

/** The numbers of users who play the journey at once, one level after the other. */
const LEVELS = counted("E2E_MEASURE_USERS", "1 4 8");
/** How many measured passes each level plays. */
const [PASSES = 5] = counted("E2E_MEASURE_PASSES", "5");
/** The most users of a level: the accounts the preparation makes. */
const USERS = Math.max(...LEVELS);

/** How often the client of `getMe` asks it, in milliseconds. */
const GET_ME_EVERY = 1_000;

/** Ask `getMe` as a user once a second until stopped; the round trips, in milliseconds. */
function probeGetMe(request: APIRequestContext, token: string) {
  const roundTrips: number[] = [];
  const state = { stopped: false };
  const asking = (async () => {
    while (!state.stopped) {
      const asked = performance.now();
      const answer = await request.get(`${API}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (answer.ok()) {
        roundTrips.push(performance.now() - asked);
      }
      await new Promise((resolve) => setTimeout(resolve, GET_ME_EVERY));
    }
  })();
  return async (): Promise<number[]> => {
    state.stopped = true;
    await asking;
    return roundTrips;
  };
}

/** Sign each user in, in a browser context of its own, outside the measure. */
async function signedIn(
  browser: Browser,
  users: readonly LocalPerson[],
  origin: string,
): Promise<Player[]> {
  const players: Player[] = [];
  for (const user of users) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const one = await player(page, origin);
    await signIn(page, user, "/account");
    // The screen of the account prefetches the screens its links lead to: a navigation away before
    // they are answered leaves requests the browser never ends, and the page would never settle.
    await settle(one.requests);
    players.push(one);
  }
  return players;
}

/** A user of the measure: its account, its browser, the task it writes. */
interface Member {
  readonly person: LocalPerson;
  readonly player: Player;
  readonly target: Target;
}

/** A line of the log of the run: a step at a level, its medians. */
function logged(level: LevelReport): void {
  for (const [step, report] of Object.entries(level.steps)) {
    const kib = Math.round(report.bytes.median / 1024).toString();
    console.log(
      `${String(level.users)} user(s), ${step}: usable ${String(report.usable_ms.median)} ms` +
        ` (worst ${String(report.usable_ms.worst)}, spread ${String(report.usable_ms.spread)});` +
        ` API ${String(report.api_ms.median)}, Next ${String(report.next_ms.median)},` +
        ` browser ${String(report.browser_ms.median)}; ${kib} KiB;` +
        ` ${String(report.incomplete)} incomplete`,
    );
  }
  console.log(
    `${String(level.users)} user(s), getMe: ${String(level.get_me.api_ms.median)} ms at the API` +
      ` (worst ${String(level.get_me.api_ms.worst)}), ${String(level.get_me.samples)} answered`,
  );
}

test("measures the journey of the grids against the service, at one, four and eight users at once, in three parts", async ({
  browser,
  playwright,
}, testInfo) => {
  // A bound of its working alone: five minutes a pass, a quarter of an hour to prepare.
  test.setTimeout(LEVELS.length * (PASSES + 1) * 5 * 60_000 + 15 * 60_000);
  const report = process.env.E2E_MEASURE_REPORT;
  const api = process.env.WATERFALL_API_ADDRESS;
  if (report === undefined || report === "" || api === undefined) {
    throw new Error(
      "E2E_MEASURE_REPORT and WATERFALL_API_ADDRESS are given by make measure: run it",
    );
  }
  const origin = new URL(String(testInfo.project.use.baseURL)).origin;
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    await administratorReady(browser);
    const users = await measureUsers(browser, calls, USERS);
    await contributorsOf(browser, calls, PROJECT, users);
    const offset = await clockOffset(calls, api);
    const players = await signedIn(browser, users, origin);
    const [first] = players;
    if (first === undefined) {
      throw new Error("no user to play the journey");
    }
    const written = await targets(first, USERS);
    const positions = written.map(({ position }) => String(position)).join(", ");
    console.log(`Prepared: ${String(users.length)} accounts signed in, tasks at ${positions}`);
    const team: Member[] = players.flatMap((one, index) => {
      const person = users[index];
      const target = written[index];
      return person === undefined || target === undefined ? [] : [{ person, player: one, target }];
    });
    const [lead] = team;
    if (lead === undefined) {
      throw new Error("no user to play the journey");
    }
    const levels: LevelReport[] = [];
    for (const count of LEVELS) {
      const playing = team.slice(0, count);
      const samples: Sample[] = [];
      const getMe: { api: number[][]; roundTrip: number[][] } = { api: [], roundTrip: [] };
      for (let pass = -1; pass < PASSES; pass += 1) {
        console.log(`${String(count)} user(s), pass ${pass < 0 ? "unmeasured" : String(pass + 1)}`);
        for (const { person } of playing) {
          await resetGridPreferences(browser, calls, person);
        }
        const stop = probeGetMe(calls, await frontToken(browser, lead.person));
        const from = Date.now();
        const timed = await Promise.all(
          playing.map(({ player: one, target }) =>
            journey(one, target, `${String(count)}u${String(pass)}`),
          ),
        );
        const roundTrips = await stop();
        const to = Date.now();
        if (pass < 0) {
          continue;
        }
        await Promise.all(playing.map(({ player: one }) => one.drained()));
        const answered = apiAnswered(from, to, offset);
        playing.forEach(({ person, player: one }, index) => {
          const own = answered.filter((request) => request.actor === person.id);
          for (const { step, span } of timed[index] ?? []) {
            samples.push({
              step,
              pass,
              parts: span === undefined ? undefined : partsOf(span, one.front, own),
            });
          }
        });
        getMe.api.push(getMeDurations(answered, { start: from, end: to }));
        getMe.roundTrip.push(roundTrips);
        console.log(
          `${String(count)} user(s), pass ${String(pass + 1)} read: ${String(to - from)} ms`,
        );
      }
      const level: LevelReport = {
        users: count,
        steps: stepReports(STEPS, samples, PASSES),
        get_me: getMeReport(getMe),
      };
      logged(level);
      levels.push(level);
    }
    const measured: MeasureReport = {
      measure: "grids-against-the-service",
      version: 1,
      taken_at: new Date().toISOString(),
      project: PROJECT,
      revision: REVISION,
      passes: PASSES,
      clock_offset_ms: Math.round(offset * 10) / 10,
      levels,
    };
    mkdirSync(dirname(report), { recursive: true });
    writeFileSync(report, `${JSON.stringify(measured, null, 2)}\n`);
    console.log(`The report of the measure: ${report}`);
  } finally {
    await calls.dispose();
  }
});
