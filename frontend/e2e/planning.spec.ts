// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

// The fake back serves the first example of `listNodes` whatever `kinds` asks: its line shows
// here too, where the service renders the tasks alone — the component and page tests prove
// that the planning asks for them.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("opens the grid of the planning: its icons named, the critical path marked, the predecessors by row number", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/planning`);
  await expect(page).toHaveTitle("Planification · Modernisation du poste de commande — Waterfall");
  const grid = page.getByRole("grid", { name: "Grille de planning" });
  for (const name of ["N°", "Libellé", "Mode de planification", "Avancement", "Calculé Marge"]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
  }
  const review = grid.getByRole("row", { name: /Revue de conception/ });
  await expect(review.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(review.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(review.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  await expect(review.getByRole("img", { name: "Chemin critique" })).toBeVisible();
  await expect(review.getByRole("gridcell").last()).toHaveText("2");
  await expect(
    grid.getByRole("row", { name: /^1 / }).getByRole("img", { name: "Chemin critique" }),
  ).toHaveCount(0);

  // A header asks the server for its sort: the address says it.
  await grid
    .getByRole("columnheader", { name: "Mode de planification" })
    .getByRole("button")
    .click();
  await expect(page).toHaveURL(/sort_by=scheduling_mode&sort_order=asc/);
});
