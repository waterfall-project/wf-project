// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { openHydrated, WORKING } from "./hydration";

// What each grid offers according to the command of the structure it reads (US-0460), against the
// fake back. It serves the first example of each read whatever the request: the witness project is
// in progress, so its main structure lists the planning and the remaining to commit available and
// the estimate not (`structures`, WF-DEV-0050, WF-RAE-0040). The journeys read the structure by
// marks the generator writes (`test_the_marks_the_journeys_read`): row 9, the task « Câblage des
// armoires ».
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

test("proposes no entry in the estimate of the main structure of a project in progress [WF-DEV-0050-A]", async ({
  page,
}) => {
  test.slow();
  // Sur un projet En cours, la grille de devis de la structure principale ne propose aucune saisie
  // : the structure lists the estimate unavailable (`project_before_in_progress`), and the grid is
  // read only whatever the planning lists. The gestures of writing are L3b's.
  const { table, cell } = await focusRow(
    page,
    "estimate",
    "Grille de devis",
    /^9 .*Câblage des armoires/,
  );
  await expect(cell).toHaveAttribute("aria-readonly", "true");
  await expect(table.locator('td[data-column]:not([aria-readonly="true"])')).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Annuler", exact: true })).toHaveCount(0);
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
