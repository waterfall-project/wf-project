// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the revisions of a project (`/projects/{id}/revisions`), against the fake back and,
 * tagged `@shared`, against the service, which serves the history, the revision and its structures
 * (US-0960).
 *
 * The fake back serves the first example of each operation: the history of three revisions —
 * the reference, the draft, the offer v1.0 —, the draft read whatever the address names, its
 * structures, no rate update proposed for it, and the comparison of the offer to the reference;
 * the comparison proves the fake back serves `compareRevisions` — its path,
 * `/revisions/comparison`, could be mistaken for a revision named `comparison`. The service serves
 * the witness, of which PRJ-001 holds the same three revisions, its 100 and 101 marked by the loader
 * as the worker marks (US-0970).
 */
import { readFileSync } from "node:fs";

import { expect } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

// The current revision is the first of the history: the fake back's, opened in 2026; the service's,
// the revision 102 of PRJ-001, whose reference year is that of the loading of the witness, not of
// the run of the test: a four-digit year only is asserted there.
const CURRENT_YEAR: string | RegExp = inService ? /^\d{4}$/ : "2026";

// What the service does not replay before EP-07, which serves the comparison and the rate update:
// skipped in it, as the guide lists (« Un parcours de bout en bout »).
const BEFORE_EP07 = "EP-07 serves the comparison and the rate update";

test("the history of the revisions of a project, each attribute of a revision in it, no note of the mock-up (US-0960) @shared [WF-REV-0070-A] [WF-REV-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/revisions`);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Gestion des révisions");
  await expect(main.getByRole("note")).toHaveCount(0);

  // Chacun de ces attributs est présent dans l’historique des révisions — the reference character
  // is the badge of the version, which the test of the page proves on the reference.
  const history = main.getByRole("table", { name: "Historique des révisions" });
  for (const column of ["Version", "État", "Marquée le", "Année de référence", "Description"]) {
    await expect(history.getByRole("columnheader", { name: column, exact: true })).toBeVisible();
  }
  const current = history.getByRole("row").nth(1);
  await expect(current).toContainText("Révision en cours");
  await expect(current).toContainText("En cours d’élaboration");
  await expect(current).toContainText("Non marquée");
  // The cell of the column « Année de référence » itself: the text of a row runs its cells together.
  const yearColumn = (await history.getByRole("columnheader").allTextContents()).indexOf(
    "Année de référence",
  );
  await expect(current.getByRole("cell").nth(yearColumn)).toHaveText(CURRENT_YEAR);
  // Three revisions, the current one and the two marked, on both sides.
  await expect(history.getByRole("row")).toHaveCount(4);
  await expect(
    current.getByRole("link", { name: "Ouvrir la révision «\u00a0Révision en cours\u00a0»" }),
  ).toBeVisible();
});

test("the revisions of a project, their comparison as the API renders it, its structures and the rates proposed @shared [WF-ARC-0020-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_EP07);
  // Les montants, dates et indices affichés sont ceux que l'API renvoie, sans recalcul.
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Gestion des révisions");

  // The history, in the order of the server, and the commands of the revision the address
  // carries.
  const history = main.getByRole("table", { name: "Historique des révisions" });
  await expect(history.getByRole("row")).toHaveCount(4);
  await expect(history.getByRole("row").nth(3)).toContainText("Offre v1.0");
  const commands = main.getByRole("region", { name: "Commandes" });
  await expect(commands.getByRole("button", { name: "Marquer la révision" })).toBeVisible();

  // The structures of the revision, and no rate update: the current revision, opened in 2026 as
  // the reference it copies, has none to propose (WF-REV-0060).
  await expect(main.getByRole("table", { name: "Structures de coûts" })).toContainText(
    "Structure principale",
  );
  await expect(main).toContainText("aucune mise à jour des taux n’est proposée");
  await expect(main.getByRole("table", { name: "Mise à jour des taux proposée" })).toHaveCount(0);

  // The comparison asked of the server: what it answers is shown, nothing paired by the front.
  // The example is a window, the sub-tree of « Installation sur site » (#1193), as its description
  // counts it: 2 nodes added, 2 removed, 2 lines re-estimated at the rates of 2026 (EP-14/L45a),
  // and 5 deviations — 3 natures of cost, 2 sub-projects —, each table with its header row. The
  // nodes come in the dense grid of the structures, each with the mark the server gives it, and
  // the screen keeps the bound of a screen of grid (`WORKING`): read unfiltered against the
  // service, the comparison is still the whole structure (#1201).
  await main.getByRole("button", { name: "Comparer" }).click();
  await expect(page).toHaveURL(/from_revision_id=.+&to_revision_id=.+/, { timeout: WORKING });
  const nodes = main.getByRole("grid", { name: "Nœuds comparés" });
  await expect(nodes.getByRole("row")).toHaveCount(11);
  await expect(nodes.getByRole("row", { name: /Assistance aux essais de câblage/ })).toContainText(
    "Ajouté",
  );
  await expect(nodes.getByRole("row", { name: /Essais préliminaires sur site/ })).toContainText(
    "Retiré",
  );
  const wiring = nodes.getByRole("row", { name: /Câblage sur site/ });
  await expect(wiring).toContainText("Modifié");
  await expect(wiring).toContainText("Montant réestimé");
  const deltas = main.getByRole("table", { name: "Écarts de montants" });
  await expect(deltas.getByRole("row")).toHaveCount(6);
  // Both deviations, each under the header that names it: budgeted 3 000,00, re-estimated 3 300,00.
  await expect(deltas.getByRole("columnheader", { name: "Écart budgété" })).toBeVisible();
  await expect(deltas.getByRole("columnheader", { name: "Écart réestimé" })).toBeVisible();
  await expect(deltas.getByRole("row").nth(1)).toContainText("3 000,00 €");
  await expect(deltas.getByRole("row").nth(1)).toContainText("3 300,00 €");
});

// The comparison of the volume: the project 300 is served the offer compared to the reference over
// the whole structure of the witness, 5 999 nodes read unfiltered, with `fields` reduced to what the
// screen shows (`comparison_volume`, #1201). The bound of 15 seconds of the criterion of US-0500 is
// proven on it: the grid is up with its marks, from the address opened, under `WORKING`.
const VOLUME_PROJECT = "01926f3a-7c00-7000-8000-000300000300";
const FROM = "01926f3a-7c00-7000-8000-000000000100";
const TO = "01926f3a-7c00-7000-8000-000000000101";
// The nodes of the example of the volume, the header and the totals besides making the rows.
const VOLUME_NODES = (
  JSON.parse(
    readFileSync(
      `${import.meta.dirname}/../../fixtures/api/volume/comparison_volume.json`,
      "utf-8",
    ),
  ) as { value: { items: unknown[] } }
).value.items.length;

test("the comparison of the whole structure, 5 999 nodes, shows its grid with its marks under the bound of a screen of grid @shared [WF-REV-0080-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_EP07);
  test.slow();
  const started = Date.now();
  await openHydrated(
    page,
    `/projects/${VOLUME_PROJECT}/revisions?from_revision_id=${FROM}&to_revision_id=${TO}`,
  );
  const nodes = page.getByRole("main").getByRole("grid", { name: "Nœuds comparés" });
  // The first rows of the plan, each with the mark the server gives it.
  await expect(nodes.getByRole("row", { name: /Études de détail/ })).toBeVisible({
    timeout: WORKING,
  });
  await expect(nodes.getByRole("row", { name: /Études$/ }).first()).toContainText("Modifié", {
    timeout: WORKING,
  });
  // The whole structure is the grid's, the rows drawn being those in view.
  await expect(nodes).toHaveAttribute("aria-rowcount", (VOLUME_NODES + 2).toString());
  const elapsed = Date.now() - started;
  test.info().annotations.push({ type: "duration", description: `${elapsed.toString()} ms` });
  expect(elapsed).toBeLessThan(WORKING);
});

test("retains the differences alone in the comparison: pressed, in the address and the banner, kept through the choice of the pair @shared [WF-REV-0080-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_EP07);
  // The fake back serves the same comparison whatever the address names: what the server retains is
  // proven on `comparison_differences` by the test of the page (`revisions/page.test.tsx`).
  await openHydrated(
    page,
    `/projects/${PROJECT}/revisions?revision_id=${REVISION}&from_revision_id=${FROM}&to_revision_id=${TO}`,
  );
  const main = page.getByRole("main");
  const only = main.getByRole("button", { name: "Écarts seulement" });
  await expect(only).toHaveAttribute("aria-pressed", "false");
  await only.click();
  await expect(page).toHaveURL(/difference=added%2Cremoved%2Cmodified/, { timeout: WORKING });
  await expect(only).toHaveAttribute("aria-pressed", "true");
  const filters = page.getByRole("list", { name: "Filtres actifs" });
  await expect(filters).toContainText("Écarts seulement");
  await expect(main.getByRole("grid", { name: "Nœuds comparés" })).toBeVisible();
  // The choice of the pair carries the filter on.
  await main.getByRole("button", { name: "Comparer" }).click();
  await expect(page).toHaveURL(/difference=added/, { timeout: WORKING });
  await filters.getByRole("link", { name: /Lever le filtre/ }).click();
  await expect(page).not.toHaveURL(/difference=/, { timeout: WORKING });
  await expect(only).toHaveAttribute("aria-pressed", "false");
});
