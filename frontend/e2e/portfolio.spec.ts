// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { withinBox } from "./scroll";

// The fake back serves the first example of each read of the portfolio — the three hundred projects
// of §4.6.2 at 16 March 2026, the witness project first, and the views summed from them —, whatever
// the perimeter, the sort or the page asked: the component and page tests prove what each screen
// asks. The marks read here are fixed by `test_the_marks_the_portfolio_journey_reads`.
const PROJECTS = "/portfolio/projects";

test("reads the portfolio of three hundred projects: its value, its perimeter, the list the server sorts and filters [WF-PTF-0040-A]", async ({
  page,
}) => {
  await page.goto(PROJECTS);
  await expect(page).toHaveTitle("Portefeuille de projets — Waterfall");
  await expect(page.getByRole("main")).toContainText(
    "En cours et Chiffrage · 300 projets · calculé au 16 mars 2026",
  );
  await expect(page.getByRole("region", { name: "Valeur du portefeuille" })).toContainText(
    "Taux de transformation40 %",
  );
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  // Each column the requirement names.
  for (const name of [
    "Libellé",
    "Code",
    "État",
    "Budget de référence",
    "Devis courant",
    "Probabilité de gain",
    "Projection du chef de projet",
    "Écart au budget",
    "Indice de coût",
    "Indice de délai",
    "Dernière révision marquée",
  ]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
  }
  const witness = grid.getByRole("row", { name: /Modernisation du poste de commande/ });
  await expect(witness.getByRole("img", { name: "Alerte" })).toBeVisible();
  // The grid holds in the window: its totals, the number of projects the server retained, in view.
  // Its cells stick to the foot of the grid, their row keeping its place in the table.
  const total = grid.getByRole("gridcell", { name: "300 projets retenus" });
  await expect(total).toHaveCount(1);
  expect(await withinBox(grid, total)).toBe(true);

  // The sort by the cost index and a state added, asked of the server by the address.
  await grid.getByRole("columnheader", { name: "Indice de coût" }).getByRole("button").click();
  await expect(page).toHaveURL(`${PROJECTS}?sort_by=cost_index&sort_order=asc`);
  const states = page.getByRole("group", { name: "États retenus" });
  await states.getByRole("button", { name: "Terminé" }).click();
  await expect(page).toHaveURL(
    `${PROJECTS}?sort_by=cost_index&sort_order=asc&states=in_progress%2Cpricing%2Ccompleted`,
  );
  await expect(states.getByRole("button", { name: "Terminé" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
