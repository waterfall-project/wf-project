// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated } from "./hydration";
import { rowAt } from "./scroll";

// The estimate of the current revision of the witness project, which the session may enter:
// undo and redo are placed in its bar, in the menu of its cells and on its keys, unavailable until
// EP-06 wires them (US-0140). Row 4 is a line of labour, « Heures d'ingénierie »
// (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const TOLD_UNDO =
  "Annuler est indisponible : le serveur ne conserve pas encore l’historique des saisies.";

test("places Undo and Redo in the grid, its menu and its keys, unavailable and saying why, and leaves Ctrl+Z to the cell being entered", async ({
  page,
}) => {
  await openHydrated(page, ESTIMATE);
  const grid = page.getByRole("grid", { name: "Grille de devis" });
  const reason = "Indisponibles tant que le serveur ne conserve pas l’historique des saisies.";
  for (const name of ["Annuler", "Rétablir"]) {
    const button = page.getByRole("button", { name, exact: true });
    await expect(button).toHaveAttribute("aria-disabled", "true");
    await expect(button).toHaveAccessibleDescription(reason);
  }

  // The menu of a cell, by a right click and from the keyboard, the focus back on the cell.
  const cell = rowAt(grid, 10).getByRole("gridcell").nth(1);
  const menu = page.getByRole("menu", { name: "Menu de la cellule" });
  await cell.click({ button: "right" });
  await expect(menu.getByRole("menuitem", { name: /^Annuler/ })).toContainText("Ctrl+Z");
  await expect(menu.getByRole("menuitem", { name: /^Rétablir/ })).toContainText("Ctrl+Maj+Z");
  await expect(menu.getByRole("menuitem", { name: /^Annuler/ })).toHaveAccessibleDescription(
    reason,
  );
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await cell.click();
  await expect(cell).toBeFocused();
  await page.keyboard.press("Shift+F10");
  await expect(menu).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(cell).toBeFocused();

  // On the grid, the shortcut tells the command unavailable.
  await page.keyboard.press("Control+z");
  await expect(page.getByRole("status").filter({ hasText: TOLD_UNDO })).toHaveCount(1);

  // In the editor of the cell, Ctrl+Z is the browser's: it undoes what was typed there.
  await page.keyboard.press("F2");
  const field = page.getByRole("textbox", { name: "Libellé" });
  await expect(field).toBeFocused();
  const label = await field.inputValue();
  await page.keyboard.insertText(" bis");
  await expect(field).toHaveValue(`${label} bis`);
  await page.keyboard.press("Control+z");
  await expect(field).toHaveValue(label);
  await expect(field).toBeFocused();
});
