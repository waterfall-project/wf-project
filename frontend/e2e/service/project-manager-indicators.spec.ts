// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { columnsOf } from "../columns";
import { idle, PHASE, seedEstimate, TASK } from "../estimate-seed";
import { PROJECT_MANAGER_PATH, WORKING } from "../bounds";
import { openHydrated } from "../hydration";
import { analyseActualCosts, applyReport, mark } from "../in-progress";
import { inService, test } from "../mode";
import { openRevision } from "../own-project";
import { rowAt } from "../scroll";

// The reading of the indicators (FBS-4.8) by the account « chef de projet » of the run, on a project
// it creates (WF-INTF-0010-A): priced in the grid of the estimate, its revision marked by the worker
// and designated as the reference, the code entered to take it In progress — the course of
// `pricing.spec.ts` — then the screen of the indicators of the revision, which reads the indicators
// the service serves for this project, not those of the witness. The fake back keeps nothing of the
// project it is asked to create (`context.spec.ts`), so the path plays against the service alone.

test("the project manager of the run reads the indicators of a project she creates, prices and takes In progress, its revision marked: the reference budget is the amount priced, the context the revision marked, nothing refused (FBS-4.8), after her planning entered and her actual costs imported (path of the project manager) [WF-INTF-0010-A] [WF-QUA-0050-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the project it is asked to create");
  test.setTimeout(PROJECT_MANAGER_PATH);
  const main = page.getByRole("main");

  // The project made and its nodes seeded, as a user starts one.
  const seeded = await seedEstimate(
    page,
    browser,
    request,
    manager,
    "Indicateurs du chef de projet",
  );
  // Planned: the duration of the task entered in the grid of the planning, the service keeping it.
  await openHydrated(page, seeded.planning);
  const plan = page.getByRole("treegrid", { name: "Grille de planning" });
  const during = await columnsOf(plan, { duration: "Durée" });
  const task = plan.getByRole("row", { name: new RegExp(`^2 .*${TASK}`) });
  await task.getByRole("gridcell").nth(during.duration).click();
  await page.keyboard.press("F2");
  await plan.getByRole("textbox", { name: "Durée" }).fill("8 j");
  await page.keyboard.press("Enter");
  await idle(plan);
  await expect(task.getByRole("gridcell").nth(during.duration)).toContainText("8", {
    timeout: WORKING,
  });

  // Priced: a quantity of 4 on the line at 1 000,00, the amount computed by the service.
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

  // The actual costs imported in two steps, the report read then the application confirmed, and
  // read on the screen of the actual costs (FLX-07, WF-INTF-0140-A).
  const code = `IND-${seeded.own.label.slice(-8).toUpperCase()}`;
  const extracted = "extraction-parcours.xlsx";
  const report = await analyseActualCosts(page, seeded.revision, extracted, [
    [code, "FA-0101", "2026-03-02", 1000],
    [code, "FA-0102", "2026-03-09", 250.5],
  ]);
  await expect(report.getByText("2 lignes lues.")).toBeVisible();
  await applyReport(page, report, extracted);
  await openHydrated(page, `${seeded.revision}/actual-costs`);
  await expect(page.getByRole("region", { name: "Totaux des lignes retenues" })).toContainText(
    /Périmètre suivi\s*1\s250,50\s€/,
    { timeout: WORKING },
  );

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
