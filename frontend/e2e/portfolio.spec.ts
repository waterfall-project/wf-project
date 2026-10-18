// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Download, expect, type Locator, test } from "@playwright/test";

import { compile } from "./compile";
import { sortUntilAddress, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each read of the portfolio — the three hundred projects
// of §4.6.2 at 3 June 2026, the witness project first, and the views summed from them —, whatever
// the perimeter, the sort or the page asked: the component and page tests prove what each screen
// asks. The marks read here are fixed by `test_the_marks_the_portfolio_journey_reads`.
const PROJECTS = "/portfolio/projects";
const PERFORMANCE = "/portfolio/performance";
const COST_CURVE = "/portfolio/cost-curve";
// The columns of the cost index and of the schedule index in the grid of the projects.
const COST_INDEX = 8;
const SCHEDULE_INDEX = 9;
const INDICATORS =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/indicators";

/** The colour a signal is painted in. */
function colour(signal: Locator): Promise<string> {
  return signal.evaluate((element) => getComputedStyle(element).color);
}

test("reads the portfolio of three hundred projects: its value, its perimeter, the list the server sorts and filters [WF-PTF-0040-A]", async ({
  page,
}) => {
  // The sort, given the time to hydrate and to read the grid anew, then the filter: more than the
  // thirty seconds of a test.
  test.slow();
  await page.goto(PROJECTS);
  await expect(page).toHaveTitle("Portefeuille de projets — Waterfall");
  await expect(page.getByRole("main")).toContainText(
    "En cours et Chiffrage · 300 projets · calculé au 3 juin 2026",
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
    "Écart à la référence",
    "Indice de coût",
    "Indice de délai",
    "Dernière révision marquée",
  ]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
  }
  // The witness project, its cost index nominal and its schedule index on watch — the tasks drawn
  // around its core under way, planned and not yet earned —, as the server classes them.
  const witness = grid.getByRole("row", { name: /Modernisation du poste de commande/ });
  await expect(witness.getByRole("img", { name: "Nominal" })).toHaveCount(1);
  await expect(witness.getByRole("img", { name: "Vigilance" })).toHaveCount(1);
  // The grid holds in the window: its totals, the number of projects the server retained, in view.
  // Its cells stick to the foot of the grid, their row keeping its place in the table.
  const total = grid.getByRole("gridcell", { name: "300 projets retenus" });
  await expect(total).toHaveCount(1);
  expect(await withinBox(grid, total)).toBe(true);

  // The sort by the cost index and a state added, asked of the server by the address.
  // No project is opened here, nothing witnesses the hydration: the sort is pressed again until
  // React answers it, never while an earlier press is under way (`sortUntilAddress`).
  await sortUntilAddress(
    grid.getByRole("columnheader", { name: "Indice de coût" }),
    grid,
    `${PROJECTS}?sort_by=cost_index&sort_order=asc`,
  );
  const states = page.getByRole("group", { name: "États retenus" });
  await states.getByRole("button", { name: "Terminé" }).click();
  await expect(page).toHaveURL(
    `${PROJECTS}?sort_by=cost_index&sort_order=asc&states=in_progress%2Cpricing%2Ccompleted`,
    { timeout: WORKING },
  );
  await expect(states.getByRole("button", { name: "Terminé" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("paints the same zone of an index the same colour in the list of the projects, in the indicators of the project and in the performance of the portfolio [WF-IHM-0070-A]", async ({
  page,
}) => {
  await compile(page.request, PROJECTS, INDICATORS, PERFORMANCE);
  await page.goto(PROJECTS);
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  /** The signal of an index of a project of the list, by its code and the column of the index. */
  const signal = (code: string, column: number, zone: string) =>
    grid
      .getByRole("row", { name: new RegExp(code) })
      .getByRole("gridcell")
      .nth(column)
      .getByRole("img", { name: zone });
  // The schedule index of a project in alert, the cost indices of two others nominal and in
  // watch: the colours of reference, read once shown.
  const zones = {
    Alerte: signal("PRJ-003", SCHEDULE_INDEX, "Alerte"),
    Nominal: signal("PRJ-004", COST_INDEX, "Nominal"),
    Vigilance: signal("PRJ-003", COST_INDEX, "Vigilance"),
  };
  const painted: Record<string, string> = {};
  for (const [zone, locator] of Object.entries(zones)) {
    await expect(locator).toBeVisible();
    painted[zone] = await colour(locator);
  }

  await page.goto(INDICATORS);
  await expect(page.getByRole("main").getByText("Alerte", { exact: true }).first()).toHaveCSS(
    "color",
    painted.Alerte ?? "",
  );

  await page.goto(PERFORMANCE);
  const distribution = page.getByRole("table", { name: "Répartition des projets par zone" });
  for (const [zone, count] of [
    ["Nominal", 169],
    ["Vigilance", 47],
    ["Alerte", 53],
  ] as const) {
    const row = distribution.getByRole("row", {
      name: new RegExp(`Indice de coût\\s*${zone}\\s*${String(count)}`),
    });
    await expect(row.getByText(zone, { exact: true })).toHaveCSS("color", painted[zone] ?? "");
  }
  // Two zones never share their colour.
  await expect
    .poll(() => colour(distribution.getByText("Alerte", { exact: true }).first()))
    .not.toBe(painted.Nominal);
  expect(new Set(Object.values(painted)).size).toBe(3);
});

test("exports the S-curve of the portfolio as a PNG image named after the date of its perimeter (#312)", async ({
  page,
}) => {
  await page.goto(COST_CURVE);
  const command = page
    .getByRole("figure", { name: "Coûts cumulés du portefeuille" })
    .getByRole("button", { name: "Exporter en PNG" });
  // No project is opened here, nothing witnesses the hydration: the command is pressed again
  // until the browser saves the image.
  let download: Download | undefined;
  await expect(async () => {
    [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 1_000 }),
      command.click(),
    ]);
  }).toPass({ timeout: WORKING });
  expect(download?.suggestedFilename()).toBe("couts-cumules-portefeuille-2026-06-03.png");
});
