// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";
import { rowAt, scroller, withinBox } from "./scroll";

// The fake back serves the first example of `listNodes`, the structure of the volumes of §4.6.2
// (EP-02/L2), which the journeys read by marks the generator writes
// (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py): row 1, the phase
// « Études »; row 21, a provision, whose quantity and unit disbursement the server computes; six
// thousand rows in all.
//
// Every gesture is a key: the grid is reached by Tab, as a user who never takes the mouse.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

// The columns the journeys move along, by their heading (`columnsOf`).
const COLUMNS = {
  label: "Libellé",
  quantity: "Qté",
  hours: "Charge (h)",
  disbursement: "Débours unit.",
  reference: "Montant (année de réf.)",
  inflated: "Montant corrigé de l’inflation",
} as const;

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * Open the estimate hydrated, and reach its active cell by Tab alone, as the keyboard does: past
 * the shell and the bar of the grid, to the one stop of the grid (#182) — each stop a round trip
 * to the browser, which the journey is given the time of (`test.slow`).
 */
async function tabIntoGrid(page: Page): Promise<{
  readonly grid: Locator;
  readonly at: Readonly<Record<keyof typeof COLUMNS, number>>;
}> {
  test.slow();
  await openHydrated(page, ESTIMATE);
  const grid = page.getByRole("grid", { name: "Grille de devis" });
  const active = grid.locator('td[tabindex="0"]');
  await expect(active).toHaveCount(1);
  await expect
    .poll(
      async () => {
        await page.keyboard.press("Tab");
        return active.evaluate((element) => element === document.activeElement);
      },
      { intervals: [0], timeout: 30_000 },
    )
    .toBe(true);
  // The first row, at its label.
  const at = await columnsOf(grid, COLUMNS);
  await expect(cellAt(grid, 1, at.label)).toBeFocused();
  return { grid, at };
}

/** Press keys, one after the other. */
async function press(page: Page, ...keys: readonly string[]): Promise<void> {
  for (const key of keys) {
    await page.keyboard.press(key);
  }
}

/** A key pressed as many times as there are columns from one to another. */
function times(key: string, count: number): string[] {
  return Array.from({ length: count }, () => key);
}

test("is one stop of the tabulation, and reaches the header by the arrows, which sorts its column by Enter [WF-IHM-0100-A]", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page);
  // Tab leaves the grid, Shift+Tab comes back to its active cell: no other stop within it.
  await page.keyboard.press("Tab");
  await expect(grid.locator(":focus")).toHaveCount(0);
  await page.keyboard.press("Shift+Tab");
  await expect(cellAt(grid, 1, at.label)).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(grid.locator(":focus")).toHaveCount(0);
  await page.keyboard.press("Tab");
  await expect(cellAt(grid, 1, at.label)).toBeFocused();
  // The up arrow reaches the header, which Enter sorts by, the focus kept on it.
  await page.keyboard.press("ArrowUp");
  const header = grid.getByRole("columnheader", { name: "Libellé" });
  await expect(header).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${ESTIMATE}?sort_by=label&sort_order=asc`, { timeout: WORKING });
  await expect(header).toHaveAttribute("aria-sort", "ascending");
  await expect(header).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(cellAt(grid, 1, at.label)).toBeFocused();
});

test("stops on the computed cells without entering them, and refuses a try", async ({ page }) => {
  const { grid, at } = await tabIntoGrid(page);
  for (let row = 1; row < 21; row += 1) {
    await page.keyboard.press("ArrowDown");
  }
  await expect(rowAt(grid, 21)).toContainText("Provision");
  await expect(cellAt(grid, 21, at.label)).toBeFocused();
  await expect(cellAt(grid, 21, at.label)).toBeInViewport();

  // The arrows stop on the quantity the server computes, which opens no entry, and go past it.
  await press(page, ...times("ArrowRight", at.quantity - at.label));
  const quantity = cellAt(grid, 21, at.quantity);
  await expect(quantity).toBeFocused();
  await expect(quantity).toHaveAttribute("aria-readonly", "true");
  await press(page, ...times("ArrowRight", at.disbursement - at.quantity));
  await expect(cellAt(grid, 21, at.disbursement)).toBeFocused();
  await expect(grid.getByRole("textbox")).toHaveCount(0);

  // A try is refused, naming what the value depends on, with no field; Escape comes back.
  await page.keyboard.press("Enter");
  const refusal = page.getByRole("dialog", { name: "Valeur calculée" });
  await expect(refusal).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Débours unit." })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(refusal).toHaveCount(0);
  await expect(cellAt(grid, 21, at.disbursement)).toBeFocused();
  await press(page, "ArrowLeft", ...times("ArrowRight", at.reference - at.disbursement + 1));
  await expect(cellAt(grid, 21, at.reference)).toBeFocused();
  // The effort of a provision, which its node does not accept, is read only as well (#219).
  await expect(cellAt(grid, 21, at.hours)).toHaveAttribute("aria-readonly", "true");
});

test("keeps the active cell in the window, clear of the header and the totals, from the first row to the six thousandth", async ({
  page,
}) => {
  const { grid, at } = await tabIntoGrid(page);
  const header = grid.getByRole("columnheader", { name: "Libellé" });
  // The caption of the totals: its cells stick to the foot of the grid, its row keeps its place.
  const totals = grid.getByRole("row").last().getByRole("gridcell").nth(at.label);
  for (const keys of [["PageDown", "PageDown"], ["Control+End"], ["PageUp"], ["Control+Home"]]) {
    await press(page, ...keys);
    const active = grid.locator("td:focus");
    await expect(active).toHaveCount(1);
    await expect(active).toBeInViewport();
    expect(await withinBox(grid, active)).toBe(true);
    await expect(header).toBeInViewport();
    await expect(totals).toBeInViewport();
    // Neither under the header nor under the totals.
    const [cell, top, foot] = await Promise.all([
      active.boundingBox(),
      header.boundingBox(),
      totals.boundingBox(),
    ]);
    expect(cell?.y ?? 0).toBeGreaterThanOrEqual((top?.y ?? 0) + (top?.height ?? 0) - 1);
    // The border the last row and the totals share aside.
    expect((cell?.y ?? 0) + (cell?.height ?? 0)).toBeLessThanOrEqual((foot?.y ?? 0) + 2);
  }
  await press(page, "Control+End");
  await expect(cellAt(grid, 6000, at.inflated)).toBeFocused();
});

test.describe("on a narrow window", () => {
  test.use({ viewport: { width: 700, height: 500 } });

  test("keeps the active cell clear of the pinned columns as it goes back along the row", async ({
    page,
  }) => {
    const { grid, at } = await tabIntoGrid(page);
    const label = grid.getByRole("columnheader", { name: "Libellé" });
    await page.keyboard.press("End");
    await expect(cellAt(grid, 1, at.inflated)).toBeFocused();
    for (let column = at.inflated - 1; column >= at.quantity; column -= 1) {
      await page.keyboard.press("ArrowLeft");
      const active = cellAt(grid, 1, column);
      await expect(active).toBeFocused();
      const [cell, pinned] = await Promise.all([active.boundingBox(), label.boundingBox()]);
      expect(cell?.x ?? 0, `column ${column.toString()}`).toBeGreaterThanOrEqual(
        (pinned?.x ?? 0) + (pinned?.width ?? 0) - 1,
      );
    }
  });

  test("brings each header into view sideways as the arrows move along the header, the rows left where they are", async ({
    page,
  }) => {
    const { grid, at } = await tabIntoGrid(page);
    const label = grid.getByRole("columnheader", { name: "Libellé" });
    const headers = grid.getByRole("columnheader");
    await page.keyboard.press("ArrowUp");
    await page.keyboard.press("End");
    await expect(headers.nth(at.inflated)).toBeFocused();
    await expect(headers.nth(at.inflated)).toBeInViewport({ ratio: 1 });
    // The rows scrolled down, as the wheel does: moving along the header scrolls them no more.
    const top = await scroller(grid).evaluate((element) => {
      element.scrollTop = 560;
      return element.scrollTop;
    });
    expect(top).toBeGreaterThan(0);
    for (let column = at.inflated - 1; column >= at.quantity; column -= 1) {
      await page.keyboard.press("ArrowLeft");
      const active = headers.nth(column);
      await expect(active).toBeFocused();
      const [cell, pinned] = await Promise.all([active.boundingBox(), label.boundingBox()]);
      expect(cell?.x ?? 0, `column ${column.toString()}`).toBeGreaterThanOrEqual(
        (pinned?.x ?? 0) + (pinned?.width ?? 0) - 1,
      );
    }
    expect(await scroller(grid).evaluate((element) => element.scrollTop)).toBe(top);
  });
});

test.describe("on a window lower than the floor of the grid", () => {
  test.use({ viewport: { width: 700, height: 300 } });

  test("brings a cell of a pinned column into the window as the arrows move it down (#183)", async ({
    page,
  }) => {
    const { grid } = await tabIntoGrid(page);
    // The page scrolled back to its top: the grid overflows the window below it.
    await scroller(grid).evaluate((element) => {
      for (let each: Element | null = element; each !== null; each = each.parentElement) {
        each.scrollTop = 0;
      }
    });
    await page.keyboard.press("PageDown");
    const active = grid.locator("td:focus");
    await expect(active).toHaveAttribute("data-column", "label");
    await expect(active).toBeInViewport();
  });
});
