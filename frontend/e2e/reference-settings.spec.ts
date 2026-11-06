// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screens of the settings of the risks and of the indicators (`/reference/risks`,
 * `/reference/indicators`): the risk matrix, the thresholds of the indices and the delay between two
 * reviews, against the fake back.
 */
import { expect, test } from "@playwright/test";

import { WORKING } from "./hydration";

test("modifies the risk matrix and the thresholds of the indices in their forms, a bound out of order refused before asking, the mock-up saying the fake back keeps nothing (EP-14/L43e) [WF-REF-0160-A] [WF-REF-0170-A] [WF-REF-0180-A]", async ({
  page,
}) => {
  test.slow();
  await page.goto("/reference/risks");
  await expect(page.getByRole("note")).toContainText("le service simulé ne conserve");

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
  await second.fill("25");
  await matrix
    .getByRole("group", { name: "Probabilité, niveau 1" })
    .getByRole("combobox", { name: "Gravité, niveau 4" })
    .selectOption({ label: "Alerte" });
  await matrix.getByRole("button", { name: "Enregistrer" }).click();
  await expect(matrix).toBeHidden({ timeout: WORKING });
  // The fake back answers the first example of the operation whatever was written — the thresholds
  // written by the other screen, the matrix as it was —, and the screen shows what it answered.
  await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
    "Matrice de risques enregistrée.",
  );
  await expect(
    page
      .getByRole("table", { name: "Bornes de la matrice de risques" })
      .getByRole("row", { name: "Probabilité 10 % 30 % 60 %" }),
  ).toHaveCount(1);
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
  await expect(
    page
      .getByRole("table", { name: "Seuils d’alerte des indices" })
      .getByRole("row", { name: "Indice de coût 0,95 0,85" }),
  ).toHaveCount(1);
  await expect(page.getByText("6 semaines")).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});
