// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { columnsOf } from "../columns";
import { idle, PHASE, seedEstimate } from "../estimate-seed";
import { WORKING } from "../bounds";
import { openHydrated } from "../hydration";
import { mark } from "../in-progress";
import { inService, test } from "../mode";
import { openRevision } from "../own-project";
import { rowAt } from "../scroll";

// The reading of the indicators (FBS-4.8) by the account « chef de projet » of the run, on a project
// it creates (WF-INTF-0010-A): priced in the grid of the estimate, its revision marked by the worker
// and designated as the reference, the code entered to take it In progress — the course of
// `pricing.spec.ts` — then the screen of the indicators of the revision, which reads the indicators
// the service serves for this project, not those of the witness. The fake back keeps nothing of the
// project it is asked to create (`context.spec.ts`), so the path plays against the service alone.

test("the project manager of the run reads the indicators of a project she creates, prices and takes In progress, its revision marked: the reference budget is the amount priced, the context the revision marked, nothing refused (FBS-4.8) [WF-INTF-0010-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the project it is asked to create");
  test.slow();
  const main = page.getByRole("main");

  // Priced: a quantity of 4 on the line at 1 000,00, the amount computed by the service.
  const seeded = await seedEstimate(
    page,
    browser,
    request,
    manager,
    "Indicateurs du chef de projet",
  );
  await openHydrated(page, seeded.estimate);
  const grid = page.getByRole("treegrid", { name: "Grille de devis" });
  const at = await columnsOf(grid, { quantity: "Qté", reference: "Montant (année de réf.)" });
  const summary = grid.getByRole("row", { name: new RegExp(`^1 .*${PHASE}`) });
  await rowAt(grid, 3).getByRole("gridcell").nth(at.quantity).click();
  await page.keyboard.press("F2");
  await page.getByRole("textbox", { name: "Qté" }).fill("4");
  await page.keyboard.press("Enter");
  await expect(summary.getByRole("gridcell").nth(at.reference)).toHaveText(/4\s000,00\s€/, {
    timeout: WORKING,
  });
  await idle(grid);

  // The revision marked by the worker, designated as the reference.
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
  await mark(page, "v1.0");
  const history = main.getByRole("table", { name: "Historique des révisions" });
  const designate = history
    .getByRole("row")
    .filter({ hasText: "v1.0" })
    .getByRole("button", { name: "Désigner comme référence" });
  await expect(designate).not.toHaveAttribute("aria-disabled", "true", { timeout: WORKING });
  await designate.click();
  await history.getByRole("button", { name: "Confirmer la désignation" }).click();
  await expect(history.getByRole("row").nth(1)).toContainText("Référence", { timeout: WORKING });

  // The code entered takes the project In progress.
  await openHydrated(page, `${seeded.own.path}/settings`);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", { name: /^Modifier/ });
  await identity
    .getByRole("textbox", { name: /^Code projet/ })
    .fill(`IND-${seeded.own.label.slice(-8).toUpperCase()}`);
  await identity.getByRole("button", { name: "Enregistrer" }).click();
  await expect(identity).toBeHidden({ timeout: WORKING });
  await openHydrated(page, `${seeded.own.path}/lifecycle`);
  await expect(
    main.getByRole("table", { name: "Historique des états" }).getByRole("row").last(),
  ).toContainText("En cours", { timeout: WORKING });

  // A revision opened and marked now, the project In progress: the marking keeps its indicators
  // (the one marked before the passage kept none, which the service refuses with a 409).
  await openRevision(page, seeded.own);
  const opened = /revision_id=([0-9a-f-]{36})$/.exec(page.url())?.[1] ?? "";
  expect(opened, "the address of the revision opened names it").toMatch(/^[0-9a-f-]{36}$/);
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${opened}`);
  await mark(page, "v1.1");

  // The indicators of the revision marked: served for this project, the reference budget the
  // amount priced, the context the revision marked, and no refusal said in place of the figures.
  await openHydrated(page, `${seeded.own.path}/revisions/${opened}/indicators`);
  await expect(page.getByRole("heading", { level: 1, name: "Indicateurs projets" })).toBeVisible({
    timeout: WORKING,
  });
  await expect(main.getByText("Indicateurs indisponibles")).toHaveCount(0);
  const budget = main
    .getByRole("term")
    .filter({ hasText: /^Budget de référence$/ })
    .first()
    .locator("..");
  await expect(budget.getByRole("definition")).toHaveText(/4\s000,00\s€/, { timeout: WORKING });
  const context = page.getByRole("region", { name: "Contexte de lecture" });
  await expect(context).toContainText("v1.1");
  await expect(context).toContainText("Marquée");
});
