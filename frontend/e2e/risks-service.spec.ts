// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { MARKING, WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { bringInProgress } from "./in-progress";
import { inService, test } from "./mode";
import { openRevision } from "./own-project";
import { seedPlanning } from "./planning-seed";

// What the fake back cannot replay: the success of a task of occurrence (#1830) — its exemples hold
// the queued task alone, and the contract is not given another — and the risk it then reads occurred.
// The path plays against the service, on a project the run creates and takes In progress.
const SERVICE_ONLY =
  "the service keeps what is written and runs the task, which the fake back does not";

test("declares a risk occurred against the service: the report, the task succeeded with its message, and the risk read occurred @shared [US-2640] [WF-RIS-0060-A] [WF-IHM-0020-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const seeded = await seedPlanning(page, browser, calls, manager, "Risque survenu");
    await bringInProgress(page, calls, seeded);
    // The reference is read-only: the risks are declared on the current revision, opened as a copy.
    await openRevision(page, seeded.own);
    const current = new URL(page.url()).searchParams.get("revision_id");
    const risks = `${seeded.own.path}/revisions/${current ?? ""}/risks`;
    await openHydrated(page, risks);
    // Identify a risk: its form, then its own estimate opens in the grid of the estimate.
    await page.getByRole("button", { name: "Identifier un risque" }).click();
    const identify = page.getByRole("dialog", { name: "Identifier un risque" });
    await identify.getByRole("textbox", { name: "Libellé" }).fill("Grue indisponible");
    await identify.getByRole("textbox", { name: "Probabilité (%)" }).fill("20");
    await identify.getByRole("combobox", { name: "Catégorie" }).selectOption({ index: 1 });
    await identify.getByRole("button", { name: "Créer" }).click();
    await expect(page).toHaveURL(/\/estimate\?.*structure=/, { timeout: WORKING });
    // The register lists it; its detail declares it occurred, from the report the service computed.
    await openHydrated(page, risks);
    await page.getByRole("link", { name: "Grue indisponible" }).click();
    const detail = page.getByRole("region", { name: "Grue indisponible" });
    await detail.getByRole("button", { name: "Déclarer survenu" }).click();
    const declare = detail.getByRole("form", { name: "Déclarer survenu" });
    await expect(declare.getByRole("table", { name: /écarts/i })).toBeVisible({
      timeout: WORKING,
    });
    await declare.getByRole("button", { name: "Déclarer le risque survenu" }).click();
    await expect(
      detail.getByText(/La survenance de « Grue indisponible » est confiée/),
    ).toBeVisible({ timeout: WORKING });
    // The task succeeded, the service says it, and the risk is read anew, occurred.
    await page.getByRole("button", { name: /^Tâches et messages/ }).click();
    const task = page
      .getByRole("dialog", { name: "Tâches et messages" })
      .getByRole("region", { name: "Tâches de fond" })
      .getByRole("listitem")
      .filter({ hasText: "Survenance d’un risque « Grue indisponible »" });
    await expect(task.getByText("Réussie")).toBeVisible({ timeout: MARKING });
    await task.getByRole("button", { name: "Recharger l’écran" }).click();
    // Read anew, the risk is occurred: no command of entry is offered, « Réexaminer » says why.
    await expect(detail.getByRole("button", { name: "Réexaminer" })).toHaveAccessibleDescription(
      /risque non survenu/,
      { timeout: WORKING },
    );
    await expect(detail.getByRole("button", { name: "Déclarer survenu" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  } finally {
    await calls.dispose();
  }
});
