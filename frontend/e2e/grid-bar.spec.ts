// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar of a grid in a tree that holds a thousand tasks, measured (US-2020, #3089): on the planning
 * and the estimate of the witness of volume (PRJ-001, which the fake back serves with a thousand
 * tasks), the bar keeps its height — the search, the filters, « Arbre » and « Colonnes » stay in
 * sight and under the pointer — at 1440 × 900 and in a large window; the grid gives way, down to its
 * floor. The remaining to commit, which the fake back serves with the volume too, and the flat tables keep
 * their bar too. The grids of the other paths
 * hold too few rows to show the defect: the bar, which scrolls sideways, lost its least height and
 * gave up all the room the frame of a thousand rows would not.
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

/** The grids of a thousand tasks, and the filter their bar holds beside the search. */
const TREES = [
  { address: path(`${REVISION}/planning`), filter: "Lot ou poste" },
  { address: path(`${REVISION}/estimate`), filter: "Lot ou poste" },
] as const;

/** The screens whose bar holds no tree filter: the remaining, and two flat tables. */
const OTHERS = [path(`${REVISION}/remaining`), "/portfolio/projects", "/admin/users"] as const;

/** Open a screen in a window, until its first grid shows and the page is hydrated. */
async function open(page: Page, address: string, size: { width: number; height: number }) {
  await page.setViewportSize(size);
  await page.goto(address);
  await expect(page.locator("main [role='grid'], main [role='treegrid']").first()).toBeVisible({
    timeout: WORKING,
  });
  await untilHydrated(page);
}

/** The height of the bar of the first grid of the screen, as laid out. */
async function barHeight(page: Page): Promise<number> {
  const height = await page
    .locator("main [data-grid-toolbar]")
    .first()
    .evaluate((bar) => {
      const first = bar.firstElementChild;
      const line = bar.hasAttribute("data-folded") && first instanceof HTMLElement ? first : bar;
      return line.getBoundingClientRect().height;
    });
  return height;
}

for (const { address, filter } of TREES) {
  test(`${address}: the bar of a grid of a thousand tasks keeps its height, its search and its filter in reach [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const height = await barHeight(page);
      // Printed for the record: the height measured is the evidence of the defect and of its fix.
      console.log(`bar height ${where}: ${String(height)}`);
      expect(height, `the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const bar = page.locator("main [data-grid-toolbar]").first();
      const search = bar.getByRole("search");
      await expect(search).toBeVisible();
      await search.getByRole("searchbox").click({ trial: true });
      const choice = bar.getByRole("button", { name: new RegExp(filter) });
      await expect(choice).toBeVisible();
      await choice.click({ trial: true });
    }
  });
}

for (const address of OTHERS) {
  test(`${address}: the bar of a flat table and of the remaining keeps its height and its search [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await compile(page.request, address);
    for (const size of WINDOWS) {
      await open(page, address, size);
      const where = `${address} at ${String(size.width)} × ${String(size.height)}`;
      const height = await barHeight(page);
      console.log(`bar height ${where}: ${String(height)}`);
      expect(height, `the bar of ${where}`).toBeGreaterThanOrEqual(BAR_FLOOR);
      const search = page.locator("main [data-grid-toolbar]").first().getByRole("search");
      await expect(search).toBeVisible();
      await search.getByRole("searchbox").click({ trial: true });
    }
  });
}
