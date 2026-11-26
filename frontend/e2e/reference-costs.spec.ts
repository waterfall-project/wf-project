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
 * not, those being served later (US-0850). In service the first path writes the rate of 2014 of
 * MO-003, a cell of its own: the first rate of a year refused with a conflict when another writer
 * enters it at the same time, the 2015 cell is written by the path of the category alone and the
 * 2013 cell by `service/reference-manager.spec.ts`, which no project orders (US-1890).
 *
 * The path of the deactivated failed the merge queue now and then (#3135), and not at an Escape:
 * its commands of a row were pressed again each second until the row answered, and the server
 * action answering past that second, a click pressed again then waited for the command its answer
 * had just taken away — or pressed the other one —, the state shared with no other path. Its
 * commands are now pressed until the request of their action is sent, and never after, by `pressOnce`
 * (#3252); it shows the deactivated ones by the filter of the state of each table, which replaced the
 * switch of the screen (US-2090, #3076, #3191). The path of
 * the deactivation of a nature failed for a cause of its own (#3190): it awaited the reactivation of
 * a row the page read anew had taken out of a list without the deactivated; in service it now reads
 * its nature alone, the deactivated shown. Neither failure was a state another path left, nor the
 * load of the API, which answered their writes within about a second (US-2060).
 */
import { expect, type Locator, type Page, type Request } from "@playwright/test";

import { RATE_PATH_IN_SERVICE, WORKING } from "./bounds";
import { openFilters, pick } from "./check-menu";
import { sortUntilAddress } from "./hydration";
import { inService, test } from "./mode";
import { rowAt, scroller, withinBox } from "./scroll";
import {
  answerOf,
  isDeactivation,
  isReactivation,
  isServerAction,
  pressOnce,
} from "./server-action";

/**
 * A command of a row pressed once (`pressOnce`), its action answered (`answerOf`), and no command of
 * the page busy any more (`aria-busy`) before the state of the row is affirmed: the answer puts the
 * opposite command in the place of the one pressed, and a state affirmed while the first still
 * waits is read at the wrong moment (#3448).
 */
async function pressSettled(
  page: Page,
  command: Locator,
  asked: (request: Request) => boolean,
): Promise<void> {
  const answer = await answerOf(await pressOnce(page, command, asked));
  expect(answer.ok()).toBe(true);
  await expect(page.getByRole("main").locator('button[aria-busy="true"]')).toHaveCount(0, {
    timeout: WORKING,
  });
}

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
/**
 * The cell the first path writes in the row of MO-003, counted from its code: the code, the label,
 * the state, then 2012 to 2015. The fake back answers the rate of 2015 (index 6) whatever the cell;
 * the service takes 2014 (index 5), which no other path writes.
 */
const RATE_CELL = inService ? 5 : 6;
/** The address that reads the grid of the rates by code, as the fake back serves it: the service has no other order. */
const BY_CODE = "/reference/costs?sort_by=code&sort_order=asc";

test("reads the settings of the costs outside any project with no mock-up notice, and enters a rate on the dense grid of the hourly rates, the service keeping it (US-0250) @shared [WF-REF-0050-A]", async ({
  page,
}) => {
  // The write redates revision 102 of PRJ-001 against the service (`RATE_PATH_IN_SERVICE`, #4911).
  if (inService) test.setTimeout(RATE_PATH_IN_SERVICE);
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

  // The first rate of the year of RATE_CELL of the third category, entered from the keyboard and
  // answered.
  // No project is opened here, nothing witnesses the hydration: the cell is clicked and the cursor
  // moved again until React answers them, each try starting from the code of the category.
  const mechanical = rowAt(grid, 3);
  const rate = mechanical.getByRole("gridcell").nth(RATE_CELL);
  await expect(async () => {
    await mechanical.getByRole("gridcell", { name: "MO-003" }).click();
    for (let step = 0; step < RATE_CELL; step += 1) {
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
  await expect(rowAt(grid, 4).getByRole("gridcell").nth(RATE_CELL)).toBeFocused();

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
        .nth(RATE_CELL),
    ).toHaveText(ENTERED, { timeout: WORKING });
  }
});

test("reads the settings of the resources, the risks and the indicators outside any project, every state of the roles asked (US-0250)", async ({
  page,
}) => {
  // Every state of the roles asked, their chip lifted: the automation engineer, deactivated, is
  // among them only then (WF-REF-0150), whatever the fake back answers without the parameter.
  await page.goto("/reference/resources?role_is_active=all");
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
    // The filters of the rates come with their grid, in the panel of its bar (#2916).
    await openFilters(page, page.getByRole("region", { name: "Taux horaires" }));
    await expect(
      page.getByRole("form", { name: "Bornes de «\u00a0Grille des taux horaires\u00a0»" }),
    ).toHaveCount(1);
  });
}

/** The box of an element in the page, measured. */
async function box(element: Locator) {
  const measured = await element.boundingBox();
  if (measured === null) {
    throw new Error("the element is not laid out");
  }
  return {
    ...measured,
    right: measured.x + measured.width,
    middle: measured.y + measured.height / 2,
  };
}

for (const { width, height } of WINDOWS) {
  test(`sets each section in its card, the creation of a list filled at the right of the title of its card, and the column of a year filled at the right end of the bar of the rates, at ${String(width)} points (#3071) @shared [WF-IHM-0060-A]`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await page.goto("/reference/costs");
    await expect(page.getByRole("grid", { name: "Grille des taux horaires" })).toHaveAttribute(
      "aria-rowcount",
      ROW_COUNT,
    );
    const main = await box(page.getByRole("main"));
    for (const [title, creation] of [
      ["Natures de coût", "Nouvelle nature"],
      ["Catégories de coût", "Nouvelle catégorie"],
    ] as const) {
      const card = page.getByRole("region", { name: title, exact: true });
      const frame = await box(card);
      const heading = await box(card.getByRole("heading", { level: 2 }));
      const button = await box(card.getByRole("button", { name: creation }));
      const bar = await box(card.getByRole("searchbox"));
      // The card within the column of the screen; the creation at its right edge, inside its
      // padding, on the line of its title, above the bar of its table.
      expect(frame.x).toBeGreaterThanOrEqual(main.x - 1);
      expect(frame.right).toBeLessThanOrEqual(main.right + 1);
      expect(frame.right - button.right, `the creation of ${title}`).toBeLessThanOrEqual(32);
      expect(frame.right - button.right, `the creation of ${title}`).toBeGreaterThan(0);
      expect(button.x).toBeGreaterThan(heading.right);
      expect(Math.abs(button.middle - heading.middle), `the line of ${title}`).toBeLessThanOrEqual(
        8,
      );
      expect(button.y + button.height).toBeLessThanOrEqual(bar.y);
    }
    // The rates: no command at the right of the title; the column of a year at the end of the bar,
    // its button at the right edge of the bar, after « Colonnes », the year just before it — on
    // the line of « Colonnes », or wrapped whole under it when the line is too short, the search
    // never crushed —; then « Retirer la colonne » and the message of a year added before them.
    const rates = page.getByRole("region", { name: "Taux horaires", exact: true });
    const toolbar = rates.locator("[data-grid-toolbar]");
    const form = rates.getByRole("form", { name: "Ajouter une année à la grille" });
    const add = form.getByRole("button", { name: "Ajouter la colonne" });
    const year = form.getByRole("textbox", { name: "Année" });
    await expect(rates.getByRole("heading", { level: 2 })).toBeVisible();
    const card = await box(rates);
    const expectEnding = async () => {
      const bar = await box(toolbar);
      const button = await box(add);
      const field = await box(year);
      const columns = await box(toolbar.getByRole("button", { name: /^Colonnes/ }));
      const search = await box(toolbar.getByRole("searchbox"));
      expect(
        Math.abs(bar.right - button.right),
        "the button at the end of the bar",
      ).toBeLessThanOrEqual(1);
      expect(bar.right, "the bar within its card").toBeLessThanOrEqual(card.right);
      expect(field.right).toBeLessThanOrEqual(button.x);
      expect(
        Math.abs(field.middle - button.middle),
        "the year on the line of its button",
      ).toBeLessThanOrEqual(2);
      // The end of the bar, beside « Colonnes » or wrapped whole under it: never over it.
      const end = await box(toolbar.locator('[data-slot="bar-ending"]'));
      expect(
        end.x > columns.right || end.y >= columns.y + columns.height,
        "the end of the bar after « Colonnes »",
      ).toBe(true);
      expect(field.x).toBeGreaterThanOrEqual(end.x);
      expect(search.width, "the search kept its width").toBeGreaterThanOrEqual(150);
      return { field, button, columns };
    };
    const before = await expectEnding();
    // The page scrolls: the card of the rates brought to the top of the window, its bar — « Ajouter
    // la colonne » among it, on two lines at 911 points — is whole in the window; brought to its
    // bottom, its pages are, inside the card.
    await rates.evaluate((element) => {
      element.scrollIntoView({ block: "start" });
    });
    await expect(toolbar).toBeInViewport({ ratio: 1 });
    await expect(add).toBeInViewport({ ratio: 1 });
    const pages = rates.getByRole("navigation");
    await rates.evaluate((element) => {
      element.scrollIntoView({ block: "end" });
    });
    await expect(pages).toBeInViewport({ ratio: 1 });
    const bottom = await box(pages);
    const frame = await box(rates);
    expect(bottom.y + bottom.height, "the pages within their card").toBeLessThanOrEqual(
      frame.y + frame.height,
    );
    if (width === 1366) {
      expect(
        Math.abs(before.button.middle - before.columns.middle),
        "on the line of « Colonnes »",
      ).toBeLessThanOrEqual(2);
    }
    // A year added: its message and « Retirer la colonne » come before the year, in the bar.
    await expect(async () => {
      await year.fill("2027");
      await add.click();
      await expect(form.getByRole("button", { name: "Retirer la colonne 2027" })).toHaveCount(1, {
        timeout: 1_000,
      });
    }).toPass({ timeout: WORKING });
    const after = await expectEnding();
    const remove = await box(form.getByRole("button", { name: "Retirer la colonne 2027" }));
    const said = await box(form.getByRole("status"));
    expect(remove.right <= after.field.x || remove.y + remove.height <= after.field.y).toBe(true);
    expect(said.y).toBeLessThanOrEqual(remove.y);
    expect(said.right).toBeLessThanOrEqual(card.right);
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
  await openFilters(page, page.getByRole("region", { name: "Catégories de coût" }));
  const nature = page.getByRole("combobox", { name: "Nature" });
  await nature.selectOption({ label: "MO · Main-d'œuvre" });
  await expect(nature).toHaveValue("01926f3a-7c00-7000-8000-000000000461");
  await expect(page).toHaveURL(
    /sort_by=rate\.2026&sort_order=asc&category_cost_type_id=01926f3a-7c00-7000-8000-000000000461$/,
    { timeout: WORKING },
  );
  // The rate of a year between bounds, under the names of the contract (#545), the rest kept.
  await openFilters(page, page.getByRole("region", { name: "Taux horaires" }));
  const rateBounds = page.getByRole("form", {
    name: "Bornes de «\u00a0Grille des taux horaires\u00a0»",
  });
  await rateBounds.getByRole("combobox", { name: "Année du taux" }).selectOption("2026");
  const rateLeast = rateBounds.getByRole("textbox", { name: "Taux horaire, du" });
  await rateLeast.fill("110,5");
  await rateLeast.press("Enter");
  await expect(page).toHaveURL(/category_cost_type_id=[\w-]+&rate_min=110\.5&rate_year=2026$/, {
    timeout: WORKING,
  });
});

// The roles are read on `/reference/resources`, served since US-0850: the path asserts addresses
// alone, with the identifiers of the witness, which the fixtures hold; it writes nothing.
test("filters the roles by calendar, bounds their monthly hours and filters their code by the server [WF-IHM-0060-A] [WF-IHM-0130-A] @shared", async ({
  page,
}) => {
  test.slow();
  // The roles filtered by calendar, back to their first page. No project is opened here, nothing
  // witnesses the hydration: the calendar is chosen again until React answers — until the
  // navigation it asks leaves —, and never once it has: chosen anew, the list would ask again,
  // and each navigation would replace the one before. A choice made before the hydration stays in
  // the list, which React then takes for none: the list is emptied first.
  await page.goto("/reference/resources?role_offset=50");
  await openFilters(page, page.getByRole("region", { name: "Rôles de ressources" }));
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
  const hoursLeast = roleBounds.getByRole("textbox", { name: "Heures par mois, du" });
  await hoursLeast.fill("300 000");
  await hoursLeast.press("Enter");
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
  // of the witness is overwritten; in the fake back the first path enters the same rate in it. Answered by the
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
  // The service keeps the deactivation: the path deactivates a nature of its own, whose code no run
  // before holds, and leaves the others as they are. The fake back keeps nothing, and answers the
  // deactivation of its first nature, « Débours », whatever the row pressed.
  // In service the path reads its nature alone (`type_search`), every state shown (`all`): on the
  // list of the active ones alone the row of the nature deactivated left the grid as soon as the
  // page was read anew (`readAnew`), at once when Next applied the answer of the action with that
  // reading, and the reactivation it offers was then never seen — the failures of the queue of 2026-11-14, one
  // deactivation answered 200 and the grid read anew in less than two seconds (#3190).
  const suffix = String(Date.now() % 1_000_000);
  const code = `NE-${suffix}`;
  await page.goto(
    inService ? `/reference/costs?type_is_active=all&type_search=${code}` : "/reference/costs",
  );
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  let label = "Débours";
  if (inService) {
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
    await form.getByRole("textbox", { name: "Code", exact: true }).fill(code);
    await form.getByRole("textbox", { name: "Libellé" }).fill(label);
    await form.getByRole("combobox", { name: "Type" }).selectOption({ label: "Hors main-d’œuvre" });
    await form.getByRole("button", { name: "Créer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(natures.getByRole("row", { name: new RegExp(label) })).toHaveCount(1, {
      timeout: WORKING,
    });
  }
  // A nature deactivated from its row: the row shows what the server answers, deactivated and
  // offering its reactivation. The deactivation is pressed again until React takes it — its action
  // sent —, and never after: a press past it would wait for a command the answer has taken away, or
  // press the reactivation put in its place (#3135).
  const reactivation = natures.getByRole("button", { name: `Réactiver «\u00a0${label}\u00a0»` });
  await pressSettled(
    page,
    natures.getByRole("button", { name: `Désactiver «\u00a0${label}\u00a0»` }),
    isDeactivation,
  );
  await expect(reactivation).toBeVisible({ timeout: WORKING });
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

test("presents fixed the type of a nature whose category is employed, with its conditions — in service, those of the rates and of the roles alone —, and the deactivation of the nature of provision for risks available [WF-IHM-0090-A] @shared", async ({
  page,
}) => {
  await page.goto("/reference/costs");
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  // The rule of #578 withdrawn (EP-14/L42p), the last nature of provision deactivates as any other.
  const deactivation = natures.getByRole("button", { name: "Désactiver « Provision »" });
  await expect(deactivation).not.toHaveAttribute("aria-disabled", "true");

  // The type of the labour, whose categories the estimate employs, bear rates and serve roles, is
  // fixed with its conditions (EP-14/L42r). The service plays two of the three with certainty, those
  // of the rates and of the roles; the one of the estimates may be present or absent there, the
  // journeys of EP-07 writing labour lines into the shared installation in an order not fixed. The
  // fake back and the unit tests carry it.
  // Une commande momentanément impossible est présentée indisponible, avec la condition qui manque.
  // Its modification is opened from its row, pressed again until React opens it.
  const form = page.getByRole("dialog", { name: "Modifier « Main-d'œuvre »" });
  await expect(async () => {
    if (!(await form.isVisible())) {
      await natures
        .getByRole("button", { name: "Modifier « Main-d'œuvre »" })
        .click({ timeout: 1_000 });
    }
    await expect(form).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  const type = form.getByRole("textbox", { name: "Type" });
  await expect(type).toHaveAttribute("readonly", "");
  await expect(type).toHaveValue("Main-d’œuvre");
  // The conditions the service lacks are those of its data: the witness holds rates and roles of
  // resource attached to its categories (US-0850); whether an estimate employs a category of the
  // nature depends on the journeys already played, so that condition is optional in service.
  await expect(type).toHaveAccessibleDescription(
    inService
      ? /^Le type ne se modifie pas\. Conditions non remplies\s:\s(?:aucune catégorie de la nature employée, )?aucune catégorie de la nature portant un taux horaire et aucune catégorie de la nature rattachée à un rôle de ressource\.$/
      : /^Le type ne se modifie pas\. Conditions non remplies\s:\saucune catégorie de la nature employée, aucune catégorie de la nature portant un taux horaire et aucune catégorie de la nature rattachée à un rôle de ressource\.$/,
  );
  await expect(form.getByRole("combobox", { name: "Type" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(form).toBeHidden();
});

/**
 * What a command to delete is called: the settings of the costs offer none (WF-REF-0010-A). « Effacer
 * les filtres », which the chips of the filters of a table bring, lifts filters and deletes nothing.
 */
const DELETION = /supprim|effac(?!er les filtres)|delete/i;

test("shows the deactivated natures and categories by the filter of the state of each table and reactivates them, offers no deletion, proposes only the active natures to a category, and the nature again once reactivated, the category too, proposed to the form of a role (US-0880, US-2090) @shared [WF-REF-0010-A] [WF-REF-0150-A]", async ({
  page,
}) => {
  test.slow();
  const suffix = String(Date.now() % 1_000_000);
  const natureCode = `ND-${suffix}`;
  const categoryCode = `CD-${suffix}`;
  // The service keeps what is written: the path makes a nature and a category of its own, whose
  // codes no run before holds, and the grids of its account start from their defaults (`mode.ts`).
  // The fake back keeps nothing and ignores the state asked: it answers its example whatever the
  // address says, so what a read leaves out is asserted in service alone, and the commands against
  // the fake back are answered by its examples.
  const natureLabel = inService ? `Nature désactivable ${suffix}` : "Débours";
  const categoryLabel = `Catégorie désactivable ${suffix}`;
  const choice = inService ? `${natureCode} · ${natureLabel}` : "DEB · Débours";
  const naturesRegion = page.getByRole("region", { name: "Natures de coût" });
  const categoriesRegion = page.getByRole("region", { name: "Catégories de coût" });
  const natures = page.getByRole("grid", { name: "Natures de coût" });
  const categories = page.getByRole("grid", { name: "Catégories de coût" });
  const category = categories.getByRole("row", { name: new RegExp(categoryCode) });
  const nature = natures.getByRole("row", { name: new RegExp(natureLabel) });
  const form = page.getByRole("dialog", { name: "Nouvelle catégorie de coût" });
  const reactivation = natures.getByRole("button", {
    name: `Réactiver «\u00a0${natureLabel}\u00a0»`,
  });
  const deactivation = natures.getByRole("button", {
    name: `Désactiver «\u00a0${natureLabel}\u00a0»`,
  });
  const categoryReactivation = categories.getByRole("button", {
    name: `Réactiver «\u00a0${categoryLabel}\u00a0»`,
  });
  const categoryDeactivation = categories.getByRole("button", {
    name: `Désactiver «\u00a0${categoryLabel}\u00a0»`,
  });
  // The nature deactivated on its list of the active ones alone: its row offers the reactivation
  // until the page read anew leaves it out, at once or nearly (`readAnew`), and the region of the
  // list says the deactivation — what stays once the row is gone.
  const deactivated = reactivation
    .or(
      naturesRegion
        .getByRole("status")
        .filter({ hasText: `«\u00a0${natureLabel}\u00a0» désactivée.` }),
    )
    .first();
  /** The chip of the state of a table, as its filter says it. */
  const stateChip = (region: Locator, state: string) =>
    region.getByRole("listitem").filter({ hasText: new RegExp(`^État : ${state}`) });
  /** The command that lifts the chip of the state of a table. */
  const liftState = (region: Locator, state: string) =>
    region.getByRole("button", { name: `Retirer le filtre État : ${state}` });
  const natureChoice = form
    .getByRole("combobox", { name: "Nature" })
    .getByRole("option", { name: choice });
  /** A dialog opened by its command, pressed again until React opens it, and never once it is open. */
  const open = async (dialog: Locator, region: string, command: string) => {
    await expect(async () => {
      if (!(await dialog.isVisible())) {
        await page
          .getByRole("region", { name: region })
          .getByRole("button", { name: command })
          .click();
      }
      await expect(dialog).toBeVisible({ timeout: 1_000 });
    }).toPass({ timeout: WORKING });
  };

  await page.goto(`/reference/costs?category_search=${categoryCode}`);
  await expect(natures).toBeVisible({ timeout: WORKING });
  await expect(categories).toBeVisible();
  if (inService) {
    const creation = page.getByRole("dialog", { name: "Nouvelle nature de coût" });
    await open(creation, "Natures de coût", "Nouvelle nature");
    await creation.getByRole("textbox", { name: "Code", exact: true }).fill(natureCode);
    await creation.getByRole("textbox", { name: "Libellé" }).fill(natureLabel);
    await creation.getByRole("combobox", { name: "Type" }).selectOption({ label: "Main-d’œuvre" });
    await creation.getByRole("button", { name: "Créer" }).click();
    await expect(creation).toBeHidden({ timeout: WORKING });
    await expect(nature).toHaveCount(1, { timeout: WORKING });

    await open(form, "Catégories de coût", "Nouvelle catégorie");
    await form.getByRole("textbox", { name: "Code", exact: true }).fill(categoryCode);
    await form.getByRole("textbox", { name: "Libellé" }).fill(categoryLabel);
    await form.getByRole("combobox", { name: "Nature" }).selectOption({ label: choice });
    await form.getByRole("textbox", { name: "Code comptable" }).fill(`607${suffix}`);
    await form.getByRole("button", { name: "Créer" }).click();
    await expect(form).toBeHidden({ timeout: WORKING });
    await expect(category).toHaveCount(1, { timeout: WORKING });
  }

  try {
    // Each table opens on its active objects alone, which the chip of its state says (#3076).
    await expect(stateChip(naturesRegion, "Actifs \\(par défaut\\)")).toBeVisible();
    await expect(stateChip(categoriesRegion, "Actifs \\(par défaut\\)")).toBeVisible();
    await expect(page.getByRole("link", { name: "Afficher aussi les désactivés" })).toHaveCount(0);

    // The nature deactivated from its row: its categories go with it (WF-REF-0010-A). The command
    // is pressed until the request of its action leaves, and never after (#3135, #3252).
    await pressSettled(page, deactivation, isDeactivation);
    await expect(deactivated).toBeVisible({ timeout: WORKING });
    if (inService) {
      // A page read anew, the active ones alone, leaves both out.
      await page.goto(`/reference/costs?category_search=${categoryCode}`);
      await expect(natures).toBeVisible({ timeout: WORKING });
      await expect(categories).toBeVisible();
      await expect(nature).toHaveCount(0);
      await expect(category).toHaveCount(0);
    }

    // The deactivated natures alone, by the filter of the state of their table.
    await openFilters(page, naturesRegion);
    // The menu read by its accessible name, whose non-breaking spaces read as spaces.
    await pick(page, "État des objets de « Natures de coût »", "Désactivés", "radio");
    await expect(page).toHaveURL(/type_is_active=false/, { timeout: WORKING });
    await expect(stateChip(naturesRegion, "Désactivés")).toBeVisible();
    if (inService) {
      await expect(nature).toContainText("Désactivé", { timeout: WORKING });
      await expect(reactivation).toBeVisible();
      await expect(natures.getByRole("row", { name: /Main-d'œuvre/ })).toHaveCount(0);
    }
    // Every category, the chip of their state lifted: the one under the nature, deactivated with it,
    // names the nature it is employed under.
    await liftState(categoriesRegion, "Actifs (par défaut)").click();
    await expect(page).toHaveURL(/category_is_active=all/, { timeout: WORKING });
    await expect(stateChip(categoriesRegion, "")).toHaveCount(0);
    if (inService) {
      await expect(category).toContainText(natureLabel, { timeout: WORKING });
      await expect(category).toContainText("Désactivé");
      await expect(categoryReactivation).toBeVisible();
    }
    // No screen offers to delete an object: neither a button nor a link of the page says it —
    // « Effacer les filtres » lifts filters, and deletes nothing.
    await expect(page.getByRole("main").getByRole("button", { name: DELETION })).toHaveCount(0);
    await expect(page.getByRole("main").getByRole("link", { name: DELETION })).toHaveCount(0);
    await expect(page.getByRole("menuitem", { name: DELETION })).toHaveCount(0);

    if (inService) {
      // A deactivated nature is not among the choices of a category, whatever its table shows.
      await open(form, "Catégories de coût", "Nouvelle catégorie");
      await expect(natureChoice).toHaveCount(0);
      await page.keyboard.press("Escape");
      await expect(form).toBeHidden();

      // Every nature, the chip of their state lifted: kept with the grid for the account, the page
      // opened again without a state shows them so. The settings are written once the page shows
      // the address, after a pause: their request, told by the state it keeps, is awaited answered
      // before the page is left.
      const keeping = page.waitForRequest(
        (request) =>
          isServerAction(request) && (request.postData() ?? "").includes('"type_is_active":"all"'),
      );
      await liftState(naturesRegion, "Désactivés").click();
      await expect(page).toHaveURL(/type_is_active=all/, { timeout: WORKING });
      expect((await answerOf(await keeping)).ok()).toBe(true);
      await page.goto(`/reference/costs?category_search=${categoryCode}`);
      await expect(reactivation).toBeVisible({ timeout: WORKING });
      await expect(stateChip(naturesRegion, "")).toHaveCount(0);

      // Reactivated by its row: the row shows what the server answers, active again. The fake back
      // has no example of a reactivation: the service alone.
      await pressSettled(page, reactivation, isReactivation);
      await expect(deactivation).toBeVisible({ timeout: WORKING });
      await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
      // The category stays deactivated with the nature reactivated: its row is reactivated in turn
      // (WF-REF-0150-A), and the row shows it active again.
      await pressSettled(page, categoryReactivation, isReactivation);
      await expect(categoryDeactivation).toBeVisible({ timeout: WORKING });
      await expect(category).not.toContainText("Désactivé");
      await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
      // Proposed again: the page read anew, the nature is among the choices.
      await page.goto(`/reference/costs?category_search=${categoryCode}`);
      await expect(natures).toBeVisible({ timeout: WORKING });
      await expect(categories).toBeVisible();
      await open(form, "Catégories de coût", "Nouvelle catégorie");
      await expect(natureChoice).toHaveCount(1);
      await page.keyboard.press("Escape");
      await expect(form).toBeHidden();
      // The nature being of labour, the category is proposed to the form of a role.
      // The form offers the categories the page read with its lists: the form opens once that
      // reading is over, the grid of the roles shown — opened before, under the load of the
      // queue, it found no category reactivated (#3266).
      await page.goto("/reference/resources");
      await expect(page.getByRole("grid", { name: "Rôles de ressources" })).toBeVisible({
        timeout: WORKING,
      });
      const roleForm = page.getByRole("dialog", { name: "Nouveau rôle de ressource" });
      await open(roleForm, "Rôles de ressources", "Nouveau rôle");
      await expect(
        roleForm
          .getByRole("combobox", { name: "Catégorie de coût" })
          .getByRole("option", { name: `${categoryCode} · ${categoryLabel}` }),
      ).toHaveCount(1);
      await page.keyboard.press("Escape");
      await expect(roleForm).toBeHidden();
    }
  } finally {
    if (inService) {
      // The nature is left deactivated, as the other paths leave theirs, even on a failure: every
      // nature asked, whatever state the account keeps.
      await page.goto(`/reference/costs?category_search=${categoryCode}&type_is_active=all`);
      await expect(natures).toBeVisible({ timeout: WORKING });
      await expect(categories).toBeVisible();
      if (await deactivation.isVisible()) {
        await pressSettled(page, deactivation, isDeactivation);
        await expect(reactivation).toBeVisible({ timeout: WORKING });
      }
    }
  }
});
