// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

// The second of §4.6.2 — « ouvrir une grille de planning, de devis ou de reste à engager de mille
// tâches : 1 s » —, measured on the structure of the volumes the fake back serves (EP-02/L2): a
// thousand tasks and five thousand lines, six thousand rows, for the estimate and for the
// planning alike — the fake back serves them whatever `kinds` asks, where the service will give
// the planning its tasks alone.
//
// An opening lasts from its start — the start of the navigation, for a grid opened by its
// address; the click, for a grid opened from the navigation — to the first frame the browser
// draws with the grid usable: the header of its columns, the caption of its totals and the first
// row of the answer wholly within the window. A script given to each document watches every frame
// for it, and writes the time it finds, as the start, on the clock of the operating system
// (`performance.timeOrigin`), which survives the document when a click loads another. Nothing of
// the harness counts: neither Playwright's round trips nor its polling. Each grid opens once
// before it is measured, so that the server's first load of its modules does not count — the
// front is built for production, and compiles nothing on demand (`playwright.config.ts`) —,
// then five times each way, and every opening must hold the second: the median and the worst are
// written in the log of the run.
//
// The project runs after all the other paths, alone on the machine: `playwright.config.ts`.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The objective of §4.6.2, in milliseconds. */
const OBJECTIVE = 1_000;

/** How many times a grid opens each way, once opened unmeasured. */
const OPENINGS = 5;

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
 * first frame at which its header, its totals and its first row are wholly within the window.
 * A mark is named for the grid it marks; its detail is the time it was reached on the clock of
 * the operating system. Self-contained: Playwright hands its source to the page.
 */
function markUsableGrids(clicked: string): void {
  const marked = new WeakSet<Element>();
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
  const usable = (grid: Element): boolean =>
    inWindow(grid.querySelector("thead th")) &&
    inWindow(grid.querySelector("tfoot td")) &&
    inWindow(grid.querySelector('tbody tr[aria-rowindex="2"] td'));
  document.addEventListener(
    "click",
    (event) => {
      sessionStorage.setItem(clicked, String(performance.timeOrigin + event.timeStamp));
    },
    { capture: true },
  );
  const frame = () => {
    for (const grid of document.querySelectorAll('[role="grid"][aria-label]')) {
      if (!marked.has(grid) && usable(grid)) {
        marked.add(grid);
        performance.mark(`usable:${grid.getAttribute("aria-label") ?? ""}`, {
          detail: performance.timeOrigin + performance.now(),
        });
      }
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/**
 * When the grid of a screen was first usable in the page, on the clock of the operating system,
 * once it is — the last time, should it have been more than once.
 */
async function usableAt(page: Page, screen: GridScreen): Promise<number> {
  const read = () =>
    page.evaluate((name) => {
      const marks = performance.getEntriesByName(name, "mark");
      const last = marks.at(-1);
      return last instanceof PerformanceMark && typeof last.detail === "number"
        ? last.detail
        : null;
    }, `usable:${screen.grid}`);
  await expect.poll(read, { timeout: 15_000 }).not.toBeNull();
  return (await read()) ?? Number.POSITIVE_INFINITY;
}

/** How long an opening took, from its start, in milliseconds. */
interface Opening {
  readonly duration: number;
  /**
   * For an opening by the address, where the time went: when the server had sent the whole
   * document, and when the browser had parsed it and run its scripts.
   */
  readonly phases?: { readonly served: number; readonly parsed: number };
}

/** Open the screen of a grid by its address; how long it took, and where the time went. */
async function openByAddress(page: Page, screen: GridScreen): Promise<Opening> {
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
  return { duration: usable - started, phases: { served, parsed } };
}

/**
 * Open the screen of a grid from that of another, by its link in the navigation; how long it
 * took, from the click, in milliseconds.
 */
async function openByClick(page: Page, from: GridScreen, to: GridScreen): Promise<Opening> {
  await page.goto(address(from));
  await usableAt(page, from);
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: to.link })
    .click();
  const usable = await usableAt(page, to);
  const clicked = await page.evaluate((key) => Number(sessionStorage.getItem(key)), CLICKED);
  await expect(page).toHaveURL(address(to));
  return { duration: usable - clicked };
}

/** The median of some durations. */
function median(durations: readonly number[]): number {
  const sorted = durations.toSorted((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? (sorted[middle] ?? 0)
    : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}

/** The median of some times, rounded to the millisecond, as the log writes it. */
function inLog(times: readonly number[]): string {
  return Math.round(median(times)).toString();
}

/**
 * Open a grid some times one way, and say how long each took, the median and the worst — and,
 * by the address, the medians of the phases.
 */
async function measure(way: string, open: () => Promise<Opening>): Promise<readonly number[]> {
  await open();
  const openings: Opening[] = [];
  for (let opening = 0; opening < OPENINGS; opening += 1) {
    openings.push(await open());
  }
  const durations = openings.map((opening) => Math.round(opening.duration));
  const phases = openings.flatMap((opening) =>
    opening.phases === undefined ? [] : [opening.phases],
  );
  const where =
    phases.length === 0
      ? ""
      : `; median document served at ${inLog(phases.map((phase) => phase.served))} ms, parsed at ${inLog(phases.map((phase) => phase.parsed))} ms`;
  console.log(
    `${way}: ${durations.join(", ")} ms — median ${inLog(durations)} ms, worst ${Math.max(...durations).toString()} ms${where}`,
  );
  return durations;
}

/**
 * Open the screen of a grid by its address and from the navigation, and hold every opening to
 * the second; then check, by the view of Playwright, that what the measure waited for is there.
 */
async function holdsTheSecond(page: Page, screen: GridScreen, from: GridScreen) {
  const byAddress = await measure(`${screen.grid}, by its address`, () =>
    openByAddress(page, screen),
  );
  const byClick = await measure(`${screen.grid}, from the navigation`, () =>
    openByClick(page, from, screen),
  );
  expect(Math.max(...byAddress)).toBeLessThanOrEqual(OBJECTIVE);
  expect(Math.max(...byClick)).toBeLessThanOrEqual(OBJECTIVE);

  const grid = page.getByRole("grid", { name: screen.grid });
  await expect(grid).toHaveAttribute("aria-rowcount", "6002");
  for (const shown of [
    grid.getByRole("columnheader", { name: "Libellé" }),
    grid.getByRole("gridcell", { name: screen.totals }),
    grid.getByRole("row", { name: /^1 .*Études/ }),
  ]) {
    await expect(shown).toBeInViewport({ ratio: 1 });
  }
}

test.describe("the opening of a grid of a thousand tasks", () => {
  test.describe.configure({ timeout: 180_000 });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(markUsableGrids, CLICKED);
  });

  // US-0110, a criterion of its own; US-0220, its third.
  test("opening the grid of the estimate of a thousand tasks holds the objective of one second of §4.6.2, measured against the fake back", async ({
    page,
  }) => {
    await holdsTheSecond(page, ESTIMATE, PLANNING);
  });

  test("on a thousand tasks served by the fake back, opening the grid of the planning holds the objective of one second of §4.6.2", async ({
    page,
  }) => {
    await holdsTheSecond(page, PLANNING, ESTIMATE);
  });
});
