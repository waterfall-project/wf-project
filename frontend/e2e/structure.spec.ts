// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";

// The gestures that create and delete tasks and lines (US-0460), against the fake back. It serves
// the first example of each read whatever the request: the witness project is in progress, so its
// main structure lists the planning and the remaining to commit available and the estimate not
// (`structures`, WF-DEV-0050, WF-RAE-0040); and the first example of `createNode` and `deleteNode`
// whatever was sent, which keeps nothing — what the grid sends is proven by
// `structure-gestures.dom.test.tsx`, the answer it takes here, said in the status of the screen.
// The journeys read the structure by marks the generator writes (`test_the_marks_the_journeys_read`):
// row 8, the summary « Poste de commande »; row 9 under it, the task « Câblage des armoires ».
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

/** The cell of the label of the row of a task, found by the name the row reads. */
async function labelOf(grid: Locator, name: RegExp): Promise<Locator> {
  const at = await columnsOf(grid, { label: "Libellé" });
  return grid.getByRole("row", { name }).getByRole("gridcell").nth(at.label);
}

/**
 * Wait for what a gesture says it did, then for the reading anew its answer asked: the grid says it
 * is busy until then, and holds the next gesture.
 */
async function saidAndRead(page: Page, table: Locator, said: string) {
  await expect(page.getByText(said)).toBeVisible({ timeout: WORKING });
  await expect(table).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
}

/** Open a grid of a screen hydrated, and give the cell of the label of a row its focus. */
async function focusRow(page: Page, screen: string, grid: string, name: RegExp) {
  await openHydrated(page, `${IN_REVISION}/${screen}`);
  const table = page.getByRole("treegrid", { name: grid });
  const cell = await labelOf(table, name);
  await cell.click();
  await expect(cell).toBeFocused();
  return { table, cell };
}

test("inserts a task below, then a sub-task, in the planning, from the menu of a cell and from the keys, the creation said and the grid read anew", async ({
  page,
}) => {
  test.slow();
  const { table, cell } = await focusRow(
    page,
    "planning",
    "Grille de planning",
    /^9 .*Câblage des armoires/,
  );

  // From the menu of the cell: the dialog names the task, which is created below.
  await cell.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer au-dessous" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Note de calcul des protections");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, table, "« Note de calcul des protections » créée.");
  await expect(dialog).toHaveCount(0);
  // The focus goes back to the cell the menu opened on.
  await expect(cell).toBeFocused();

  // From the keys, on the cell, once the grid is read anew: Alt+Insert asks the sub-task; a label
  // left blank creates nothing.
  await page.keyboard.press("Alt+Insert");
  const child = page.getByRole("dialog", { name: "Insérer une sous-tâche" });
  await child.getByRole("button", { name: "Créer" }).click();
  await expect(child.getByRole("textbox", { name: "Libellé" })).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  await child.getByRole("textbox", { name: "Libellé" }).fill("Relevé des réglages existants");
  await page.keyboard.press("Enter");
  await expect(page.getByText("« Relevé des réglages existants » créée.")).toBeVisible({
    timeout: WORKING,
  });

  // The planning has no line to insert.
  await cell.click({ button: "right" });
  const menu = page.getByRole("menu", { name: "Menu de la cellule" });
  await expect(menu.getByRole("menuitem", { name: "Insérer une sous-tâche" })).toBeVisible();
  await expect(menu.getByRole("menuitem", { name: "Insérer une ligne" })).toHaveCount(0);
});

test("confirms the deletion of a summary of the planning before it is sent, and deletes a task at once, from the menu of a cell and from the keys", async ({
  page,
}) => {
  test.slow();
  const { table, cell } = await focusRow(
    page,
    "planning",
    "Grille de planning",
    /^8 .*Poste de commande/,
  );

  // The summary carries its subordinates away: Ctrl+Delete asks first, and abandoned changes nothing.
  await page.keyboard.press("Control+Delete");
  const confirm = page.getByRole("dialog", { name: "Supprimer « Poste de commande » ?" });
  await expect(confirm).toContainText("leurs lignes et leurs liaisons");
  await confirm.getByRole("button", { name: "Annuler" }).click();
  await expect(confirm).toHaveCount(0);
  await expect(page.getByText("« Poste de commande » supprimée.")).toHaveCount(0);
  await cell.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Supprimer" })
    .click();
  await page
    .getByRole("dialog", { name: "Supprimer « Poste de commande » ?" })
    .getByRole("button", { name: "Supprimer" })
    .click();
  await saidAndRead(page, table, "« Poste de commande » supprimée.");

  // A task without subordinates is deleted at once, from the menu of its cell, once the grid is
  // read anew.
  const leaf = await labelOf(table, /^9 .*Câblage des armoires/);
  await leaf.click({ button: "right" });
  const menu = page.getByRole("menu", { name: "Menu de la cellule" });
  await expect(menu.getByRole("menuitem").filter({ hasText: /Insérer|Supprimer/ })).toHaveText([
    "Insérer au-dessous",
    "Insérer une sous-tâche",
    "Supprimer",
  ]);
  await menu.getByRole("menuitem", { name: "Supprimer" }).click();
  await expect(page.getByText("« Câblage des armoires » supprimée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(cell).toBeVisible();
});

test("gives the focus to a cell of the grid once a task is deleted by the keys", async ({
  page,
}) => {
  test.slow();
  const { table, cell } = await focusRow(
    page,
    "planning",
    "Grille de planning",
    /^9 .*Câblage des armoires/,
  );
  await page.keyboard.press("Control+Delete");
  await expect(page.getByText("« Câblage des armoires » supprimée.")).toBeVisible({
    timeout: WORKING,
  });
  // The fake back keeps the structure whole: the grid read anew is the same, and the focus is on
  // the cell of the label at the place of the row deleted — the row that takes it with a real back
  // —, never on the page.
  const place = await cell.getAttribute("data-row");
  expect(place).not.toBeNull();
  await expect(table.locator(`td[data-row="${place ?? ""}"][data-column="label"]`)).toBeFocused();
  await expect(cell).toBeVisible();
});

test("indents a summary under the task above it and outdents a task from the keys and from the menu, each said [WF-PLA-0080-A]", async ({
  page,
}) => {
  test.slow();
  // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : the
  // summary « Risque survenu » follows the task « Câblage des armoires » among the subordinates of
  // « Poste de commande »; the fake back serves the first example of `moveNodes` whatever was
  // sent, and what the gesture sends is proven by `structure-move.dom.test.tsx`.
  const { table, cell } = await focusRow(
    page,
    "planning",
    "Grille de planning",
    /^13 .*Risque survenu — Retard de livraison/,
  );
  await page.keyboard.press("Alt+Shift+ArrowRight");
  await saidAndRead(page, table, "« Risque survenu — Retard de livraison des armoires » indentée.");
  await expect(cell).toBeFocused();

  // From the menu of the cell of a task under it, once the grid is read anew: outdented.
  const task = await labelOf(table, /^16 .*Transport exceptionnel/);
  await task.click({ button: "right" });
  const menu = page.getByRole("menu", { name: "Menu de la cellule" });
  await expect(menu.getByRole("menuitem", { name: "Indenter", exact: true })).toHaveAttribute(
    "aria-keyshortcuts",
    "Alt+Shift+ArrowRight",
  );
  await menu.getByRole("menuitem", { name: "Désindenter" }).click();
  await expect(page.getByText("« Transport exceptionnel » désindentée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(task).toBeFocused();
});

test("selects tasks of the planning by their handles, indents the group from the keys and drags it under a task, each said [WF-PLA-0080-A]", async ({
  page,
}) => {
  test.slow();
  // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : rows 4
  // and 5, « Pupitres opérateurs » and « Revue de conception », follow « Études de détail » among
  // the sub-tasks of « Études »; the fake back serves the first example of `moveNodes` whatever was
  // sent, and what the gestures send is proven by `row-selection.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const table = page.getByRole("treegrid", { name: "Grille de planning" });
  const handle = (number: number) =>
    table.getByRole("gridcell", { name: `${String(number)} — poignée de la ligne`, exact: true });
  await handle(4).click();
  await handle(5).click({ modifiers: ["Shift"] });
  await expect(table.getByRole("row", { selected: true })).toHaveCount(2);
  await expect(page.getByText("2 lignes sélectionnées")).toBeAttached();

  // From the keys, on the handle that has the focus: the group indented.
  await expect(handle(5)).toBeFocused();
  await page.keyboard.press("Alt+Shift+ArrowRight");
  await saidAndRead(page, table, "« Pupitres opérateurs » et la ligne suivante indentées.");

  // By the handle, once the grid is read anew, dragged onto the middle of the row of « Études de
  // détail »: under it.
  const target = await labelOf(table, /^2 .*Études de détail/);
  await handle(4).dragTo(target, { targetPosition: { x: 20, y: 14 } });
  await saidAndRead(page, table, "« Pupitres opérateurs » et la ligne suivante déplacées.");
  await expect(table.getByRole("row", { selected: true })).toHaveCount(2);
  // Read anew, the row dropped stands at the level the reading gives it — the fake back reads the
  // same rows —, and the active cell, with the focus, is on the handle of the first of the rows
  // dropped.
  await expect(table.getByRole("row", { name: /^4 .*Pupitres opérateurs/ })).toHaveAttribute(
    "aria-level",
    "2",
  );
  await expect(handle(4)).toHaveAttribute("tabindex", "0");
  await expect(handle(4)).toBeFocused();
});

test("adds a task from the remaining to commit of a project in progress, below a row, the creation said and the grid read anew [WF-RAE-0040-A]", async ({
  page,
}) => {
  test.slow();
  // Une tâche ajoutée depuis la grille de reste à engager : the structure lists `edit_remaining`
  // available, and the gesture is the planning's; that it appears in the planning, the reference
  // unchanged, is the service's (EP-09).
  const { cell } = await focusRow(
    page,
    "remaining",
    "Grille de reste à engager",
    /^9 .*Câblage des armoires/,
  );
  await page.keyboard.press("Insert");
  const dialog = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Reprise des borniers");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText("« Reprise des borniers » créée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(dialog).toHaveCount(0);
  await expect(cell).toBeFocused();
});

test("proposes no entry and no command of writing in the estimate of the main structure of a project in progress [WF-DEV-0050-A]", async ({
  page,
}) => {
  test.slow();
  // Sur un projet En cours, la grille de devis de la structure principale ne propose aucune saisie
  // : the structure lists the estimate unavailable (`project_before_in_progress`), and the grid is
  // read only whatever the planning lists.
  const { table, cell } = await focusRow(
    page,
    "estimate",
    "Grille de devis",
    /^9 .*Câblage des armoires/,
  );
  await expect(cell).toHaveAttribute("aria-readonly", "true");
  await expect(table.locator('td[data-column]:not([aria-readonly="true"])')).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Annuler", exact: true })).toHaveCount(0);
  // No command of writing either: neither the keys nor the menu of the cell offer Insert or Delete.
  await page.keyboard.press("Insert");
  await page.keyboard.press("Control+Delete");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await cell.click({ button: "right" });
  await expect(page.getByRole("menuitem", { name: /Insérer|Supprimer/ })).toHaveCount(0);
});

test("inserts a line in the remaining to commit of a project in progress, named, of a category and of a quantity", async ({
  page,
}) => {
  test.slow();
  // Sur un projet En cours, la grille de reste à engager propose la création d'une ligne et d'une
  // tâche : the structure lists `edit_remaining` available. The categories come from the reference.
  const { cell } = await focusRow(
    page,
    "remaining",
    "Grille de reste à engager",
    /^9 .*Câblage des armoires/,
  );
  await cell.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer une ligne" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Insérer une ligne" });
  await expect(
    dialog.getByRole("combobox", { name: "Catégorie" }).getByRole("option"),
  ).not.toHaveCount(0);
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Consommables d’essais");
  await dialog.getByRole("textbox", { name: "Quantité" }).fill("2,5");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText("« Consommables d’essais » créée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(cell).toBeFocused();
});

test("filters the remaining to commit by the post « Poste 1.1 » chosen among the work breakdown, the filter shown active in the banner and lifted from it", async ({
  page,
}) => {
  test.slow();
  // Le lot ou le poste porté par une tâche rattachée : as the planning and the estimate. The fake
  // back serves the structure whole whatever the filter asks; what the page sends is proven by
  // `remaining/page.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/remaining`);
  const filter = page.getByRole("combobox", { name: "Lot ou poste" });
  await expect(filter.getByRole("option")).toHaveText([
    "Tous les lots et postes",
    "Lot : Lot 1",
    "Poste : Poste 1.1",
  ]);
  await filter.selectOption({ label: "Poste : Poste 1.1" });
  await expect(page).toHaveURL(
    `${IN_REVISION}/remaining?order_item_id=01926f3a-7c00-7000-8000-000000000712`,
    { timeout: WORKING },
  );
  const chips = page
    .getByRole("region", { name: "Contexte de lecture" })
    .getByRole("list", { name: "Filtres actifs" })
    .getByRole("listitem");
  await expect(chips).toHaveText(["Poste : Poste 1.1, sur la grille seulement"]);
  await chips.getByRole("link", { name: /^Lever le filtre/ }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/remaining`, { timeout: WORKING });
  await expect(filter).toHaveValue("");
});
