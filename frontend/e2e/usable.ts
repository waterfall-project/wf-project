// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * When a grid becomes usable, as the measures define it: the measure of the second of §4.6.2
 * against the fake back (`opening.spec.ts`, which says why) and the measure of the journey of the
 * grids against the service (`measure/grids.measure.ts`, US-2210) share it, so that both measure
 * the same thing.
 *
 * A grid is usable once it is drawn and hydrated. Drawn is the first frame the browser draws with
 * the header of its columns, the caption of its totals and the first row of the answer wholly
 * within the window; hydrated, the first frame at which React has taken over the whole grid, which
 * the measure tells by the keys React gives the last element of the grid, the last cell of its
 * totals (`__reactProps$…`), as it hydrates it: an internal of React, read by the measures and
 * nowhere in the front. A script given to each document watches every frame for them, and writes
 * the times it finds on the clock of the operating system (`performance.timeOrigin`), which
 * survives the document when a click loads another. Nothing of the harness counts: neither
 * Playwright's round trips nor its polling.
 */
import { expect, type Page, type Request } from "@playwright/test";

/**
 * How long a measure waits for what it needs to go on — a grid usable, a page settled —, in
 * milliseconds: a bound of its working, far from what it measures, which measures nothing.
 */
export const MEASURE_WAIT = 15_000;

/** Where the start of a gesture by a click is kept: it survives a document replaced. */
export const CLICKED = "wf_e2e_clicked";

/**
 * The name under which the script of each document leaves its two tests of a grid — drawn,
 * hydrated — to the page, and the one they draw on, whether an element is wholly within the window
 * (`Reached`): for a measure that waits for a grid changed in place rather than for a grid new to
 * the document (`measure/steps.ts`).
 */
export const REACHED = "wfGridReached";

/** The tests the script of each document leaves to the page, under `REACHED`. */
export interface Reached {
  readonly drawn: (grid: Element) => boolean;
  readonly hydrated: (grid: Element) => boolean;
  readonly inWindow: (element: Element | null) => boolean;
}

/** Where the script of each document keeps what it finds: the start of a click, the two tests. */
export interface GridWatch {
  readonly clicked: string;
  readonly reached: string;
}

/**
 * Run in each document from its start: keep the time of each click, and mark, for each grid, the
 * first frame at which its header, its totals and its first row are wholly within the window —
 * `drawn:` — and the first at which React has hydrated the last cell of its totals, the last
 * element of the grid — `hydrated:`. A mark is named for the grid it marks; its detail is the time
 * it was reached on the clock of the operating system. The two tests are left to the page under
 * `REACHED`. Self-contained: Playwright hands its source to the page, its arguments beside it.
 */
export function markUsableGrids({ clicked, reached: reachedName }: GridWatch): void {
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
  Object.defineProperty(window, reachedName, { value: { ...reached, inWindow } });
  document.addEventListener(
    "click",
    (event) => {
      sessionStorage.setItem(clicked, String(performance.timeOrigin + event.timeStamp));
    },
    { capture: true },
  );
  const frame = () => {
    const now = performance.timeOrigin + performance.now();
    for (const grid of document.querySelectorAll('[role="treegrid"][aria-label]')) {
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

/** Give each document of a page the script that marks its usable grids. */
export async function watchGrids(page: Page): Promise<void> {
  await page.addInitScript(markUsableGrids, { clicked: CLICKED, reached: REACHED });
}

/** When a grid was drawn, and when it was hydrated, on the clock of the operating system. */
export interface Usable {
  readonly drawn: number;
  readonly hydrated: number;
}

/**
 * When a grid, by its name, was first drawn and first hydrated in the page, on the clock of the
 * operating system, once it is both — the last time, should it have been more than once —, waited
 * for within a bound of working (`MEASURE_WAIT`, unless a measure under load gives a wider one).
 */
export async function usableAt(page: Page, grid: string, bound = MEASURE_WAIT): Promise<Usable> {
  const read = () =>
    page.evaluate((name) => {
      const at = (state: string) => {
        const last = performance.getEntriesByName(`${state}:${name}`, "mark").at(-1);
        return last instanceof PerformanceMark && typeof last.detail === "number"
          ? last.detail
          : null;
      };
      const drawn = at("drawn");
      const hydrated = at("hydrated");
      return drawn === null || hydrated === null ? null : { drawn, hydrated };
    }, grid);
  await expect.poll(read, { message: `${grid} usable`, timeout: bound }).not.toBeNull();
  return (await read()) ?? { drawn: Number.POSITIVE_INFINITY, hydrated: Number.POSITIVE_INFINITY };
}

/** How long a page must have had no request under way to be settled, in milliseconds. */
const QUIET = 500;

/** The requests of a page under way, and when the last of them started or ended. */
export interface Requests {
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
export function followRequests(page: Page): Requests {
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
 * renders them — the first time, loading the modules of each route —, in the time of the gesture
 * measured next. Waited for between the gestures, never within one, within a bound of working
 * (`MEASURE_WAIT`, unless a measure under load gives a wider one).
 */
export async function settle(requests: Requests, bound = MEASURE_WAIT): Promise<void> {
  await expect
    .poll(() => requests.underWay() === 0 && requests.quietFor() >= QUIET, {
      message: `the page settles: no request under way for ${QUIET.toString()} ms`,
      timeout: bound,
    })
    .toBe(true);
}
