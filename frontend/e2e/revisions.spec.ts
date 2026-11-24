// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the revisions of a project (`/projects/{id}/revisions`), against the fake back and,
 * tagged `@shared`, against the service, which serves the history, the revision and its commands
 * (US-0960). The screen holds the history and the commands of the revision read, no comparison
 * (US-2370): « Comparer à la révision lue » leads a marked revision of the history to the grid
 * chosen, that revision as its base. The comparison itself is played on the grids, below (US-2380).
 *
 * The fake back serves the first example of each operation: the history of three revisions —
 * the reference, the draft, the offer v1.0 —, the draft read whatever the address names, its
 * structures, and no rate update proposed for it. The service serves the witness, of which PRJ-001
 * holds the same three revisions, its 100 and 101 marked by the loader as the worker marks
 * (US-0970).
 */
import { expect, type Locator, type Page } from "@playwright/test";

import {
  COMPARING_REVISION_102,
  COMPARISON_PATH_IN_SERVICE,
  LOADED,
  MARKING,
  WORKING,
} from "./bounds";
import { columnsOf } from "./columns";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";
import { SECOND_TASK_DAYS, seedPlanning } from "./planning-seed";
import { rowAt, scrollToFoot } from "./scroll";

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

test("the revisions of a project, the history and the commands, no list of structures nor of rates @shared [WF-ARC-0020-A]", async ({
  page,
}) => {
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
    // Each text is the whole of what the screen says there: the fake back's account holds the one
    // condition unmet, the service's account is no contributor of the project, which is another.
    await expect(rates).toHaveAccessibleDescription(
      inService
        ? /^Conditions non remplies\s?: être contributeur du projet et une mise à jour des taux disponible\.$/
        : /^Condition non remplie\s?: une mise à jour des taux disponible\.$/,
    );
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

// The comparison, played on the grids of the current revision of PRJ-001 (US-2380), which the three
// of them read with the reference for base (US-2320 to US-2360). The fake back serves the first
// example of `compareRevisions` whatever the address names (`comparison`, the offer against the
// reference, over the installation on site, every node of it in difference): the marks, the values
// of the base and the totals are read on it, and nothing is folded. The service compares the
// revision under way to its reference, on all of PRJ-001: its nodes in difference are marked, the
// branches without difference fold, and the witness is never written (#2193): the writing of a
// finish is played on a project of the run, below.
const BASE = `/projects/${PROJECT}/revisions/${REVISION}`;
const REFERENCE_PARAMETER = "base_revision_id=[0-9a-f-]{36}";

/** The banner of the reading context. */
function banner(page: Page): Locator {
  return page.getByRole("region", { name: "Contexte de lecture" });
}

/**
 * Reach a cell of a grid by the arrows of the keyboard alone, from the cell of another: each press
 * moves the focus one cell to the right, until it is on the cell.
 */
async function reachByKeyboard(page: Page, from: Locator, to: Locator): Promise<void> {
  await from.click();
  await expect(async () => {
    if (!(await to.evaluate((cell) => cell === document.activeElement))) {
      // The arrows only go right: the focus on the last cell of its row, the aim is out of reach.
      const end = await page.evaluate(() => {
        const cell = document.activeElement;
        return cell?.parentElement?.lastElementChild === cell;
      });
      expect(
        end,
        "the cell aimed at is not to the right of the focus, on the last cell of its row",
      ).toBe(false);
      await page.keyboard.press("ArrowRight");
    }
    await expect(to).toBeFocused({ timeout: 500 });
  }).toPass({ timeout: WORKING });
}

/** The base the banner names, and the locator that says it. */
interface Compared {
  /** The definition « Comparée à … » of the banner. */
  comparedTo: Locator;
  /** The name of the reference, as the banner says it. */
  named: string;
  /** The query of the address that carries the base. */
  compared: string;
}

/**
 * Open a screen of the current revision of PRJ-001 and compare it to the reference of the project,
 * chosen in the banner without leaving the screen, which names it.
 */
async function compareToReference(page: Page, screen: string): Promise<Compared> {
  await openHydrated(page, `${BASE}/${screen}`);
  const comparedTo = banner(page)
    .getByRole("definition")
    .filter({ hasText: /^Comparée à / });
  await expect(comparedTo).toHaveCount(0);
  await banner(page).getByRole("button", { name: "Choisir une base de comparaison" }).click();
  // The reference of the project is the one of the bases that says so: « Référence » itself against
  // the fake back, the offer v1.0 designated in the witness of the service.
  const reference = page.getByRole("menuitemradio", { name: /\(référence\)$/ });
  const named = (await reference.innerText()).replace(/\s*\(référence\)$/, "");
  await reference.click();
  // Against the service, the address waits for the read of revision 102 compared, which overran
  // `WORKING` (`COMPARING_REVISION_102`, #4911).
  await expect(page).toHaveURL(new RegExp(`${BASE}/${screen}\\?${REFERENCE_PARAMETER}$`), {
    timeout: inService ? COMPARING_REVISION_102 : WORKING,
  });
  await expect(comparedTo).toContainText(named);
  return { comparedTo, named, compared: new URL(page.url()).search };
}

// The comparison of PRJ-001 is played in two paths, the estimate in one, the planning and the
// remaining to commit in the other. Each read of it compared took 11 to 24 s in the queue, where the
// quiet measure is 3.5 s (`LOADED`): the six of a single path, each under its own bound, overran its
// ninety seconds together (run 45006353429, 92 s, #4678). Each path keeps the margin of `test.slow`
// for three or four of them.
test("the comparison of the current revision of PRJ-001 to its reference on the estimate, the cell marked and the value of its base read at the keyboard, the totals and the differences of the amounts, the comparison lifted @shared [WF-IHM-0010-A] [WF-IHM-0020-A] [WF-IHM-0150-A] [WF-IHM-0160-A]", async ({
  page,
}) => {
  // The estimate of PRJ-001 read twice, compared then not, and walked at the keyboard. Against the
  // service, a budget measured in place of `test.slow` (`COMPARISON_PATH_IN_SERVICE`, #4911).
  if (inService) test.setTimeout(COMPARISON_PATH_IN_SERVICE);
  else test.slow();
  const { comparedTo, named } = await compareToReference(page, "estimate");
  const estimate = page.getByRole("treegrid", { name: "Grille de devis" });
  await expect(estimate).toBeVisible({ timeout: WORKING });

  // A row marked, and the value its base held in the cell that differs, read at the keyboard: the
  // focus on the cell says it, as the pointer does. The row is one with such a cell among the
  // columns of the estimate: a task modified by its progress alone is marked without one
  // (WF-IHM-0150), as the service reads the first rows of the 102 against the 101.
  const marked = estimate
    .getByRole("row")
    .filter({ hasText: "Modifié" })
    .filter({ has: page.getByRole("gridcell").filter({ hasText: "Δ" }) })
    .first();
  await expect(marked).toBeVisible({ timeout: WORKING });
  const at = await columnsOf(estimate, { label: "Libellé" });
  const differing = marked.getByRole("gridcell").filter({ hasText: "Δ" }).first();
  await expect(differing).toContainText(/Base\s*:/);
  await reachByKeyboard(page, marked.getByRole("gridcell").nth(at.label), differing);
  // The cell says the value of its base to a reader of the screen at once. The scroll that brought
  // the cell into view closes the tooltip that has just opened (Radix closes it on any scroll of
  // the cell's ancestors, #3901): it opens again when the cell is reached again, the arrows left
  // and right.
  await expect(differing).toContainText(/Base\s*:/);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowRight");
  await expect(differing).toBeFocused();
  await expect(page.getByRole("tooltip")).toContainText(/^Base\s*:/);
  await page.keyboard.press("Escape");

  // The totals say the total read, that of the base and their difference; the differences of the
  // amounts open from the estimate.
  await expect(estimate.getByText(/^Total — /)).toHaveCount(1);
  await expect(estimate.getByText(/^Base : Total — /)).toHaveCount(1);
  await expect(estimate.getByText(/^Écart : Total — /)).toHaveCount(1);
  await page.getByRole("button", { name: "Écarts de montants" }).click();
  const dialog = page.getByRole("dialog", { name: "Écarts de montants à la base" });
  await expect(dialog.getByRole("table", { name: "Écarts de montants à la base" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();

  // The comparison lifted: the base leaves the address and the banner offers the choice again.
  await banner(page)
    .getByRole("link", { name: `Lever la comparaison avec «\u00a0${named}\u00a0»` })
    .click();
  await expect(page).toHaveURL(`${BASE}/estimate`, { timeout: WORKING });
  await expect(comparedTo).toHaveCount(0);
  await expect(
    banner(page).getByRole("button", { name: "Choisir une base de comparaison" }),
  ).toBeVisible();
});

test("the comparison of the current revision of PRJ-001 to its reference on the planning, the branches without difference folded, then on the remaining to commit with the same base @shared [WF-IHM-0010-A] [WF-IHM-0020-A] [WF-IHM-0170-A]", async ({
  page,
}) => {
  // The planning and the remaining to commit of PRJ-001, the slowest reads of the comparison.
  test.slow();
  const { comparedTo, named, compared } = await compareToReference(page, "planning");
  const planning = page.getByRole("treegrid", { name: "Grille de planning" });
  // The planning compared is a read slowed by the queue: past 15 s, the screen still « Chargement
  // de l'écran », where the quiet measure is far under (`LOADED`, #4326, #4678).
  await expect(planning).toBeVisible({ timeout: LOADED });

  // The branches without difference fold, each run said in its place with its number of rows, and
  // unfold. Every node of the example of the fake back is in difference: none folds there; the
  // planning of PRJ-001 holds many that the base leaves as they are. The fold on a response with
  // branches without difference is proved without the service, by `folded-runs.dom.test.tsx`.
  const only = page.getByRole("button", { name: "Écarts seulement" });
  await only.click();
  await expect(only).toHaveAttribute("aria-pressed", "true");
  const runs = planning.getByRole("button", { name: /sans écart repliées?$/ });
  if (inService) {
    // The grid renders the rows in view: the runs are those of the foot, where the plan ends.
    await scrollToFoot(planning);
    const run = runs.last();
    await expect(run).toBeVisible({ timeout: WORKING });
    // Said collapsed, it unfolds its rows at the click: the run is no more, among those in view.
    await expect(run).toHaveAttribute("aria-expanded", "false");
    const folded = await runs.count();
    await run.click();
    await expect(runs).toHaveCount(folded - 1, { timeout: WORKING });
  } else {
    await expect(runs).toHaveCount(0);
  }
  await only.click();
  await expect(only).toHaveAttribute("aria-pressed", "false");

  // The remaining to commit with the same base: the banner names it, the address carries it.
  const functions = page.getByRole("navigation", { name: "Fonctions" });
  await functions.getByRole("link", { name: "Estimation du reste à engager", exact: true }).click();
  await expect(page).toHaveURL(`${BASE}/remaining${compared}`, { timeout: WORKING });
  const remaining = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  // The slowest read of the path, the remaining to commit compared (`LOADED`, #4326).
  await expect(remaining).toBeVisible({ timeout: LOADED });
  await expect(comparedTo).toContainText(named);
  await expect(page.getByRole("button", { name: "Écarts de montants" })).toBeVisible();
});

// The writing of a finish needs a service that remembers it, and a project the account of the run
// writes: PRJ-001 is never written by a path (#2193), so the path makes its own, as the cycle of the
// revisions does (`revision-cycle.spec.ts`) — its six tasks, its revision marked by the worker, a
// current revision opened, which is the grid compared to the revision marked.
const SERVICE_ONLY =
  "the fake back keeps nothing of what is written, and answers each write by its first example";

test("a finish pushed from the planning is read modified, with the date of the base, brought back, and read modified no more @shared [WF-IHM-0150-A] [WF-REV-0080-A]", async ({
  page,
  browser,
  request,
  manager,
}) => {
  // Wanted, not a gap: the fake back plays no write of a finish, as the issue and the criterion say.
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const seeded = await seedPlanning(page, browser, request, manager, "Fin repoussée");
  const main = page.getByRole("main");

  // The revision marked by the worker, then a current revision opened, a copy of it.
  await openHydrated(page, `${seeded.own.path}/revisions?revision_id=${seeded.ids.revision}`);
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Marquer la révision" }).click();
  const marking = commands.getByRole("form");
  await marking.getByRole("textbox", { name: "Nom de version" }).fill("v1.0");
  await marking.getByRole("button", { name: "Marquer", exact: true }).click();
  await expect(commands.getByRole("form")).toHaveCount(0);
  await page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ }).click();
  const task = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Tâches de fond" })
    .getByRole("listitem")
    .filter({ hasText: "Marquage d’une révision « v1.0 »" });
  await expect(task.getByText("Réussie")).toBeVisible({ timeout: MARKING });
  await task.getByRole("button", { name: "Recharger l’écran" }).click();
  const opened = page.url();
  await main
    .getByRole("region", { name: "Historique des révisions" })
    .getByRole("button", { name: "Ouvrir une révision en cours" })
    .click();
  await expect(page).not.toHaveURL(opened, { timeout: WORKING });
  const current = new URL(page.url()).searchParams.get("revision_id");
  expect(current, "the revision opened is named by the address").not.toBeNull();

  // Its planning, compared to the revision marked: nothing differs yet.
  await openHydrated(
    page,
    `${seeded.own.path}/revisions/${current ?? ""}/planning?base_revision_id=${seeded.ids.revision}`,
  );
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { label: "Libellé", duration: "Durée", finish: "Fin" });
  // The row of the second task of the plan, by its place in the answer: its name changes as it is marked.
  const row = rowAt(grid, 2);
  const finish = row.getByRole("gridcell").nth(at.finish);
  await expect(finish).toBeVisible({ timeout: WORKING });
  await expect(row).not.toContainText("Modifié");
  await expect(finish).not.toContainText("Δ");
  const settled = () => expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  const date = /\d{2}\/\d{2}\/\d{4}/;
  const before = date.exec(await finish.innerText())?.[0] ?? "";
  expect(before, "the finish is a date").not.toBe("");

  /** Write the duration of the task, which moves its finish: `updateTaskFacet`. */
  const lasting = async (duration: string): Promise<void> => {
    await row.getByRole("gridcell").nth(at.duration).click();
    await page.keyboard.press("F2");
    await grid.getByRole("textbox", { name: "Durée" }).fill(duration);
    await page.keyboard.press("Enter");
    await settled();
  };

  // The finish pushed two days: the task is read modified, its finish marked, the date of the base
  // given — as the grid reads its comparison anew once the write answered.
  await lasting("7 j");
  await expect(row).toContainText("Modifié", { timeout: WORKING });
  await expect(finish).toContainText("Δ");
  await expect(finish).toContainText(`Base : ${before}`);
  await expect(finish).not.toContainText(new RegExp(`^${before}`));

  // The finish brought back: the task is read modified no more.
  await lasting(`${SECOND_TASK_DAYS} j`);
  await expect(row).not.toContainText("Modifié", { timeout: WORKING });
  await expect(finish).not.toContainText("Δ");
  await expect(finish).toContainText(before);
});
