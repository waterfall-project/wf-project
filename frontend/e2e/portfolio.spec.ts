// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, test } from "@playwright/test";

import { withinBox } from "./scroll";

// The fake back serves the first example of each read of the portfolio — the three hundred projects
// of §4.6.2 at 16 March 2026, the witness project first, and the views summed from them —, whatever
// the perimeter, the sort or the page asked: the component and page tests prove what each screen
// asks. The marks read here are fixed by `test_the_marks_the_portfolio_journey_reads`.
const PROJECTS = "/portfolio/projects";
const INDICATORS =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/indicators";

/** The colour a signal is painted in. */
function colour(signal: Locator): Promise<string> {
  return signal.evaluate((element) => getComputedStyle(element).color);
}

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

test("paints the same zone of an index the same colour in the list of the projects, in the indicators of the project and in the performance of the portfolio [WF-IHM-0070-A]", async ({
  page,
}) => {
  await page.goto(PROJECTS);
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  const inList = await colour(
    grid
      .getByRole("row", { name: /Modernisation du poste de commande/ })
      .getByRole("img", { name: "Alerte" }),
  );

  await page.goto(INDICATORS);
  const inProject = await colour(
    page.getByRole("main").getByText("Alerte", { exact: true }).first(),
  );

  await page.goto("/portfolio/performance");
  const distribution = page.getByRole("table", { name: "Répartition des projets par zone" });
  await expect(
    distribution.getByRole("row", { name: /Indice de coût\s*Alerte\s*53/ }),
  ).toBeVisible();
  const inPortfolio = await colour(distribution.getByText("Alerte", { exact: true }).first());
  const nominal = await colour(distribution.getByText("Nominal", { exact: true }).first());

  expect(inProject).toBe(inList);
  expect(inPortfolio).toBe(inList);
  expect(nominal).not.toBe(inList);
});
