// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { sortUntilAddress, WORKING } from "./hydration";
import { rowAt, scroller, withinBox } from "./scroll";

/** The automation engineer, the deactivated role of the witness. */
const AUTOMATION = "01926f3a-7c00-7000-8000-000000000453";

// The fake back serves the first example of each read of the reference data — the grid of the
// volumes, a hundred and fifty categories of labour over fifteen years, the natures, the
// organisation, the roles and the calendars of the witness —, and the first example of
// `setHourlyRate` whatever was written: the first rate of 2015 of the mechanical engineering of
// level 1, the third row of the grid, which has none before 2016. What the screens ask of each is
// proven by the tests of the pages and of the grid.

test("reads the settings of the reference data outside any project, and enters a rate on the dense grid of the hourly rates (US-0250)", async ({
  page,
}) => {
  await page.goto("/reference/costs");
  await expect(page).toHaveTitle("Paramètres de coûts — Waterfall");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de coûts");
  await expect(page.getByText("Montants exprimés en EUR")).toBeVisible();

  // The grid of the rates: a hundred and fifty rows over fifteen years, its totals row in view.
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  await expect(grid).toHaveAttribute("aria-rowcount", "152");
  await expect(grid.getByRole("columnheader", { name: "2012", exact: true })).toBeVisible();
  await expect(grid.getByRole("columnheader", { name: "2026", exact: true })).toHaveCount(1);
  const totals = grid.getByRole("gridcell", { name: "150 catégories, taux horaires en EUR" });
  expect(await withinBox(grid, totals)).toBe(true);

  // The first rate of 2015 of the third category, entered from the keyboard and answered.
  // No project is opened here, nothing witnesses the hydration: the cell is clicked and the cursor
  // moved again until React answers them, each try starting from the code of the category.
  const mechanical = rowAt(grid, 3);
  // The code, the label, the state, then 2012 to 2015.
  const rate = mechanical.getByRole("gridcell").nth(6);
  await expect(async () => {
    await mechanical.getByRole("gridcell", { name: "MO-003" }).click();
    for (let step = 0; step < 6; step += 1) {
      await page.keyboard.press("ArrowRight");
    }
    await expect(rate).toBeFocused({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(rate).toHaveText("");
  // What is typed differs from what the fake back answers: the cell shows the answer.
  await page.keyboard.type("85");
  await page.keyboard.press("Enter");
  await expect(rate).not.toHaveAttribute("aria-busy", "true");
  await expect(rate).toHaveText("85,48");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  await expect(rowAt(grid, 4).getByRole("gridcell").nth(6)).toBeFocused();

  // Beside it, the natures and the categories of cost, on the dense grid: the header, the three
  // natures, the totals; the categories, of which the server retains two hundred.
  await expect(page.getByRole("grid", { name: "Natures de coût" }).getByRole("row")).toHaveCount(5);
  const categories = page.getByRole("grid", { name: "Catégories de coût" });
  await expect(categories).toHaveAttribute("aria-rowcount", "202");
  // By code, as the list without sort gives them: the subcontracting first.
  await expect(rowAt(categories, 1)).toContainText("ACH-001Sous-traitance");

  // The deactivated objects asked too: the automation engineer, deactivated, is among the roles
  // only then (WF-REF-0150), whatever the fake back answers without the parameter.
  await page.goto("/reference/resources?include_inactive=true");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de ressources");
  // The header, the five roles, the totals; the header, the two calendars, the totals.
  await expect(
    page.getByRole("grid", { name: "Rôles de ressources" }).getByRole("row"),
  ).toHaveCount(7);
  await expect(page.getByRole("grid", { name: "Calendriers" }).getByRole("row")).toHaveCount(4);
  await expect(page.getByRole("treegrid", { name: "Arbre d’organisation" })).toBeVisible();

  await page.goto("/reference/risks");
  await expect(
    page
      .getByRole("table", { name: "Bornes de la matrice de risques" })
      .getByRole("row", { name: "Probabilité 10 % 30 % 60 %" }),
  ).toHaveCount(1);

  await page.goto("/reference/indicators");
  await expect(
    page
      .getByRole("table", { name: "Seuils d’alerte des indices" })
      .getByRole("row", { name: "Indice de coût 0,9 0,8" }),
  ).toHaveCount(1);
  await expect(page.getByText("8 semaines")).toBeVisible();
});

test("keeps the header and the totals row of the grid of the rates in a wide window, under its filters (US-0250)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/reference/costs");
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  await expect(
    page.getByRole("form", { name: "Bornes de «\u00a0Grille des taux horaires\u00a0»" }),
  ).toBeInViewport();
  // The screen fills the window: the grid scrolls in its box, its header and its totals in view,
  // in the window and not only in their container (défaut n° 13 de `typescript.md`).
  await expect(grid.getByRole("columnheader", { name: "Code", exact: true })).toBeInViewport();
  const totals = grid.getByRole("gridcell", { name: "150 catégories, taux horaires en EUR" });
  await expect(totals).toBeInViewport();
  expect(await withinBox(grid, totals)).toBe(true);
  // The fake back answers the grid in one page, which offers no pages; the box the grid scrolls
  // in, where they would come below, ends within the window.
  const foot = await scroller(grid).boundingBox();
  expect((foot?.y ?? 0) + (foot?.height ?? 0)).toBeLessThanOrEqual(1080);
});

test("stacks the grid of the rates and the natures of cost in a narrow window, neither over the other (US-0250)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 800, height: 720 });
  await page.goto("/reference/costs");
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  const totals = grid.getByRole("gridcell", { name: "150 catégories, taux horaires en EUR" });
  // The page scrolls, not the screen: the foot of the box of the grid brought into the window
  // brings its totals.
  await scroller(grid).evaluate((element) => {
    element.scrollIntoView({ block: "end" });
  });
  await expect(totals).toBeInViewport();
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  await natures.scrollIntoViewIfNeeded();
  await expect(natures).toBeInViewport();
  // The natures come below the box the grid scrolls in, never over it.
  const box = await scroller(grid).boundingBox();
  const below = await natures.boundingBox();
  expect(box).not.toBeNull();
  expect(below).not.toBeNull();
  expect((below?.y ?? 0) >= (box?.y ?? 0) + (box?.height ?? 0)).toBe(true);
});

test("adds the column of a year to the grid of the hourly rates, empty, and refuses a year the grid has [WF-REF-0060-A]", async ({
  page,
}) => {
  await page.goto("/reference/costs");
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  const form = page.getByRole("form", { name: "Ajouter une année à la grille" });
  const year = form.getByRole("textbox", { name: "Année" });
  // No project is opened here, nothing witnesses the hydration: the year is added again until
  // React answers, the column then shown.
  await expect(async () => {
    await year.fill("2027");
    await form.getByRole("button", { name: "Ajouter la colonne" }).click();
    await expect(grid.getByRole("columnheader", { name: "2027", exact: true })).toHaveCount(1, {
      timeout: 1_000,
    });
  }).toPass({ timeout: WORKING });
  // The column added is empty; the rates of the years before are as they were.
  const first = rowAt(grid, 1);
  await expect(first.locator('td[data-column="year_2027"]')).toHaveText("");
  await expect(first.locator('td[data-column="year_2026"]')).toHaveText("80,00");
  await year.fill("2026");
  await form.getByRole("button", { name: "Ajouter la colonne" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "L’année 2026 a déjà sa colonne dans la grille.",
  );
  await expect(grid.getByRole("columnheader", { name: "2026", exact: true })).toHaveCount(1);
});

test("sorts and searches each list of the settings of the resources by the server, folds the tree, and shows and reactivates the deactivated objects [WF-IHM-0060-A] [WF-REF-0150-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/resources");
  const roles = page.getByRole("grid", { name: "Rôles de ressources" });
  // A header of the roles asks the server for its sort, under the names of the grid.
  await sortUntilAddress(
    roles.getByRole("columnheader", { name: "Heures par mois" }),
    roles,
    "/reference/resources?role_sort_by=monthly_hours&role_sort_order=asc",
  );
  // The tree sorts nothing, folds and unfolds, and its search keeps the sort of the roles.
  const tree = page.getByRole("treegrid", { name: "Arbre d’organisation" });
  await expect(tree.locator("thead button")).toHaveCount(0);
  const direction = tree.getByRole("row", { name: /Direction technique/ });
  await direction.getByRole("button", { name: "Plier" }).click();
  await expect(tree.getByRole("row")).toHaveCount(3);
  await direction.getByRole("button", { name: "Déplier" }).click();
  await expect(tree.getByRole("row")).toHaveCount(6);
  await page
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Arbre d’organisation\u00a0»" })
    .fill("BE");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/role_sort_by=monthly_hours.*&org_search=BE$/, { timeout: WORKING });

  // The deactivated objects asked of the server, each offered to be reactivated.
  await page.getByRole("link", { name: "Afficher aussi les désactivés" }).click();
  await expect(page).toHaveURL(/include_inactive=true/, { timeout: WORKING });
  await expect(page.getByRole("link", { name: "Masquer les désactivés" })).toBeVisible();
  // The reactivation is a server action, which carries the role: its answer awaited, from before
  // the click.
  const reactivated = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.request().headers()["next-action"] !== undefined &&
      (response.request().postData() ?? "").includes(AUTOMATION),
  );
  await roles.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }).click();
  expect((await reactivated).status()).toBe(200);
  await expect(
    roles.getByRole("button", { name: "Réactiver «\u00a0Automaticien\u00a0»" }),
  ).not.toHaveAttribute("aria-busy", "true");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  // The programmer of automata, under a node deactivated: its reactivation is unavailable, named
  // by its condition, and a press says it without asking anything (WF-REF-0080, WF-IHM-0090).
  const programmer = roles.getByRole("button", {
    name: "Réactiver «\u00a0Programmeur d'automates\u00a0»",
  });
  await expect(programmer).toHaveAttribute("aria-disabled", "true");
  await expect(programmer).toHaveAccessibleDescription(
    "Condition non remplie : nœud d’organisation actif.",
  );
  // Playwright clicks no button marked unavailable: the press is dispatched as a pointer would.
  await programmer.dispatchEvent("click");
  await expect(
    page
      .getByRole("region", { name: "Rôles de ressources" })
      .getByRole("status")
      .filter({ hasText: "indisponible" }),
  ).toHaveText(
    "La réactivation de «\u00a0Programmeur d'automates\u00a0» est indisponible. Condition non remplie\u00a0: nœud d’organisation actif.",
  );
});

test("sorts the grid of the hourly rates by the rate of a year, filters the categories and the roles, and bounds the rates and the hours of the roles by the server [WF-IHM-0060-A] [WF-IHM-0130-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/costs");
  const rates = page.getByRole("grid", { name: "Grille des taux horaires" });
  // A year's header asks the server for its sort, under the names of the contract.
  await sortUntilAddress(
    rates.getByRole("columnheader", { name: "2026", exact: true }),
    rates,
    "/reference/costs?sort_by=rate.2026&sort_order=asc",
  );
  // The categories filtered by nature, under the names of their grid, the sort of the rates kept:
  // the nature shows chosen at once, and the address carries it once the server has read the
  // screen anew — its three dense grids, in the bound of a grid (`WORKING`).
  const nature = page.getByRole("combobox", { name: "Nature" });
  await nature.selectOption({ label: "MO · Main-d'œuvre" });
  await expect(nature).toHaveValue("01926f3a-7c00-7000-8000-000000000461");
  await expect(page).toHaveURL(
    /sort_by=rate\.2026&sort_order=asc&category_cost_type_id=01926f3a-7c00-7000-8000-000000000461$/,
    { timeout: WORKING },
  );
  // The rate of a year between bounds, under the names of the contract (#545), the rest kept.
  const rateBounds = page.getByRole("form", {
    name: "Bornes de «\u00a0Grille des taux horaires\u00a0»",
  });
  await rateBounds.getByRole("combobox", { name: "Année du taux" }).selectOption("2026");
  await rateBounds.getByRole("textbox", { name: "Taux horaire, min." }).fill("110,5");
  await rateBounds.getByRole("button", { name: "Filtrer" }).click();
  await expect(page).toHaveURL(/category_cost_type_id=[\w-]+&rate_min=110\.5&rate_year=2026$/, {
    timeout: WORKING,
  });

  // The roles filtered by calendar, back to their first page. No project is opened here, nothing
  // witnesses the hydration: the calendar is chosen again until React answers — until the
  // navigation it asks leaves —, and never once it has: chosen anew, the list would ask again,
  // and each navigation would replace the one before. A choice made before the hydration stays in
  // the list, which React then takes for none: the list is emptied first.
  await page.goto("/reference/resources?role_offset=50");
  const calendar = page.getByRole("combobox", { name: "Calendrier" });
  const standard = "01926f3a-7c00-7000-8000-000000000481";
  await expect(async () => {
    await Promise.all([
      page.waitForRequest((request) => request.url().includes(`role_calendar_id=${standard}`), {
        timeout: 1_000,
      }),
      (async () => {
        await calendar.selectOption("");
        await calendar.selectOption({ label: "Semaine standard" });
      })(),
    ]);
  }).toPass({ timeout: WORKING });
  await expect(calendar).toHaveValue(standard);
  await expect(page).toHaveURL(`/reference/resources?role_calendar_id=${standard}`, {
    timeout: WORKING,
  });
  // The monthly hours of the roles bounded, entered as French writes a number.
  const roleBounds = page.getByRole("form", {
    name: "Bornes de «\u00a0Rôles de ressources\u00a0»",
  });
  await roleBounds.getByRole("textbox", { name: "Heures par mois, min." }).fill("300 000");
  await roleBounds.getByRole("button", { name: "Filtrer" }).click();
  await expect(page).toHaveURL(
    "/reference/resources?role_calendar_id=01926f3a-7c00-7000-8000-000000000481&role_monthly_hours_min=300000",
    { timeout: WORKING },
  );
});
