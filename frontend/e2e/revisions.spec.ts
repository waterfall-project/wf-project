// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the revisions of a project (`/projects/{id}/revisions`), against the fake back and,
 * tagged `@shared`, against the service, which serves the history, the revision and its commands
 * (US-0960). The screen holds the history and the commands of the revision read, no comparison
 * (US-2370): « Comparer à la révision lue » leads a marked revision of the history to the grid
 * chosen, that revision as its base. The comparison itself is played on the grids (US-2380).
 *
 * The fake back serves the first example of each operation: the history of three revisions —
 * the reference, the draft, the offer v1.0 —, the draft read whatever the address names, its
 * structures, and no rate update proposed for it. The service serves the witness, of which PRJ-001
 * holds the same three revisions, its 100 and 101 marked by the loader as the worker marks
 * (US-0970).
 */
import { expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const FROM = "01926f3a-7c00-7000-8000-000000000100";

// The current revision is the first of the history: the fake back's, opened in 2026; the service's,
// the revision 102 of PRJ-001, whose reference year is that of the loading of the witness, not of
// the run of the test: a four-digit year only is asserted there.
const CURRENT_YEAR: string | RegExp = inService ? /^\d{4}$/ : "2026";

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

// In quarantine against the service (decision of the author of 2026-11-14), the path having read
// the comparison of the whole of PRJ-001 (#3168, #3172, #3192): it keeps its quarantine, and plays
// against the fake back what the screen holds now, the history and the commands. The comparison is
// played on the grids (US-2380).
const QUARANTINED_3192 =
  "in quarantine against the service until EP-27 moves the comparison to the grids (#3192)";

test("the revisions of a project, the history and the commands, no list of structures nor of rates @shared [WF-ARC-0020-A]", async ({
  page,
}) => {
  test.skip(inService, QUARANTINED_3192);
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

  // The rate update is a command of the revision: pressed available, it opens its dialog, which
  // reads the proposal then (never at the render); unavailable, it names its conditions (the
  // description is the hydrated tooltip's).
  const rates = main.getByRole("button", { name: "Appliquer la mise à jour des taux" });
  await expect(rates).toBeVisible();
  if ((await rates.getAttribute("aria-disabled")) === "true") {
    await expect(rates).toHaveAccessibleDescription(/Condition non remplie/);
  } else {
    await rates.click();
    const dialog = page.getByRole("dialog", { name: "Appliquer la mise à jour des taux" });
    await expect(
      dialog
        .getByRole("table", { name: "Mise à jour des taux proposée" })
        .or(dialog.getByText(/aucune mise à jour des taux n’est proposée/)),
    ).toBeVisible({ timeout: WORKING });
    await dialog.getByRole("button", { name: "Annuler" }).click();
    await expect(dialog).toBeHidden();
  }

  // The screen holds the history and the commands: neither the structures of the revision nor the
  // rate update it proposes are listed (US-2370); the banner offers the structures, the command of
  // the revision the rate update.
  await expect(main.getByRole("table", { name: "Structures de coûts" })).toHaveCount(0);
  await expect(main.getByRole("table", { name: "Mise à jour des taux proposée" })).toHaveCount(0);
});

test("« Comparer à la révision lue » leads a marked revision of the history to the grid chosen, that revision as its base (US-2370) [WF-IHM-0010-A]", async ({
  page,
}) => {
  await openHydrated(page, `/projects/${PROJECT}/revisions?revision_id=${REVISION}`);
  const main = page.getByRole("main");
  // The screen holds the history alone: no section of comparison.
  await expect(main.getByRole("region", { name: "Comparaison de deux révisions" })).toHaveCount(0);
  await main
    .getByRole("button", { name: "Comparer à la révision lue\u00a0: «\u00a0Offre v1.0\u00a0»" })
    .click();
  await page.getByRole("menuitem", { name: "Planification" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/projects/${PROJECT}/revisions/${REVISION}/planning\\?.*base_revision_id=${FROM}`),
  );
});
