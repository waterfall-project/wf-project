// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the correspondence of the extraction of the actual costs
 * (`/reference/costs/actual-cost-mapping`, US-0870): a label entered for a column and saved whole,
 * against the fake back and, tagged `@shared`, against the service.
 *
 * The fake back keeps nothing: against it, the journey asserts the saving only (the status). The
 * reading anew after a reload is asserted in service only (`inService`). The service keeps its
 * state, so the journey removes its label at the end and saves again: it can be replayed on the
 * same installation without reaching the limit of labels per column.
 */
import { expect } from "@playwright/test";

import { WORKING } from "./hydration";
import { inService, test } from "./mode";

const COLUMN = "Poste de la pièce";

test("enters a label for the optional column of the extraction and saves the correspondence whole, the service alone proving it kept it, with no mock-up notice (US-0870) @shared [WF-REF-0190-A]", async ({
  page,
}) => {
  test.slow();
  // A label no other holds, whatever the run left in the correspondence.
  const label = `Pos. pièce ${String(Date.now())}`;
  await page.goto("/reference/costs/actual-cost-mapping");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Correspondance des coûts réels",
  );
  await expect(page.getByRole("note")).toHaveCount(0);

  const labels = page.getByRole("group", { name: new RegExp(`^${COLUMN}`) }).getByRole("textbox");
  const before = await labels.count();
  // No project is opened here, nothing witnesses the hydration: the command is pressed again until
  // React adds the field, and never once it is added.
  await expect(async () => {
    if ((await labels.count()) === before) {
      await page.getByRole("button", { name: `Ajouter un intitulé à « ${COLUMN} »` }).click();
    }
    await expect(labels).toHaveCount(before + 1, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await labels.last().fill(label);
  await page.getByRole("button", { name: "Enregistrer la correspondance" }).click();
  await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
    "Correspondance enregistrée.",
  );
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);

  if (inService) {
    // The service kept it: a page read anew shows the label in its column.
    await page.goto("/reference/costs/actual-cost-mapping");
    await expect
      .poll(
        () =>
          labels.evaluateAll((fields) =>
            fields.map((field) => (field instanceof HTMLInputElement ? field.value : "")),
          ),
        { timeout: WORKING },
      )
      .toContain(label);
    // Leave the correspondence as found: the label removed, the correspondence saved again.
    const own = page.getByRole("group", { name: new RegExp(`^${COLUMN}`) });
    await own
      .getByRole("button", { name: /^Retirer l’intitulé/ })
      .last()
      .click();
    await page.getByRole("button", { name: "Enregistrer la correspondance" }).click();
    await expect(page.getByRole("status").filter({ hasText: "enregistrée" })).toHaveText(
      "Correspondance enregistrée.",
    );
    await expect(labels).toHaveCount(before);
  }
});

test("offers no deletion of an object on the correspondence of the extraction, which holds labels to enter and remove, not objects to deactivate (US-0880) @shared [WF-REF-0010-A]", async ({
  page,
}) => {
  await page.goto("/reference/costs/actual-cost-mapping");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Correspondance des coûts réels",
  );
  await expect(page.getByRole("button", { name: "Enregistrer la correspondance" })).toBeVisible();
  // The only removal is that of a label of a column, saved with the whole correspondence.
  const main = page.getByRole("main");
  await expect(main.getByRole("button", { name: /supprim|effac|delete/i })).toHaveCount(0);
  await expect(main.getByRole("link", { name: /supprim|effac|delete/i })).toHaveCount(0);
  await expect(main.getByRole("button", { name: /désactiv|réactiv/i })).toHaveCount(0);
});
