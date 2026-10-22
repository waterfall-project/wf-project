// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";

// The journey of an amendment (US-0510), against the fake back, which keeps nothing: it serves the
// first example of each operation whatever was sent. The amendment is prepared from the current
// revision (`create_structure`), whose answer — the example `amendment_created`, the structure 213 —
// leads the screen to the grid of the planning on it; the fake back lists the amendment 2 of the
// current revision at the structure 203 (`structures`), which the journeys that follow open at its
// address: a task added in its grid, then the amendment contractualised, its report read
// (`structure_merge_report`), the version name asked, the merge followed in « Tâches de fond » and
// the new reference told. What the front sends is proven by `amendment.dom.test.tsx`.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;
const AMENDMENT = "01926f3a-7c00-7000-8000-000000000203";
const CREATED = "01926f3a-7c00-7000-8000-000000000213";

/** Open the planning of the amendment 2, hydrated. */
async function openAmendment(page: Page): Promise<void> {
  await openHydrated(page, `${IN_REVISION}/planning?structure=${AMENDMENT}`);
}

test("prepares an amendment from the current revision: a label asked, the differential created and opened in the planning [WF-REV-0100-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Préparer un avenant" }).click();
  const form = commands.getByRole("form", { name: "Préparer un avenant" });
  await form.getByRole("textbox", { name: "Libellé de l’avenant" }).fill("Avenant 3");
  await form.getByRole("button", { name: "Créer l’avenant" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning?structure=${CREATED}`, {
    timeout: WORKING,
  });
});

test("adds a task in the grid of the amendment, said and read anew [WF-REV-0100-A]", async ({
  page,
}) => {
  test.slow();
  await openAmendment(page);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const task = grid.getByRole("row", { name: /Montage des armoires sur site/ });
  const cell = task.getByRole("gridcell").nth(2);
  await cell.click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Insérer au-dessous" })
    .click();
  const dialog = page.getByRole("dialog", { name: "Insérer au-dessous" });
  await dialog.getByRole("textbox", { name: "Libellé" }).fill("Essais de réception");
  await dialog.getByRole("button", { name: "Créer" }).click();
  await expect(page.getByText(/créée\./).first()).toBeVisible({ timeout: WORKING });
});

test("contractualises the amendment: the report read with its marks, the version name asked, the merge followed, the reference told [WF-REV-0050-A]", async ({
  page,
}) => {
  test.slow();
  await openAmendment(page);
  await page.getByRole("button", { name: "Contractualiser l’avenant" }).click();
  const form = page.getByRole("form", { name: "Contractualiser l’avenant" });
  const counts = form.getByRole("list", { name: "Écarts par objet" });
  await expect(counts).toBeVisible({ timeout: WORKING });
  await expect(counts).toContainText("2 ajoutées");
  await expect(form.getByRole("table", { name: /écarts/i })).toContainText("Essais sur site");

  // The version name is asked before the confirmation can be given.
  const confirm = form.getByRole("button", { name: "Confirmer la fusion" });
  await expect(confirm).toHaveAttribute("aria-disabled", "true");
  await form.getByRole("textbox", { name: "Nom de version" }).fill("Avenant 2");
  await confirm.click();
  await expect(form).toHaveCount(0);

  // The merge is followed in « Tâches de fond », then the new reference is told.
  await expect(page.getByText(/« Avenant 2 » est la nouvelle révision de référence/)).toBeVisible({
    timeout: WORKING,
  });
  await page.getByRole("button", { name: /^Tâches et messages/ }).click();
  const tasks = page.getByRole("dialog", { name: "Tâches et messages" });
  await expect(tasks.getByRole("region", { name: "Tâches de fond" })).toBeVisible();
});

test("abandons at the report: nothing is merged and the command stays offered [WF-REV-0050-A]", async ({
  page,
}) => {
  await openAmendment(page);
  await page.getByRole("button", { name: "Contractualiser l’avenant" }).click();
  const form = page.getByRole("form", { name: "Contractualiser l’avenant" });
  await expect(form.getByRole("list", { name: "Écarts par objet" })).toBeVisible({
    timeout: WORKING,
  });
  await form.getByRole("button", { name: "Annuler" }).click();
  await expect(form).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toBeFocused();
});
