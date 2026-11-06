// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the correspondence of the extraction of the actual costs
 * (`/reference/costs/actual-cost-mapping`, US-0870): a label entered for a column and saved whole,
 * against the fake back and, tagged `@shared`, against the service.
 */
import { expect } from "@playwright/test";

import { WORKING } from "./hydration";
import { inService, test } from "./mode";

const COLUMN = "Poste de la pièce";

test("enters a label for the optional column of the extraction and saves the correspondence whole, the service keeping it, with no mock-up notice (US-0870) @shared [WF-REF-0190-A]", async ({
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
  }
});
