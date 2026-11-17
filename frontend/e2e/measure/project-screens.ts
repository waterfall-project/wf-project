// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The three screens of EP-10 as the report of a version measures them (US-2300, US-2420): the
 * workload of the project, then the projection of expenses, then the indicators of the current
 * revision, each opened by the navigation from the screen before — the workload from the planning,
 * where the journey of the grids ends (`steps.ts`) —, from the click to the screen usable. None is
 * a grid, and each has its own definition of usable, in the spirit of `usable.ts`: the first frame
 * at which each section it names is there, and, for a chart, hydrated — React has taken over its
 * choices — and drawn — the chart is drawn by the browser alone, once hydrated — or, when the
 * project has nothing to draw, the text that says so; the top of the first section within the
 * window. A script started before the click watches the frames for it, in the document of the
 * click: the navigation of Next replaces no document.
 */
import { expect, type Page } from "@playwright/test";

import { CLICKED } from "../usable";
import { forget, gestureStart, LOADED } from "./steps";
import type { Interval } from "./report";

/** A section of a screen the script waits for, by the name the page gives it. */
interface Watched {
  readonly name: string;
  /** Whether it holds a chart, which is hydrated and drawn before the section is usable. */
  readonly chart: boolean;
  /** Whether its top, or its chart's, must lie within the window. */
  readonly windowed: boolean;
}

/** A screen of the project: its step in the report, its link, its address, its sections. */
interface Screen {
  readonly step: string;
  readonly link: string;
  readonly address: RegExp;
  readonly sections: readonly Watched[];
}

/** The workload, its step in the report of a version (`version.ts`). */
const WORKLOAD: Screen = {
  step: "workload.from-planning",
  link: "Plan de charge",
  address: /\/workload(\?|$)/,
  sections: [{ name: "Plan de charge du projet", chart: true, windowed: true }],
};

/** The projection of expenses, after the workload. */
const SPENDING: Screen = {
  step: "spending.from-workload",
  link: "Projection de dépenses",
  address: /\/spending(\?|$)/,
  sections: [{ name: "Projection de dépenses", chart: true, windowed: true }],
};

/**
 * The indicators of the current revision, after the projection: its first card within the window,
 * and the three charts below it — the milestones, the cumulative costs, the earned value — drawn.
 */
const INDICATORS: Screen = {
  step: "indicators.from-spending",
  link: "Indicateurs projets",
  address: /\/indicators(\?|$)/,
  sections: [
    { name: "Avancement financier", chart: false, windowed: true },
    { name: "Suivi des jalons", chart: true, windowed: false },
    { name: "Coûts cumulés", chart: true, windowed: false },
    { name: "Courbes de valeur acquise", chart: true, windowed: false },
  ],
};

/** The name of the step of each screen in the log and in the report (`version.ts`). */
export const WORKLOAD_STEP = WORKLOAD.step;
export const SPENDING_STEP = SPENDING.step;
export const INDICATORS_STEP = INDICATORS.step;

/** Where the script writes the moment the screen became usable. */
const ARMED = "wfMeasureScreen";

/** The arguments of the script that watches a screen. */
interface Watch {
  readonly sections: readonly Watched[];
  readonly armed: string;
}

/**
 * Run in the page before the click: watch every frame until each section is usable, and write the
 * moment, on the clock of the operating system. Self-contained: Playwright hands its source to the
 * page.
 */
function armScreen({ sections, armed }: Watch): void {
  const slot = window as unknown as Record<string, number | null>;
  slot[armed] = null;
  const hydrated = (element: Element) =>
    Object.keys(element).some((key) => key.startsWith("__reactProps$"));
  const within = (element: Element) => {
    const box = element.getBoundingClientRect();
    return box.top >= 0 && box.top < innerHeight;
  };
  const usable = ({ name, chart, windowed }: Watched): boolean => {
    const section = document.querySelector(
      `section[aria-label="${name}"], [role="region"][aria-label="${name}"]`,
    );
    if (section === null) {
      return false;
    }
    if (!chart) {
      return !windowed || within(section);
    }
    if (![...section.querySelectorAll("button")].some(hydrated)) {
      return false;
    }
    const drawn = section.querySelector('[role="img"]');
    if (drawn === null) {
      return section.querySelector("p") !== null;
    }
    return drawn.querySelector("svg path") !== null && (!windowed || within(drawn));
  };
  const frame = () => {
    if (sections.every(usable)) {
      slot[armed] = performance.timeOrigin + performance.now();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/** Open a screen of the project by the navigation, from the screen shown: from the click. */
async function opened(page: Page, { sections, link, address }: Screen): Promise<Interval> {
  await forget(page);
  await page.evaluate(armScreen, { sections, armed: ARMED });
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: link, exact: true })
    .click();
  const read = () =>
    page.evaluate((armed) => (window as unknown as Record<string, number | null>)[armed], ARMED);
  const names = sections.map(({ name }) => name).join(", ");
  await expect
    .poll(read, { message: `${names} usable after the click`, timeout: LOADED })
    .not.toBeNull();
  await expect(page).toHaveURL(address);
  return { start: await gestureStart(page, CLICKED), end: (await read()) ?? Number.NaN };
}

/** Open the workload of the project by the navigation, from the planning. */
export function workloadFromPlanning(page: Page): Promise<Interval> {
  return opened(page, WORKLOAD);
}

/** Open the projection of expenses by the navigation, from the workload. */
export function spendingFromWorkload(page: Page): Promise<Interval> {
  return opened(page, SPENDING);
}

/** Open the indicators of the current revision by the navigation, from the projection. */
export function indicatorsFromSpending(page: Page): Promise<Interval> {
  return opened(page, INDICATORS);
}
