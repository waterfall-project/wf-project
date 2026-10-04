// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { rowAt } from "./scroll";

// The fake back serves the first example of `listNodes`, the structure of the volumes of §4.6.2
// (EP-02/L2), which the journeys read by marks the generator writes
// (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py): row 4, a line of
// labour, « Heures d'ingénierie », 33 hours; row 21, a provision, whose quantity and unit
// disbursement the server computes. A cell validated is written by `updateEstimateLine`, whose
// first example the fake back serves whatever was written: the line of row 4, its label entered
// « Heures de câblage », nothing else changed — the fake back keeps nothing of what it is sent,
// so that each cell entered after it differs from the row answered, and is written. What the
// grid does with another answer is proven on its own examples by the tests of the grid
// (`entry.dom.test.tsx`).
//
// Every gesture is a key: the grid is reached by Tab, as a user who never takes the mouse.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;

// Number, label, category, role, quantity, hours, unit disbursement, amount at the year of
// reference, amount corrected for inflation.
const LABEL = 1;
const CATEGORY = 2;
const ROLE = 3;
const QUANTITY = 4;
const HOURS = 5;
const REFERENCE = 7;

/** A cell of the row at a position among the rows of the answer, by the position of its column. */
function cellAt(grid: Locator, row: number, column: number): Locator {
  return rowAt(grid, row).getByRole("gridcell").nth(column);
}

/**
 * Open the estimate, and reach its active cell by Tab alone, as the keyboard does: past the
 * shell and the bar of the grid, to the one stop of the grid (#182) — each stop a round trip to
 * the browser, which the journey is given the time of (`test.slow`).
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
  await expect(cellAt(grid, 1, LABEL)).toBeFocused();
  return grid;
}

/** Press keys, one after the other. */
async function press(page: Page, ...keys: readonly string[]): Promise<void> {
  for (const key of keys) {
    await page.keyboard.press(key);
  }
}

test("enters a whole line of the estimate without the mouse — label, category, role, quantity, effort —, and the last cell validated places the cursor on the next row [WF-IHM-0040-A]", async ({
  page,
}) => {
  const grid = await tabIntoGrid(page);
  // Each cell validated leaves by a server action of its own.
  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.headers()["next-action"] !== undefined) {
      writes.push(request.url());
    }
  });
  await press(page, "ArrowDown", "ArrowDown", "ArrowDown");
  await expect(cellAt(grid, 4, LABEL)).toBeFocused();

  // Typed, the label replaces the one read; Tab validates it and goes along the row.
  await page.keyboard.type("Heures de câblage");
  await page.keyboard.press("Tab");
  await expect(cellAt(grid, 4, CATEGORY)).toBeFocused();
  // The category is chosen by the first letters of its name, typed on the cell: its list opens.
  await page.keyboard.type("Mise en service");
  const categories = page.getByRole("combobox", { name: "Catégorie" });
  await expect(categories).toBeFocused();
  await expect(categories).toHaveValue("01926f3a-7c00-7000-8000-000000000405");
  await page.keyboard.press("Tab");
  await expect(cellAt(grid, 4, ROLE)).toBeFocused();
  // The role, from its list opened by Enter.
  await page.keyboard.press("Enter");
  await page.keyboard.type("Technicien");
  await expect(page.getByRole("combobox", { name: "Rôle" })).toHaveValue(
    "01926f3a-7c00-7000-8000-000000000452",
  );
  await page.keyboard.press("Tab");
  await expect(cellAt(grid, 4, QUANTITY)).toBeFocused();
  await page.keyboard.type("2");
  await page.keyboard.press("Tab");
  await page.keyboard.type("12,5");
  await page.keyboard.press("Enter");

  // The row below, at the cell the line was started from, in view.
  const next = cellAt(grid, 5, LABEL);
  await expect(next).toBeFocused();
  await expect(next).toBeInViewport();
  // The five cells written, one after the other.
  await expect.poll(() => writes.length).toBe(5);
  // The line as the server last answered it — the fake back keeps nothing of what it is sent —,
  // in place of what was typed.
  await expect(rowAt(grid, 4).getByRole("gridcell")).toHaveText([
    "4",
    "Heures de câblage",
    "Ingénierie électrique",
    "Ingénieur électricien",
    "1",
    "33",
    "",
    /2\s640,00$/,
    /2\s640,00$/,
  ]);
  // No refusal told.
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("leaves a cell at its value before when its entry under way is abandoned [WF-IHM-0040-A]", async ({
  page,
}) => {
  const grid = await tabIntoGrid(page);
  await press(page, "ArrowDown", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowRight");
  await press(page, "ArrowRight", "ArrowRight");
  const hours = cellAt(grid, 4, HOURS);
  await expect(hours).toBeFocused();
  await page.keyboard.type("99");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("99");
  await page.keyboard.press("Escape");
  await expect(hours.getByRole("textbox")).toHaveCount(0);
  await expect(hours).toHaveText("33");
  await expect(hours).toBeFocused();
});

test("traverses the computed cells of a line entered along its row, without entering them [WF-IHM-0040-A]", async ({
  page,
}) => {
  const grid = await tabIntoGrid(page);
  for (let row = 1; row < 21; row += 1) {
    await page.keyboard.press("ArrowDown");
  }
  await expect(rowAt(grid, 21)).toContainText("Provision");
  await expect(cellAt(grid, 21, LABEL)).toBeFocused();
  // From its label, Tab goes past its quantity and its unit disbursement, which the server
  // computes, past its category, its role and its effort, which its node does not accept (#219),
  // and past its amounts, to the next row.
  await press(page, "Enter", "Tab");
  await expect(cellAt(grid, 22, LABEL)).toBeFocused();
  for (const column of [CATEGORY, ROLE, QUANTITY, HOURS]) {
    await expect(cellAt(grid, 21, column)).toHaveAttribute("aria-readonly", "true");
  }
  await expect(grid.getByRole("textbox")).toHaveCount(0);
});

test("opens the entry of the effort on a digit typed, and the refusal of the amount, with no field, on the same digit [WF-IHM-0040-A]", async ({
  page,
}) => {
  const grid = await tabIntoGrid(page);
  await press(page, "ArrowDown", "ArrowDown", "ArrowDown", "ArrowRight", "ArrowRight");
  await press(page, "ArrowRight", "ArrowRight");
  const hours = cellAt(grid, 4, HOURS);
  await expect(hours).toBeFocused();
  // The effort of a line of labour is entered: a digit opens its entry, with it.
  await page.keyboard.press("7");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("7");
  await page.keyboard.press("Escape");
  await expect(hours).toHaveText("33");
  // Its amount is computed: the arrows reach it, the same digit opens no field but its refusal.
  await press(page, "ArrowRight", "ArrowRight");
  const amount = cellAt(grid, 4, REFERENCE);
  await expect(amount).toBeFocused();
  await expect(amount).toHaveAttribute("aria-readonly", "true");
  await page.keyboard.press("7");
  await expect(page.getByRole("dialog", { name: "Valeur calculée" })).toBeVisible();
  await expect(grid.getByRole("textbox")).toHaveCount(0);
});
