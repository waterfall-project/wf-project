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
  const totals = grid.getByRole("gridcell", { name: "Taux horaires en EUR" });
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

  // Beside it, the natures and the categories of cost.
  await expect(page.getByRole("table", { name: "Natures de coût" }).getByRole("row")).toHaveCount(
    4,
  );
  await expect(
    page.getByRole("table", { name: "Catégories de coût" }).getByRole("row", {
      name: "MO-001 Ingénierie électrique Main-d'œuvre 641001 Actif",
    }),
  ).toHaveCount(1);

  // The deactivated objects asked too: the automation engineer, deactivated, is among the roles
  // only then (WF-REF-0150), whatever the fake back answers without the parameter.
  await page.goto("/reference/resources?include_inactive=true");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de ressources");
  // The header, the four roles, the totals; the header, the two calendars, the totals.
  await expect(
    page.getByRole("grid", { name: "Rôles de ressources" }).getByRole("row"),
  ).toHaveCount(6);
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

test("stacks the grid of the rates and the natures of cost in a narrow window, neither over the other (US-0250)", async ({
  page,
}) => {
  await page.setViewportSize({ width: 800, height: 720 });
  await page.goto("/reference/costs");
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  const totals = grid.getByRole("gridcell", { name: "Taux horaires en EUR" });
  // The page scrolls, not the screen: the foot of the box of the grid brought into the window
  // brings its totals.
  await scroller(grid).evaluate((element) => {
    element.scrollIntoView({ block: "end" });
  });
  await expect(totals).toBeInViewport();
  const natures = page.getByRole("table", { name: "Natures de coût" });
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
  await expect(page).toHaveURL(/role_sort_by=monthly_hours.*&org_search=BE$/);

  // The deactivated objects asked of the server, each offered to be reactivated.
  await page.getByRole("link", { name: "Afficher aussi les désactivés" }).click();
  await expect(page).toHaveURL(/include_inactive=true/);
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
  await expect(roles.getByRole("button", { name: /^Réactiver/ })).not.toHaveAttribute(
    "aria-busy",
    "true",
  );
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});
