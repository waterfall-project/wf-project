// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

test("opens the list of projects, a project, and reads a grid [WF-QUA-0050-A]", async ({
  page,
}) => {
  await page.goto("/projects");
  await page.getByRole("link", { name: "Modernisation du poste de commande" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Modernisation du poste de commande",
  );
  await page.getByRole("link", { name: "Référence" }).click();
  // The grid of the estimate: its header, the four nodes of the structure, its totals.
  const grid = page.getByRole("grid", { name: "Grille de devis" });
  await expect(grid.getByRole("row")).toHaveCount(6);
  await expect(grid.getByRole("gridcell", { name: "Ingénierie de détail" })).toBeVisible();
});
