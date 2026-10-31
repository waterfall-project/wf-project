// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Download, expect, type Locator, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { scrollPageToGrid, withinBox } from "./scroll";

// The fake back serves the first example of each read of the risks — the register of three risks,
// one in each state, its matrix, the risk of rewiring and the history of its reviews —, whatever
// the risk asked: the component and page tests prove what the screen asks of each.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const RISKS = `/projects/${PROJECT}/revisions/${REVISION}/risks`;
const CABLING = "01926f3a-7c00-7000-8000-000000000751";

/** The box of an element in the window, which the page has laid out. */
async function boxOf(element: Locator) {
  const box = await element.boundingBox();
  expect(box).not.toBeNull();
  return { x: 0, y: 0, width: 0, height: 0, ...box };
}

test("reads the risks of a revision: the register and its totals, the detail of a risk, the sort and the filter asked of the server [WF-RIS-0040-A]", async ({
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
  // The grid holds in the window, under the matrix folded: its totals, the general total the
  // server gives, are in view.
  await scrollPageToGrid(grid);
  const total = grid.getByRole("row").last();
  await expect(total).toHaveText(/^Total général\s*1\s100\s060,00$/);
  expect(await withinBox(grid, total)).toBe(true);
  await expect(page.getByRole("region", { name: "Provisions des risques retenus" })).toHaveText(
    /^Provisions des risques retenus\s*Risques identifiés\s*500\s000,00\s*Risques survenus\s*60,00\s*Risques écartés\s*600\s000,00\s*Total général\s*1\s100\s060,00$/,
  );
  // The coverage of the risks, each amount as the server computes it, the variance signed.
  await expect(page.getByRole("region", { name: "Couverture des risques" })).toHaveText(
    /Réserve pour risques\s*850\s060,00\s*Provisions restantes\s*500\s000,00\s*Coût des risques survenus\s*200,00\s*Écart de couverture\s*349\s860,00/,
  );

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

test("draws the matrix over the whole width between the cards and the grid, the count of each cell in a table under it [WF-IHM-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, RISKS);
  const grid = page.getByRole("grid", { name: "Registre des risques" });
  // The matrix, a bubble chart over the whole width between the cards and the grid; the count of
  // each cell stays in a table under it, each named by its signal, never by its colour alone.
  const figure = page.getByRole("figure", { name: "Matrice des risques" });
  // The matrix starts folded, so that the grid keeps its totals in a window 768 high (#1252); a
  // command unfolds it, and folds it again.
  const drawing = figure.getByRole("img", { name: /^Nuage de bulles des risques/ });
  await expect(drawing).toHaveCount(0);
  const toggle = figure.getByRole("button", { name: "Graphique", exact: true });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(drawing).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  // Unfolded, the figure lies between the cards and the grid, over the whole width.
  const unfolded = await boxOf(figure);
  const cardsBox = await boxOf(page.getByRole("region", { name: "Couverture des risques" }));
  const registerBox = await boxOf(grid);
  expect(unfolded.y).toBeGreaterThan(cardsBox.y + cardsBox.height - 1);
  expect(unfolded.y + unfolded.height).toBeLessThan(registerBox.y + 1);
  expect(unfolded.width).toBeGreaterThan(registerBox.width - 1);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(drawing).toHaveCount(0);
  const frame = await boxOf(figure);
  const cards = await boxOf(page.getByRole("region", { name: "Couverture des risques" }));
  const register = await boxOf(grid);
  expect(frame.y).toBeGreaterThan(cards.y + cards.height - 1);
  expect(frame.y).toBeLessThan(register.y);
  expect(frame.width).toBeGreaterThan(register.width - 1);
  await figure.getByText("Valeurs du graphique").click();
  const matrix = figure.getByRole("table", { name: "Décompte des risques par case de la matrice" });
  await expect(matrix.getByRole("columnheader", { name: "10 % et plus" })).toBeVisible();
  await expect(matrix.getByRole("rowheader", { name: "60 % et plus" })).toBeVisible();
  await expect(matrix.getByRole("img", { name: "Alerte" })).toHaveCount(3);
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

test("names the category and the sub-project a risk designates for its provision, in its detail (EP-14/L42p)", async ({
  page,
}) => {
  await openHydrated(page, `${RISKS}?risk=${CABLING}`);
  const provision = page
    .getByRole("region", { name: "Risque de reprise du câblage" })
    .getByRole("region", { name: "Ligne de provision" });
  await expect(provision).toContainText(
    /Catégorie\s*Provisions pour risques\s*Sous-projet\s*Hors sous-projet/,
  );
});

test("lays the provisions and the coverage of the risks side by side on a wide window [WF-RIS-0050-A]", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await openHydrated(page, RISKS);
  const provisions = await page
    .getByRole("region", { name: "Provisions des risques retenus" })
    .boundingBox();
  const coverage = await page.getByRole("region", { name: "Couverture des risques" }).boundingBox();
  expect(provisions).not.toBeNull();
  expect(coverage).not.toBeNull();
  // On the one row: the same top, the second one to the right of the first.
  expect(coverage?.y).toBeCloseTo(provisions?.y ?? Number.NaN, 0);
  expect(coverage?.x ?? 0).toBeGreaterThan((provisions?.x ?? 0) + (provisions?.width ?? 0) - 1);
});

test("places the risks as bubbles that a hover tells and a click opens, the zones named in their areas [WF-IHM-0070-A]", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 900 });
  await openHydrated(page, RISKS);
  const figure = page.getByRole("figure", { name: "Matrice des risques" });
  await figure.getByRole("button", { name: "Graphique", exact: true }).click();
  const drawing = figure.getByRole("img", { name: /^Nuage de bulles des risques/ });
  await expect(drawing.locator("svg")).toBeVisible();
  // The zones are named in their areas, not told by their colour alone: the twelve zones that have
  // room for a line — the four thinner bands of the lowest severity are not named — are, each one,
  // three of the nominal zone, six of the watch zone and three of the alert zone.
  for (const [zone, count] of [
    ["Nominal", 3],
    ["Vigilance", 6],
    ["Alerte", 3],
  ] as const) {
    const names = drawing.locator("text", { hasText: new RegExp(`^${zone}$`) });
    await expect(names, `the zones named ${zone}`).toHaveCount(count);
    for (const name of await names.all()) {
      await expect(name).toBeVisible();
    }
  }
  // The legend names the states of the risks, each by the shape of its bubbles too.
  for (const state of ["Identifié", "Survenu", "Écarté"]) {
    await expect(drawing.locator("text", { hasText: new RegExp(`^${state}$`) })).toBeVisible();
  }
  // The heaviest risk (12 000 000,00) is the largest bubble: those of the legend are smaller.
  const bubbles = await drawing.locator("path[fill-opacity='0.85']").evaluateAll((paths) =>
    paths.map((path) => {
      const box = path.getBoundingClientRect();
      return { x: box.x + box.width / 2, y: box.y + box.height / 2, size: box.width };
    }),
  );
  const heaviest = bubbles.reduce((most, each) => (each.size > most.size ? each : most));
  expect(heaviest.size).toBeGreaterThan(30);
  await page.mouse.move(heaviest.x, heaviest.y);
  await expect(drawing).toContainText("Indisponibilité de l'automaticien");
  await expect(drawing).toContainText("Gravité : 12 000 000,00 (17,58 %)");
  await page.mouse.click(heaviest.x, heaviest.y);
  await expect(page).toHaveURL(`${RISKS}?risk=01926f3a-7c00-7000-8000-000000000753`, {
    timeout: WORKING,
  });
});

test("exports the matrix as a PNG image named after the project and its revision [WF-IHM-0130-A]", async ({
  page,
}) => {
  await openHydrated(page, RISKS);
  const command = page
    .getByRole("figure", { name: "Matrice des risques" })
    .getByRole("button", { name: "Exporter en PNG" });
  let download: Download | undefined;
  await expect(async () => {
    [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 1_000 }),
      command.click(),
    ]);
  }).toPass({ timeout: WORKING });
  expect(download?.suggestedFilename()).toBe("matrice-des-risques-PRJ-001.png");
});

test("walks the screens of the cycle of a risk: identify it, open an estimate, review it, declare it occurred, without pricing anything", async ({
  page,
}) => {
  // The fake back keeps no state: it serves the first example of each answer — the risk declared
  // (754, its own structure 208), then the risk of rewiring for the detail, its review confirmed
  // and its occurrence queued — so that the steps are played one after the other from the screens
  // they lead to, never from one another's effects (#1350).
  test.slow();
  await compile(page.request, `/projects/${PROJECT}/revisions/${REVISION}/estimate`);
  await openHydrated(page, RISKS);

  // Identify: the form, then the own estimate of the risk in the grid of the estimate, to price.
  await page.getByRole("button", { name: "Identifier un risque" }).click();
  const identify = page.getByRole("dialog", { name: "Identifier un risque" });
  await identify.getByRole("textbox", { name: "Libellé" }).fill("Indisponibilité de la grue");
  await identify.getByRole("textbox", { name: "Probabilité (%)" }).fill("20");
  await identify.getByRole("button", { name: "Créer" }).click();
  await expect(page).toHaveURL(/\/estimate\?.*structure=01926f3a-7c00-7000-8000-000000000208/, {
    timeout: WORKING,
  });
  // The structure 208 is a counterfactual no read of the fake back knows (the screen says it is not
  // found): the own estimate that is priced is that of the risk of rewiring, its structure 204.
  await openHydrated(
    page,
    `/projects/${PROJECT}/revisions/${REVISION}/estimate?structure=01926f3a-7c00-7000-8000-000000000204`,
  );
  await expect(page.getByRole("treegrid", { name: "Grille de devis" })).toBeVisible({
    timeout: WORKING,
  });

  // Review: confirmed with no change, the status says it.
  await openHydrated(page, `${RISKS}?risk=${CABLING}`);
  const detail = page.getByRole("region", { name: "Risque de reprise du câblage" });
  await detail.getByRole("button", { name: "Réexaminer" }).click();
  const review = page.getByRole("dialog", { name: "Réexaminer « Risque de reprise du câblage »" });
  await expect(review.getByRole("textbox", { name: "Probabilité (%)" })).toHaveValue("40");
  await review.getByRole("button", { name: "Réexaminer" }).click();
  await expect(detail.getByRole("status").filter({ hasText: "réexaminé" })).toHaveText(
    "Risque « Risque de reprise du câblage » réexaminé.",
  );

  // A risk a marked revision cites is not deleted: the command says why.
  await expect(detail.getByRole("button", { name: "Supprimer le risque" })).toHaveAttribute(
    "aria-disabled",
    "true",
  );

  // Declare occurred: the confirmation says the provision withdrawn, then the task is queued.
  await detail.getByRole("button", { name: "Déclarer survenu" }).click();
  const declare = detail.getByRole("form", { name: "Déclarer survenu" });
  await expect(declare).toContainText("sa ligne de provision est retirée du reste à engager");
  await expect(declare.getByRole("table", { name: /écarts/i })).toBeVisible({ timeout: WORKING });
  await declare.getByRole("button", { name: "Déclarer le risque survenu" }).click();
  await expect(
    detail.getByText(/La survenance de « Risque de reprise du câblage » est confiée/),
  ).toBeVisible();
});

test("shows the report of the occurrence in the marks before confirming, and abandons without writing [WF-RIS-0060-A] [WF-IHM-0110-A]", async ({
  page,
}) => {
  await openHydrated(page, `${RISKS}?risk=${CABLING}`);
  const detail = page.getByRole("region", { name: "Risque de reprise du câblage" });
  await detail.getByRole("button", { name: "Déclarer survenu" }).click();
  const declare = detail.getByRole("form", { name: "Déclarer survenu" });
  const table = declare.getByRole("table", { name: /écarts/i });
  await expect(table).toBeVisible({ timeout: WORKING });
  // The marks of the diff of the grids, each doubled by a word, and the provision withdrawn.
  const markOf = (label: string) =>
    table
      .getByRole("row", { name: new RegExp(label) })
      .getByRole("cell")
      .first();
  await expect(markOf("Diagnostic des défauts de câblage")).toHaveAccessibleName("Ajouté");
  await expect(markOf("Câblage des armoires")).toHaveAccessibleName("Modifié");
  await expect(markOf("Provision — risque de reprise du câblage")).toHaveAccessibleName("Retiré");
  await expect(declare).toContainText("500 000,00 de provision en moins");
  // Abandoned: the form closes and nothing is declared.
  await declare.getByRole("button", { name: "Annuler" }).click();
  await expect(declare).toBeHidden();
  await expect(detail.getByText(/est confiée/)).toBeHidden();
});
