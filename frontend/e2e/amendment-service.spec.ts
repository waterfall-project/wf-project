// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page } from "@playwright/test";

import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";
import { type Seeded, seedPlanning } from "./planning-seed";
import { API } from "./service/realm";

// What the fake back cannot replay: it keeps nothing, so the amendment « Préparer un avenant » creates
// (the structure 213 of its example) is never listed, and « Abandonner l’avenant » and « Mettre à jour
// l’avenant » have no state to act on (#1363). The paths play against the service, on a project the
// run creates and writes, and are tagged `@shared`.
const SERVICE_ONLY = "the service keeps what is written, which the fake back does not";

/** The non-breaking space the banner puts inside the guillemets. */
const NBSP = "\u00a0";

/** The button of the banner that names the structure read. */
function named(page: Page, structure: string) {
  return page.getByRole("button", {
    name: `Changer de structure, «${NBSP}${structure}${NBSP}» lue`,
  });
}

/** Prepare an amendment from the revisions screen, as a user does, and return the address it opens. */
async function prepare(page: Page, seeded: Seeded, label: string): Promise<string> {
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Préparer un avenant" }).click();
  const form = commands.getByRole("form", { name: "Préparer un avenant" });
  await form.getByRole("textbox", { name: "Libellé de l’avenant" }).fill(label);
  await form.getByRole("button", { name: "Créer l’avenant" }).click();
  await expect(page).toHaveURL(/\/planning\?structure=[0-9a-f-]{36}$/, { timeout: WORKING });
  return page.url();
}

test("opens the amendment « Préparer un avenant » creates, names it in the banner, and abandons it back to the main structure @shared [US-2640] [WF-IHM-0020-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const seeded = await seedPlanning(page, browser, calls, manager, "Avenant ouvert");
    await prepare(page, seeded, "Avenant service");
    // The amendment is found by the service, listed, and its grid opens under its name (#1363).
    await expect(named(page, "Avenant service")).toBeVisible({ timeout: WORKING });
    await expect(page.getByRole("treegrid", { name: "Grille de planning" })).toBeVisible();
    // Up to date: it is merged, not updated, and abandoned.
    await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Mettre à jour l’avenant" })).toHaveCount(0);
    await page.getByRole("button", { name: "Abandonner l’avenant" }).click();
    const form = page.getByRole("form", { name: "Abandonner l’avenant" });
    await form.getByRole("button", { name: /Confirmer l’abandon/ }).click();
    await expect(page).not.toHaveURL(/structure=/, { timeout: WORKING });
    // The grid reads the main structure, the only one left: the banner names it, and offers no other
    // to choose. No count of tasks is asserted: it is what `seedPlanning` wrote, not what this proves.
    await expect(page.getByText(/Structure principale/).first()).toBeVisible({ timeout: WORKING });
    await expect(named(page, "Avenant service")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Abandonner l’avenant" })).toHaveCount(0);
  } finally {
    await calls.dispose();
  }
});

test("says an amendment in arrears is late, updates it from the report, and offers the merge once it is up to date @shared [US-2640] [WF-IHM-0110-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const seeded = await seedPlanning(page, browser, calls, manager, "Avenant retard");
    const amendment = await prepare(page, seeded, "Avenant en retard");
    // The main structure receives a task after the amendment was opened: the amendment is late.
    const written = await calls.post(
      `${API}/projects/${seeded.ids.project}/revisions/${seeded.ids.revision}/structures/${seeded.ids.structure}/nodes`,
      {
        headers: seeded.headers,
        data: {
          kind: "task",
          parent_id: null,
          task: { label: "Tâche reçue depuis", duration: { value: "1", unit: "d" } },
        },
      },
    );
    expect(written.status(), "POST nodes of the main structure").toBe(201);
    await openHydrated(page, amendment);
    await expect(page.getByRole("note").filter({ hasText: "est en retard" })).toBeVisible({
      timeout: WORKING,
    });
    await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toHaveCount(0);
    await page.getByRole("button", { name: "Mettre à jour l’avenant" }).click();
    const form = page.getByRole("form", { name: "Mettre à jour l’avenant" });
    await expect(form.getByRole("list", { name: "Écarts par changement" })).toContainText(
      "1 reportée comme ajout",
      { timeout: WORKING },
    );
    await expect(form.getByRole("table", { name: /écarts/i })).toContainText("Tâche reçue depuis");
    await form.getByRole("button", { name: "Confirmer la mise à jour" }).click();
    // Read anew: the amendment is up to date, and the merge is offered.
    await expect(page.getByRole("note").filter({ hasText: "est en retard" })).toHaveCount(0, {
      timeout: WORKING,
    });
    await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Mettre à jour l’avenant" })).toHaveCount(0);
    // Contractualised at last, against the service: the report read, the version name asked, the
    // merge handed to the worker and followed to its end, which marks the revision that carries it.
    await page.getByRole("button", { name: "Contractualiser l’avenant" }).click();
    const merge = page.getByRole("form", { name: "Contractualiser l’avenant" });
    await expect(merge.getByRole("list", { name: "Écarts par objet" })).toBeVisible({
      timeout: WORKING,
    });
    await merge.getByRole("textbox", { name: "Nom de version" }).fill("Avenant contractualisé");
    await merge.getByRole("button", { name: "Confirmer la fusion" }).click();
    await expect(merge).toHaveCount(0, { timeout: WORKING });
    // The worker ends: the screen tells the reference, and no more offers the merge of what is merged.
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: "« Avenant contractualisé » est la nouvelle révision de référence" }),
    ).toBeVisible({ timeout: WORKING });
    await expect(page.getByRole("button", { name: "Contractualiser l’avenant" })).toHaveCount(0);
  } finally {
    await calls.dispose();
  }
});
