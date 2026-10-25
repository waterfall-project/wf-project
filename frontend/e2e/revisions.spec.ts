// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import { openHydrated, WORKING } from "./hydration";

// The fake back serves the first example of each operation: the history of three revisions —
// the reference, the draft, the offer v1.0 —, the draft read whatever the address names, its
// structures, no rate update proposed for it, and the comparison of the offer to the
// reference. The screen of the revisions shows them all; the comparison proves the fake back
// serves `compareRevisions` — its path, `/revisions/comparison`, could be mistaken for a
// revision named `comparison`.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";

test("the revisions of a project, their comparison as the API renders it, its structures and the rates proposed [WF-ARC-0020-A]", async ({
  page,
}) => {
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
  await expect(deltas.getByRole("row").nth(1)).toContainText("3 300,00");
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

test("the comparison of the whole structure, 5 999 nodes, shows its grid with its marks under the bound of a screen of grid [WF-REV-0080-A]", async ({
  page,
}) => {
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
