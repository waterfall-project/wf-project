// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { rowAt, scroller, withinBox } from "./scroll";

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
  const mechanical = rowAt(grid, 3);
  await mechanical.getByRole("gridcell", { name: "MO-003" }).click();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const rate = mechanical.getByRole("gridcell").nth(5);
  await expect(rate).toBeFocused();
  await expect(rate).toHaveText("");
  // What is typed differs from what the fake back answers: the cell shows the answer.
  await page.keyboard.type("85");
  await page.keyboard.press("Enter");
  await expect(rate).not.toHaveAttribute("aria-busy", "true");
  await expect(rate).toHaveText("85,48");
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  await expect(rowAt(grid, 4).getByRole("gridcell").nth(5)).toBeFocused();

  // Beside it, the natures and the categories of cost.
  await expect(page.getByRole("table", { name: "Natures de coût" }).getByRole("row")).toHaveCount(
    4,
  );
  await expect(
    page.getByRole("table", { name: "Catégories de coût" }).getByRole("row", {
      name: "MO-001 Ingénierie électrique Main-d'œuvre 641001 Actif",
    }),
  ).toHaveCount(1);

  await page.goto("/reference/resources");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Paramètres de ressources");
  await expect(
    page.getByRole("table", { name: "Rôles de ressources" }).getByRole("row"),
  ).toHaveCount(4);
  await expect(page.getByRole("table", { name: "Calendriers" }).getByRole("row")).toHaveCount(3);

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
