// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The trees, their filters ranged in the bar (#2916/L6): each keeps its keyboard, its entry, its
 * fold, its undo and its commands of structure. The planning and the estimate replay them in their
 * own files — `keyboard.spec.ts`, `entry.spec.ts`, `paste.spec.ts`, `undo.spec.ts`,
 * `structure.spec.ts`, the fold in `planning.spec.ts` and `grid.spec.ts` —; the remaining to commit,
 * whose fold no path played, here, in one path, against the fake back. It pastes nothing: its grid
 * takes no block (`remaining-grid.tsx`). Row 10 is a line of labour, « Raccordement des borniers »
 * (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py).
 */
import { expect } from "@playwright/test";

import { openHydrated } from "./hydration";
import { test } from "./mode";
import { rowAt } from "./scroll";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const TOLD_UNDO =
  "Annuler est indisponible\u00a0: le serveur ne conserve pas encore l’historique des saisies.";

test("the remaining to commit, its filter in the bar, keeps its keyboard, its entry, its fold, its undo and its commands of structure [WF-IHM-0060-A]", async ({
  page,
}) => {
  await openHydrated(page, REMAINING);
  const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  // The filter of the tree lies in the bar of the grid, a menu that opens a dialog (L6).
  await expect(page.locator("[data-grid-toolbar] button[aria-haspopup='dialog']")).toHaveCount(1);

  // The keyboard: the arrows go from row to row, the grid one stop of the tabulation.
  const line = rowAt(grid, 10);
  await expect(line).toHaveAccessibleName(/Raccordement des borniers/);
  const label = line.getByRole("gridcell").nth(1);
  await label.click();
  await expect(label).toBeFocused();
  await page.keyboard.press("ArrowUp");
  await expect(rowAt(grid, 9).getByRole("gridcell").nth(1)).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(label).toBeFocused();

  // The entry: the effort re-estimated, abandoned by Escape, as it was.
  const header = grid.getByRole("columnheader", { name: "Charge (h)", exact: true });
  const position = await header.evaluate((th) =>
    th instanceof HTMLTableCellElement ? th.cellIndex : -1,
  );
  const hours = line.getByRole("gridcell").nth(position);
  const before = await hours.innerText();
  await hours.click();
  await page.keyboard.press("7");
  await expect(hours.getByRole("textbox", { name: "Charge (h)" })).toHaveValue("7");
  await page.keyboard.press("Escape");
  await expect(hours.getByRole("textbox")).toHaveCount(0);
  await expect(hours).toHaveText(before);
  await expect(hours).toBeFocused();

  // The commands of structure, from the keyboard: the menu of the cell inserts a line.
  const menu = page.getByRole("menu", { name: "Menu de la cellule" });
  await page.getByRole("heading", { level: 1 }).hover();
  await page.keyboard.press("Shift+F10");
  await expect(menu.getByRole("menuitem", { name: "Insérer une ligne" })).toBeFocused();
  await expect(menu.getByRole("menuitem", { name: /^Annuler/ })).toContainText("Ctrl+Z");
  // Escape closes the tooltip of the item first, once it opened, then the menu (#1541).
  const tooltip = page.locator("[data-slot=tooltip-content]");
  await expect(tooltip).toContainText("Insérer une ligne");
  await page.keyboard.press("Escape");
  await expect(tooltip).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(hours).toBeFocused();

  // The undo, on its keys, told unavailable: the server keeps no history of the entries yet.
  await page.keyboard.press("Control+z");
  await expect(page.getByRole("status").filter({ hasText: TOLD_UNDO })).toHaveCount(1);

  // The fold, by the keys of Microsoft Project: Alt and minus on a line folds the task over it,
  // the line out of the grid, the focus on the task; Alt and plus unfolds it.
  await label.click();
  await page.keyboard.press("Alt+Minus");
  const task = grid.getByRole("row").and(grid.locator("[aria-expanded='false']"));
  await expect(task).toHaveCount(1);
  await expect(grid.getByRole("row", { name: /Raccordement des borniers/ })).toHaveCount(0);
  await expect(task.getByRole("gridcell").nth(1)).toBeFocused();
  await page.keyboard.press("Alt+Shift+Equal");
  await expect(task).toHaveCount(0);
  await expect(grid.getByRole("row", { name: /Raccordement des borniers/ })).toHaveCount(1);
});
