// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the revisions of a project (`/projects/{id}/revisions`), against the fake back and,
 * tagged `@shared`, against the service, which serves the history, the revision and its structures
 * (US-0960). The comparison, which the screen no longer shows (US-2370), reads, against the service,
 * the whole structure of PRJ-001 from its revision 100 to its revision 101 — 5 966 nodes there, not
 * the 5 999 of the volume, which stays with the fake back until EP-13 (#2696) —, of which the grid
 * draws the rows in view (virtualised: as many as the window shows, `ROWS_IN_VIEW`) and
 * counts all, the nodes of the answer and its two header rows (`aria-rowcount`); against the fake
 * back, the window of its example (« 2 nodes added, 2 removed… »).
 *
 * The fake back serves the first example of each operation: the history of three revisions —
 * the reference, the draft, the offer v1.0 —, the draft read whatever the address names, its
 * structures, no rate update proposed for it, and the comparison of the offer to the reference;
 * the comparison proves the fake back serves `compareRevisions` — its path,
 * `/revisions/comparison`, could be mistaken for a revision named `comparison`. The service serves
 * the witness, of which PRJ-001 holds the same three revisions, its 100 and 101 marked by the loader
 * as the worker marks (US-0970).
 */
import { type Browser, expect } from "@playwright/test";

import { WORKING } from "./bounds";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";
import { ScreenSteps } from "./screen-steps";
import { API, frontToken, type LocalPerson } from "./service/realm";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const FROM = "01926f3a-7c00-7000-8000-000000000100";
const TO = "01926f3a-7c00-7000-8000-000000000101";
// The rows of the grid in view (virtualised) of PRJ-001 compared, 100 to 101, against the service:
// exactly the count that the window of the harness shows, which fixes the height of the grid.
const ROWS_IN_VIEW = 39;

interface AmountDelta {
  dimension: string;
  label: string | null;
  budgeted_delta: string;
  reestimated_delta: string;
}

/** An amount as the screen writes it (fr-FR, euro), whitespace normalised as an assertion does. */
function asTheScreenWrites(amount: string): string {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" })
    .format(Number(amount))
    .replace(/\s+/g, " ");
}

/** A text that ends on the amount whole, not on the tail of a larger one (« 0,00 € » of « 3 000,00 € »). */
function amountWhole(amount: string): RegExp {
  const escaped = amount.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![\\d,\\-\u2212])${escaped}$`);
}

interface ServedComparison {
  items: { difference: string }[];
  amount_deltas: AmountDelta[];
}

/** The comparison of 100 to 101 as the service renders it, which the screen asks of it. */
async function comparisonServed(
  browser: Browser,
  manager: LocalPerson | undefined,
): Promise<ServedComparison> {
  if (manager === undefined) {
    throw new Error("a path in the service has its manager");
  }
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const headers = { Authorization: `Bearer ${await frontToken(browser, manager)}` };
    const response = await context.request.get(`${API}/projects/${PROJECT}/revisions/comparison`, {
      headers,
      params: { from_revision_id: FROM, to_revision_id: TO, fields: "kind" },
    });
    expect(response.status(), "GET comparison").toBe(200);
    return (await response.json()) as ServedComparison;
  } finally {
    await context.close();
  }
}

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

// In quarantine against the service (decision of the author of 2026-11-14): the comparison of the
// whole of PRJ-001 does not show within `WORKING` by moments in the queue (#3168, #3172). The fake
// back still plays the path; EP-27 rewrites it on the grids and plays it again (#3192).
const QUARANTINED_3192 =
  "in quarantine against the service until EP-27 moves the comparison to the grids (#3192)";

test("the revisions of a project, their comparison as the API renders it, the history and no list of structures nor of rates @shared [WF-ARC-0020-A]", async ({
  page,
  browser,
  manager,
}) => {
  test.skip(inService, QUARANTINED_3192);
  // Against the service the path reads the comparison of the whole structure of PRJ-001 twice — the
  // screen, then the API, whose answer gives both the count of the nodes and the deviations —, two
  // bounds of a screen of grid besides the opening, more than the thirty seconds of a test: the
  // comparison takes 2.2 s at the API alone, 5 to 16 s in the queue, whose paths read PRJ-001 on the
  // one process of the API together (run 43403635976, 16.1 s for the one of this path; #2942).
  test.slow();
  const steps = new ScreenSteps(page, "the comparison as the API renders it");
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

  // The comparison asked of the server: what it answers is shown, nothing paired by the front.
  // Against the service, it is the whole structure of PRJ-001 from 100 to 101, of which the grid
  // draws the rows in view. Against the fake back, the example is a window, the sub-tree of
  // « Installation sur site » (#1193), as its description counts it: 2 nodes added, 2 removed, 2
  // lines re-estimated at the rates of 2026 (EP-14/L45a), and 5 deviations — 3 natures of cost, 2
  // sub-projects —, each table with its header row. The nodes come in the dense grid of the
  // structures, each with the mark the server gives it, and the screen keeps the bound of a screen
  // of grid (`WORKING`).
  await steps.timed("compare", async () => {
    await main.getByRole("button", { name: "Comparer" }).click();
    await expect(page).toHaveURL(/from_revision_id=.+&to_revision_id=.+/, { timeout: WORKING });
  });
  const nodes = main.getByRole("grid", { name: "Nœuds comparés" });
  // The window of the fake back is 11 rows; the service compares the whole structure, of which the
  // grid draws the rows in view and counts all of them, its two header rows besides.
  await expect(nodes.getByRole("row")).toHaveCount(inService ? ROWS_IN_VIEW : 11);
  const served = inService
    ? await steps.timed("the API", () => comparisonServed(browser, manager))
    : undefined;
  if (served !== undefined) {
    await expect(nodes).toHaveAttribute("aria-rowcount", (served.items.length + 2).toString());
  }
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
  // Both deviations, each under the header that names it, on the row of the nature of cost
  // « Main-d'œuvre ». The fake back's window: budgeted 3 000,00, re-estimated 2 840,83. Against
  // the service, the amounts are those the API renders for the comparison, read of it and written
  // as the screen writes them, none pinned (the loader changes them with the provisions, EP-08).
  await expect(deltas.getByRole("columnheader", { name: "Écart budgété" })).toBeVisible();
  await expect(deltas.getByRole("columnheader", { name: "Écart réestimé" })).toBeVisible();
  const labour = deltas
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "Main-d'œuvre", exact: true }) });
  let budgeted = "3000.00";
  let reestimated = "2840.83";
  if (served !== undefined) {
    const delta = served.amount_deltas.find(
      ({ dimension, label }) => dimension === "cost_type" && label === "Main-d'œuvre",
    );
    expect(delta, "the nature of cost « Main-d'œuvre » in the comparison").toBeDefined();
    budgeted = delta?.budgeted_delta ?? "";
    reestimated = delta?.reestimated_delta ?? "";
  }
  await expect(
    labour.getByRole("cell", { name: amountWhole(asTheScreenWrites(budgeted)) }),
  ).toHaveCount(1);
  await expect(
    labour.getByRole("cell", { name: amountWhole(asTheScreenWrites(reestimated)) }),
  ).toHaveCount(1);
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
