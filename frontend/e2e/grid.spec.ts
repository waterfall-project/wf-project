// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { scrollPageToGrid, scroller, scrollToFoot, withinBox } from "./scroll";

// The fake back serves the first example of `listNodes`, the structure of the volumes of §4.6.2
// (EP-02/L2): a thousand tasks and five thousand lines, six thousand rows, of which the grid
// renders those in view. The journeys read it by marks the generator writes today, which no test
// of the generator holds yet — the summary task of row 1, « Études », the lot of row 2, the task of
// row 3, the milestone of row 6000, the totals of the answer —, and never count the rows rendered:
// the row count of the grid says how many there are. Measuring the second of §4.6.2 is US-0110/L2
// (#107).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const GRID = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

/** The rows of the answer, and the header and totals around them. */
const ROW_COUNT = "6002";

/** The grid of the estimate. */
function grid(page: Page) {
  return page.getByRole("grid", { name: "Grille de devis" });
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
    last: grid(page).getByRole("row", { name: /^6000 .*Fin du lot 10\.3/ }),
  };
}

test("opens the estimate of a thousand tasks and five thousand lines, and scrolls down to its last row [WF-IHM-0060-A]", async ({
  page,
}) => {
  await page.goto(GRID);
  const { header, totals, first, last } = edges(page);
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  // The grid holds in the window as it opens, under the header and the indicators of its screen:
  // its header and its totals are in view, the totals those of the answer under their column.
  expect(await withinBox(grid(page), header)).toBe(true);
  expect(await withinBox(grid(page), totals)).toBe(true);
  await expect(await totalUnder(page, "Charge (h)")).toHaveText(/^116\s348$/);
  await expect(first).toBeVisible();
  await expect(last).toHaveCount(0);

  await scrollToFoot(grid(page));
  await expect(last).toBeVisible();
  await expect(last).toHaveAttribute("aria-rowindex", "6001");
  await expect(first).toHaveCount(0);
  expect(await withinBox(grid(page), header)).toBe(true);
  expect(await withinBox(grid(page), totals)).toBe(true);
});

test.describe("on a low window", () => {
  test.use({ viewport: { width: 700, height: 300 } });

  test("keeps the header and the totals in view as the grid scrolls down to its last row [WF-IHM-0060-A]", async ({
    page,
  }) => {
    await page.goto(GRID);
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
    await page.goto(GRID);
    await expect(grid(page)).toBeVisible();
    // The user enlarges the font of the browser: the root font grows, and the window says so.
    await page.addStyleTag({ content: "html { font-size: 24px; }" });
    await page.evaluate(() => window.dispatchEvent(new Event("resize")));
    const first = await edges(page).first.boundingBox();
    const second = await grid(page)
      .getByRole("row", { name: /^2 .*Études — Poste de commande/ })
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
    await page.goto(GRID);
    const label = grid(page).getByRole("gridcell", { name: /Préparation 1\.1\.1$/ });
    const { totals } = edges(page);
    const box = scroller(grid(page));
    await expect(label).toBeInViewport({ ratio: 1 });
    await expect(totals).toBeInViewport({ ratio: 1 });

    // The grid is wider than the window: it scrolls sideways, to its last column.
    await box.evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
    });
    await expect.poll(() => box.evaluate((element) => element.scrollLeft)).toBeGreaterThan(100);
    const reestimated = grid(page).getByRole("columnheader", { name: "Calculé Réestimé" });
    await expect(reestimated).toBeInViewport();

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

test("asks the server for the sort of a column clicked, both ways, by the parameters of the contract", async ({
  page,
}) => {
  await page.goto(GRID);
  const header = grid(page).getByRole("columnheader", { name: "Calculé Budgété" });
  await expect(header).not.toHaveAttribute("aria-sort");
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?sort_by=budgeted_amount&sort_order=asc`);
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  await header.getByRole("button").click();
  await expect(page).toHaveURL(`${GRID}?sort_by=budgeted_amount&sort_order=desc`);
  await expect(header).toHaveAttribute("aria-sort", "descending");
  await expect(grid(page)).toHaveAttribute("aria-busy", "false");
  // The rows are those of the answer, in its order: the fake back serves the same example
  // whatever the sort (US-0110, gap on WF-IHM-0060-A), and the grid reorders nothing.
  await expect(grid(page)).toHaveAttribute("aria-rowcount", ROW_COUNT);
  await expect(grid(page).getByRole("row").nth(1)).toHaveAccessibleName(/^1 .*Études/);
});

test("hides a column chosen in the menu of the columns, and searches the labels on the server", async ({
  page,
}) => {
  await page.goto(GRID);
  await page.getByRole("button", { name: "Colonnes" }).click();
  await page.getByRole("menuitemcheckbox", { name: "Qté" }).click();
  await page.keyboard.press("Escape");
  await expect(grid(page).getByRole("columnheader", { name: "Qté" })).toHaveCount(0);
  await expect(grid(page).getByRole("columnheader", { name: "Charge (h)" })).toBeVisible();

  await page.getByRole("searchbox", { name: "Rechercher un libellé" }).fill("revue");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${GRID}?search=revue`);
});
