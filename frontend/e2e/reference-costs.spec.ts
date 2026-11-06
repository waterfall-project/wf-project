// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the settings of the costs (`/reference/costs`): the natures, the categories and the
 * grid of the hourly rates, against the fake back and, for the paths tagged `@shared`, against the
 * service (US-0830).
 *
 * The fake back serves the first example of each read of the reference data — the grid of the
 * volumes, a hundred and fifty categories of labour over fifteen years, the natures, the
 * organisation, the roles and the calendars of the witness —, and the first example of
 * `setHourlyRate` whatever was written: the first rate of 2015 of the mechanical engineering of
 * level 1, the third row of the grid, which has none before 2016. What the screens ask of each is
 * proven by the tests of the pages and of the grid. The service keeps what is entered and answers
 * it: the rate shown after an entry is the one typed (`inService`), and the paths that write choose
 * their own cells — empty in the witness, or a rate they write the same each time — and their own
 * codes, for the installation to be played again. Every path that plays this screen alone is tagged
 * `@shared`; the one that plays the screens of the resources, the risks and the indicators too is
 * not, those being served later (US-0850).
 */
import { expect } from "@playwright/test";

import { sortUntilAddress, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { rowAt, scroller, withinBox } from "./scroll";

/** The rate typed in a cell, and what the cell then shows: the service answers what was typed. */
const TYPED = "85";
const ENTERED = inService ? "85,00 €" : "85,48 €";
/**
 * The categories of labour the grid of the rates holds in the answer it reads: the fake back
 * serves the hundred and fifty at once, whatever the size asked, and the service pages them by
 * fifty (the totals row, which counts all of them, says a hundred and fifty in both).
 */
const ROWS_READ = inService ? 50 : 150;
/** The rows of the grid then: those read, its header and its totals row. */
const ROW_COUNT = String(ROWS_READ + 2);
/** The address that reads the grid of the rates by code, as the fake back serves it: the service has no other order. */
const BY_CODE = "/reference/costs?sort_by=code&sort_order=asc";

test("reads the settings of the costs outside any project with no mock-up notice, and enters a rate on the dense grid of the hourly rates, the service keeping it (US-0250) @shared [WF-REF-0050-A]", async ({
  page,
}) => {
  await page.goto(BY_CODE);
  await expect(page).toHaveTitle("Paramètres de coûts — Waterfall");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de coûts");
  await expect(page.getByText("Montants exprimés en EUR")).toBeVisible();
  // The service keeps what is written: the screen no longer says the opposite.
  await expect(page.getByRole("note")).toHaveCount(0);

  // The grid of the rates: a row for each category of labour over fifteen years, its totals row at the foot.
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  await expect(grid).toHaveAttribute("aria-rowcount", ROW_COUNT);
  await expect(grid.getByRole("columnheader", { name: "2012", exact: true })).toBeVisible();
  await expect(grid.getByRole("columnheader", { name: "2026", exact: true })).toHaveCount(1);
  const totals = grid.getByRole("gridcell", { name: "150 catégories, taux horaires en EUR" });
  // Its totals row is in the grid; that it stays in view is proven by the stacked layout below.
  await expect(totals).toHaveCount(1);

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
  if (!inService) {
    // The fake back keeps nothing: the cell is empty. The service may hold the rate of a run before.
    await expect(rate).toHaveText("");
  }
  // What is typed differs from what the fake back answers: the cell shows the answer, which the
  // service makes the rate typed.
  await page.keyboard.type(TYPED);
  await page.keyboard.press("Enter");
  await expect(rate).not.toHaveAttribute("aria-busy", "true");
  await expect(rate).toHaveText(ENTERED);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  await expect(rowAt(grid, 4).getByRole("gridcell").nth(6)).toBeFocused();

  // Beside it, the natures and the categories of cost, on the dense grid.
  await expect(page.getByRole("grid", { name: "Natures de coût" })).toBeVisible();
  const categories = page.getByRole("grid", { name: "Catégories de coût" });
  await expect(categories).toBeVisible();
  if (!inService) {
    // The fake back: the header, the three natures, the totals; the categories, of which the server
    // retains two hundred, by code as the list without sort gives them: the subcontracting first.
    await expect(page.getByRole("grid", { name: "Natures de coût" }).getByRole("row")).toHaveCount(
      5,
    );
    await expect(categories).toHaveAttribute("aria-rowcount", "202");
    await expect(rowAt(categories, 1)).toContainText("ACH-001Sous-traitance");
  } else {
    // The service kept the rate: the grid read anew shows it.
    await page.reload();
    await expect(
      rowAt(page.getByRole("grid", { name: "Grille des taux horaires" }), 3)
        .getByRole("gridcell")
        .nth(6),
    ).toHaveText(ENTERED, { timeout: WORKING });
  }
});

test("reads the settings of the resources, the risks and the indicators outside any project, the deactivated objects asked too (US-0250)", async ({
  page,
}) => {
  // The deactivated objects asked: the automation engineer, deactivated, is among the roles
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

const WINDOWS = [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
] as const;

for (const { width, height } of WINDOWS) {
  test(`stacks the natures, the categories and the hourly rates in a page that scrolls, each grid no taller than the window, at ${String(width)} points (US-0570) @shared`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/reference/costs");
    const natures = page.getByRole("grid", { name: "Natures de coût" });
    const categories = page.getByRole("grid", { name: "Catégories de coût" });
    const rates = page.getByRole("grid", { name: "Grille des taux horaires" });
    await expect(rates).toHaveAttribute("aria-rowcount", ROW_COUNT);
    // Where each grid's box starts and how tall it is, in the page, whatever the scroll.
    const placed = async (grid: typeof rates) =>
      scroller(grid).evaluate((element) => ({
        top: element.getBoundingClientRect().top + window.scrollY,
        height: element.getBoundingClientRect().height,
      }));
    const first = await placed(natures);
    const second = await placed(categories);
    const third = await placed(rates);
    // One under the other, in this order, none over the next.
    expect(first.top + first.height).toBeLessThanOrEqual(second.top);
    expect(second.top + second.height).toBeLessThanOrEqual(third.top);
    // The page scrolls; each grid keeps a height of its own, never past the window.
    for (const box of [first, second, third]) {
      expect(box.height).toBeLessThanOrEqual(height);
    }
    // The rates, a hundred and fifty rows, fill the window at most: their totals are one scroll away.
    await scroller(rates).evaluate((element) => {
      element.scrollIntoView({ block: "end" });
    });
    const totals = rates.getByRole("gridcell", { name: "150 catégories, taux horaires en EUR" });
    await expect(rates.getByRole("columnheader", { name: "Code", exact: true })).toBeInViewport();
    await scroller(rates).evaluate((element) => {
      element.scrollTop = element.scrollHeight;
    });
    await expect(totals).toBeInViewport();
    expect(await withinBox(rates, totals)).toBe(true);
    // The filters of the rates come with their grid, under its title.
    await expect(
      page.getByRole("form", { name: "Bornes de «\u00a0Grille des taux horaires\u00a0»" }),
    ).toHaveCount(1);
  });
}

test("adds the column of a year to the grid of the hourly rates, empty, and refuses a year the grid has, the grid alone judging it, against the service as against the fake back (#299) @shared [WF-REF-0060-A]", async ({
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
  await expect(first.locator('td[data-column="year_2026"]')).toHaveText("80,00 €");
  await year.fill("2026");
  await form.getByRole("button", { name: "Ajouter la colonne" }).click();
  await expect(form.getByRole("alert")).toHaveText(
    "L’année 2026 a déjà sa colonne dans la grille.",
  );
  await expect(grid.getByRole("columnheader", { name: "2026", exact: true })).toHaveCount(1);
});

test("sorts the grid of the hourly rates by the rate of a year, filters the categories, and bounds the rates by the server [WF-IHM-0060-A] [WF-IHM-0130-A] @shared", async ({
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
});

// Apart from the sort of the rates, which is tagged: the roles are read on `/reference/resources`,
// which the service does not serve yet (US-0850), so this path is played against the fake back only.
test("filters the roles by calendar, bounds their monthly hours and filters their code by the server [WF-IHM-0060-A] [WF-IHM-0130-A]", async ({
  page,
}) => {
  test.slow();
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
  // The code of the roles, filtered by the server under the name of their grid (EP-14/L42r).
  await page.getByRole("searchbox", { name: "Code du rôle" }).fill("AUT");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/role_monthly_hours_min=300000&role_code=AUT$/, {
    timeout: WORKING,
  });
});

test("creates a category and enters a rate beside it, the page read anew dropping neither, with no mock-up notice (EP-02/L43a, US-0830) @shared [WF-REF-0050-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto(BY_CODE);
  await expect(page.getByRole("note")).toHaveCount(0);
  // A code, an accounting code and a label no run before holds (the service holds the accounting
  // code once, 20 signs at most): it keeps the category, the fake back answers its example.
  const suffix = String(Date.now() % 1_000_000);
  const code = `FRN-${suffix}`;
  const label = inService ? `Petites fournitures ${suffix}` : "Petites fournitures";

  // A category created in its form. No project is opened here, nothing witnesses the hydration:
  // the creation is pressed again until React opens its form, and never once it is open.
  const categories = page.getByRole("region", { name: "Catégories de coût" });
  const form = page.getByRole("dialog", { name: "Nouvelle catégorie de coût" });
  await expect(async () => {
    if (!(await form.isVisible())) {
      await categories.getByRole("button", { name: "Nouvelle catégorie" }).click();
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await form.getByRole("textbox", { name: "Code", exact: true }).fill(code);
  await form.getByRole("textbox", { name: "Libellé" }).fill(label);
  await form.getByRole("combobox", { name: "Nature" }).selectOption({ label: "DEB · Débours" });
  await form.getByRole("textbox", { name: "Code comptable" }).fill(`606${suffix}`);
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toBeHidden({ timeout: WORKING });
  // The list says what the server created — its example —, and adds no row of its own.
  await expect(categories.getByRole("status").filter({ hasText: "créée" })).toHaveText(
    `«\u00a0${label}\u00a0» créée.`,
  );

  // A rate entered on the grid, in a cell the witness leaves empty (MO-003 holds none for 2015, the
  // cell of the example of `setHourlyRate`, which is where the fake back answers), so that no rate
  // of the witness is overwritten; the first path enters the same rate in it. Answered by the
  // service — by that example at the fake back. The page the creation read anew may arrive before the rate leaves, between its leaving and its answer, or
  // after it: the same address read anew drops neither the cell pending nor its answer (défaut
  // n° 22 de `typescript.md`), and the path does not depend on the order.
  const grid = page.getByRole("grid", { name: "Grille des taux horaires" });
  const mechanical = rowAt(grid, 3);
  // The code, the label, the state, then 2012 to 2015.
  const rate = mechanical.getByRole("gridcell").nth(6);
  await mechanical.getByRole("gridcell", { name: "MO-003" }).click();
  for (let step = 0; step < 6; step += 1) {
    await page.keyboard.press("ArrowRight");
  }
  await expect(rate).toBeFocused();
  await page.keyboard.type(TYPED);
  await page.keyboard.press("Enter");
  await expect(rate).toHaveText(ENTERED, { timeout: WORKING });
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("deactivates a nature from its row, the row showing what the service or the fake back answers, deactivated and offering its reactivation (EP-02/L43a) @shared [WF-REF-0030-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/costs");
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  // The service keeps the deactivation: the path deactivates a nature of its own, whose code no run
  // before holds, and leaves the others as they are. The fake back keeps nothing, and answers the
  // deactivation of its first nature, « Débours », whatever the row pressed.
  let label = "Débours";
  if (inService) {
    const suffix = String(Date.now() % 1_000_000);
    label = `Nature d’essai ${suffix}`;
    const form = page.getByRole("dialog", { name: "Nouvelle nature de coût" });
    const section = page.getByRole("region", { name: "Natures de coût" });
    // No project is opened here, nothing witnesses the hydration: the creation is pressed again
    // until React opens its form, and never once it is open.
    await expect(async () => {
      if (!(await form.isVisible())) {
        await section.getByRole("button", { name: "Nouvelle nature" }).click();
      }
      await expect(form).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: WORKING });
    await form.getByRole("textbox", { name: "Code", exact: true }).fill(`NE-${suffix}`);
    await form.getByRole("textbox", { name: "Libellé" }).fill(label);
    await form.getByRole("combobox", { name: "Type" }).selectOption({ label: "Hors main-d’œuvre" });
    await form.getByRole("button", { name: "Créer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(natures.getByRole("row", { name: new RegExp(label) })).toHaveCount(1, {
      timeout: WORKING,
    });
  }
  // A nature deactivated from its row: the row shows what the server answers, deactivated and
  // offering its reactivation. The deactivation is pressed again until React answers it, and never
  // once the row offers the reactivation.
  const reactivation = natures.getByRole("button", { name: `Réactiver «\u00a0${label}\u00a0»` });
  await expect(async () => {
    if (!(await reactivation.isVisible())) {
      await natures.getByRole("button", { name: `Désactiver «\u00a0${label}\u00a0»` }).click();
    }
    await expect(reactivation).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  if (inService) {
    await expect(natures.getByRole("row", { name: new RegExp(label) })).toContainText("Désactivé");
  } else {
    await expect(rowAt(natures, 1)).toContainText("Désactivé");
  }
  await expect(
    page
      .getByRole("region", { name: "Natures de coût" })
      .getByRole("status")
      .filter({ hasText: "désactivée" }),
  ).toHaveText(`«\u00a0${label}\u00a0» désactivée.`);
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("presents fixed the type of a nature whose category is employed, with its condition, and the deactivation of the nature of provision for risks available [WF-IHM-0090-A] @shared", async ({
  page,
}) => {
  await page.goto("/reference/costs");
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  // The rule of #578 withdrawn (EP-14/L42p), the last nature of provision deactivates as any other.
  const deactivation = natures.getByRole("button", { name: "Désactiver « Provision »" });
  await expect(deactivation).not.toHaveAttribute("aria-disabled", "true");

  // The type of the labour, whose categories the estimate employs, bear rates and serve roles, is
  // fixed with its conditions (EP-14/L42r):
  // Une commande momentanément impossible est présentée indisponible, avec la condition qui manque.
  // Its modification is opened from its row, pressed again until React opens it.
  const form = page.getByRole("dialog", { name: "Modifier « Main-d'œuvre »" });
  await expect(async () => {
    if (!(await form.isVisible())) {
      await natures.getByRole("button", { name: "Modifier « Main-d'œuvre »" }).click();
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  const type = form.getByRole("textbox", { name: "Type" });
  await expect(type).toHaveAttribute("readonly", "");
  await expect(type).toHaveValue("Main-d’œuvre");
  // The conditions the service lacks are those of its data: the witness holds rates and roles of
  // resource attached to its categories (US-0850), and no estimate employing a category of the nature.
  await expect(type).toHaveAccessibleDescription(
    inService
      ? /^Le type ne se modifie pas\. Conditions non remplies\s:\saucune catégorie de la nature portant un taux horaire et aucune catégorie de la nature rattachée à un rôle de ressource\.$/
      : /^Le type ne se modifie pas\. Conditions non remplies\s:\saucune catégorie de la nature employée, aucune catégorie de la nature portant un taux horaire et aucune catégorie de la nature rattachée à un rôle de ressource\.$/,
  );
  await expect(form.getByRole("combobox", { name: "Type" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(form).toBeHidden();
});
