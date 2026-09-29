// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

// The fake back serves the first example of `listNodes`, the structure of the volumes of §4.6.2
// (EP-02/L2). The journeys read it by marks the generator writes, which
// `test_the_marks_the_journeys_read` (tools/tests/test_mockstructure.py) holds: row 1, the phase
// « Études », a summary whose subordinates are the lots of rows 2, 201 and 401; row 4, a line of
// labour, « Heures d'ingénierie ». What a computed value depends on, the refusal asks the server
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
  await page.goto(`${REVISION_PATH}/estimate`);
  const grid = page.getByRole("grid", { name: "Grille de devis" });
  const labour = grid.getByRole("row", { name: /^4 .*Heures d'ingénierie/ });
  await expect(labour.getByRole("img", { name: "Ligne de main-d’œuvre" })).toBeVisible();
  // Number, label, quantity, hours, unit disbursement, budgeted, re-estimated.
  const hours = cellOf(labour, 3);
  const amount = cellOf(labour, 5);

  // The effort is entered: its figure alone. The amount is computed: marked Σ, named so, on
  // another background — the mark reads without the colour.
  await expect(hours).toHaveText(/^\d+$/);
  await expect(hours.getByRole("button")).toHaveCount(0);
  await expect(hours.getByRole("img")).toHaveCount(0);
  const computed = amount.getByRole("button", { name: /^Calculé [\d\s]+,\d\d$/ });
  await expect(computed.getByRole("img", { name: "Calculé" })).toBeVisible();
  expect(await background(amount)).not.toBe(await background(hours));

  // A try on the amount is refused beside it, naming what the server says it depends on — here
  // what the fake back answers for any value —: nothing opens to type.
  await computed.click();
  await expect(refusal(page)).toBeInViewport();
  await expect(refusal(page)).toContainText("Budgété ne se saisit pas");
  await expect(refusal(page).getByRole("list", { name: /^Elle dépend de\s:$/ })).toBeVisible();
  await expect(refusal(page).getByRole("status")).toHaveCount(0);
  await expect(amount.getByRole("textbox")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(refusal(page)).toHaveCount(0);
  await expect(amount.getByRole("button")).toBeFocused();
});

test("refuses to change the finish date of a summary task, from the keyboard, naming its subordinates [WF-IHM-0030-A]", async ({
  page,
}) => {
  await page.goto(`${REVISION_PATH}/planning`);
  const grid = page.getByRole("grid", { name: "Grille de planning" });
  const summary = grid.getByRole("row", { name: /^1 .*Études/ });
  await expect(summary.getByRole("img", { name: "Tâche récapitulative" })).toBeVisible();
  // Number, label, mode, duration, start, finish.
  const finish = cellOf(summary, 5).getByRole("button", { name: /^Calculé \d\d\/\d\d\/\d{4}$/ });

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
    /^2\s*Études — Poste de commande$/,
    /^201\s*Études — Ligne d'essais$/,
    /^401\s*Études — Utilités$/,
  ]);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(cellOf(summary, 5).getByRole("button")).toBeFocused();
});
