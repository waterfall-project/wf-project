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
import { armScreen, type Watched } from "./screen-watch";

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
  sections: [
    { name: "Plan de charge du projet", chart: true, empty: "^Aucun rôle", windowed: true },
  ],
};

/** The projection of expenses, after the workload. */
const SPENDING: Screen = {
  step: "spending.from-workload",
  link: "Projection de dépenses",
  address: /\/spending(\?|$)/,
  sections: [
    { name: "Projection de dépenses", chart: true, empty: "^Aucune nature", windowed: true },
  ],
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
    { name: "Suivi des jalons", chart: true, empty: "^Aucun jalon", windowed: false },
    { name: "Coûts cumulés", chart: true, empty: "^Rien à tracer", windowed: false },
    { name: "Courbes de valeur acquise", chart: true, empty: "^Rien à tracer", windowed: false },
  ],
};

/** The screens, for the tests that read them against the catalogue of the messages. */
export const SCREENS: readonly Screen[] = [WORKLOAD, SPENDING, INDICATORS];

/** The name of the step of each screen in the log and in the report (`version.ts`). */
export const WORKLOAD_STEP = WORKLOAD.step;
export const SPENDING_STEP = SPENDING.step;
export const INDICATORS_STEP = INDICATORS.step;

/** Where the script writes the moment the screen became usable. */
const ARMED = "wfMeasureScreen";

/** Open a screen of the project by the navigation, from the screen shown: from the click. */
async function opened(page: Page, { sections, link, address }: Screen): Promise<Interval> {
  await forget(page);
  await page.evaluate(armScreen, { sections, address: address.source, armed: ARMED });
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
