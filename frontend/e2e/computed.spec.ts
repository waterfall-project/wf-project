// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { columnsOf } from "./columns";
import { idle, PHASE, seedEstimate, TASK } from "./estimate-seed";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { SEEDED, seedPlanning } from "./planning-seed";

// The fake back serves the first example of `listNodes`, the structure of the witness at the sizes
// of §4.6.2, its core first (#376). The journeys read it by marks the generator writes, which
// `test_the_marks_the_journeys_read` (tools/tests/test_mockstructure.py) holds: row 1, the studies,
// « Études », a summary whose subordinates are the tasks of rows 2, 4, 5, 6 and 7; row 10, a line
// of labour, « Raccordement des borniers », 12,5 hours. What a computed value depends on, the refusal asks the server
// (`getComputedValueDependencies`), whose first example the fake back serves whatever the value
// tried: the finish date of row 1, its subordinates named from the same structure. What another
// value depends on is proven on its own example by the tests of the cell
// (`computed-cell.dom.test.tsx`).
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const REVISION_PATH = `/projects/${PROJECT}/revisions/${REVISION}`;

/** A cell of a row, by its position: the number, the label, then the columns. */
function cellOf(row: Locator, position: number): Locator {
  return row.getByRole("gridcell").nth(position);
}

/** The colour behind an element, as the browser paints it. */
function background(cell: Locator): Promise<string> {
  return cell.evaluate((element) => getComputedStyle(element).backgroundColor);
}

/** The refusal of an entry, beside the cell tried. */
function refusal(page: Page): Locator {
  return page.getByRole("dialog", { name: "Valeur calculée" });
}

test("shows the amount of a line of labour as computed, apart from its effort in hours, and refuses to enter it [WF-IHM-0030-A]", async ({
  page,
}) => {
  await openHydrated(page, `${REVISION_PATH}/estimate`);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const labour = grid.getByRole("row", { name: /^10 .*Raccordement des borniers/ });
  await expect(labour.getByRole("img", { name: "Ligne de main-d’œuvre" })).toBeVisible();
  // The effort and the amount, found by their heading (`columnsOf`).
  const at = await columnsOf(grid, { hours: "Charge (h)", reference: "Montant (année de réf.)" });
  const hours = cellOf(labour, at.hours);
  const amount = cellOf(labour, at.reference);

  // The effort is a figure alone — the estimate of a project in progress is read only
  // (WF-DEV-0050). The amount is computed: marked Σ, named so, on another background — the mark
  // reads without the colour.
  await expect(hours).toHaveText(/^\d+(,\d+)?$/);
  await expect(hours.getByRole("img")).toHaveCount(0);
  await expect(amount).toHaveAccessibleName(/^Calculé [\d\s]+,\d\d\s€$/);
  await expect(amount.getByRole("img", { name: "Calculé" })).toBeVisible();
  expect(await background(amount)).not.toBe(await background(hours));

  // A digit typed on the effort opens no field: the grid is read only here.
  await hours.focus();
  await page.keyboard.press("7");
  await expect(hours.getByRole("textbox")).toHaveCount(0);

  // The same digit on the amount opens no field: the try is refused beside it, naming what the
  // server says it depends on — the reading done, at least one rule said, whatever the fake back
  // answers for any value.
  for (let column = at.hours; column < at.reference; column += 1) {
    await page.keyboard.press("ArrowRight");
  }
  await expect(amount).toBeFocused();
  await page.keyboard.press("7");
  await expect(refusal(page)).toBeInViewport();
  await expect(refusal(page)).toContainText("Montant (année de réf.) ne se saisit pas");
  await expect(page.getByRole("textbox", { name: "Montant (année de réf.)" })).toHaveCount(0);
  const said = refusal(page).getByRole("status");
  await expect(said).toHaveAttribute("aria-busy", "false");
  await expect(said).not.toContainText("Lecture de ce dont elle dépend");
  // What the server said, and no refusal of it: a rule in a sentence after « ne se saisit pas ».
  await expect(said.getByRole("alert")).toHaveCount(0);
  await expect(said.getByRole("paragraph").first()).not.toBeEmpty();
  await page.keyboard.press("Escape");
  await expect(refusal(page)).toHaveCount(0);
  await expect(amount).toBeFocused();
  // The pointer tries it as well.
  await amount.click();
  await expect(refusal(page)).toContainText("Montant (année de réf.) ne se saisit pas");
  await expect(amount.getByRole("textbox")).toHaveCount(0);
});

test("refuses to change the finish date of a summary task, from the keyboard, naming its subordinates [WF-IHM-0030-A]", async ({
  page,
}) => {
  await openHydrated(page, `${REVISION_PATH}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const summary = grid.getByRole("row", { name: /^1 .*Études/ });
  await expect(summary.getByRole("img", { name: "Tâche récapitulative" })).toBeVisible();
  const at = await columnsOf(grid, { finish: "Fin" });
  const finish = cellOf(summary, at.finish);
  await expect(finish).toHaveAccessibleName(/^Calculé \d\d\/\d\d\/\d{4}$/);

  await finish.focus();
  await page.keyboard.press("Enter");
  const dialog = refusal(page);
  await expect(dialog).toBeInViewport();
  await expect(dialog).toContainText("Fin ne se saisit pas");
  await expect(dialog).toContainText(
    "Une tâche récapitulative tient ses dates, sa durée et son avancement de ses subordonnées.",
  );
  const subordinates = dialog
    .getByRole("list", { name: /^Elle dépend de\s:$/ })
    .getByRole("listitem");
  await expect(subordinates).toHaveText([
    /^2\s*Études de détail$/,
    /^4\s*Pupitres opérateurs$/,
    /^5\s*Revue de conception$/,
    /^6\s*Réception des études$/,
    /^7\s*Dossier de conception$/,
  ]);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(finish).toBeFocused();
});

test("refuses to change the finish date of a summary task against the service, which names its subordinates @shared [WF-IHM-0030-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(
    !inService,
    "the service answers getComputedValueDependencies from the structure it keeps",
  );
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Valeur calculée");
  await openHydrated(page, seeded.planning);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${SEEDED[1]}`) });
  await expect(summary.getByRole("img", { name: "Tâche récapitulative" })).toBeVisible({
    timeout: WORKING,
  });
  const at = await columnsOf(grid, { finish: "Fin" });
  const finish = cellOf(summary, at.finish);
  await expect(finish).toHaveAccessibleName(/^Calculé \d\d\/\d\d\/\d{4}$/);

  await finish.focus();
  await page.keyboard.press("Enter");
  const dialog = refusal(page);
  await expect(dialog).toBeInViewport();
  await expect(dialog).toContainText("Fin ne se saisit pas");
  const subordinates = dialog
    .getByRole("list", { name: /^Elle dépend de\s:$/ })
    .getByRole("listitem");
  await expect(subordinates).toHaveText([
    new RegExp(`^2\\s*${SEEDED[2]}$`),
    new RegExp(`^3\\s*${SEEDED[3]}$`),
    new RegExp(`^4\\s*${SEEDED[4]}$`),
  ]);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(finish).toBeFocused();
});

test("recalculates the amount of a summary task at each write of a line and refuses to enter it, naming its lines and subordinates, against the service; the grid proposes neither the duration nor the predecessors of a task @shared [WF-DEV-0050-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the service computes the amounts from the lines it keeps");
  test.slow();
  const seeded = await seedEstimate(page, browser, request, manager, "Montant récapitulatif");
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, { quantity: "Qté", reference: "Montant (année de réf.)" });
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${PHASE}`) });
  await expect(summary.getByRole("img", { name: "Tâche récapitulative" })).toBeVisible({
    timeout: WORKING,
  });
  const amount = cellOf(summary, at.reference);
  await expect(amount).toHaveText(/1\s000,00\s€/);

  // The quantity of the line entered: the amount of the summary follows, as the service recalculates it.
  const quantity = cellOf(grid.getByRole("row", { name: /^3 / }), at.quantity);
  await quantity.click();
  await page.keyboard.press("F2");
  await page.getByRole("textbox", { name: "Qté" }).fill("3");
  await page.keyboard.press("Enter");
  await expect(amount).toHaveText(/3\s000,00\s€/, { timeout: WORKING });
  await idle(grid);

  // The amount of the summary is not entered: the refusal names what the service says it depends on.
  await amount.click();
  await page.keyboard.press("7");
  await expect(refusal(page)).toContainText("Montant (année de réf.) ne se saisit pas");
  await expect(refusal(page)).toContainText(
    "Le montant d’une tâche est celui des lignes qu’elle porte et de ses subordonnées.",
  );
  await page.keyboard.press("Escape");
  await expect(refusal(page)).toHaveCount(0);

  // Neither the duration nor the predecessors of a task are entered in the estimate: they are the planning's.
  await expect(grid.getByRole("columnheader", { name: "Durée" })).toHaveCount(0);
  await expect(grid.getByRole("columnheader", { name: "Prédécesseurs" })).toHaveCount(0);
  await expect(grid.getByRole("row", { name: new RegExp(TASK) }).first()).toBeVisible();
});

test("shows a line whose task is dated two years after the year of reference, with an inflation of 2 %, 4,04 % above its amount at the rates of the year of reference, and no budgeted amount @shared [WF-DEV-0050-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the service computes the re-estimated amount from the planning it keeps");
  test.slow();
  const seeded = await seedEstimate(page, browser, request, manager, "Inflation", {
    inflation: "0.02",
    dated: true,
  });
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, {
    reference: "Montant (année de réf.)",
    reestimated: "Montant réestimé",
  });
  const line = grid.getByRole("row", { name: /^3 / });
  await expect(cellOf(line, at.reference)).toHaveText(/1\s000,00\s€/, { timeout: WORKING });
  // 1 000,00 x 1,02 x 1,02: 4,04 % above.
  await expect(cellOf(line, at.reestimated)).toHaveText(/1\s040,40\s€/);
  await expect(grid.getByRole("columnheader", { name: /Montant budgété/ })).toHaveCount(0);
});
