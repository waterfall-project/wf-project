// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { rowAt, withinBox } from "./scroll";

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

// Number, label, quantity, hours, unit disbursement, budgeted, re-estimated.
const LABEL = 1;
const QUANTITY = 2;
const HOURS = 3;
const DISBURSEMENT = 4;
const BUDGETED = 5;
const REESTIMATED = 6;

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * Open the estimate, and reach its active cell by Tab alone, as the keyboard does: some forty
 * stops, each a round trip to the browser, which the journey is given the time of (`test.slow`).
 */
async function tabIntoGrid(page: Page): Promise<Locator> {
  test.slow();
  await page.goto(ESTIMATE);
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
  await expect(cellAt(grid, 1, LABEL)).toBeFocused();
  return grid;
}

/** Press keys, one after the other. */
async function press(page: Page, ...keys: readonly string[]): Promise<void> {
  for (const key of keys) {
    await page.keyboard.press(key);
  }
}

test("stops on the computed cells without entering them, and refuses a try", async ({ page }) => {
  const grid = await tabIntoGrid(page);
  for (let row = 1; row < 21; row += 1) {
    await page.keyboard.press("ArrowDown");
  }
  await expect(rowAt(grid, 21)).toContainText("Provision");
  await expect(cellAt(grid, 21, LABEL)).toBeFocused();
  await expect(cellAt(grid, 21, LABEL)).toBeInViewport();

  // The arrows stop on the quantity the server computes, which opens no entry, and go past it.
  await page.keyboard.press("ArrowRight");
  const quantity = cellAt(grid, 21, QUANTITY);
  await expect(quantity).toBeFocused();
  await expect(quantity).toHaveAttribute("aria-readonly", "true");
  await press(page, "ArrowRight", "ArrowRight");
  await expect(cellAt(grid, 21, DISBURSEMENT)).toBeFocused();
  await expect(grid.getByRole("textbox")).toHaveCount(0);

  // A try is refused, naming what the value depends on, with no field; Escape comes back.
  await page.keyboard.press("Enter");
  const refusal = page.getByRole("dialog", { name: "Valeur calculée" });
  await expect(refusal).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Débours unit." })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(refusal).toHaveCount(0);
  await expect(cellAt(grid, 21, DISBURSEMENT)).toBeFocused();
  await press(page, "ArrowLeft", "ArrowRight", "ArrowRight");
  await expect(cellAt(grid, 21, BUDGETED)).toBeFocused();
  await expect(cellAt(grid, 21, HOURS)).not.toHaveAttribute("aria-readonly");
});

test("keeps the active cell in the window, clear of the header and the totals, from the first row to the six thousandth", async ({
  page,
}) => {
  const grid = await tabIntoGrid(page);
  const header = grid.getByRole("columnheader", { name: "Libellé" });
  // The caption of the totals: its cells stick to the foot of the grid, its row keeps its place.
  const totals = grid.getByRole("row").last().getByRole("gridcell").nth(LABEL);
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
  await expect(cellAt(grid, 6000, REESTIMATED)).toBeFocused();
});

test.describe("on a narrow window", () => {
  test.use({ viewport: { width: 700, height: 500 } });

  test("keeps the active cell clear of the pinned columns as it goes back along the row", async ({
    page,
  }) => {
    const grid = await tabIntoGrid(page);
    const label = grid.getByRole("columnheader", { name: "Libellé" });
    await page.keyboard.press("End");
    await expect(cellAt(grid, 1, REESTIMATED)).toBeFocused();
    for (const column of [BUDGETED, DISBURSEMENT, HOURS, QUANTITY]) {
      await page.keyboard.press("ArrowLeft");
      const active = cellAt(grid, 1, column);
      await expect(active).toBeFocused();
      const [cell, pinned] = await Promise.all([active.boundingBox(), label.boundingBox()]);
      expect(cell?.x ?? 0, `column ${column.toString()}`).toBeGreaterThanOrEqual(
        (pinned?.x ?? 0) + (pinned?.width ?? 0) - 1,
      );
    }
  });
});
