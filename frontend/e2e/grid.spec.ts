// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

// The fake back serves the first example of `listNodes`, a summary task, two tasks and a line:
// too few rows to scroll a thousand of them, which comes with the volumes of EP-02/L2 (#106) and
// the journey of US-0110/L2 (#107) — the component tests prove it on a thousand rows. Here, a
// narrow window makes the grid scroll sideways, as a wide one would on more columns.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const GRID = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

/** The grid of the estimate. */
function grid(page: Page) {
  return page.getByRole("grid", { name: "Grille de devis" });
}

/** The element the grid scrolls in. */
function scroller(page: Page) {
  return grid(page).locator("xpath=..");
}

/**
 * Scroll the grid to its foot, until it stays there: the grid may still be taking its first
 * measures when the page shows.
 */
async function scrollToFoot(page: Page) {
  await expect
    .poll(() =>
      scroller(page).evaluate((element) => {
        element.scrollTop = element.scrollHeight;
        return (
          element.scrollTop > 0 &&
          element.scrollTop + element.clientHeight >= element.scrollHeight - 1
        );
      }),
    )
    .toBe(true);
}

/**
 * Whether a cell lies wholly within the box of the element the grid scrolls in: the cells of
 * the header and of the totals are what sticks, their rows keep their place in the table.
 */
async function withinBox(page: Page, cell: Locator) {
  const box = await scroller(page).boundingBox();
  const bounds = await cell.boundingBox();
  if (box === null || bounds === null) {
    return false;
  }
  return bounds.y >= box.y - 1 && bounds.y + bounds.height <= box.y + box.height + 1;
}

/** The header of the labels, and the caption of the totals. */
function edges(page: Page) {
  return {
    header: grid(page).getByRole("columnheader", { name: "Libellé" }),
    totals: grid(page).getByRole("gridcell", { name: /^Total — 3 tâches, 1 ligne/ }),
    first: grid(page).getByRole("gridcell", { name: /Études$/ }),
  };
}

test.describe("on a low window", () => {
  test.use({ viewport: { width: 700, height: 300 } });

  test("keeps the header and the totals in view as the grid scrolls down to its last row [WF-IHM-0060-A]", async ({
    page,
  }) => {
    await page.goto(GRID);
    // The window is low enough for the grid to scroll down, even on the four nodes served.
    await expect(grid(page)).toBeVisible();
    expect(
      await scroller(page).evaluate((element) => element.scrollHeight > element.clientHeight),
    ).toBe(true);
    await scrollToFoot(page);
    const { header, totals, first } = edges(page);
    expect(await withinBox(page, header)).toBe(true);
    expect(await withinBox(page, totals)).toBe(true);
    // The first row went up under the header, which stays over it.
    const [under, over] = await Promise.all([first.boundingBox(), header.boundingBox()]);
    expect(under?.y ?? 0).toBeLessThan((over?.y ?? 0) + (over?.height ?? 0));
  });

  test("sizes its rows by the root font: enlarged, the rows grow with it and the header and totals stay in view", async ({
    page,
  }) => {
    await page.goto(GRID);
    await expect(grid(page)).toBeVisible();
    // The user enlarges the font of the browser: the root font grows, and the window says so.
    await page.addStyleTag({ content: "html { font-size: 24px; }" });
    await page.evaluate(() => window.dispatchEvent(new Event("resize")));
    const first = await grid(page)
      .getByRole("row", { name: /^1 .*Études/ })
      .boundingBox();
    const second = await grid(page)
      .getByRole("row", { name: /^2 .*Études de détail/ })
      .boundingBox();
    // 1.75 rem at 24 pixels: 42 pixels from one row to the next.
    expect((second?.y ?? 0) - (first?.y ?? 0)).toBeCloseTo(42, 0);
    await scrollToFoot(page);
    const { header, totals } = edges(page);
    expect(await withinBox(page, header)).toBe(true);
    expect(await withinBox(page, totals)).toBe(true);
  });
});

test.describe("on a narrow window", () => {
  test.use({ viewport: { width: 700, height: 700 } });

  test("keeps the label of each row, the header and the totals in view as the grid scrolls sideways [WF-IHM-0060-A]", async ({
    page,
  }) => {
    await page.goto(GRID);
    const label = grid(page).getByRole("gridcell", { name: "Ingénierie de détail" });
    const totals = grid(page).getByRole("gridcell", { name: /^Total — 3 tâches, 1 ligne/ });
    await expect(label).toBeInViewport();

    // The grid is wider than the window: it scrolls sideways, to its last column.
    const scroller = grid(page).locator("xpath=..");
    await scroller.evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
    });
    await expect
      .poll(() => scroller.evaluate((element) => element.scrollLeft))
      .toBeGreaterThan(100);
    const reestimated = grid(page).getByRole("columnheader", { name: "Calculé Réestimé" });
    await expect(reestimated).toBeInViewport();

    // The label, its header and the caption of the totals stay at the start, beside the row
    // numbers, whatever is scrolled under them.
    const start = await scroller.boundingBox();
    for (const pinned of [
      label,
      totals,
      grid(page).getByRole("columnheader", { name: "Libellé" }),
    ]) {
      await expect(pinned).toBeInViewport();
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
  // The rows are those of the answer, in its order: the fake back serves the same example
  // whatever the sort (US-0110, gap on WF-IHM-0060-A).
  await expect(grid(page).getByRole("row")).toHaveCount(6);
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
