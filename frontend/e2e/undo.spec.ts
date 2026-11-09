// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { columnsOf } from "./columns";
import { idle, seedEstimate } from "./estimate-seed";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { createOwnProject, openRevision } from "./own-project";
import { rowAt } from "./scroll";

// The remaining to commit of the current revision of the witness project, which the session may
// enter — the project is in progress, and its main structure lists the remaining to commit
// available, where it lists the estimate unavailable (WF-RAE-0040, WF-DEV-0050): undo and redo are
// placed in its bar, in the menu of its cells and on its keys, unavailable until its entries are
// recorded (US-0140). EP-06 wires those of the planning (US-1450): the last journey of this file
// plays them against the service, on a project the run creates. Row 10 is a line of labour, « Raccordement des borniers »
// (`test_the_marks_the_journeys_read`, tools/tests/test_mockstructure.py).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const REMAINING = `/projects/${PROJECT}/revisions/${REVISION}/remaining`;
const TOLD_UNDO =
  "Annuler est indisponible\u00a0: le serveur ne conserve pas encore l’historique des saisies.";

/**
 * Longer than the focus or the pointer rests on an item of a menu before its tooltip opens
 * (`HOVER_DELAY_MS`, `command-tooltip.tsx`: 300 ms).
 */
const REST = 1_000;

/** The cell of the grid whose menu the journeys open, and that menu. */
function cellAndMenu(page: Page): { cell: Locator; menu: Locator } {
  const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  return {
    cell: rowAt(grid, 10).getByRole("gridcell").nth(1),
    menu: page.getByRole("menu", { name: "Menu de la cellule" }),
  };
}

/**
 * Open the menu of a cell from the keyboard, the cell focused by a click and the pointer then left
 * on the heading of the screen, away from where the menu opens: a pointer left on the cell rests on
 * the menu, on an item the size of the window decides.
 */
async function openFromKeyboard(page: Page, cell: Locator, menu: Locator): Promise<void> {
  await cell.click();
  await page.getByRole("heading", { level: 1 }).hover();
  await expect(cell).toBeFocused();
  await page.keyboard.press("Shift+F10");
  await expect(menu).toBeVisible();
}

/**
 * Close by Escape the menu of a cell opened from the keyboard, the focus back on the cell. The menu
 * gives its first item the focus, whose tooltip opens once the focus has rested on it 300 ms
 * (`command-tooltip.tsx`), and Escape closes the tooltip first, as WCAG 1.4.13 wants, then the
 * menu. A single Escape closed the menu only if it came before the tooltip: under load, the rest
 * was over by then, and it closed the tooltip alone (#1541). So the tooltip is awaited open, and
 * each Escape is seen closing what it closes, whatever the time between.
 */
async function escapeMenu(page: Page, cell: Locator, menu: Locator): Promise<void> {
  await expect(menu.getByRole("menuitem", { name: "Insérer une ligne" })).toBeFocused();
  const tooltip = page.locator("[data-slot=tooltip-content]");
  await expect(tooltip).toContainText("Insérer une ligne");
  await page.keyboard.press("Escape");
  await expect(tooltip).toHaveCount(0);
  await expect(menu).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(cell).toBeFocused();
}

test("places Undo and Redo in the grid, its menu and its keys, unavailable and saying why, and leaves Ctrl+Z to the cell being entered", async ({
  page,
}) => {
  await openHydrated(page, REMAINING);
  const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  const reason = "Indisponibles tant que le serveur ne conserve pas l’historique des saisies.";
  for (const name of ["Annuler", "Rétablir"]) {
    const button = page.getByRole("button", { name, exact: true });
    await expect(button).toHaveAttribute("aria-disabled", "true");
    await expect(button).toHaveAccessibleDescription(reason);
  }

  // The menu of a cell, by a right click and from the keyboard, the focus back on the cell.
  const { cell, menu } = cellAndMenu(page);
  await cell.click({ button: "right" });
  await expect(menu.getByRole("menuitem", { name: /^Annuler/ })).toContainText("Ctrl+Z");
  await expect(menu.getByRole("menuitem", { name: /^Rétablir/ })).toContainText("Ctrl+Maj+Z");
  await expect(menu.getByRole("menuitem", { name: /^Annuler/ })).toHaveAccessibleDescription(
    reason,
  );
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await openFromKeyboard(page, cell, menu);
  await escapeMenu(page, cell, menu);

  // On the grid, the shortcut tells the command unavailable.
  await page.keyboard.press("Control+z");
  await expect(page.getByRole("status").filter({ hasText: TOLD_UNDO })).toHaveCount(1);

  // In the editor of the effort re-estimated, Ctrl+Z is the browser's: it undoes what was typed.
  const header = grid.getByRole("columnheader", { name: "Charge (h)", exact: true });
  const position = await header.evaluate((th) =>
    th instanceof HTMLTableCellElement ? th.cellIndex : -1,
  );
  const hours = rowAt(grid, 10).getByRole("gridcell").nth(position);
  await hours.click();
  await page.keyboard.press("F2");
  const field = page.getByRole("textbox", { name: "Charge (h)" });
  await expect(field).toBeFocused();
  const effort = await field.inputValue();
  await page.keyboard.insertText("9");
  await expect(field).toHaveValue(`${effort}9`);
  await page.keyboard.press("Control+z");
  await expect(field).toHaveValue(effort);
  await expect(field).toBeFocused();
});

test("closes the menu of a cell opened from the keyboard by Escape, its tooltip first, however long the focus has rested on its first item since it opened (#1541)", async ({
  page,
}) => {
  // The clock of the page, driven: the rest that the load let pass between the menu shown and
  // Escape is given at once, whatever the load.
  await page.clock.install();
  await openHydrated(page, REMAINING);
  const { cell, menu } = cellAndMenu(page);
  await openFromKeyboard(page, cell, menu);
  await page.clock.runFor(REST);
  await escapeMenu(page, cell, menu);
});

// The history is the server's: the fake back keeps nothing of what is written, and answers an undo
// by none of the examples of the contract.
const SERVICE_ONLY = "the history of the entries is the service's, not the fake back's";

// How many entries the journey undoes and redoes (WF-IHM-0110-A, « cinquante modifications »).
const ENTRIES = 50;

test("fifty entries of the planning are undone one by one by the grid, then redone in order @shared [WF-IHM-0110-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  // A task created and fifty entries of its label, each undone and redone: a screen of grid under
  // load takes its `WORKING` bound for each.
  test.setTimeout(20 * 60_000);
  const own = await createOwnProject(page, "Annulation");
  await openRevision(page, own);
  const revision = new URL(page.url()).searchParams.get("revision_id");
  expect(revision, "the revision opened").not.toBeNull();
  await openHydrated(page, `${own.path}/revisions/${revision ?? ""}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });

  /** The grid is idle: the command that follows is not held by a write under way. */
  const idle = () => expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });

  // The first task is created from the empty grid.
  await page.getByRole("button", { name: "Insérer une tâche" }).click();
  const dialog = page.getByRole("dialog", { name: "Insérer une tâche" });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Tâche 0");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText("« Tâche 0 » créée.")).toBeVisible({ timeout: WORKING });
  await idle();

  const at = await columnsOf(grid, { label: "Libellé" });
  const label = rowAt(grid, 1).getByRole("gridcell").nth(at.label);
  await expect(label).toContainText("Tâche 0", { timeout: WORKING });

  // Fifty entries of the label, each a cell entered and validated.
  for (let entry = 1; entry <= ENTRIES; entry += 1) {
    await label.click();
    await page.keyboard.press("F2");
    const field = page.getByRole("textbox", { name: "Libellé" });
    await expect(field).toBeFocused();
    await field.fill(`Tâche ${entry.toString()}`);
    await page.keyboard.press("Enter");
    await expect(label).toContainText(`Tâche ${entry.toString()}`, { timeout: WORKING });
    await idle();
  }

  // Undone one by one, by the bar of the grid: each returns the label to the one before.
  const undo = page.getByRole("button", { name: "Annuler", exact: true });
  const redo = page.getByRole("button", { name: "Rétablir", exact: true });
  for (let entry = ENTRIES - 1; entry >= 0; entry -= 1) {
    await undo.click();
    await expect(label).toContainText(`Tâche ${entry.toString()}`, { timeout: WORKING });
    await idle();
  }
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  // Redone in order, up to the last.
  for (let entry = 1; entry <= ENTRIES; entry += 1) {
    await redo.click();
    await expect(label).toContainText(`Tâche ${entry.toString()}`, { timeout: WORKING });
    await idle();
  }
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  // Nothing is left to redo: the refusal is told by the catalogue, naming the condition.
  await redo.click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "historique de rétablissement non vide",
    {
      timeout: WORKING,
    },
  );
  await expect(label).toContainText(`Tâche ${ENTRIES.toString()}`);
});

test("fifty entries of a line of the estimate are undone one by one by the grid, then redone in order @shared [WF-IHM-0110-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  // A line seeded and fifty entries of its label, each undone and redone: a screen of grid under
  // load takes its `WORKING` bound for each.
  test.setTimeout(20 * 60_000);
  const seeded = await seedEstimate(page, browser, request, manager, "Annulation du devis");
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, { label: "Libellé" });
  const label = rowAt(grid, 3).getByRole("gridcell").nth(at.label);
  await expect(label).toContainText("Tâche du devis", { timeout: WORKING });

  // Fifty entries of the label of the line, each a cell entered and validated.
  for (let entry = 1; entry <= ENTRIES; entry += 1) {
    await label.click();
    await page.keyboard.press("F2");
    const field = page.getByRole("textbox", { name: "Libellé" });
    await expect(field).toBeFocused();
    await field.fill(`Ligne ${entry.toString()}`);
    await page.keyboard.press("Enter");
    await expect(label).toContainText(`Ligne ${entry.toString()}`, { timeout: WORKING });
    await idle(grid);
  }

  // Undone one by one, by the bar of the grid: each returns the label to the one before.
  const undo = page.getByRole("button", { name: "Annuler", exact: true });
  const redo = page.getByRole("button", { name: "Rétablir", exact: true });
  for (let entry = ENTRIES - 1; entry >= 1; entry -= 1) {
    await undo.click();
    await expect(label).toContainText(`Ligne ${entry.toString()}`, { timeout: WORKING });
    await idle(grid);
  }
  await undo.click();
  await expect(label).toContainText("Tâche du devis", { timeout: WORKING });
  await idle(grid);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  // Redone in order, up to the last.
  for (let entry = 1; entry <= ENTRIES; entry += 1) {
    await redo.click();
    await expect(label).toContainText(`Ligne ${entry.toString()}`, { timeout: WORKING });
    await idle(grid);
  }
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("a task deleted from the estimate grid comes back with its line once the deletion is undone @shared [WF-IHM-0110-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedEstimate(page, browser, request, manager, "Suppression du devis");
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, { label: "Libellé" });
  const task = rowAt(grid, 2).getByRole("gridcell").nth(at.label);
  await expect(task).toContainText("Tâche du devis", { timeout: WORKING });
  await expect(grid.getByRole("gridcell", { name: /^Total — 2 tâches, 1 ligne$/ })).toBeVisible();

  // The task goes with its line, once confirmed.
  await task.click();
  await page.keyboard.press("Control+Delete");
  const confirm = page.getByRole("dialog", { name: "Supprimer « Tâche du devis » ?" });
  await expect(confirm).toContainText("leurs lignes et leurs liaisons");
  await confirm.getByRole("button", { name: "Supprimer" }).click();
  await expect(grid.getByRole("gridcell", { name: /^Total — 1 tâche, 0 ligne$/ })).toBeVisible({
    timeout: WORKING,
  });
  await idle(grid);

  // Undone, the task and its line are back, as the totals say.
  await page.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(grid.getByRole("gridcell", { name: /^Total — 2 tâches, 1 ligne$/ })).toBeVisible({
    timeout: WORKING,
  });
  await expect(rowAt(grid, 2)).toContainText("Tâche du devis");
  await expect(rowAt(grid, 3)).toContainText("Tâche du devis");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});
