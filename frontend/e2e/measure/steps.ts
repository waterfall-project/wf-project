// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The journey of the grids the measure plays for each user (US-2210), on PRJ-001: open the grid of
 * the planning by its address; go to that of the estimate, filter it by a lot, sort it, search it;
 * go to that of the remaining to commit, then back to the planning; enter a label, then a duration
 * that redates its task. Each step lasts from its gesture to the grid usable, as `usable.ts`
 * defines it for the measure of the second of §4.6.2:
 *
 * - a grid opened by its address, from the start of the navigation; by a link of the navigation,
 *   from the click: the first frame at which the new grid is drawn and hydrated, as the script of
 *   each document marks it;
 * - a grid changed in place — filtered, sorted, searched, written —, from the click or from the key
 *   that sends: the first frame at which the grid is hydrated and no longer reading, shows what was
 *   asked — the address of the reading, or the cell written —, and is drawn: the header, the
 *   totals and the first row within the height of the window, whatever the grid has scrolled
 *   sideways, or, for a cell written, that cell within the window. A script started before the
 *   gesture watches the frames for it; a write ends once its server action has answered, too.
 *
 * Between two steps, the page settles outside the measure (`settle`). Every request the browser
 * makes of the server of Next is kept with the bytes of its answer, for the parts of each step
 * (`report.ts`).
 */
import { expect, type Locator, type Page, type Request } from "@playwright/test";

import { pick } from "../check-menu";
import { columnsOf } from "../columns";
import { scrollToPosition } from "../scroll";
import { isServerAction } from "../server-action";
import {
  CLICKED,
  followRequests,
  type Reached,
  REACHED,
  type Requests,
  settle,
  usableAt,
  watchGrids,
} from "../usable";
import type { FrontRequest, Interval } from "./report";

export const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
export const REVISION = "01926f3a-7c00-7000-8000-000000000102";

/** The steps of the journey, in its order: the names the report gives them. */
export const STEPS = [
  "planning.by-address",
  "estimate.from-planning",
  "estimate.filter",
  "estimate.sort",
  "estimate.search",
  "remaining.from-estimate",
  "planning.from-remaining",
  "planning.label",
  "planning.duration",
] as const;

export type Step = (typeof STEPS)[number];

/** A screen of a grid: its address, the link of the navigation to it, its grid. */
interface GridScreen {
  readonly segment: string;
  readonly link: string;
  readonly grid: string;
}

const PLANNING: GridScreen = {
  segment: "planning",
  link: "Planification",
  grid: "Grille de planning",
};
const ESTIMATE: GridScreen = {
  segment: "estimate",
  link: "Chiffrage et devis",
  grid: "Grille de devis",
};
const REMAINING: GridScreen = {
  segment: "remaining",
  link: "Estimation du reste à engager",
  grid: "Grille de reste à engager",
};

/** The address of the screen of a grid. */
function address(screen: GridScreen): string {
  return `/projects/${PROJECT}/revisions/${REVISION}/${screen.segment}`;
}

/**
 * How long the measure waits for a grid, a page settled, an answer: a bound of its working, as
 * `WORKING` is for the paths, but under the load of eight users at once, where the estimate took
 * past fifteen seconds to show.
 */
const LOADED = 60_000;

/** Where the start of a gesture by a key that sends — Enter — is kept, beside that of a click. */
const KEYED = "wf_measure_keyed";

/** Where the script started before a gesture in place writes the moment the grid became usable. */
const ARMED = "wfMeasureUsable";

/** Run in each document from its start: keep the time of each key Enter, as that of a click. */
function markKeys(keyed: string): void {
  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key === "Enter") {
        sessionStorage.setItem(keyed, String(performance.timeOrigin + event.timeStamp));
      }
    },
    { capture: true },
  );
}

/** What a grid changed in place shows once the gesture is served. */
interface Expected {
  /** The name of the grid. */
  readonly grid: string;
  /** What the address of the reading holds, for a gesture that reads the grid anew. */
  readonly query?: string;
  /** The cell written, by the `aria-rowindex` of its row and its position: what it shows then. */
  readonly cell?: {
    readonly row: number;
    readonly column: number;
    readonly shows?: string;
    readonly differsFrom?: string;
  };
}

/** The arguments of the script that watches a grid changed in place. */
interface Watch {
  readonly reached: string;
  readonly armed: string;
  readonly expected: Expected;
}

/**
 * Run in the page before a gesture in place: watch every frame until the grid is usable and shows
 * what the gesture asked, and write the moment, on the clock of the operating system.
 * Self-contained: Playwright hands its source to the page.
 */
function armUsable({ reached: reachedName, armed, expected }: Watch): void {
  const tests = (window as unknown as Record<string, Reached>)[reachedName];
  const slot = window as unknown as Record<string, number | null>;
  slot[armed] = null;
  // The watch of a gesture before, whose grid never showed what it asked, stops at this one's.
  const generation = performance.now();
  slot[`${armed}:generation`] = generation;
  if (tests === undefined) {
    return;
  }
  const shows = (grid: Element): boolean => {
    if (expected.query !== undefined && !window.location.search.includes(expected.query)) {
      return false;
    }
    const { cell: wanted } = expected;
    if (wanted === undefined) {
      // Drawn in place: the header, the totals and the first row within the height of the window —
      // a grid sorted by a column far to the right has scrolled sideways to it, and stays so.
      return ["thead th", "tfoot td", 'tbody tr[aria-rowindex="2"] td'].every((selector) => {
        const box = grid.querySelector(selector)?.getBoundingClientRect();
        return box !== undefined && box.height > 0 && box.top >= 0 && box.bottom <= innerHeight;
      });
    }
    const row = grid.querySelector(`tbody tr[aria-rowindex="${String(wanted.row)}"]`);
    const cell = row instanceof HTMLTableRowElement ? row.cells.item(wanted.column) : null;
    const text = cell?.textContent ?? "";
    return (
      cell !== null &&
      grid.querySelector("input, textarea") === null &&
      tests.inWindow(cell) &&
      (wanted.shows === undefined || text.includes(wanted.shows)) &&
      (wanted.differsFrom === undefined || text !== wanted.differsFrom)
    );
  };
  const frame = () => {
    if (slot[`${armed}:generation`] !== generation) {
      return;
    }
    const grid = document.querySelector(`[role="treegrid"][aria-label="${expected.grid}"]`);
    if (
      grid !== null &&
      grid.getAttribute("aria-busy") !== "true" &&
      tests.hydrated(grid) &&
      shows(grid)
    ) {
      slot[armed] = performance.timeOrigin + performance.now();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/** A user of the measure in its browser: its page, its requests, those it made of Next. */
export interface Player {
  readonly page: Page;
  readonly requests: Requests;
  /** The requests the page made of the server of Next, with their bytes. */
  readonly front: readonly FrontRequest[];
  /** Wait until every request finished so far is kept, its bytes read. */
  readonly drained: () => Promise<void>;
}

/**
 * Whether a request is one the server of Next answers, rendering: a document, a tree of components
 * of the server, a server action — no asset.
 */
function rendered(request: Request, origin: string): boolean {
  return request.url().startsWith(origin) && ["document", "fetch"].includes(request.resourceType());
}

/** How long the sizes of an answer are waited for, in milliseconds. */
const SIZED = 5_000;

/** Make a page a player: its grids and its keys watched, its requests of Next kept. */
export async function player(page: Page, origin: string): Promise<Player> {
  await watchGrids(page);
  await page.addInitScript(markKeys, KEYED);
  const front: FrontRequest[] = [];
  const reading: Promise<void>[] = [];
  page.on("requestfinished", (request) => {
    if (!rendered(request, origin)) {
      return;
    }
    const { startTime: start, responseEnd } = request.timing();
    const prefetch = request.headers()["next-router-prefetch"] !== undefined;
    // The sizes of an answer the browser no longer reads — a prefetch a navigation left behind —
    // never come, or are refused once its page is gone: its time is kept all the same, and its
    // bytes counted for none.
    const unsized = new Promise<number>((resolve) => {
      setTimeout(() => {
        resolve(0);
      }, SIZED);
    });
    const sized = request.sizes().then(
      ({ responseBodySize }) => responseBodySize,
      () => 0,
    );
    reading.push(
      Promise.race([sized, unsized]).then((bytes) => {
        front.push({ start, end: start + responseEnd, bytes, prefetch });
      }),
    );
  });
  // A request the router gave up — a navigation that took the place of another — was waited for
  // until then: its time counts, up to the moment it failed, and none of its bytes.
  page.on("requestfailed", (request) => {
    if (rendered(request, origin)) {
      const { startTime: start } = request.timing();
      const prefetch = request.headers()["next-router-prefetch"] !== undefined;
      front.push({ start, end: Date.now(), bytes: 0, prefetch });
    }
  });
  return {
    page,
    requests: followRequests(page),
    front,
    drained: async () => {
      await Promise.all(reading);
    },
  };
}

/** The task a user writes: its position among the tasks of the planning, and its label as read. */
export interface Target {
  readonly position: number;
  readonly label: string;
}

/** The columns of the planning a write reads. */
interface Columns {
  readonly label: number;
  readonly duration: number;
  readonly finish: number;
}

/** The columns of the planning, by their headings. */
async function planningColumns(page: Page): Promise<Columns> {
  return columnsOf(page.getByRole("treegrid", { name: PLANNING.grid }), {
    label: "Libellé",
    duration: "Durée",
    finish: "Fin",
  });
}

/** How far apart the tasks of two users lie, so that a redating of one seldom reaches another. */
const APART = 10;

/** Where the search of the tasks the users write starts: past the first screen of the planning. */
const FROM = 20;

/**
 * The tasks the users write, one each: tasks in automatic mode, not started, apart from one
 * another, read on the planning as the first user sees it, outside the measure — a duration
 * entered redates such a task.
 */
export async function targets({ page, requests }: Player, count: number): Promise<Target[]> {
  await page.goto(address(PLANNING));
  await usableAt(page, PLANNING.grid, LOADED);
  const grid = page.getByRole("treegrid", { name: PLANNING.grid });
  const at = await planningColumns(page);
  const rows = Number(await grid.getAttribute("aria-rowcount")) - 2;
  const found: Target[] = [];
  for (let position = FROM; position <= rows && found.length < count; position += 1) {
    const row = await scrollToPosition(grid, position);
    const writable =
      (await row.getByRole("img", { name: "Tâche", exact: true }).count()) === 1 &&
      (await row.getByRole("img", { name: "Automatique" }).count()) === 1 &&
      (await row.getByRole("img", { name: "Non démarrée" }).count()) === 1;
    if (writable) {
      const label = (await row.getByRole("gridcell").nth(at.label).textContent()) ?? "";
      found.push({ position, label: label.trim() });
      position += APART - 1;
    }
  }
  expect(found, "tasks to write, one for each user").toHaveLength(count);
  await settle(requests, LOADED);
  return found;
}

/** Forget the marks and the gestures of the page: what follows is the next step's. */
async function forget(page: Page): Promise<void> {
  await page.evaluate(
    ([clicked, keyed]) => {
      performance.clearMarks();
      sessionStorage.removeItem(clicked);
      sessionStorage.removeItem(keyed);
    },
    [CLICKED, KEYED] as const,
  );
}

/** When the last gesture of a kind started, on the clock of the operating system. */
async function gestureStart(page: Page, key: string): Promise<number> {
  const read = () => page.evaluate((name) => sessionStorage.getItem(name), key);
  await expect.poll(read, { message: `the gesture kept under ${key}` }).not.toBeNull();
  return Number(await read());
}

/** Open the screen of a grid by its address: from the start of the navigation. */
async function byAddress(page: Page, screen: GridScreen): Promise<Interval> {
  await page.goto(address(screen), { waitUntil: "commit" });
  const { drawn, hydrated } = await usableAt(page, screen.grid, LOADED);
  const start = await page.evaluate(() => performance.timeOrigin);
  return { start, end: Math.max(drawn, hydrated) };
}

/** Open the screen of a grid by its link in the navigation: from the click. */
async function byLink(page: Page, screen: GridScreen): Promise<Interval> {
  await forget(page);
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: screen.link })
    .click();
  const { drawn, hydrated } = await usableAt(page, screen.grid, LOADED);
  await expect(page).toHaveURL(new RegExp(`/${screen.segment}(\\?|$)`));
  return { start: await gestureStart(page, CLICKED), end: Math.max(drawn, hydrated) };
}

/**
 * A gesture on a grid in place: the watch started, the gesture made, the moment the grid showed
 * what it asked, from the click or the key that sent it.
 */
async function inPlace(
  page: Page,
  expected: Expected,
  started: string,
  gesture: () => Promise<void>,
): Promise<Interval> {
  await forget(page);
  await page.evaluate(armUsable, { reached: REACHED, armed: ARMED, expected });
  await gesture();
  const read = () =>
    page.evaluate((armed) => (window as unknown as Record<string, number | null>)[armed], ARMED);
  await expect
    .poll(read, { message: `${expected.grid} usable after the gesture`, timeout: LOADED })
    .not.toBeNull();
  return { start: await gestureStart(page, started), end: (await read()) ?? Number.NaN };
}

/**
 * When the answer of a request ended, on the clock of the operating system: its timing says so once
 * its body has come — waited for within the bound of a wait, an answer whose end the browser never
 * reports (`Response.finished()` then never settles) failing the step instead.
 */
async function answeredAt(request: Request): Promise<number> {
  await expect
    .poll(() => request.timing().responseEnd >= 0, {
      message: "the answer of the server action ends",
      timeout: LOADED,
    })
    .toBe(true);
  const { startTime, responseEnd } = request.timing();
  return startTime + responseEnd;
}

/**
 * Write a cell of the task of a user, entered by F2: the gesture is the key Enter that sends it;
 * the step ends once the cell shows what was expected — for a label, which the grid may show as it
 * was typed, once the server action has answered too; a date the server computed is its answer.
 */
async function write(
  page: Page,
  cell: Locator,
  value: string,
  expected: Expected,
  answered: "shown" | "awaited",
): Promise<Interval> {
  const grid = page.getByRole("treegrid", { name: PLANNING.grid });
  await cell.click();
  await page.keyboard.press("F2");
  await grid.locator("input, textarea").fill(value);
  const [span, sent] = await Promise.all([
    inPlace(page, expected, KEYED, () => page.keyboard.press("Enter")),
    page.waitForRequest(isServerAction, { timeout: LOADED }),
  ]);
  if (answered === "shown") {
    return span;
  }
  return { start: span.start, end: Math.max(span.end, await answeredAt(sent)) };
}

/** The duration a task is given: a different one from the one it shows. */
function otherDuration(shown: string): string {
  return /^\s*7(\s|j|$)/.test(shown) ? "8 j" : "7 j";
}

/** What the grids of the page say of themselves, for the log of a step not reached. */
async function gridsShown(page: Page): Promise<string> {
  const shown = await page.evaluate(() =>
    [...document.querySelectorAll('[role="treegrid"][aria-label]')].map((grid) => {
      const first = grid.querySelector('tbody tr[aria-rowindex="2"]') === null ? "none" : "shown";
      return [
        grid.getAttribute("aria-label") ?? "",
        `rows ${grid.getAttribute("aria-rowcount") ?? "?"}`,
        `busy ${grid.getAttribute("aria-busy") ?? "?"}`,
        `first row ${first}`,
      ].join(", ");
    }),
  );
  return shown.length === 0 ? "no grid" : shown.join("; ");
}

/**
 * How long a step may take, its settling included, in milliseconds: a bound of its working, past
 * the bounds of each of its waits, so that a wait that never ends — a page that never answers —
 * ends the step rather than the whole measure.
 */
const STEP_BOUND = 180_000;

/** Play a step within its bound; past it, the step fails. */
async function bounded<T>(step: Step, play: () => Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const late = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`${step} took more than ${String(STEP_BOUND / 1000)} s`));
    }, STEP_BOUND);
  });
  try {
    return await Promise.race([play(), late]);
  } finally {
    clearTimeout(timer);
  }
}

/** A step of the journey: its name, and its span, if the user reached its end. */
export interface Timed {
  readonly step: Step;
  readonly span: Interval | undefined;
}

/**
 * Play the journey once for a user, writing a task of its own, its label marked by `tag`. A step
 * that does not reach its end ends the journey of the pass: it and the steps after it have no span,
 * and the report counts them incomplete — the measure fails on no duration.
 */
export async function journey(player: Player, target: Target, tag: string): Promise<Timed[]> {
  const { page, requests } = player;
  const planning = page.getByRole("treegrid", { name: PLANNING.grid });
  const estimate = page.getByRole("treegrid", { name: ESTIMATE.grid });
  const plays: readonly (readonly [Step, () => Promise<Interval>])[] = [
    ["planning.by-address", () => byAddress(page, PLANNING)],
    ["estimate.from-planning", () => byLink(page, ESTIMATE)],
    [
      "estimate.filter",
      () =>
        inPlace(page, { grid: ESTIMATE.grid, query: "work_package_id=" }, CLICKED, () =>
          pick(page, "Lot ou poste", "Lot : Lot 1", "radio"),
        ),
    ],
    [
      "estimate.sort",
      () =>
        inPlace(page, { grid: ESTIMATE.grid, query: "sort_by=base_amount" }, CLICKED, () =>
          estimate
            .getByRole("columnheader", { name: "Calculé Montant (année de réf.)" })
            .getByRole("button")
            .click(),
        ),
    ],
    [
      "estimate.search",
      async () => {
        await page.getByRole("searchbox", { name: "Rechercher un libellé" }).fill("revue");
        return inPlace(page, { grid: ESTIMATE.grid, query: "search=revue" }, KEYED, () =>
          page.keyboard.press("Enter"),
        );
      },
    ],
    ["remaining.from-estimate", () => byLink(page, REMAINING)],
    ["planning.from-remaining", () => byLink(page, PLANNING)],
    [
      "planning.label",
      async () => {
        const at = await planningColumns(page);
        const row = await scrollToPosition(planning, target.position);
        const label = `${target.label} · ${tag}`;
        const expected: Expected = {
          grid: PLANNING.grid,
          cell: { row: target.position + 1, column: at.label, shows: label },
        };
        return write(page, row.getByRole("gridcell").nth(at.label), label, expected, "awaited");
      },
    ],
    [
      "planning.duration",
      async () => {
        const at = await planningColumns(page);
        const row = await scrollToPosition(planning, target.position);
        const cells = row.getByRole("gridcell");
        const finish = (await cells.nth(at.finish).textContent()) ?? "";
        const duration = otherDuration((await cells.nth(at.duration).textContent()) ?? "");
        const expected: Expected = {
          grid: PLANNING.grid,
          cell: { row: target.position + 1, column: at.finish, differsFrom: finish },
        };
        return write(page, cells.nth(at.duration), duration, expected, "shown");
      },
    ],
  ];
  const timed: Timed[] = [];
  let reached = true;
  for (const [step, play] of plays) {
    if (!reached) {
      timed.push({ step, span: undefined });
      continue;
    }
    try {
      const span = await bounded(step, async () => {
        const played = await play();
        await settle(requests, LOADED);
        return played;
      });
      timed.push({ step, span });
    } catch (error) {
      const [why = ""] = (error instanceof Error ? error.message : String(error)).split("\n");
      console.log(`${step}: not reached at ${page.url()}, ${await gridsShown(page)} (${why})`);
      reached = false;
      timed.push({ step, span: undefined });
    }
  }
  return timed;
}
