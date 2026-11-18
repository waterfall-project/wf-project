// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { columnsOf } from "./columns";
import { idle, PHASE, seedEstimate } from "./estimate-seed";
import { openHydrated } from "./hydration";
import { mark } from "./in-progress";
import { inService, test } from "./mode";
import { rowAt } from "./scroll";

// The definition of done of EP-07 (US-1570/L3), against the service: the account of the run, which
// holds « Chef de projet » beside « Manager », prices a project and takes it In progress (WF-INTF-0010-A,
// FBS-4.4). The project is made from the home, its revision opened, a phase, a task and a line
// written by the API (`seedEstimate`); the rest is the screens' — the quantity of the line entered
// in the grid of the estimate, the amount the service computes, the revision marked by the worker,
// designated as the reference, the code of the project entered. The fifty entries undone and
// redone are `undo.spec.ts`'s, the estimate exported and imported back without a difference
// `exchanges.spec.ts`'s: this path is the course that leads to En cours.

test("the project manager of the run prices a project — a quantity entered, its amount computed by the service — and takes it In progress: the revision marked, designated as the reference, the code entered @shared [WF-INTF-0010-A] [WF-CYC-0020-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the service computes the amounts and moves the project");
  test.slow();
  const main = page.getByRole("main");

  // Priced: the quantity of the line entered in the grid of the estimate, and the amount of the
  // line, which the front does not compute, read as the service answers it (FBS-4.4).
  const seeded = await seedEstimate(page, browser, request, manager, "Chiffrage complet");
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, { quantity: "Qté", reference: "Montant (année de réf.)" });
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${PHASE}`) });
  await expect(summary.getByRole("gridcell").nth(at.reference)).toHaveText(/1\s000,00\s€/, {
    timeout: WORKING,
  });
  await rowAt(grid, 3).getByRole("gridcell").nth(at.quantity).click();
  await page.keyboard.press("F2");
  await page.getByRole("textbox", { name: "Qté" }).fill("4");
  await page.keyboard.press("Enter");
  await expect(summary.getByRole("gridcell").nth(at.reference)).toHaveText(/4\s000,00\s€/, {
    timeout: WORKING,
  });
  await idle(grid);

  // In pricing: the next state names what the project lacks — the reference and the code.
  await openHydrated(page, `${seeded.own.path}/lifecycle`);
  const states = main.getByRole("table", { name: "Historique des états" });
  await expect(states.getByRole("row").last()).toContainText("Chiffrage");
  const next = main.getByRole("region", { name: "Prochain état" });
  await expect(next).toContainText("code projet renseigné");
  await expect(next).toContainText("révision de référence désignée");

  // The revision marked by the worker, then designated: the reference bears a task and a line.
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
  await mark(page, "v1.0");
  const history = main.getByRole("table", { name: "Historique des révisions" });
  const designate = history
    .getByRole("row")
    .filter({ hasText: "v1.0" })
    .getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
  await designate.click();
  // The confirmation unfolds in the cell of a table of ten columns: it stays in the window.
  const confirmation = history.getByRole("button", { name: "Confirmer la désignation" });
  await expect(confirmation).toBeInViewport({ ratio: 1 });
  await confirmation.click();
  await expect(history.getByRole("row").nth(1)).toContainText("Référence", { timeout: WORKING });

  // The code entered takes the project In progress, without another action.
  await openHydrated(page, `${seeded.own.path}/settings`);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", { name: /^Modifier/ });
  await identity
    .getByRole("textbox", { name: /^Code projet/ })
    .fill(`CHF-${seeded.own.label.slice(-8).toUpperCase()}`);
  await identity.getByRole("button", { name: "Enregistrer" }).click();
  await expect(identity).toBeHidden({ timeout: WORKING });
  await openHydrated(page, `${seeded.own.path}/lifecycle`);
  await expect(states.getByRole("row").last()).toContainText("En cours", { timeout: WORKING });

  // The reference keeps its amounts, read in the estimate of the revision marked, which no longer
  // takes an entry (WF-DEV-0050-A).
  await openHydrated(page, seeded.estimate);
  await expect(summary.getByRole("gridcell").nth(at.reference)).toHaveText(/4\s000,00\s€/, {
    timeout: WORKING,
  });
  await rowAt(grid, 3).getByRole("gridcell").nth(at.quantity).click();
  await page.keyboard.press("F2");
  await expect(page.getByRole("textbox", { name: "Qté" })).toHaveCount(0);
});
