// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { appendFileSync, existsSync, readFileSync } from "node:fs";

import { expect, type Page, type Request, test } from "@playwright/test";

// The second of §4.6.2 — « ouvrir une grille de planning, de devis ou de reste à engager de mille
// tâches : 1 s » —, measured on the structure of the volumes the fake back serves (EP-02/L2): a
// thousand tasks and five thousand lines, six thousand rows, for the estimate and for the
// planning alike — the fake back serves them whatever `kinds` asks, where the service will give
// the planning its tasks alone.
//
// An opening lasts from its start — the start of the navigation, for a grid opened by its
// address; the click, for a grid opened from the navigation — until the grid is usable: drawn and
// hydrated. Drawn is the first frame the browser draws with the header of its columns, the
// caption of its totals and the first row of the answer wholly within the window; hydrated, the
// first frame at which React has taken over the whole grid — the server renders its first screen,
// which may show before a click does anything —, which the test tells by the keys React gives the
// last element of the grid, the last cell of its totals (`__reactProps$…`), as it hydrates it: an
// internal of React, read here and nowhere in the front.
// The later of the two is set against the second. A script given to each document watches every frame
// for them, and writes the times it finds, as the start, on the clock of the operating system
// (`performance.timeOrigin`), which survives the document when a click loads another. Nothing of
// the harness counts: neither Playwright's round trips nor its polling.
//
// The front is built for production, and compiles nothing on demand (`playwright.config.ts`).
// Before each series of five openings, one opening is not measured: the server's first load of
// its modules does not count, and the cache of the browser is warm, as for a user who has opened
// the application. Each opening starts once the one before is wholly served, its prefetches
// included — the page has had no request under way for half a second —, which is waited for
// outside the measure; the log writes how many requests were under way as each measured opening
// started, which must be none. Every opening is set against the second; the log of the run
// writes the median and the worst, drawn and hydrated, and where the time went by the address,
// and so does the summary of the job of the chain. An opening over the second is a warning, not
// a failure: measured against the fake back, for one user, on a shared machine of the chain, it
// does not say what the service will hold — the second is held, failing, in EP-13, on the
// reference data set, with fifty users, against the real service. Once
// measured, the document is checked for a field of a node the grid does not read: the page hands
// its grid what it shows alone (`projectNodes`).
//
// The path keeps bounds of its working alone, far from the second, which measure nothing: fifteen
// seconds for a grid to become usable and for a page to settle (`WORKING`), the five seconds of
// Playwright for the address after a click, three minutes for each test. Past one, the path no
// longer works — a grid never usable, a page never settled — and fails, whatever the second.
//
// The project runs after all the other paths, alone on the machine: `playwright.config.ts`.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The objective of §4.6.2, in milliseconds. */
const OBJECTIVE = 1_000;

/** How many times a grid opens each way, once opened unmeasured. */
const OPENINGS = 5;

/**
 * How long the path waits for what it needs to go on — a grid usable, a page settled —, in
 * milliseconds: a bound of its working, far from the second, which measures nothing.
 */
const WORKING = 15_000;

/** Where the start of an opening by a click is kept: it survives a document replaced. */
const CLICKED = "wf_e2e_clicked";

/** A screen of a grid: its address, the link of the navigation to it, its grid and totals. */
interface GridScreen {
  readonly segment: string;
  readonly link: string;
  readonly grid: string;
  readonly totals: RegExp;
}

const ESTIMATE: GridScreen = {
  segment: "estimate",
  link: "Chiffrage et devis",
  grid: "Grille de devis",
  totals: /^Total — 1\s000 tâches, 5\s000 lignes$/,
};

const PLANNING: GridScreen = {
  segment: "planning",
  link: "Planification",
  grid: "Grille de planning",
  totals: /^Total — 1\s000 tâches$/,
};

/** The address of the screen of a grid. */
function address(screen: GridScreen): string {
  return `/projects/${PROJECT}/revisions/${REVISION}/${screen.segment}`;
}

/**
 * Run in each document from its start: keep the time of each click, and mark, for each grid, the
 * first frame at which its header, its totals and its first row are wholly within the window —
 * `drawn:` — and the first at which React has hydrated the last cell of its totals, the last
 * element of the grid — `hydrated:`. A
 * mark is named for the grid it marks; its detail is the time it was reached on the clock of the
 * operating system. Self-contained: Playwright hands its source to the page.
 */
function markUsableGrids(clicked: string): void {
  const marked = { drawn: new WeakSet<Element>(), hydrated: new WeakSet<Element>() };
  const inWindow = (element: Element | null): boolean => {
    if (element === null) {
      return false;
    }
    const box = element.getBoundingClientRect();
    return (
      box.height > 0 &&
      box.top >= 0 &&
      box.left >= 0 &&
      box.bottom <= window.innerHeight &&
      box.right <= window.innerWidth
    );
  };
  const reached = {
    drawn: (grid: Element): boolean =>
      inWindow(grid.querySelector("thead th")) &&
      inWindow(grid.querySelector("tfoot td")) &&
      inWindow(grid.querySelector('tbody tr[aria-rowindex="2"] td')),
    hydrated: (grid: Element): boolean => {
      const last = grid.querySelector("tfoot tr:last-child td:last-child");
      return last !== null && Object.keys(last).some((key) => key.startsWith("__reactProps$"));
    },
  };
  document.addEventListener(
    "click",
    (event) => {
      sessionStorage.setItem(clicked, String(performance.timeOrigin + event.timeStamp));
    },
    { capture: true },
  );
  const frame = () => {
    const now = performance.timeOrigin + performance.now();
    for (const grid of document.querySelectorAll('[role="grid"][aria-label]')) {
      for (const state of ["drawn", "hydrated"] as const) {
        if (!marked[state].has(grid) && reached[state](grid)) {
          marked[state].add(grid);
          performance.mark(`${state}:${grid.getAttribute("aria-label") ?? ""}`, { detail: now });
        }
      }
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/** When a grid was drawn, and when it was hydrated, on the clock of the operating system. */
interface Usable {
  readonly drawn: number;
  readonly hydrated: number;
}

/**
 * When the grid of a screen was first drawn and first hydrated in the page, on the clock of the
 * operating system, once it is both — the last time, should it have been more than once.
 */
async function usableAt(page: Page, screen: GridScreen): Promise<Usable> {
  const read = () =>
    page.evaluate((grid) => {
      const at = (state: string) => {
        const last = performance.getEntriesByName(`${state}:${grid}`, "mark").at(-1);
        return last instanceof PerformanceMark && typeof last.detail === "number"
          ? last.detail
          : null;
      };
      const drawn = at("drawn");
      const hydrated = at("hydrated");
      return drawn === null || hydrated === null ? null : { drawn, hydrated };
    }, screen.grid);
  await expect.poll(read, { timeout: WORKING }).not.toBeNull();
  return (await read()) ?? { drawn: Number.POSITIVE_INFINITY, hydrated: Number.POSITIVE_INFINITY };
}

/** How long an opening took, from its start, in milliseconds: drawn, hydrated, usable. */
interface Opening {
  readonly drawn: number;
  readonly hydrated: number;
  /** The later of the two: what is set against the second. */
  readonly usable: number;
  /**
   * For an opening by the address, where the time went: when the server had sent the whole
   * document, and when the browser had parsed it and run its scripts.
   */
  readonly phases?: { readonly served: number; readonly parsed: number };
  /** How many requests of the page were under way as the opening started: none, once settled. */
  readonly underWay: number;
}

/** An opening started at a time, the grid drawn and hydrated at others. */
function opening(started: number, { drawn, hydrated }: Usable, underWay: number): Opening {
  return {
    drawn: drawn - started,
    hydrated: hydrated - started,
    usable: Math.max(drawn, hydrated) - started,
    underWay,
  };
}

/** How long a page must have had no request under way to be settled, in milliseconds. */
const QUIET = 500;

/** The requests of a page under way, and when the last of them started or ended. */
interface Requests {
  /** How many requests are under way. */
  readonly underWay: () => number;
  /** How long no request has started nor ended, in milliseconds. */
  readonly quietFor: () => number;
}

/**
 * Follow the requests of a page as they start and end — finished or failed —, whatever document
 * sends them: a navigation within the page, a click on a link, sends its own as a new document
 * does.
 */
function followRequests(page: Page): Requests {
  const pending = new Set<Request>();
  let changed = Date.now();
  const started = (request: Request) => {
    pending.add(request);
    changed = Date.now();
  };
  const ended = (request: Request) => {
    pending.delete(request);
    changed = Date.now();
  };
  page.on("request", started);
  page.on("requestfinished", ended);
  page.on("requestfailed", ended);
  return { underWay: () => pending.size, quietFor: () => Date.now() - changed };
}

/**
 * Wait until the page has had no request under way for half a second: once the grid is hydrated,
 * its links in the navigation still ask the server for the screens they lead to (prefetching),
 * and a navigation started before they are answered would cut them, while the server still
 * renders them — the first time, loading the modules of each route —, in the time of the opening
 * it measures. Waited for between the openings, never within one.
 */
async function settle(requests: Requests): Promise<void> {
  await expect
    .poll(() => requests.underWay() === 0 && requests.quietFor() >= QUIET, {
      message: `the page settles: no request under way for ${QUIET.toString()} ms`,
      timeout: WORKING,
    })
    .toBe(true);
}

/**
 * How many requests of the page are under way as an opening starts: none, the page settled —
 * checked here, and written in the log.
 */
function underWayAtStart(requests: Requests): number {
  const underWay = requests.underWay();
  expect(underWay, "requests under way as an opening starts").toBe(0);
  return underWay;
}

/** Open the screen of a grid by its address; how long it took, and where the time went. */
async function openByAddress(page: Page, requests: Requests, screen: GridScreen): Promise<Opening> {
  const underWay = underWayAtStart(requests);
  await page.goto(address(screen), { waitUntil: "commit" });
  const usable = await usableAt(page, screen);
  const { started, served, parsed } = await page.evaluate(() => {
    const [entry] = performance.getEntriesByType("navigation");
    const timing = entry instanceof PerformanceNavigationTiming ? entry : undefined;
    return {
      started: performance.timeOrigin,
      served: timing?.responseEnd ?? Number.NaN,
      parsed: timing?.domContentLoadedEventEnd ?? Number.NaN,
    };
  });
  await settle(requests);
  return { ...opening(started, usable, underWay), phases: { served, parsed } };
}

/**
 * Open the screen of a grid from that of another, by its link in the navigation; how long it
 * took, from the click, in milliseconds.
 */
async function openByClick(
  page: Page,
  requests: Requests,
  from: GridScreen,
  to: GridScreen,
): Promise<Opening> {
  await page.goto(address(from));
  await usableAt(page, from);
  await settle(requests);
  const underWay = underWayAtStart(requests);
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: to.link })
    .click();
  const usable = await usableAt(page, to);
  const clicked = await page.evaluate((key) => Number(sessionStorage.getItem(key)), CLICKED);
  await expect(page).toHaveURL(address(to));
  await settle(requests);
  return opening(clicked, usable, underWay);
}

/** The median of some durations. */
function median(durations: readonly number[]): number {
  const sorted = durations.toSorted((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? (sorted[middle] ?? 0)
    : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}

/** Some times as the log writes them, rounded to the millisecond: the median and the worst. */
function inLog(times: readonly number[]): string {
  const rounded = (time: number) => Math.round(time).toString();
  return `median ${rounded(median(times))} ms, worst ${rounded(Math.max(...times))} ms`;
}

/** The title of what the measure writes in the summary of the job of the chain. */
const SUMMARY_TITLE = "### The second of §4.6.2";

/**
 * Write a line in the summary of the job of the chain, when there is one — a variable set but
 * empty names none —, under its title, written before the first line.
 */
function toSummary(line: string): void {
  const summary = process.env.GITHUB_STEP_SUMMARY;
  if (!summary) {
    return;
  }
  const written = existsSync(summary) ? readFileSync(summary, "utf8") : "";
  const title = written.includes(SUMMARY_TITLE) ? "" : `\n${SUMMARY_TITLE}\n\n`;
  appendFileSync(summary, `${title}${line}\n`);
}

/**
 * Write what a series of openings measured: in the log, in the summary of the job of the chain
 * when there is one, and, when an opening overran the second, as a warning of the test and of the
 * chain — never as a failure.
 */
function report(way: string, usable: readonly number[], measured: string): void {
  const worst = Math.max(...usable);
  const verdict =
    worst <= OBJECTIVE
      ? `holds the second of §4.6.2`
      : `over the second of §4.6.2 by ${Math.round(worst - OBJECTIVE).toString()} ms`;
  console.log(`${way}: ${measured}; ${verdict}`);
  toSummary(`- ${way}: ${measured}; **${verdict}**`);
  if (worst > OBJECTIVE) {
    test.info().annotations.push({ type: "warning", description: `${way}: ${verdict}` });
    if (process.env.CI !== undefined) {
      console.log(`::warning title=The second of §4.6.2::${way}: ${verdict}`);
    }
  }
}

/**
 * Open a grid some times one way, once unmeasured first, and say how long each took until the
 * grid was usable, the median and the worst, drawn and hydrated — and, by the address, the medians
 * of the phases (`report`).
 */
async function measure(way: string, open: () => Promise<Opening>): Promise<void> {
  await open();
  const openings: Opening[] = [];
  for (let count = 0; count < OPENINGS; count += 1) {
    openings.push(await open());
  }
  const usable = openings.map((measured) => measured.usable);
  const phases = openings.flatMap((measured) =>
    measured.phases === undefined ? [] : [measured.phases],
  );
  const served = phases.map((phase) => phase.served);
  const parsed = phases.map((phase) => phase.parsed);
  const rounded = (times: readonly number[]) =>
    times.map((time) => Math.round(time).toString()).join(", ");
  const where =
    phases.length === 0
      ? ""
      : `; document served at a median ${rounded([median(served)])} ms,` +
        ` parsed at ${rounded([median(parsed)])} ms`;
  report(
    way,
    usable,
    `usable ${rounded(usable)} ms — ${inLog(usable)};` +
      ` drawn ${inLog(openings.map((measured) => measured.drawn))};` +
      ` hydrated ${inLog(openings.map((measured) => measured.hydrated))}${where};` +
      ` requests under way at the start ${rounded(openings.map((measured) => measured.underWay))}`,
  );
}

/**
 * Open the screen of a grid by its address and from the navigation, and set every opening
 * against the second (`report`); then check, by the view of Playwright, that what the measure waited for is there,
 * and that the document holds no field of a node the grid does not read.
 */
async function measuresTheSecond(page: Page, screen: GridScreen, from: GridScreen) {
  const requests = followRequests(page);
  await measure(`${screen.grid}, by its address`, () => openByAddress(page, requests, screen));
  await measure(`${screen.grid}, from the navigation`, () =>
    openByClick(page, requests, from, screen),
  );

  const grid = page.getByRole("grid", { name: screen.grid });
  await expect(grid).toHaveAttribute("aria-rowcount", "6002");
  for (const shown of [
    grid.getByRole("columnheader", { name: "Libellé" }),
    grid.getByRole("gridcell", { name: screen.totals }),
    grid.getByRole("row", { name: /^1 .*Études/ }),
  ]) {
    await expect(shown).toBeInViewport({ ratio: 1 });
  }
  await page.goto(address(screen));
  expect(await page.content()).not.toContain("lineage_id");
  await settle(requests);
}

test.describe("the opening of a grid of a thousand tasks", () => {
  test.describe.configure({ timeout: 180_000 });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(markUsableGrids, CLICKED);
  });

  // US-0110 and US-0220, a declared deviation: measured, never failing on the second.
  test("measures the opening of the grid of the estimate of a thousand tasks, served by the fake back, against the objective of one second of §4.6.2", async ({
    page,
  }) => {
    await measuresTheSecond(page, ESTIMATE, PLANNING);
  });

  test("measures the opening of the grid of the planning of a thousand tasks, served by the fake back, against the objective of one second of §4.6.2", async ({
    page,
  }) => {
    await measuresTheSecond(page, PLANNING, ESTIMATE);
  });
});
