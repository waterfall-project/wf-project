// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar of a grid in a tree that holds a thousand tasks, measured (US-2020, #3089): on the planning,
 * the estimate and the remaining to commit of the witness of volume (PRJ-001, which the fake back
 * serves with a thousand tasks), the bar keeps its height — the search, the filter, « Arbre » and
 * « Colonnes » stay in the window and under the pointer — at 1440 × 900 and in a large window; the
 * grid gives way, down to its floor, and stays in the window under the bar. The flat tables, one
 * of them with the panel of its filters, keep their bar too, « Colonnes » and the panel included. The grids of the other paths hold too
 * few rows to show the defect: the bar, which scrolls sideways, lost its least height and gave up
 * all the room the frame of a thousand rows would not.
 */
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { untilHydrated, WORKING } from "./hydration";
import { path } from "./routes";

test.describe.configure({ mode: "parallel" });
test.slow();

const REVISION = "/projects/[projectId]/revisions/[revisionId]";

/** The window of a portable, and a large one. */
const WINDOWS = [
  { width: 1440, height: 900 },
  { width: 3840, height: 2000 },
] as const;

/** The least height, in pixels, of a bar on one line: its buttons are 28 high, its search 28. */
const BAR_FLOOR = 28;

/** The rows a grid of the witness holds at least: a thousand tasks, and their header and totals. */
const VOLUME = 1000;

/** The grids of a thousand tasks, and the filter their bar holds beside the search. */
const TREES = [
  { address: path(`${REVISION}/planning`), filter: "Lot ou poste" },
  { address: path(`${REVISION}/estimate`), filter: "Lot ou poste" },
  { address: path(`${REVISION}/remaining`), filter: "Lot ou poste" },
] as const;

/** The flat tables, whose bar is folded over the panel of their filters. */
const OTHERS = ["/portfolio/projects", "/admin/users", "/admin/audit-log"] as const;

/** Open a screen in a window, until its first grid shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/** The height of the bar of the first grid of the screen, as laid out: its line, even under a panel. */
async function barHeight(page: Page): Promise<number> {
  const box = await page.locator("main [data-grid-toolbar]").first().boundingBox();
  return box?.height ?? 0;
}

for (const { address, filter } of TREES) {
  test(`${address}: the bar of a grid of a thousand tasks keeps its height, its search and its filter in reach [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const grid = page.locator("main [role='treegrid'], main [role='grid']").first();
      const rows = Number(await grid.getAttribute("aria-rowcount"));
      expect(rows, `the rows of the grid of ${where}`).toBeGreaterThanOrEqual(VOLUME);
      await expect(grid).toBeInViewport();
      const height = await barHeight(page);
      expect(height, `the height of the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const bar = page.locator("main [data-grid-toolbar]").first();
      const search = bar.getByRole("search");
      await expect(search).toBeVisible();
      await expect(search).toBeInViewport();
      await search.getByRole("searchbox").click({ trial: true });
      for (const name of [filter, "Arbre", "Colonnes"]) {
        const control = bar.getByRole("button", { name: new RegExp(name) });
        await expect(control, `« ${name} » of ${where}`).toBeVisible();
        await expect(control, `« ${name} » of ${where}`).toBeInViewport();
        await control.click({ trial: true });
      }
    }
  });
}

for (const address of OTHERS) {
  test(`${address}: the bar of a flat table keeps its height, its search, « Colonnes » and the panel of its filters in reach [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const bar = page.locator("main [data-grid-toolbar]").first();
      // The panel of the filters folds the bar into a frame that holds the line and the panel.
      const folded = await bar.evaluate((el) => el.parentElement?.hasAttribute("data-folded"));
      expect(folded, `the bar of ${where} is folded over its panel`).toBe(true);
      const height = await barHeight(page);
      expect(height, `the height of the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const search = bar.getByRole("search");
      await expect(search).toBeVisible();
      await expect(search).toBeInViewport();
      await search.getByRole("searchbox").click({ trial: true });
      // « Colonnes » and the button of the filters stay in the window and under the pointer, and
      // the panel the button opens shows in the window as well (#3118).
      const columns = bar.getByRole("button", { name: /^Colonnes/ });
      await expect(columns, `« Colonnes » of ${where}`).toBeVisible();
      await expect(columns, `« Colonnes » of ${where}`).toBeInViewport();
      await columns.click({ trial: true });
      const toggle = bar.getByRole("button", { name: /^Filtres( \(|$)/ });
      await expect(toggle, `« Filtres » of ${where}`).toBeInViewport();
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      const panel = page.locator(`[id="${(await toggle.getAttribute("aria-controls")) ?? ""}"]`);
      await expect(panel, `the panel of the filters of ${where}`).toBeVisible();
      await expect(panel, `the panel of the filters of ${where}`).toBeInViewport();
    }
  });
}
