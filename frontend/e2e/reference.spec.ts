// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { rowAt, withinBox } from "./scroll";

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
  await page.keyboard.type("85,48");
  await page.keyboard.press("Enter");
  await expect(rate).toHaveText("85,48");
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
