// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workload of the project, as the report of a version measures it (US-2300): its screen opened
 * by the navigation from the planning, where the journey of the grids ends (`steps.ts`), from the
 * click to the workload usable. The screen is no grid, and has its own definition of usable, in the
 * spirit of `usable.ts`: the first frame at which its section is hydrated — React has taken over its
 * choices — and shows what the server read, the chart of the workload drawn — the chart is drawn by
 * the browser alone, once hydrated — with its top within the window, or, when the project has no
 * workload to draw, the text that says so. A script started before the click watches the frames for
 * it, in the document of the click: the navigation of Next replaces no document.
 */
import { expect, type Page } from "@playwright/test";

import { CLICKED } from "../usable";
import { forget, gestureStart, LOADED } from "./steps";
import type { Interval } from "./report";

/** The name of the step in the log and in the report (`version.ts`). */
export const WORKLOAD_STEP = "workload.from-planning";

/** The name of the section of the workload, and the link of the navigation to its screen. */
const SECTION = "Plan de charge du projet";
const LINK = "Plan de charge";

/** Where the script writes the moment the workload became usable. */
const ARMED = "wfMeasureWorkload";

/** The arguments of the script that watches the workload. */
interface Watch {
  readonly section: string;
  readonly armed: string;
}

/**
 * Run in the page before the click: watch every frame until the section of the workload is
 * hydrated and drawn, and write the moment, on the clock of the operating system.
 * Self-contained: Playwright hands its source to the page.
 */
function armWorkload({ section: name, armed }: Watch): void {
  const slot = window as unknown as Record<string, number | null>;
  slot[armed] = null;
  const hydrated = (element: Element) =>
    Object.keys(element).some((key) => key.startsWith("__reactProps$"));
  const usable = (): boolean => {
    const section = document.querySelector(`section[aria-label="${name}"]`);
    if (section === null || ![...section.querySelectorAll("button")].some(hydrated)) {
      return false;
    }
    const chart = section.querySelector('[role="img"]');
    if (chart === null) {
      return section.querySelector("p") !== null;
    }
    const box = chart.getBoundingClientRect();
    return chart.querySelector("svg path") !== null && box.top >= 0 && box.top < innerHeight;
  };
  const frame = () => {
    if (usable()) {
      slot[armed] = performance.timeOrigin + performance.now();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

/** Open the workload of the project by the navigation, from the planning: from the click. */
export async function workloadFromPlanning(page: Page): Promise<Interval> {
  await forget(page);
  await page.evaluate(armWorkload, { section: SECTION, armed: ARMED });
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: LINK, exact: true })
    .click();
  const read = () =>
    page.evaluate((armed) => (window as unknown as Record<string, number | null>)[armed], ARMED);
  await expect
    .poll(read, { message: `${SECTION} usable after the click`, timeout: LOADED })
    .not.toBeNull();
  await expect(page).toHaveURL(/\/workload(\?|$)/);
  return { start: await gestureStart(page, CLICKED), end: (await read()) ?? Number.NaN };
}
