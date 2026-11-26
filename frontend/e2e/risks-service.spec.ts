// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { MARKING, WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";
import { addOwnTask, identifyRisk } from "./risk-seed";

// What the fake back cannot replay: the success of a task of occurrence (#1830) — its exemples hold
// the queued task alone, and the contract is not given another — and the risk it then reads occurred.
// The path plays against the service, on a project the run creates and takes In progress.
const SERVICE_ONLY =
  "the service keeps what is written and runs the task, which the fake back does not";

test("writes the risk after a cell of its own estimate was entered and the detail found again in the same tab, with no stale version @shared [US-2640] [WF-RIS-0010-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const { risks, own } = await identifyRisk(
      page,
      browser,
      calls,
      manager,
      "Risque devis propre",
      "Fuite du toit",
    );
    // The detail of the risk, mounted from the register: the counter of the risk it reads is the
    // one the entry below will advance.
    await openHydrated(page, risks);
    await page.getByRole("link", { name: "Fuite du toit" }).click();
    const detail = page.getByRole("region", { name: "Fuite du toit" });
    await expect(detail.getByRole("button", { name: "Réexaminer" })).toBeVisible();
    // A first review, which advances the counter of the risk the detail holds.
    await detail.getByRole("button", { name: "Réexaminer" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Réexaminer" }).click();
    await expect(detail.getByRole("status").filter({ hasText: "réexaminé" })).toBeVisible({
      timeout: WORKING,
    });
    // Left for the own estimate in the same tab, by the links of the shell; a cell is entered.
    await page.getByRole("link", { name: "Chiffrage et devis", exact: true }).click();
    await expect(page).toHaveURL(/\/estimate/, { timeout: WORKING });
    // #1369: the structure of the own estimate of the risk created is listed, and opens (against the service).
    await page.getByRole("button", { name: /^Changer de structure/ }).click();
    await page.getByRole("menuitemradio", { name: /Fuite du toit/ }).click();
    await expect(page).toHaveURL(/structure=/, { timeout: WORKING });
    expect(page.url()).toBe(own);
    const grid = page.getByRole("treegrid", { name: "Grille de devis" });
    await expect(grid).toBeVisible({ timeout: WORKING });
    // A task entered in its own estimate, born whole (US-3070), is a write of the structure of the
    // risk, which advances the counter of the risk (#1626).
    await addOwnTask(page, grid, "Bâche");
    // Back to the detail in the same tab, without reloading the document: the commands read the risk
    // anew at their mount, and the second review is written from the counter the entry advanced
    // (#1626). The browser of this run reads the page anew on the way back by itself: the case proves
    // the journey holds, the unit tests (`risk-lifecycle.dom.test.tsx`) prove the reading.
    await page.goBack();
    await page.goBack();
    await expect(detail).toBeVisible({ timeout: WORKING });
    await detail.getByRole("button", { name: "Réexaminer" }).click();
    const review = page.getByRole("dialog", { name: /Réexaminer/ });
    await review.getByRole("button", { name: "Réexaminer" }).click();
    // The form closes on the answer; a refusal (412) would be told under it, and keep it open.
    await expect(review).toBeHidden({ timeout: WORKING });
    await expect(detail.getByRole("alert")).toHaveCount(0);
  } finally {
    await calls.dispose();
  }
});

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
    const { risks } = await identifyRisk(
      page,
      browser,
      calls,
      manager,
      "Risque survenu",
      "Grue indisponible",
    );
    // The register lists it; its detail declares it occurred, from the report the service computed.
    await openHydrated(page, risks);
    await page.getByRole("link", { name: "Grue indisponible" }).click();
    const detail = page.getByRole("region", { name: "Grue indisponible" });
    await detail.getByRole("button", { name: "Déclarer survenu" }).click();
    const declare = detail.getByRole("form", { name: "Déclarer survenu" });
    // Its own estimate, born whole, designates nothing (US-3070): the report says no difference,
    // the provision withdrawn alone (US-3100).
    await expect(
      declare.getByRole("region", { name: "Compte rendu de la survenance" }),
    ).toBeVisible({ timeout: WORKING });
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
    // The success of the task itself, in its message (#1830): the detail says the occurrence done.
    await expect(
      detail.getByText(
        "La survenance de « Grue indisponible » est terminée : son devis propre est fusionné dans la structure principale.",
      ),
    ).toBeVisible({ timeout: WORKING });
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
