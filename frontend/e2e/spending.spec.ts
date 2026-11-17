// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { compile } from "./compile";
import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const ESTIMATE = `/projects/${PROJECT}/revisions/${REVISION}/estimate`;
const SCREEN = `/projects/${PROJECT}/revisions/${REVISION}/spending`;
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";

test.use({ colorScheme: "light" });

test("leads from the estimate to the spending projection on the reference budget, drawn in stacked bars, its values in a table @shared [WF-DEV-0100-A] [WF-IHM-0130-A]", async ({
  page,
}) => {
  // Two bounds of a screen of grid (`WORKING`): the estimate of the witness, then the projection.
  test.slow();
  await compile(page.request, SCREEN);
  await openHydrated(page, `${ESTIMATE}?as_of=2026-03-16`);
  await page.getByRole("main").getByRole("link", { name: "Projection de dépenses" }).click();
  await expect(page).toHaveURL(`${SCREEN}?as_of=2026-03-16&basis=reference_budget`, {
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1, name: "Projection de dépenses" })).toBeVisible(
    { timeout: WORKING },
  );
  const region = page.getByRole("region", { name: "Projection de dépenses", exact: true });
  const figure = region.getByRole("figure", { name: "Dépenses par nature de coût et par mois" });
  await expect(
    figure.getByRole("img", { name: /^Barres empilées de la dépense/ }).locator("svg"),
  ).toBeVisible();
  // The values of the chart are read in a table [WF-IHM-0130-A].
  await figure.getByText("Valeurs du graphique").click();
  await expect(figure.getByRole("table").getByRole("columnheader")).toHaveText([
    "Nature de coût",
    "Mois",
    "Montant",
  ]);
});

test("asks the projection at the date of payment, the choice an address the context keeps @shared [WF-DEV-0100-A]", async ({
  page,
}) => {
  await openHydrated(page, `${SCREEN}?as_of=2026-03-16`);
  const region = page.getByRole("region", { name: "Projection de dépenses", exact: true });
  await expect(region.getByText(/^Base : /)).toBeVisible({ timeout: WORKING });
  await region.getByLabel("Date", { exact: true }).selectOption("true");
  await region.getByRole("button", { name: "Afficher" }).click();
  await expect(page).toHaveURL(new RegExp(`as_of=2026-03-16&.*payment_delays=true`), {
    timeout: WORKING,
  });
  await expect(region.getByText(/^Base : .*Date de paiement$/)).toBeVisible();
});

test("filters the projection by a subproject of the project, the choice an address the context keeps @shared [WF-DEV-0100-A]", async ({
  page,
}) => {
  // A refusal of the projection (409, 422) is not played here: the screen offers only the bases
  // the project admits, and a shared path is held to a contract that nothing refuses; the page
  // test proves each refusal on the examples of the contract.
  await openHydrated(page, `${SCREEN}?as_of=2026-03-16`);
  const region = page.getByRole("region", { name: "Projection de dépenses", exact: true });
  await expect(region.getByText(/^Base : /)).toBeVisible({ timeout: WORKING });
  await region.getByLabel("Sous-projet", { exact: true }).selectOption(SUBPROJECT);
  await region.getByRole("button", { name: "Afficher" }).click();
  await expect(page).toHaveURL(new RegExp(`as_of=2026-03-16&.*subproject_id=${SUBPROJECT}`), {
    timeout: WORKING,
  });
  await expect(region.getByText(/^Base : /)).toBeVisible();
  await expect(region.getByLabel("Sous-projet", { exact: true })).toHaveValue(SUBPROJECT);
  await expect(
    region.getByRole("figure", { name: "Dépenses par nature de coût et par mois" }),
  ).toBeVisible();
});

test("presents the grid of the projection under its chart, a tree from the cost type to the category with a column for each month, read only @shared [WF-DEV-0100-A]", async ({
  page,
}) => {
  await openHydrated(page, SCREEN);
  const chart = page.getByRole("figure", { name: "Dépenses par nature de coût et par mois" });
  const grid = page.getByRole("treegrid", {
    name: "Projection de dépenses par nature de coût et par catégorie",
  });
  await expect(grid).toBeVisible({ timeout: WORKING });
  const [above, below] = await Promise.all([chart.boundingBox(), grid.boundingBox()]);
  expect(below?.y ?? 0).toBeGreaterThan((above?.y ?? 0) + (above?.height ?? 0));
  await expect(grid.getByRole("row").nth(1)).toHaveAttribute("aria-level", "1");
  expect(await grid.getByRole("columnheader").count()).toBeGreaterThan(5);
  // Read only, with no choice of its own: the basis, the date and the subproject are the chart's.
  await expect(grid.getByRole("textbox")).toHaveCount(0);
  await expect(grid.getByRole("searchbox")).toHaveCount(0);
});
