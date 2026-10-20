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
  const { cell } = await focusRow(
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
  await expect(page.getByText("« Note de calcul des protections » créée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(dialog).toHaveCount(0);
  // The focus goes back to the cell the menu opened on.
  await expect(cell).toBeFocused();

  // From the keys, on the cell: Alt+Insert asks the sub-task; a label left blank creates nothing.
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
  await expect(page.getByText("« Poste de commande » supprimée.")).toBeVisible({
    timeout: WORKING,
  });

  // A task without subordinates is deleted at once, from the menu of its cell.
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
