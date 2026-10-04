// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/indicators`;

// The first series of a chart in the token `--chart-1`, as the browser resolves it in each mode.
const SERIES_LIGHT = "rgb(2, 112, 179)";
const SERIES_DARK = "rgb(17, 149, 225)";

test.use({ colorScheme: "light" });

test("draws the evolution of an index in SVG, an image described in a sentence, its values in a table [WF-IHM-0100-A]", async ({
  page,
}) => {
  await page.goto(SCREEN);
  await expect(page.getByRole("heading", { level: 1, name: "Indicateurs projets" })).toBeVisible();
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator("svg")).toBeVisible();
  // The thresholds of the reference, drawn by a series of their own.
  await expect(cost.locator("svg text", { hasText: "Seuil de vigilance" })).toBeAttached();
  await expect(cost.locator("svg text", { hasText: "Seuil d’alerte" })).toBeAttached();
  const figure = page.getByRole("figure", { name: "Évolution de l’indice de coût" });
  await figure.getByText("Valeurs du graphique").click();
  const row = figure.getByRole("row", { name: /^Projet entier Révision en cours/ });
  await row.scrollIntoViewIfNeeded();
  await expect(row).toBeInViewport();
  // The date of the evolution, under the caption of its figure.
  await expect(figure.getByText(/^Calculé le/)).toBeVisible();
});

test("paints its series with the tokens of the charter, drawn again when the account forces the dark mode", async ({
  page,
}) => {
  await page.goto(SCREEN);
  const cost = page.getByRole("img", { name: /^Courbes de l’indice de coût du projet/ });
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`).first()).toBeAttached();
  // The attribute the root layout sets for an account that chose `dark`.
  await page.locator("html").evaluate((html) => {
    html.setAttribute("data-theme", "dark");
  });
  await expect(cost.locator(`path[stroke="${SERIES_DARK}"]`).first()).toBeAttached();
  await expect(cost.locator(`path[stroke="${SERIES_LIGHT}"]`)).toHaveCount(0);
});
