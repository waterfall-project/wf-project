// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

test("opens the list of projects, a project, and reads its planning and its estimate [WF-QUA-0050-A]", async ({
  page,
}) => {
  await page.goto("/projects");
  await page.getByRole("link", { name: "Modernisation du poste de commande" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Modernisation du poste de commande",
  );
  // A revision opens on its planning, the first function of a revision.
  await page.getByRole("link", { name: "Référence" }).click();
  const planning = page.getByRole("grid", { name: "Grille de planning" });
  await expect(planning.getByRole("gridcell", { name: "Revue de conception" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Planification");

  // The estimate, from the sidebar: the header, the four nodes of the structure, the totals.
  await page.getByRole("link", { name: "Chiffrage et devis" }).click();
  const estimate = page.getByRole("grid", { name: "Grille de devis" });
  await expect(estimate.getByRole("row")).toHaveCount(6);
  await expect(estimate.getByRole("gridcell", { name: "Ingénierie de détail" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Indicateurs du devis" })).toContainText(
    "100 000,00",
  );
});
