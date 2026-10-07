// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

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
  await page.goto(`/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
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
  await main.getByRole("button", { name: "Comparer" }).click();
  await expect(page).toHaveURL(/from_revision_id=.+&to_revision_id=.+/);
  await expect(main.getByRole("table", { name: "Ajouts" }).getByRole("row")).toHaveCount(6);
  await expect(main.getByRole("table", { name: "Retraits" })).toContainText(
    "Essais préliminaires sur site",
  );
  await expect(main.getByRole("table", { name: "Modifications" })).toContainText(
    "Dossier de conception",
  );
  const deltas = main.getByRole("table", { name: "Écarts de montants" });
  await expect(deltas.getByRole("row")).toHaveCount(6);
  await expect(deltas.getByRole("row").nth(1)).toContainText("3 515,00");
});
