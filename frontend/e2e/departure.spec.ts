// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type CDPSession, expect, type Page, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { path, text } from "./routes";

// What leaving a grid of a thousand tasks costs the browser (US-0800, #1230): the planning, opened
// hydrated and settled, left for the screen of the revisions by the link of the navigation. The
// work is that of the main thread of the page, which Chromium counts by itself (`TaskDuration` of
// `Performance.getMetrics`, read through a session of the DevTools protocol), from the click until
// the screen reached is shown and its first effects have run; Playwright's own work in the page
// — the click, the polling of its assertions, which the DevTools protocol drives — is taken away
// (`DevToolsCommandDuration`). It is broken down into the script, the styles, the layout and the
// rest, the native work of the browser.
//
// The processor of the page is slowed four times (`Emulation.setCPUThrottlingRate`), the slowdown
// under which #1218 measured the departure, there to stand for a runner of the chain loaded by
// several paths: the measure plays alone on its machine (`playwright.config.ts`), and would
// otherwise say little of what a loaded one pays. Five departures are measured, after one that is
// not; their median is held under one second of work. On a workstation, the front built for
// production paid a median of about 180 to 215 ms under that slowdown depending on the run, 90 to 112 ms of it native work; the
// development server of Next, which the paths played against when #1218 measured the departure,
// 955 ms, of which 390 ms of native work: the development builds of React and Next — the debug
// information of each element of the payload of the server revived, `jsxDEV`, the tracks of each
// component —, not the grid itself, whose components took 18 ms to take down even there, nor its
// styles or its layout, a few tens of milliseconds.
//
// The project runs after all the other paths, alone on the machine, without trace:
// `playwright.config.ts`.
const PLANNING = path("/projects/[projectId]/revisions/[revisionId]/planning");
const REVISIONS = path("/projects/[projectId]/revisions");

/** The slowdown of the processor of the page, as #1218 measured the departure. */
const SLOWDOWN = 4;

/** The bound of the work of a departure, in milliseconds: a second (#1230). */
const BOUND = 1_000;

/** How many departures are measured, after one that is not. */
const DEPARTURES = 5;

/** The counters of the main thread the measure reads, in seconds. */
const COUNTERS = [
  "TaskDuration",
  "ScriptDuration",
  "RecalcStyleDuration",
  "LayoutDuration",
  "DevToolsCommandDuration",
] as const;

type Counters = Record<(typeof COUNTERS)[number], number>;

/** The work of a departure, in milliseconds, broken down. */
interface Work {
  readonly total: number;
  readonly script: number;
  readonly styles: number;
  readonly layout: number;
  readonly native: number;
}

/** The counters of the main thread of the page, now. */
async function counters(session: CDPSession): Promise<Counters> {
  const { metrics } = await session.send("Performance.getMetrics");
  const read = (name: string) => {
    const value = metrics.find((metric) => metric.name === name)?.value;
    if (value === undefined) {
      throw new Error(
        `the page reports no ${name} counter, the measure has nothing to hold (US-0800)`,
      );
    }
    return value;
  };
  return Object.fromEntries(COUNTERS.map((name) => [name, read(name)])) as Counters;
}

/** The work done between two readings of the counters, in milliseconds, the harness's taken away. */
function workBetween(before: Counters, after: Counters): Work {
  const spent = (name: (typeof COUNTERS)[number]) => (after[name] - before[name]) * 1_000;
  const total = spent("TaskDuration") - spent("DevToolsCommandDuration");
  const script = spent("ScriptDuration");
  return {
    total,
    script,
    styles: spent("RecalcStyleDuration"),
    layout: spent("LayoutDuration"),
    native: total - script,
  };
}

/**
 * Open the planning hydrated, wait until the page has had no request under way for half a second
 * — the screens its links lead to prefetched —, then leave it for the revisions, the processor
 * slowed, and return the work of the departure.
 */
async function depart(page: Page, session: CDPSession): Promise<Work> {
  await openHydrated(page, PLANNING);
  await page.waitForLoadState("networkidle", { timeout: WORKING });
  const name = text("functions.revisions");
  const link = page
    .getByRole("navigation", { name: text("navigation.label") })
    .getByRole("link", { name, exact: true });
  await expect(link).toBeVisible();
  await session.send("Emulation.setCPUThrottlingRate", { rate: SLOWDOWN });
  const before = await counters(session);
  await link.click();
  await expect(page).toHaveURL((url) => url.pathname === REVISIONS, { timeout: WORKING });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name, { timeout: WORKING });
  // Two frames, so that the commit of the screen reached and its first effects are counted.
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            resolve();
          });
        });
      }),
  );
  const after = await counters(session);
  await session.send("Emulation.setCPUThrottlingRate", { rate: 1 });
  return workBetween(before, after);
}

/** The median of measures, the middle one of an odd number of them. */
function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] ?? Number.NaN;
}

/** A duration in whole milliseconds. */
function ms(value: number): string {
  return `${String(Math.round(value))} ms`;
}

test("leaves the planning of a thousand tasks for another screen within a second of the work of the browser, its processor slowed four times (US-0800)", async ({
  page,
}) => {
  test.setTimeout(180_000);
  const session = await page.context().newCDPSession(page);
  await session.send("Performance.enable");
  await depart(page, session);
  const works: Work[] = [];
  for (let index = 0; index < DEPARTURES; index += 1) {
    works.push(await depart(page, session));
  }
  const of = (part: keyof Work) => median(works.map((work) => work[part]));
  const measured =
    `work ${works.map((work) => String(Math.round(work.total))).join(", ")} ms — ` +
    `median ${ms(of("total"))}: script ${ms(of("script"))}, styles ${ms(of("styles"))}, ` +
    `layout ${ms(of("layout"))}, native ${ms(of("native"))}`;
  const slowed = `slowed ${String(SLOWDOWN)} times`;
  console.log(`Leaving the planning of a thousand tasks, ${slowed}: ${measured}`);
  test.info().annotations.push({ type: "measure", description: measured });
  // A counter at zero would let the bound pass in silence.
  for (const work of works) {
    expect(
      work.total,
      "the main thread of the page counted no work, a counter at zero (US-0800)",
    ).toBeGreaterThan(0);
  }
  expect(of("total")).toBeLessThan(BOUND);
});
