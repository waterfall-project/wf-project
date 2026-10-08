// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each read of the risks — the register of three risks,
// one in each state, its matrix, the risk of rewiring and the history of its reviews —, whatever
// the risk asked: the component and page tests prove what the screen asks of each.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const RISKS = `/projects/${PROJECT}/revisions/${REVISION}/risks`;
const CABLING = "01926f3a-7c00-7000-8000-000000000751";

test("reads the risks of a revision: the register and its totals, the matrix, the detail of a risk, the sort and the filter asked of the server [WF-RIS-0040-A]", async ({
  page,
}) => {
  // The opening and the dense grid read anew by each click, each in the bound of a grid
  // (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  await openHydrated(page, RISKS);
  await expect(page).toHaveTitle(
    "Gestion des risques · Modernisation du poste de commande — Waterfall",
  );
  const grid = page.getByRole("grid", { name: "Registre des risques" });
  for (const name of [
    "Libellé",
    "Probabilité",
    "Calculé Gravité",
    "Calculé Provision",
    "État",
    "Dernier réexamen",
  ]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
  }
  // The grid holds in the window: its totals, the general total the server gives, are in view.
  const total = grid.getByRole("row").last();
  await expect(total).toHaveText(/^Total général\s*1\s160,00$/);
  expect(await withinBox(grid, total)).toBe(true);
  await expect(page.getByRole("region", { name: "Provisions des risques retenus" })).toHaveText(
    /^Risques identifiés\s*500,00\s*Risques survenus\s*60,00\s*Risques écartés\s*600,00\s*Total général\s*1\s160,00$/,
  );
  // The coverage of the risks, each amount as the server computes it, the variance signed.
  await expect(page.getByRole("region", { name: "Couverture des risques" })).toHaveText(
    /Réserve pour risques\s*910,00\s*Provisions restantes\s*500,00\s*Coût des risques survenus\s*200,00\s*Écart de couverture\s*210,00/,
  );

  // The matrix, each cell named by its signal, never by its colour alone.
  const matrix = page.getByRole("table", { name: "Matrice des risques" });
  await expect(matrix.getByRole("columnheader", { name: "10 % et plus" })).toBeVisible();
  await expect(matrix.getByRole("rowheader", { name: "60 % et plus" })).toBeVisible();
  await expect(matrix.getByRole("img", { name: "Alerte" })).toHaveCount(3);

  // The detail of a risk, from its label: its notes, its provision line, its reviews.
  await grid.getByRole("link", { name: "Risque de reprise du câblage" }).click();
  await expect(page).toHaveURL(`${RISKS}?risk=${CABLING}`, { timeout: WORKING });
  const detail = page.getByRole("region", { name: "Risque de reprise du câblage" });
  await expect(detail).toContainText("Contrôle du câblage en atelier avant expédition");
  await expect(detail).toContainText("Présente dans la structure principale");
  await expect(
    detail.getByRole("table", { name: "Historique des réexamens" }).getByRole("row"),
  ).toHaveCount(4);
  await detail.getByRole("link", { name: "Fermer le détail du risque" }).click();
  await expect(page).toHaveURL(RISKS, { timeout: WORKING });
  await expect(detail).toHaveCount(0);

  // The sort by provision, and the filter by state, asked of the server by the address.
  await grid.getByRole("columnheader", { name: "Calculé Provision" }).getByRole("button").click();
  await expect(page).toHaveURL(`${RISKS}?sort_by=provision_amount&sort_order=asc`, {
    timeout: WORKING,
  });
  await page
    .getByRole("group", { name: "Filtrer par état" })
    .getByRole("button", { name: "Survenu" })
    .click();
  await expect(page).toHaveURL(`${RISKS}?sort_by=provision_amount&sort_order=asc&states=occurred`, {
    timeout: WORKING,
  });
  await expect(
    page.getByRole("group", { name: "Filtrer par état" }).getByRole("button", { name: "Survenu" }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("leads from the label of a risk to its detail from the keyboard alone [WF-IHM-0100-A]", async ({
  page,
}) => {
  await openHydrated(page, RISKS);
  const grid = page.getByRole("grid", { name: "Registre des risques" });
  await grid.getByRole("gridcell", { name: "Risque de reprise du câblage" }).click({
    position: { x: 2, y: 2 },
  });
  // The click made the cell the active one, and did not follow the link it holds.
  await expect(page).toHaveURL(RISKS);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${RISKS}?risk=${CABLING}`, { timeout: WORKING });
  await expect(page.getByRole("region", { name: "Risque de reprise du câblage" })).toBeVisible();
});
