// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Download, expect, type Locator, type Page } from "@playwright/test";

import { WORKING } from "./bounds";
import { menuButton, pick } from "./check-menu";
import { compile } from "./compile";
import { sortUntilAddress } from "./hydration";
import { inService, test } from "./mode";
import { scrollPageToGrid, withinBox } from "./scroll";

// The fake back serves the first example of each read of the portfolio — the three hundred projects
// of §4.6.2 at 3 June 2026, the witness project first, and the views summed from them —, whatever
// the perimeter, the sort or the page asked: the component and page tests prove what each screen
// asks. The marks read here are fixed by `test_the_marks_the_portfolio_journey_reads`. What affirms
// the three hundred projects is played against the fake back alone; the paths tagged `@shared` are
// played against the service too, on the witness loaded with its slice of the portfolio (EP-11,
// US-2770/L2), at the date of calculation of the witness, 3 June 2026, which the address names
// (`AS_OF`): the fake back ignores it, the service reads the portfolio as it was then.
const AS_OF = "as_of=2026-06-03";
const PROJECTS = "/portfolio/projects";
const PERFORMANCE = "/portfolio/performance";
const COST_CURVE = "/portfolio/cost-curve";
const WORKLOAD = "/portfolio/workload";
const RISKS = "/portfolio/risks";
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
  // The list of the portfolio is a screen of consultation, airy (EP-25, « Deux familles d'écrans »):
  // its margins and its gaps (`py-8`, `gap-7`) are taller than those of a screen of work (`py-3`,
  // `gap-3`), and the grid at its floor no longer fits the 720 points of the default window, the
  // page scrolling then. The totals are read in view in a window of 800 points: a margin over
  // what the screen needs, not a floor measured (#3273).
  await page.setViewportSize({ width: 1280, height: 800 });
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
  // The list lies in a card under the perimeter and the value, which the 800 points of the window
  // no longer leave the grid at its floor: the page scrolls to the grid (`scrollPageToGrid`), whose
  // totals, the number of projects the server retained, are then in view. Its cells stick to the
  // foot of the grid, their row keeping its place in the table.
  await scrollPageToGrid(grid);
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
  await pick(page, "États retenus", "Terminé");
  await expect(page).toHaveURL(
    `${PROJECTS}?sort_by=cost_index&sort_order=asc&states=in_progress%2Cpricing%2Ccompleted`,
    { timeout: WORKING },
  );
  await expect(menuButton(page, "États retenus")).toContainText("3 sélectionnés");
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

test("exports the S-curve of the portfolio as a PNG image named after the date of its perimeter @shared [WF-IHM-0130-A] (#312)", async ({
  page,
}) => {
  await page.goto(`${COST_CURVE}?${AS_OF}`);
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

test("exports the quarterly performance of the portfolio as a PNG image named after the date of its perimeter @shared [WF-IHM-0130-A] [US-2760]", async ({
  page,
}) => {
  await page.goto(`${PERFORMANCE}?${AS_OF}`);
  const figure = page.getByRole("figure", { name: "Évolution trimestrielle des indices" });
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  await expect(command).toBeVisible({ timeout: WORKING });
  // No project is opened here, nothing witnesses the hydration: the command is pressed again
  // until the browser saves the image.
  let download: Download | undefined;
  await expect(async () => {
    [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 1_000 }),
      command.click(),
    ]);
  }).toPass({ timeout: WORKING });
  expect(download?.suggestedFilename()).toBe("evolution-des-indices-portefeuille-2026-06-03.png");
});

test("offers the period of the projects completed to the S-curve and the structure of the costs, and keeps it in the address @shared [WF-PTF-0010-A]", async ({
  page,
}) => {
  for (const route of [COST_CURVE, "/portfolio/cost-structure"]) {
    await page.goto(`${route}?states=completed&from=2025-01-01&to=2025-12-31`);
    const period = page.getByRole("form", { name: "Période et date de calcul" });
    await expect(period).toBeVisible();
    await expect(period.getByLabel("Du", { exact: true })).toHaveValue("2025-01-01");
    await expect(period.getByLabel("Au", { exact: true })).toHaveValue("2025-12-31");
  }
});

test("draws the aggregated workload in stacked bars with the dashed capacity of the perimeter, the table of the roles under it, and exports it as a PNG image @shared [WF-PTF-0060-A] [WF-IHM-0130-A]", async ({
  page,
}) => {
  await page.goto(`${WORKLOAD}?${AS_OF}`);
  const figure = page.getByRole("figure", { name: "Charge empilée par rôle et par mois" });
  await expect(figure.getByRole("img", { name: /^Barres empilées de la charge/ })).toBeVisible({
    timeout: WORKING,
  });
  // The capacity of the perimeter, as the server sums it, said under the title of the chart.
  await expect(figure.getByText(/^Capacité du périmètre : /)).toBeVisible();
  // The line of the capacity, dashed, is drawn inside the plot — the axis reaches it — and says
  // itself in its label.
  const drawing = figure.getByRole("img", { name: /^Barres empilées de la charge/ });
  await expect(drawing.locator("text", { hasText: /^Capacité : .* h par mois$/ })).toBeVisible();
  // The plot is the span of the light dashed horizontal lines of its grid, one per value of the axis;
  // the capacity is the one dashed horizontal line across it, wider than half the drawing, drawn in
  // the colour of its label, and it lies within the plot.
  const { capacity, plot } = await drawing.evaluate((element) => {
    const width = element.getBoundingClientRect().width;
    const label = [...element.querySelectorAll("text")].find((text) =>
      /^Capacité : .* h par mois$/.test(text.textContent),
    );
    const mark = label?.getAttribute("fill");
    const lines = [...element.querySelectorAll("path")]
      .filter((path) => path.hasAttribute("stroke-dasharray"))
      .map((path) => ({ stroke: path.getAttribute("stroke"), box: path.getBoundingClientRect() }))
      .filter(({ box }) => box.height <= 1 && box.width > width / 2);
    const tops = lines.map(({ box }) => box.top);
    return {
      plot: { top: Math.min(...tops), height: Math.max(...tops) - Math.min(...tops) },
      capacity: lines.filter(({ stroke }) => stroke === mark).map(({ box }) => box.top),
    };
  });
  expect(capacity).toHaveLength(1);
  expect(capacity[0] ?? Number.NaN).toBeGreaterThanOrEqual(plot.top - 0.5);
  expect(capacity[0] ?? Number.NaN).toBeLessThanOrEqual(plot.top + plot.height + 0.5);
  // The filter by node of organisation, in the head of the view; the table of the roles after the
  // chart, in the order of the page.
  await expect(page.getByLabel("Nœud d’organisation")).toBeVisible();
  const table = page.getByRole("table", { name: "Charge par rôle et par mois" });
  const chartTop = (await figure.boundingBox())?.y ?? 0;
  expect((await table.boundingBox())?.y ?? 0).toBeGreaterThan(chartTop);
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  let download: Download | undefined;
  await expect(async () => {
    [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 1_000 }),
      command.click(),
    ]);
  }).toPass({ timeout: WORKING });
  expect(download?.suggestedFilename()).toBe("plan-de-charge-agrege-portefeuille-2026-06-03.png");
});

test("draws the risk matrix of the portfolio as a bubble chart in place of the table, and exports it as a PNG image @shared [WF-IHM-0130-A]", async ({
  page,
}) => {
  await page.goto(`${RISKS}?${AS_OF}`);
  const figure = page.getByRole("figure", { name: "Matrice des risques" });
  const drawing = figure.getByRole("img", { name: /^Nuage de bulles des risques/ });
  await expect(drawing.locator("svg")).toBeVisible({ timeout: WORKING });
  // One bubble for each risk identified the server rendered, over the sixteen zones: 429 of the
  // fake back's; the six of the witness's slice at least against the service, the paths of the other
  // workers marking revisions of their own projects beside them. The count cannot be exact there: the
  // perimeter of the risks is drawn by states, period and node of organisation alone, none of which
  // isolates the projects of the slice (no filter by project, WF-PTF-0020-A), and the other workers
  // add risks of their own as they run. The chart has no legend of states, so that no marker is
  // added to the bubbles.
  const bubbles = drawing.locator("path[fill-opacity='0.85']");
  if (inService) {
    await expect.poll(() => bubbles.count()).toBeGreaterThanOrEqual(6);
  } else {
    await expect(bubbles).toHaveCount(429);
  }
  await figure.getByText("Valeurs du graphique").click();
  await expect(
    figure.getByRole("table", { name: "Décompte des risques identifiés par case de la matrice" }),
  ).toBeVisible();
  const command = figure.getByRole("button", { name: "Exporter en PNG" });
  let download: Download | undefined;
  await expect(async () => {
    [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 1_000 }),
      command.click(),
    ]);
  }).toPass({ timeout: WORKING });
  expect(download?.suggestedFilename()).toBe("matrice-des-risques-portefeuille-2026-06-03.png");
});

const SERVICE_ONLY =
  "the service reads the slice of the portfolio the witness holds, which the fake back does not";

test("reads the portfolio of the witness at its date of calculation: its value, its perimeter, the projects of its slice, each opened from its label @shared [WF-PTF-0040-A] [WF-PTF-0030-A] [US-2760]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`${PROJECTS}?${AS_OF}`);
  await expect(page.getByRole("main")).toContainText("calculé au 3 juin 2026", {
    timeout: WORKING,
  });
  await expect(page.getByRole("region", { name: "Valeur du portefeuille" })).toBeInViewport();
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  // Two projects of the slice of the witness, one in progress and one in pricing, found by their
  // code, as the filter by column asks the server for it; then the project of the witness, which
  // opens from its label.
  for (const code of ["PRJ-301", "PRJ-306"]) {
    await page.goto(`${PROJECTS}?${AS_OF}&states=in_progress%2Cpricing&code=${code}`);
    await expect(grid.getByRole("row", { name: new RegExp(code) })).toBeVisible({
      timeout: WORKING,
    });
    await scrollPageToGrid(grid);
    await expect(grid.getByRole("row", { name: new RegExp(code) })).toBeInViewport();
  }
  await page.goto(`${PROJECTS}?${AS_OF}&code=PRJ-001`);
  const opened = grid.getByRole("link", { name: "Modernisation du poste de commande" });
  await expect(opened).toHaveAttribute("href", "/projects/01926f3a-7c00-7000-8000-000000000001");
  await scrollPageToGrid(grid);
  await expect(opened).toBeInViewport();
});

/** The number the totals row of the list says the server retained, the list read at an address. */
async function retainedAt(page: Page, address: string): Promise<number> {
  await page.goto(address);
  const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
  await scrollPageToGrid(grid);
  const total = grid.getByRole("gridcell", { name: /^\d+ projets? retenus?$/ });
  await expect(total).toHaveCount(1, { timeout: WORKING });
  await expect(total).toBeInViewport();
  const digits = /\d+/.exec(await total.innerText())?.[0];
  if (digits === undefined) {
    throw new Error(
      `The totals row of the list at ${address} states no number of retained projects.`,
    );
  }
  return Number(digits);
}

for (const [state, shown, other] of [
  ["pricing", "Chiffrage", "En cours"],
  ["in_progress", "En cours", "Chiffrage"],
] as const) {
  test(`filters the list of the portfolio on the state ${state}: only the projects of that state, and its totals count them @shared [WF-PTF-0040-A] [WF-IHM-0130-A]`, async ({
    page,
  }) => {
    test.skip(!inService, SERVICE_ONLY);
    test.slow();
    await page.setViewportSize({ width: 1280, height: 800 });
    // The totals row says how many projects the server retained: those of the state alone, not
    // those of both states. The other workers add projects as they run, so the three readings are
    // taken again until they agree: the state and the other state make the two together.
    await expect(async () => {
      const filtered = await retainedAt(page, `${PROJECTS}?states=${state}&${AS_OF}`);
      const others = await retainedAt(
        page,
        `${PROJECTS}?states=${state === "pricing" ? "in_progress" : "pricing"}&${AS_OF}`,
      );
      const both = await retainedAt(page, `${PROJECTS}?states=in_progress%2Cpricing&${AS_OF}`);
      expect(filtered).toBeGreaterThan(0);
      expect(others).toBeGreaterThan(0);
      expect(filtered).toBeLessThan(both);
      expect(filtered + others).toBe(both);
    }).toPass({ timeout: 2 * WORKING });
    // Every row in view is a project of the state, none of the other.
    await page.goto(`${PROJECTS}?states=${state}&${AS_OF}`);
    const grid = page.getByRole("grid", { name: "Projets du portefeuille" });
    await scrollPageToGrid(grid);
    const first = grid.getByRole("gridcell", { name: shown, exact: true }).first();
    await expect(first).toBeVisible({ timeout: WORKING });
    await expect(first).toBeInViewport();
    await expect(grid.getByRole("gridcell", { name: other, exact: true })).toHaveCount(0);
  });
}
