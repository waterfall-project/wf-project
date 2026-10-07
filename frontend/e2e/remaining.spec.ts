// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { withinBox } from "./scroll";

// The fake back serves the first example of each read, whatever it asks: the structure of the
// volumes of §4.6.2 for the nodes — its lines show here whatever `progress` asks, where the service
// renders the lines of the tasks started alone; the page tests prove what the screen asks —, the
// indicators of the remaining to commit of the witness, and its Kanban on 3 June 2026. The journey
// reads the structure by marks the generator writes (`test_the_marks_the_journeys_read`): row 3, a
// task completed; row 22, started.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";

test("reads the remaining to commit of a revision: its indicators, its grid, the tasks not started on demand, and the Kanban without any percentage to enter [WF-RAE-0030-A]", async ({
  page,
}) => {
  // The Kanban, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/kanban`);
  await page.goto(`${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await expect(page).toHaveTitle(
    "Estimation du reste à engager · Modernisation du poste de commande — Waterfall",
  );

  // The indicators, dated, each figure as the server gives it, the coverage of the risks with them.
  const indicators = page.getByRole("region", { name: "Indicateurs du reste à engager" });
  await expect(indicators).toContainText(/Reste à engager\s*21\s534,56/);
  await expect(indicators).toContainText("Calculé le");
  await expect(indicators.getByRole("region", { name: "Couverture des risques" })).toHaveText(
    /Réserve pour risques\s*910,00\s*Provisions restantes\s*500,00\s*Coût des risques survenus\s*200,00\s*Écart de couverture\s*210,00/,
  );
  // Each sub-project in the zone the server classes it in, named, never by its colour alone.
  // The control station and the whole without sub-project over their budget, in alert — the
  // invoice of the studies beyond the latter —; the tests and commissioning nominal.
  await expect(indicators.getByRole("img", { name: "Alerte" })).toHaveCount(2);
  await expect(indicators.getByRole("img", { name: "Nominal" })).toHaveCount(1);

  // The grid, its amounts computed, its totals those of the answer, in the window.
  const grid = page.getByRole("grid", { name: "Grille de reste à engager" });
  for (const name of [
    "Libellé",
    "Avancement",
    "Fin",
    "Calculé Montant budgété",
    "Calculé Réestimé à la revue précédente",
    "Charge (h)",
    "Calculé Montant réestimé",
  ]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  const totals = grid.getByRole("gridcell", { name: /^Total — 1\s000 tâches, 5\s000 lignes$/ });
  expect(await withinBox(grid, totals)).toBe(true);
  await expect(
    grid.getByRole("row", { name: /^3 .*Préparation 1\.1\.1/ }).getByRole("img", {
      name: "Terminée",
    }),
  ).toBeVisible();
  await expect(
    grid.getByRole("row", { name: /^15 .*Revue 1\.1\.3/ }).getByRole("img", {
      name: "Démarrée",
    }),
  ).toBeVisible();
  // The revision in progress may be re-estimated: undo and redo are placed, not wired yet.
  await expect(page.getByRole("button", { name: "Annuler" })).toHaveAttribute(
    "aria-disabled",
    "true",
  );

  // The tasks not started, on demand: the address asks the server for them, the context kept.
  // The address changes once the screen has read the grid anew, a thousand tasks: the bound of
  // the screens of grids (#315), not the five seconds of an assertion.
  await page.getByRole("link", { name: "Montrer aussi les tâches non démarrées" }).click();
  await expect(page).toHaveURL(
    `${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}&progress=not_started%2Cstarted`,
    { timeout: 15_000 },
  );
  await expect(
    page.getByRole("link", { name: "Ne montrer que les tâches démarrées" }),
  ).toBeVisible();

  // The Kanban, in the same context: the tasks not started and those started, no figure to enter.
  await page.getByRole("link", { name: "Kanban — démarrage des tâches" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/kanban?subproject_id=${SUBPROJECT}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Kanban — démarrage des tâches");
  // Every task not started (#425), none signalled: the factory acceptance waits for the wiring.
  const notStarted = page.getByRole("region", { name: "Non démarrées" });
  await expect(notStarted.getByRole("listitem")).toHaveText([
    /^18\s*Jalon\s*Réception usine\s*Fin le 30\/06\/2026$/,
    /^20\s*Montage des armoires sur site\s*Fin le 18\/12\/2026$/,
    /^23\s*Mise en service\s*Fin le 01\/01\/2027$/,
  ]);
  const started = page.getByRole("region", { name: "Démarrées", exact: true });
  await expect(started.getByRole("listitem")).toHaveText([
    /^4\s*Pupitres opérateurs\s*Fin le 24\/04\/2026/,
    /^9\s*Câblage des armoires\s*Fin le 30\/06\/2026$/,
  ]);
  await expect(started.getByRole("img", { name: "Fin dépassée" })).toHaveCount(1);
  const main = page.getByRole("main");
  for (const role of ["textbox", "spinbutton", "slider", "button", "combobox"] as const) {
    await expect(main.getByRole(role)).toHaveCount(0);
  }
});
