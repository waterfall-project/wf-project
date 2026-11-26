// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { WORKING } from "../bounds";
import { openHydrated } from "../hydration";
import { analyseActualCosts, applyReport, bringInProgress } from "../in-progress";
import { inService, test } from "../mode";
import { seedPlanning } from "../planning-seed";

// FLX-07 against the service, from the screen (WF-INTF-0140-A, #4699): the project manager of the
// run takes a project of her own In progress, then imports an extraction of actual costs in two
// steps — the file analysed, its report read before anything is applied, then the application
// confirmed and followed in the shell — and reads the lines on the screen of the actual costs. A
// second extraction, which overlaps the first, is imported as well: the line it repeats is counted
// once, the one whose amount changed is updated, a new one is added.

test("imports the actual costs in two steps from the screen of the exchanges, the report before the confirmation, then an overlapping extraction: a line repeated counted once, an amount updated, a line added, as the project manager of the run (FLX-07) [WF-INTF-0140-A] [WF-QUA-0050-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the extraction it is asked to import");
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const seeded = await seedPlanning(page, browser, calls, manager, "Coûts importés par l’écran");
    const code = await bringInProgress(page, calls, seeded);
    const costs = `${seeded.revision}/actual-costs`;
    const totals = page.getByRole("region", { name: "Totaux des lignes retenues" });
    const grid = page.getByRole("grid", { name: "Coûts réels" });
    const lines = grid.getByRole("row", { name: /FA-000\d/ });

    // The first extraction: two lines, read by the report before anything is applied.
    const first = "extraction-1.xlsx";
    const report = await analyseActualCosts(page, seeded.revision, first, [
      [code, "FA-0001", "2026-03-02", 1000],
      [code, "FA-0002", "2026-03-09", 250.5],
    ]);
    await expect(report.getByText("2 lignes lues.")).toBeVisible();
    await expect(report.getByRole("table", { name: "Lignes rejetées" })).toHaveCount(0);
    await applyReport(page, report, first);
    await openHydrated(page, costs);
    await expect(lines).toHaveCount(2, { timeout: WORKING });
    await expect(totals).toHaveText(
      /^Totaux des lignes retenues\s*Périmètre suivi\s*1\s250,50\s€\s*Exclu du périmètre suivi\s*0,00\s€\s*Total général\s*1\s250,50\s€/,
      { timeout: WORKING },
    );

    // The second extraction overlaps the first: FA-0001 is the same, FA-0002 changed in the ERP,
    // FA-0003 is new. Three lines read, one of them unchanged; the total counts FA-0001 once.
    const second = "extraction-2.xlsx";
    const overlap = await analyseActualCosts(page, seeded.revision, second, [
      [code, "FA-0001", "2026-03-02", 1000],
      [code, "FA-0002", "2026-03-09", 300],
      [code, "FA-0003", "2026-03-16", 100],
    ]);
    await expect(overlap.getByText("3 lignes lues.")).toBeVisible();
    await expect(overlap.getByText("Parmi elles, 1 est inchangée.")).toBeVisible();
    await applyReport(page, overlap, second);
    await openHydrated(page, costs);
    await expect(lines).toHaveCount(3, { timeout: WORKING });
    await expect(totals).toHaveText(
      /^Totaux des lignes retenues\s*Périmètre suivi\s*1\s400,00\s€\s*Exclu du périmètre suivi\s*0,00\s€\s*Total général\s*1\s400,00\s€/,
      { timeout: WORKING },
    );
  } finally {
    await calls.dispose();
  }
});
