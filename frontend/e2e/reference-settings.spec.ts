// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screens of the settings of the risks and of the indicators (`/reference/risks`,
 * `/reference/indicators`): the risk matrix, the thresholds of the indices and the delay between two
 * reviews, against the fake back and, tagged `@shared`, against the service.
 *
 * The fake back keeps nothing and answers the first example of the operation whatever was written:
 * against it, the journey asserts the answer it shows. In service (`inService`) the journey asserts
 * what the service kept, read anew after a reload; it writes values valid on every run, so it can be
 * replayed on the same installation.
 */
import { expect } from "@playwright/test";

import { WORKING } from "./hydration";
import { inService, test } from "./mode";

test("modifies the risk matrix and the thresholds of the indices in their forms, a bound out of order refused before asking, no mock-up notice, the service alone proving it kept them (US-0810/L2) @shared [WF-REF-0160-A] [WF-REF-0170-A] [WF-REF-0180-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/risks");
  await expect(page.getByRole("note")).toHaveCount(0);

  // No project is opened here, nothing witnesses the hydration: the command is pressed again until
  // React opens its form, and never once it is open.
  const matrix = page.getByRole("dialog", { name: "Modifier la matrice de risques" });
  await expect(async () => {
    if (!(await matrix.isVisible())) {
      await page.getByRole("button", { name: "Modifier la matrice de risques" }).click();
    }
    await expect(matrix).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  // Les six bornes sont saisissables et ordonnées : une borne sous la précédente est refusée.
  const second = matrix
    .getByRole("group", { name: "Bornes de probabilité (%)" })
    .getByRole("textbox", { name: "Deuxième borne" });
  await second.fill("5");
  await matrix.getByRole("button", { name: "Enregistrer" }).click();
  await expect(second).toBeFocused();
  await expect(second).toHaveAccessibleDescription(
    "Les bornes doivent être strictement croissantes.",
  );
  await second.fill("55");
  // The outer bounds are written too, so that the journey does not depend on the seeding.
  const bounds = matrix.getByRole("group", { name: "Bornes de probabilité (%)" });
  await bounds.getByRole("textbox", { name: "Première borne" }).fill("25");
  await bounds.getByRole("textbox", { name: "Troisième borne" }).fill("75");
  await matrix
    .getByRole("group", { name: "Probabilité, niveau 1" })
    .getByRole("combobox", { name: "Gravité, niveau 4" })
    .selectOption({ label: "Alerte" });
  await matrix.getByRole("button", { name: "Enregistrer" }).click();
  await expect(matrix).toBeHidden({ timeout: WORKING });
  await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
    "Matrice de risques enregistrée.",
  );
  // The fake back answers the first example of the operation whatever was written; the service
  // answers the bounds it kept, the second one as written, read anew after a reload.
  if (inService) {
    await page.reload();
  }
  await expect(
    page.getByRole("table", { name: "Bornes de la matrice de risques" }).getByRole("row", {
      name: inService ? "Probabilité 25 % 55 % 75 %" : "Probabilité 10 % 30 % 60 %",
    }),
  ).toHaveCount(1, { timeout: WORKING });
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  await page.goto("/reference/indicators");
  const thresholds = page.getByRole("dialog", { name: "Modifier les seuils et le délai" });
  await expect(async () => {
    if (!(await thresholds.isVisible())) {
      await page.getByRole("button", { name: "Modifier les seuils et le délai" }).click();
    }
    await expect(thresholds).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  // Les quatre seuils sont saisissables ; le délai est saisissable en semaines.
  for (const index of ["Indice de coût", "Indice de délai"]) {
    const group = thresholds.getByRole("group", { name: index });
    await group.getByRole("textbox", { name: "Seuil de vigilance" }).fill("0,95");
    await group.getByRole("textbox", { name: "Seuil d’alerte" }).fill("0,85");
  }
  await thresholds
    .getByRole("textbox", { name: "Délai maximal entre deux révisions marquées (semaines)" })
    .fill("6");
  await thresholds.getByRole("button", { name: "Enregistrer" }).click();
  await expect(thresholds).toBeHidden({ timeout: WORKING });
  await expect(page.getByRole("status").filter({ hasText: "enregistrés" })).toHaveText(
    "Seuils et délai enregistrés.",
  );
  if (inService) {
    await page.reload();
  }
  await expect(
    page
      .getByRole("table", { name: "Seuils d’alerte des indices" })
      .getByRole("row", { name: "Indice de coût 0,95 0,85" }),
  ).toHaveCount(1);
  await expect(page.getByText("6 semaines")).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});

test("offers no deletion on the settings of the risks and of the indicators, whose matrix and thresholds are constants to modify, not objects to deactivate (US-0880) @shared [WF-REF-0010-A]", async ({
  page,
}) => {
  for (const [address, table, modification] of [
    ["/reference/risks", "Bornes de la matrice de risques", "Modifier la matrice de risques"],
    ["/reference/indicators", "Seuils d’alerte des indices", "Modifier les seuils et le délai"],
  ] as const) {
    await page.goto(address);
    // The screen is read, its one command offered: nothing deactivates, nothing deletes.
    await expect(page.getByRole("table", { name: table })).toBeVisible();
    await expect(page.getByRole("button", { name: modification })).toBeVisible();
    const main = page.getByRole("main");
    await expect(main.getByRole("button", { name: /supprim|effac|delete/i })).toHaveCount(0);
    await expect(main.getByRole("link", { name: /supprim|effac|delete/i })).toHaveCount(0);
    await expect(main.getByRole("button", { name: /désactiv/i })).toHaveCount(0);
  }
});
