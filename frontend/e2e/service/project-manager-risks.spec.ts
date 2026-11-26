// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { contractualise, prepare } from "../amendment-flow";
import { MARKING, WORKING } from "../bounds";
import { columnsOf } from "../columns";
import { openHydrated } from "../hydration";
import { inService, test } from "../mode";
import { addOwnTask, identifyRisk } from "../risk-seed";

// The management of the risks (FBS-4.6) by the account « chef de projet » of the run, on a project it
// creates (WF-INTF-0010-A, US-2650): a risk declared, its own estimate priced, the risk reviewed,
// declared occurred — the task of the worker followed to its success — then an amendment prepared
// and contractualised, which makes its revision the reference. The fake back keeps nothing of what
// is written (`risks-service.spec.ts`, `amendment-service.spec.ts`), so the path plays the service alone.

test("the project manager of the run declares a risk on a project she creates, prices its own estimate, reviews it, declares it occurred, then prepares an amendment and contractualises it: the merge makes its revision the reference (FBS-4.6) [WF-INTF-0010-A] [US-2650]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, "the fake back keeps nothing of what the path writes");
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    // Declared: the register of the current revision, and the own estimate the declaration leads to.
    const { seeded, risks, own } = await identifyRisk(
      page,
      browser,
      calls,
      manager,
      "Risques du chef de projet",
      "Fuite du toit",
    );
    const project = seeded.own.path;
    const revision = /\/revisions\/([0-9a-f-]{36})\/risks$/.exec(risks)?.[1];
    if (revision === undefined) {
      throw new Error(`the address of the register names no revision: ${risks}`);
    }

    // Priced: a task and a line under it, in the own estimate of the risk.
    await openHydrated(page, own);
    const grid = page.getByRole("treegrid", { name: "Grille de devis" });
    const idle = () => expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
    await addOwnTask(page, grid, "Bâche");
    await idle();
    const task = grid.getByRole("gridcell", { name: "Bâche" });
    await task.click();
    await task.click({ button: "right" });
    await page
      .getByRole("menu", { name: "Menu de la cellule" })
      .getByRole("menuitem", { name: "Insérer une ligne" })
      .click();
    const line = page.getByRole("dialog", { name: "Insérer une ligne" });
    await line.getByRole("combobox", { name: "Rôle ou catégorie" }).selectOption({
      label: "Matériel électrique",
    });
    await line.getByRole("textbox", { name: "Libellé" }).fill("Câbles");
    await line.getByRole("textbox", { name: "Quantité" }).fill("1");
    await line.getByRole("button", { name: "Créer" }).click();
    await expect(page.getByText("« Câbles » créée.")).toBeVisible({ timeout: WORKING });
    await idle();
    await expect(grid.getByRole("gridcell", { name: "Câbles" })).toBeVisible({
      timeout: WORKING,
    });
    // The unit disbursement entered, the amount of the line is the one the service computes from it.
    const at = await columnsOf(grid, {
      disbursement: "Débours unit.",
      reference: /Montant \(année de réf\.\)$/,
    });
    const cables = grid.getByRole("row", { name: /Câbles/ });
    const disbursement = cables.getByRole("gridcell").nth(at.disbursement);
    await disbursement.click();
    await page.keyboard.press("Enter");
    await page.keyboard.type("250");
    await page.keyboard.press("Enter");
    await idle();
    await expect(cables.getByRole("gridcell").nth(at.reference)).toHaveAccessibleName(
      /^Calculé 250,00\s€$/,
      { timeout: WORKING },
    );

    // Reviewed, then declared occurred, from its detail in the register.
    await openHydrated(page, risks);
    await page.getByRole("link", { name: "Fuite du toit" }).click();
    const detail = page.getByRole("region", { name: "Fuite du toit" });
    await detail.getByRole("button", { name: "Réexaminer" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Réexaminer" }).click();
    await expect(detail.getByRole("status").filter({ hasText: "réexaminé" })).toBeVisible({
      timeout: WORKING,
    });
    await detail.getByRole("button", { name: "Déclarer survenu" }).click();
    const declare = detail.getByRole("form", { name: "Déclarer survenu" });
    await expect(declare.getByRole("table", { name: /écarts/i })).toBeVisible({
      timeout: WORKING,
    });
    await declare.getByRole("button", { name: "Déclarer le risque survenu" }).click();
    await page.getByRole("button", { name: /^Tâches et messages/ }).click();
    const occurrence = page
      .getByRole("dialog", { name: "Tâches et messages" })
      .getByRole("region", { name: "Tâches de fond" })
      .getByRole("listitem")
      .filter({ hasText: "Survenance d’un risque « Fuite du toit »" });
    await expect(occurrence.getByText("Réussie")).toBeVisible({ timeout: MARKING });
    await occurrence.getByRole("button", { name: "Recharger l’écran" }).click();
    // Read anew, the risk is occurred: « Réexaminer » says why it is no longer offered.
    await expect(detail.getByRole("button", { name: "Réexaminer" })).toHaveAccessibleDescription(
      /risque non survenu/,
      { timeout: WORKING },
    );
    await expect(detail.getByRole("button", { name: "Déclarer survenu" })).toHaveAttribute(
      "aria-disabled",
      "true",
      { timeout: WORKING },
    );

    // An amendment prepared on the revision, then contractualised: the merge ends in the worker.
    await prepare(page, project, revision, "Avenant du chef de projet");
    await contractualise(page, "Avenant du chef de projet contractualisé");
  } finally {
    await calls.dispose();
  }
});
