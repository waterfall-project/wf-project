// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The portfolio view of the report of a version (US-2970, EP-11): the list of the projects of the
 * portfolio, opened by its address, from the request to the screen usable — its value of the
 * portfolio shown and its grid holding a project. The cache of the indicators is the cost the
 * measure tells cold from hot: the first opening after the platform started, which computes what
 * the cache lacks, and the openings after it. Not a grid of the journey, so that `usable.ts` does
 * not define it: the sections the screen names are those a path of the portfolio waits for
 * (`portfolio.spec.ts`).
 */
import { expect, type Page } from "@playwright/test";

import { LOADED } from "../bounds";
import type { Interval } from "./report";

/** The step of the portfolio view in the log and in the report (`version.ts`). */
export const PORTFOLIO_STEP = "portfolio.view";

/** The address of the list of the projects of the portfolio. */
export const PORTFOLIO_ADDRESS = "/portfolio/projects";

/** Open the portfolio by its address: from the request to its value and its first project shown. */
export async function openPortfolio(page: Page): Promise<Interval> {
  const start = Date.now();
  await page.goto(PORTFOLIO_ADDRESS);
  await expect(page.getByRole("region", { name: "Valeur du portefeuille" })).toBeVisible({
    timeout: LOADED,
  });
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  await expect(grid.getByRole("row").nth(1)).toBeVisible({ timeout: LOADED });
  return { start, end: Date.now() };
}
