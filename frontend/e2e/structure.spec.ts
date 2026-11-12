// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { closeMenu, menuButton, openMenu, pick } from "./check-menu";
import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { createOwnProject, openRevision } from "./own-project";
import { SEEDED, seedPlanning } from "./planning-seed";

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
  // Each with its keys, shown off a Mac (US-0580).
  await expect(menu.getByRole("menuitem").filter({ hasText: /Insérer|Supprimer/ })).toHaveText([
    "Insérer au-dessousInser",
    "Insérer une sous-tâcheAlt+Inser",
    "SupprimerCtrl+Suppr",
  ]);
  // Its tooltip opens once the pointer rests on the item, and stays open while the pointer passes
  // over it, though the modal menu takes the pointer from the rest of the page (US-0580, WCAG 1.4.13).
  const remove = menu.getByRole("menuitem", { name: "Supprimer" });
  await remove.hover();
  const tooltip = page.locator("[data-slot=tooltip-content]");
  await expect(tooltip).toContainText(
    "Supprime la ligne ; une récapitulative emporte ses subordonnées, après confirmation.",
  );
  await tooltip.hover();
  await expect(tooltip).toHaveCSS("pointer-events", "auto");
  await expect(tooltip).toBeVisible();
  await expect(menu).toBeVisible();
  await remove.click();
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
  // summary « Poste de commande » follows the summary « Études » among the subordinates of the
  // project — « Retard de livraison des armoires », which stands after the factory acceptance, a
  // milestone, has no task to go under; the fake back serves the first example of `moveNodes`
  // whatever was sent, and what the gesture sends is proven by `structure-move.dom.test.tsx`.
  const { table, cell } = await focusRow(
    page,
    "planning",
    "Grille de planning",
    /^8 .*Poste de commande/,
  );
  await page.keyboard.press("Alt+Shift+ArrowRight");
  await saidAndRead(page, table, "« Poste de commande » indentée.");
  await expect(cell).toBeFocused();

  // From the menu of the cell of a task under it, once the grid is read anew: outdented.
  const task = await labelOf(table, /^17 .*Transport exceptionnel/);
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
  // unchanged, is the service's (EP-09, served); this path has no twin against it yet (#2909).
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

test("proposes no entry and no command of writing in the estimate of the main structure of a project in progress @shared [WF-DEV-0050-A]", async ({
  page,
}) => {
  test.slow();
  // Sur un projet En cours, la grille de devis de la structure principale ne propose aucune saisie
  // : the structure lists the estimate unavailable (`project_before_in_progress`), and the grid is
  // read only whatever the planning lists. The witness of the service is In progress too (PRJ-001,
  // US-1570): the path is played against it as against the fake back.
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
  // Not played against the service: it writes the remaining of PRJ-001, whose project manager the
  // account of the run is not (#2193); `remaining.spec.ts` plays the writes on a project the run
  // creates.
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
  // The entry is chosen in the one list of the roles and of the categories of expense.
  const entry = dialog.getByRole("combobox", { name: "Rôle ou catégorie" });
  await expect(entry.getByRole("option")).not.toHaveCount(0);
  await entry.selectOption({ index: 0 });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Consommables d’essais");
  await dialog.getByRole("textbox", { name: "Quantité" }).fill("2,5");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText("« Consommables d’essais » créée.")).toBeVisible({
    timeout: WORKING,
  });
  await expect(cell).toBeFocused();
});

test("filters the remaining to commit by the post « Poste 1.1 » chosen among the work breakdown, the filter shown active in the banner and lifted from it @shared", async ({
  page,
}) => {
  test.slow();
  // Le lot ou le poste porté par une tâche rattachée : as the planning and the estimate. The fake
  // back serves the structure whole whatever the filter asks; what the page sends is proven by
  // `remaining/page.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/remaining`);
  const filter = menuButton(page, "Lot ou poste");
  await expect((await openMenu(page, "Lot ou poste")).getByRole("radio")).toHaveText([
    "Tous les lots et postes",
    "Lot : Lot 1",
    "Poste : Poste 1.1",
  ]);
  await closeMenu(page);
  await pick(page, "Lot ou poste", "Poste\u00a0: Poste 1.1", "radio");
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
  await expect(filter).toContainText("Tous les lots et postes");
});

// The planning written against the service on a planning the run seeds (`planning-seed.ts`): the
// service keeps what the gestures write, so the grid read anew is the structure they made.
const SERVICE_ONLY = "the service keeps what is written, which the fake back does not";

test("inserts, indents a group, outdents and moves tasks against the service, each said and kept in the grid read anew @shared [WF-PLA-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Structure");
  await openHydrated(page, seeded.planning);
  const table = page.getByRole("treegrid", { name: "Grille de planning" });
  const handle = (number: number) =>
    table.getByRole("gridcell", { name: `${String(number)} — poignée de la ligne`, exact: true });
  const named = (number: number, label: string) =>
    table.getByRole("row", { name: new RegExp(`^${String(number)} .*${label}`) });

  // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : rows 3
  // and 4 follow « Études de détail », which becomes their summary.
  await handle(3).click();
  await handle(4).click({ modifiers: ["Shift"] });
  await expect(table.getByRole("row", { selected: true })).toHaveCount(2);
  await page.keyboard.press("Alt+Shift+ArrowRight");
  await saidAndRead(page, table, "« Revue de conception » et la ligne suivante indentées.");
  await expect(named(2, SEEDED[2])).toHaveAttribute("aria-expanded", "true");
  await expect(named(3, SEEDED[3])).toHaveAttribute("aria-level", "3");
  await expect(named(4, SEEDED[4])).toHaveAttribute("aria-level", "3");

  // A task inserted below one, from the menu of its cell: created, and read anew at its place.
  const at = await columnsOf(table, { label: "Libellé" });
  const cell = named(5, SEEDED[5]).getByRole("gridcell").nth(at.label);
  await cell.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer au-dessous" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Note de calcul");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, table, "« Note de calcul » créée.");
  await expect(named(6, "Note de calcul")).toBeVisible();
  await expect(named(7, SEEDED[6])).toBeVisible();

  // Outdented from the menu: the task leaves its summary, and is a task of the first level.
  const task = named(3, SEEDED[3]).getByRole("gridcell").nth(at.label);
  await task.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Désindenter" })
    .click();
  await saidAndRead(page, table, "« Revue de conception » et la ligne suivante désindentées.");
  await expect(named(3, SEEDED[3])).toHaveAttribute("aria-level", "2");
});

test("deletes a task at once and a summary after its confirmation against the service, which keeps the rows gone @shared [WF-PLA-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Suppression");
  await openHydrated(page, seeded.planning);
  const table = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(table, { label: "Libellé" });
  const label = (number: number, name: string) =>
    table
      .getByRole("row", { name: new RegExp(`^${String(number)} .*${name}`) })
      .getByRole("gridcell")
      .nth(at.label);

  // A task without subordinates, by the keys: gone from the grid once it is read anew.
  await label(6, SEEDED[6]).click();
  await page.keyboard.press("Control+Delete");
  await saidAndRead(page, table, "« Mise en service » supprimée.");
  await expect(table.getByRole("row", { name: new RegExp(SEEDED[6]) })).toHaveCount(0);

  // The summary carries its subordinates away, after the confirmation.
  await label(1, SEEDED[1]).click();
  await page.keyboard.press("Control+Delete");
  const confirm = page.getByRole("dialog", { name: "Supprimer « Études » ?" });
  await expect(confirm).toContainText("leurs lignes et leurs liaisons");
  await confirm.getByRole("button", { name: "Supprimer" }).click();
  await saidAndRead(page, table, "« Études » supprimée.");
  await expect(table.getByRole("row", { name: new RegExp(SEEDED[2]) })).toHaveCount(0);
  await expect(table.getByRole("row", { name: new RegExp(SEEDED[5]) })).toBeVisible();
});

// The estimate grid is served (US-1560): the carry-over of #1057 is played from the grid itself, a
// task created in the estimate and a line under it, read in the planning, the structure being shared.
test("reads in the planning a task created in the estimate grid, automatic, of one day and without predecessor, and the task indented from the grid, the structure being shared @shared [WF-DEV-0050-A] [WF-PLA-0080-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Report");
  await openRevision(page, own);
  const opened = new URL(page.url()).searchParams.get("revision_id");
  expect(opened, "the revision opened").not.toBeNull();
  const revision = `${own.path}/revisions/${opened ?? ""}`;
  await openHydrated(page, `${revision}/estimate`);
  const estimate = page.getByRole("treegrid", { name: "Grille de devis" });

  // A task created from the empty grid, and a line under it, from the menu of its cell.
  await page.getByRole("button", { name: "Insérer une tâche" }).click();
  const creation = page.getByRole("dialog", { name: "Insérer une tâche" });
  await creation.getByRole("textbox", { name: "Libellé" }).fill("Tâche du devis");
  await creation.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, estimate, "« Tâche du devis » créée.");
  const at = await columnsOf(estimate, { label: "Libellé" });
  const task = estimate
    .getByRole("row", { name: /^1 .*Tâche du devis/ })
    .getByRole("gridcell")
    .nth(at.label);
  await task.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer une ligne" })
    .click();
  const line = page.getByRole("dialog", { name: "Insérer une ligne" });
  await line
    .getByRole("combobox", { name: "Rôle ou catégorie" })
    .selectOption({ label: "Matériel électrique" });
  await line.getByRole("textbox", { name: "Libellé" }).fill("Câbles");
  await line.getByRole("textbox", { name: "Quantité" }).fill("2");
  await line.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, estimate, "« Câbles » créée.");
  await expect(estimate.getByRole("row", { name: /^2 .*Câbles/ })).toBeVisible();

  // A second task, created below the line, indented under the first from the grid.
  await task.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer au-dessous" })
    .click();
  const below = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await below.getByRole("textbox", { name: "Libellé" }).fill("Sous-tâche du devis");
  await below.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, estimate, "« Sous-tâche du devis » créée.");

  // Read in the planning: the first task is there, automatic, of one day, with no predecessor, and
  // the second beside it.
  await openHydrated(page, `${revision}/planning`);
  const planning = page.getByRole("treegrid", { name: "Grille de planning" });
  const columns = await columnsOf(planning, {
    mode: "Mode de planification",
    duration: "Durée",
    predecessors: "Prédécesseurs",
  });
  const created = planning.getByRole("row", { name: /^1 .*Tâche du devis/ });
  await expect(created).toBeVisible({ timeout: WORKING });
  const cells = created.getByRole("gridcell");
  await expect(cells.nth(columns.mode)).toHaveText("Automatique");
  await expect(cells.nth(columns.duration)).toHaveText(/^1\s?j/);
  await expect(cells.nth(columns.predecessors)).toHaveText("");
  // The numbers are those of the estimate, where the line of the first task is the second row.
  const second = planning.getByRole("row", { name: /^3 .*Sous-tâche du devis/ });
  await expect(second).toHaveAttribute("aria-level", "1");

  // Indented under the first task from the estimate grid, the move is read in the planning.
  await openHydrated(page, `${revision}/estimate`);
  const indent = page.getByRole("treegrid", { name: "Grille de devis" });
  await indent.getByRole("gridcell", { name: "3 — poignée de la ligne", exact: true }).click();
  await page.keyboard.press("Alt+Shift+ArrowRight");
  await expect(page.getByText(/« Sous-tâche du devis » .*indentée/)).toBeVisible({
    timeout: WORKING,
  });
  await expect(indent).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  await openHydrated(page, `${revision}/planning`);
  await expect(
    page.getByRole("treegrid", { name: "Grille de planning" }).getByRole("row", {
      name: /^3 .*Sous-tâche du devis/,
    }),
  ).toHaveAttribute("aria-level", "2", { timeout: WORKING });
});

// WF-DEV-0020-A: a line of labour is created from a role, its category computed by the server, and a
// line of expense from a category of expense — the labour and provision categories are not offered.
test("creates from the estimate grid a line of labour by a role and a line of expense by a category, and reads them in the grid @shared [WF-DEV-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Lignes");
  await openRevision(page, own);
  const opened = new URL(page.url()).searchParams.get("revision_id");
  expect(opened, "the revision opened").not.toBeNull();
  await openHydrated(page, `${own.path}/revisions/${opened ?? ""}/estimate`);
  const estimate = page.getByRole("treegrid", { name: "Grille de devis" });

  await page.getByRole("button", { name: "Insérer une tâche" }).click();
  const creation = page.getByRole("dialog", { name: "Insérer une tâche" });
  await creation.getByRole("textbox", { name: "Libellé" }).fill("Tâche des lignes");
  await creation.getByRole("button", { name: "Créer" }).click();
  await saidAndRead(page, estimate, "« Tâche des lignes » créée.");
  const at = await columnsOf(estimate, { label: "Libellé" });
  const task = estimate
    .getByRole("row", { name: /^1 .*Tâche des lignes/ })
    .getByRole("gridcell")
    .nth(at.label);

  /** Open the dialog of a line under the task, name the line, and choose its entry in the list. */
  async function insert(
    label: string,
    group: string,
    entry: { index: number } | { label: string },
  ) {
    await task.click({ button: "right" });
    await page
      .getByRole("menu", { name: "Menu de la cellule" })
      .getByRole("menuitem", { name: "Insérer une ligne" })
      .click();
    const line = page.getByRole("dialog", { name: "Insérer une ligne" });
    const list = line.getByRole("combobox", { name: "Rôle ou catégorie" });
    // A closed list does not expose its groups to the accessibility tree: they are read by their tag.
    await expect(list.locator("optgroup")).toHaveCount(2);
    await expect(list.locator(`optgroup[label="${group}"] option`)).not.toHaveCount(0);
    await list.selectOption(entry);
    await line.getByRole("textbox", { name: "Libellé" }).fill(label);
    await line.getByRole("textbox", { name: "Quantité" }).fill("2");
    await line.getByRole("button", { name: "Créer" }).click();
    await saidAndRead(page, estimate, `« ${label} » créée.`);
  }

  // The first role of the list, a line of labour; a category of expense, a line of expense.
  await insert("Études de main-d’œuvre", "Rôles (main-d’œuvre)", { index: 0 });
  await insert("Fournitures de débours", "Catégories de débours", { label: "Matériel électrique" });

  const columns = await columnsOf(estimate, { role: "Rôle", category: "Catégorie" });
  const labour = estimate.getByRole("row", { name: /^\d+ .*Études de main-d’œuvre/ });
  const expense = estimate.getByRole("row", { name: /^\d+ .*Fournitures de débours/ });
  await expect(labour).toBeVisible({ timeout: WORKING });
  await expect(expense).toBeVisible({ timeout: WORKING });
  // The labour line bears the role chosen and the category the server computed; the expense line
  // bears its category and no role.
  await expect(labour.getByRole("gridcell").nth(columns.role)).not.toHaveText("");
  await expect(labour.getByRole("gridcell").nth(columns.category)).not.toHaveText("");
  await expect(expense.getByRole("gridcell").nth(columns.category)).toHaveText(
    "Matériel électrique",
  );
  await expect(expense.getByRole("gridcell").nth(columns.role)).toHaveText("");
});
