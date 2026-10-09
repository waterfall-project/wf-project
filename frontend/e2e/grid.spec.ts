// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, type Request, test } from "@playwright/test";

import {
  rowAt,
  scrollPageToGrid,
  scroller,
  scrollToFoot,
  scrollToPosition,
  withinBox,
} from "./scroll";
import { openHydrated, openMenu, WORKING } from "./hydration";

// The fake back serves the first example of `listNodes`, the structure of the witness at the sizes
// of §4.6.2, its core first (#376): a thousand tasks and five thousand lines, six thousand rows, of
// which the grid renders those in view. The journeys read it by marks the generator writes, which
// `test_the_marks_the_journeys_read` (tools/tests/test_mockstructure.py) holds — the summary task
// of row 1, « Études », the task of row 2, the task of row 14 over its line and before its sibling
// of row 16, the first line drawn after the core, row 28, the milestone of row 6000, the totals of
// the answer —, and never count the rows rendered: the row count of the grid says how many there
// are. The second of §4.6.2 is measured in `opening.spec.ts`. Each path opens the grid hydrated
// (`openHydrated`) before it scrolls or clicks: the rows follow the scroll, and the sort answers
// its header, once React does. An address that follows a click which reads the six thousand rows
// anew is awaited with the bound of the screens of grids (`WORKING`, #315, #419).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const GRID = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

/** The rows of the answer, and the header and totals around them. */
const ROW_COUNT = "6002";

/** The grid of the estimate. */
function grid(page: Page) {
  return page.getByRole("treegrid", { name: "Grille de devis" });
}

/** The cell of the totals under the header of a column. */
async function totalUnder(page: Page, column: string) {
  const headers = grid(page).getByRole("columnheader");
  const names = await headers.allTextContents();
  const index = names.findIndex((name) => name.includes(column));
  expect(index).toBeGreaterThan(0);
  return grid(page).getByRole("row").last().getByRole("gridcell").nth(index);
}

/** The header of the labels, the caption of the totals, the first and the last rows. */
function edges(page: Page) {
  return {
    header: grid(page).getByRole("columnheader", { name: "Libellé" }),
    totals: grid(page).getByRole("gridcell", { name: /^Total — 1\s000 tâches, 5\s000 lignes$/ }),
    first: grid(page).getByRole("row", { name: /^1 .*Études/ }),
    last: grid(page).getByRole("row", { name: /^6000 .*Fin du lot 9\.3/ }),
  };
}

test("opens the estimate of a thousand tasks and five thousand lines, and scrolls down to its last row [WF-IHM-0060-A]", async ({
  page,
}) => {
  await openHydrated(page, GRID);
  const { header, totals, first, last } = edges(page);
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  // The grid holds in the window as it opens, under the header and the indicators of its screen:
  // its header and its totals are in view, the totals those of the answer under their column.
  expect(await withinBox(grid(page), header)).toBe(true);
  expect(await withinBox(grid(page), totals)).toBe(true);
  await expect(await totalUnder(page, "Charge (h)")).toHaveText(/^116\s270$/);
  await expect(first).toBeVisible();
  await expect(last).toHaveCount(0);

  await scrollToFoot(grid(page));
  await expect(last).toBeVisible();
  await expect(last).toHaveAttribute("aria-rowindex", "6001");
  // The rows of the top are gone, but the first, the row of the active cell, kept rendered.
  await expect(grid(page).getByRole("row", { name: /^2 .*Études de détail/ })).toHaveCount(0);
  await expect(first).not.toBeInViewport();
  expect(await withinBox(grid(page), header)).toBe(true);
  expect(await withinBox(grid(page), totals)).toBe(true);
});

/** The rows a step of the scroll goes through, down the six thousand of the answer. */
const STEP = 200;

test("scrolls through the thousand tasks and their lines, its header and its totals in view all the way down [WF-IHM-0060-A]", async ({
  page,
}) => {
  // Thirty steps, each checked by a few round trips to the browser: slow beside the other paths.
  test.slow();
  await openHydrated(page, GRID);
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  const { header, totals, last } = edges(page);
  // Two hundred rows at a time, as a scroll bar dragged down: each row reached is in view, between
  // the header and the totals, which have not moved from the window.
  for (let position = STEP; position <= 6000; position += STEP) {
    const row = await scrollToPosition(grid(page), position);
    expect(await withinBox(grid(page), row), `row ${position.toString()}`).toBe(true);
    expect(await withinBox(grid(page), header), `header at ${position.toString()}`).toBe(true);
    expect(await withinBox(grid(page), totals), `totals at ${position.toString()}`).toBe(true);
  }
  // Its label, pinned at the start: the row itself, with the category and the role (US-0120), is
  // wider than the grid at this width, which clips it sideways.
  await expect(last.getByRole("gridcell").nth(1)).toBeInViewport({ ratio: 1 });
  await expect(header).toBeInViewport({ ratio: 1 });
  await expect(totals).toBeInViewport({ ratio: 1 });
});

test.describe("on a low window", () => {
  test.use({ viewport: { width: 700, height: 300 } });

  test("keeps the header and the totals in view as the grid scrolls down to its last row [WF-IHM-0060-A]", async ({
    page,
  }) => {
    await openHydrated(page, GRID);
    await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
    await scrollPageToGrid(grid(page));
    await scrollToFoot(grid(page));
    const { header, totals, last } = edges(page);
    expect(await withinBox(grid(page), header)).toBe(true);
    expect(await withinBox(grid(page), totals)).toBe(true);
    // The last of the six thousand rows is in view, between the header and the totals.
    expect(await withinBox(grid(page), last)).toBe(true);
    const [over, row, under] = await Promise.all([
      header.boundingBox(),
      last.boundingBox(),
      totals.boundingBox(),
    ]);
    expect(row?.y ?? 0).toBeGreaterThanOrEqual((over?.y ?? 0) + (over?.height ?? 0) - 1);
    expect((row?.y ?? 0) + (row?.height ?? 0)).toBeLessThanOrEqual((under?.y ?? 0) + 1);
  });

  test("sizes its rows by the root font: enlarged, the rows grow with it and the header and totals stay in view", async ({
    page,
  }) => {
    await openHydrated(page, GRID);
    await expect(grid(page)).toBeVisible();
    // The user enlarges the font of the browser: the root font grows, and the window says so.
    await page.addStyleTag({ content: "html { font-size: 24px; }" });
    await page.evaluate(() => window.dispatchEvent(new Event("resize")));
    const first = await edges(page).first.boundingBox();
    const second = await grid(page)
      .getByRole("row", { name: /^2 .*Études de détail/ })
      .boundingBox();
    // 1.75 rem at 24 pixels: 42 pixels from one row to the next.
    expect((second?.y ?? 0) - (first?.y ?? 0)).toBeCloseTo(42, 0);
    await scrollPageToGrid(grid(page));
    await scrollToFoot(grid(page));
    const { header, totals } = edges(page);
    expect(await withinBox(grid(page), header)).toBe(true);
    expect(await withinBox(grid(page), totals)).toBe(true);
  });
});

test.describe("on a narrow window", () => {
  test.use({ viewport: { width: 700, height: 700 } });

  test("keeps the label of each row, the header and the totals in view as the grid scrolls sideways [WF-IHM-0060-A]", async ({
    page,
  }) => {
    await openHydrated(page, GRID);
    const label = grid(page).getByRole("gridcell", { name: /Études de détail$/ });
    const { totals } = edges(page);
    const box = scroller(grid(page));
    await expect(label).toBeInViewport({ ratio: 1 });
    await expect(totals).toBeInViewport({ ratio: 1 });

    // The grid is wider than the window: it scrolls sideways, to its last column.
    await box.evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
    });
    await expect.poll(() => box.evaluate((element) => element.scrollLeft)).toBeGreaterThan(100);
    const inflated = grid(page).getByRole("columnheader", {
      name: "Calculé Montant corrigé de l’inflation",
    });
    await expect(inflated).toBeInViewport();

    // The label, its header and the caption of the totals stay at the start, beside the row
    // numbers, whatever is scrolled under them.
    const start = await box.boundingBox();
    for (const pinned of [
      label,
      totals,
      grid(page).getByRole("columnheader", { name: "Libellé" }),
    ]) {
      await expect(pinned).toBeInViewport({ ratio: 1 });
      expect((await pinned.boundingBox())?.x).toBeCloseTo((start?.x ?? 0) + 1 + 48, 0);
    }
  });
});

/**
 * How long a path holds the server actions it proves the sort does not wait for: longer than the
 * wait of the address, so that a sort which waited for them would fail.
 */
const HELD = WORKING + 5_000;

test("asks the server for the sort of a column clicked, both ways, by the parameters of the contract", async ({
  page,
}) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  await openHydrated(page, GRID);
  const header = grid(page).getByRole("columnheader", { name: "Calculé Montant (année de réf.)" });
  await expect(header).not.toHaveAttribute("aria-sort");
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?sort_by=base_amount&sort_order=asc`, { timeout: WORKING });
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?sort_by=base_amount&sort_order=desc`, {
    timeout: WORKING,
  });
  await expect(header).toHaveAttribute("aria-sort", "descending");
  await expect(grid(page)).toHaveAttribute("aria-busy", "false");
  // The rows are those of the answer, in its order: the fake back serves the same example
  // whatever the sort (US-0110, gap on WF-IHM-0060-A), and the grid reorders nothing.
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  await expect(grid(page).getByRole("row").nth(1)).toHaveAccessibleName(/^1 .*Études/);
});

test("shows the sort asked without waiting for the server actions of the page, its preference among them", async ({
  page,
}) => {
  // The opening and the sort, each in the bound of a grid, beside actions held longer than one
  // (`HELD`): more than the thirty seconds of a test.
  test.slow();
  // Every server action of the page held longer than the wait of an address (`HELD`) — the
  // preference of the sort among them. Next shows a navigation only once the server actions dispatched after it
  // have answered: the preference is written once the sort is shown, and the page opens without
  // any — an action goes to the address the page shows as it is dispatched.
  const dispatched: string[] = [];
  await page.route(`**${GRID}*`, async (route) => {
    if (route.request().headers()["next-action"] !== undefined) {
      dispatched.push(route.request().url());
      await new Promise((resolve) => setTimeout(resolve, HELD));
    }
    await route.continue().catch(() => undefined);
  });
  await openHydrated(page, GRID);
  const header = grid(page).getByRole("columnheader", { name: "Calculé Montant (année de réf.)" });
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?sort_by=base_amount&sort_order=asc`, { timeout: WORKING });
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  expect(dispatched.filter((url) => !url.includes("?sort_by="))).toEqual([]);
});

test("shows the sort asked without waiting for the totals a searched grid reads anew after a write", async ({
  page,
}) => {
  // The opening and the sort, each in the bound of a grid, beside actions held longer than one
  // (`HELD`): more than the thirty seconds of a test.
  test.slow();
  // A grid read with a search reads its totals anew once its writes answered, by a server action
  // of its own, held here longer than the wait of an address (`HELD`): it leaves before the sort is
  // clicked, and Next shows a navigation without waiting for the actions dispatched before it.
  const isRetotal = (request: Request) =>
    request.headers()["next-action"] !== undefined &&
    (request.postData() ?? "").includes("revue") &&
    !(request.postData() ?? "").includes("lock_version");
  await page.route(`**${GRID}*`, async (route) => {
    if (isRetotal(route.request())) {
      await new Promise((resolve) => setTimeout(resolve, HELD));
    }
    await route.continue().catch(() => undefined);
  });
  await openHydrated(page, `${GRID}?search=revue`);
  // The label of row 28, the first line drawn after the core, entered: the fake back answers its
  // line. Past the rows in view as the grid opens: scrolled to first.
  const label = (await scrollToPosition(grid(page), 28)).getByRole("gridcell").nth(1);
  await label.click();
  await page.keyboard.type("Heures de câblage");
  const retotal = page.waitForRequest(isRetotal);
  await page.keyboard.press("Enter");
  await expect(label).toHaveText("Heures de câblage");
  await retotal;
  const header = grid(page).getByRole("columnheader", { name: "Calculé Montant (année de réf.)" });
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?search=revue&sort_by=base_amount&sort_order=asc`, {
    timeout: WORKING,
  });
  await expect(header).toHaveAttribute("aria-sort", "ascending");
});

test("hides a column chosen in the menu of the columns, and searches the labels on the server, the field keeping the focus", async ({
  page,
}) => {
  await openHydrated(page, GRID);
  await page.getByRole("button", { name: "Colonnes" }).click();
  await page.getByRole("menuitemcheckbox", { name: "Qté" }).click();
  await page.keyboard.press("Escape");
  await expect(grid(page).getByRole("columnheader", { name: "Qté" })).toHaveCount(0);
  await expect(grid(page).getByRole("columnheader", { name: "Charge (h)" })).toBeVisible();

  const search = page.getByRole("searchbox", { name: "Rechercher un libellé" });
  await search.fill("revue");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${GRID}?search=revue`, { timeout: WORKING });
  // The address shown is the one the grid was read under: the field stayed, with the focus and the
  // search, never remounted for it (#553).
  await expect(search).toBeFocused();
  await expect(search).toHaveValue("revue");
});

test("folds a task over its lines and the tree down to a level, the keyboard going through the rows that stay", async ({
  page,
}) => {
  await openHydrated(page, GRID);
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  // A task of the core at the third level, over its line, before its next sibling, row 16.
  const task = grid(page).getByRole("row", { name: /^14 .*Relance du fournisseur/ });
  const line = grid(page).getByRole("row", { name: /^15 .*Frais de relance/ });
  await expect(task).toHaveAttribute("aria-expanded", "true");
  await expect(line).toBeVisible();

  // Alt and minus on a cell of the task folds its lines; the down arrow goes to the next task.
  const label = task.getByRole("gridcell").nth(1);
  await label.click();
  await page.keyboard.press("Alt+Minus");
  await expect(task).toHaveAttribute("aria-expanded", "false");
  await expect(line).toHaveCount(0);
  await expect(label).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(rowAt(grid(page), 15).getByRole("gridcell").nth(1)).toBeFocused();
  await expect(rowAt(grid(page), 15)).toHaveAccessibleName(/^16 .*Transport exceptionnel/);
  await expect(rowAt(grid(page), 15)).toHaveAttribute("aria-level", "3");

  // The bar folds the tree whole, down to a level, and unfolds it whole.
  const tree = page.getByRole("button", { name: "Arbre" });
  const menu = page.getByRole("menu");
  await openMenu(tree, menu);
  await menu.getByRole("menuitem", { name: "Tout plier" }).click();
  const first = edges(page).first;
  await expect(first).toHaveAttribute("aria-expanded", "false");
  await expect(task).toHaveCount(0);
  await expect(rowAt(grid(page), 2)).toHaveAttribute("aria-level", "1");
  await openMenu(tree, menu);
  await menu.getByRole("menuitem", { name: "Jusqu’au niveau 3" }).click();
  await expect(task).toHaveAttribute("aria-expanded", "false");
  await expect(line).toHaveCount(0);
  await openMenu(tree, menu);
  await menu.getByRole("menuitem", { name: "Tout déplier" }).click();
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  await expect(line).toBeVisible();
});
