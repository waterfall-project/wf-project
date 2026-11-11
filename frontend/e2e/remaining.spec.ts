// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { columnsOf } from "./columns";
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { bringInProgress } from "./in-progress";
import { createOwnProject, openRevision } from "./own-project";
import { seedPlanning } from "./planning-seed";
import { scrollToPosition, withinBox } from "./scroll";
import { isServerAction } from "./server-action";

// Every path is tagged `@shared` (EP-09, US-1640): it plays against the fake back, and against the
// service when the service serves what it reads. The paths below that read the witness's own
// structure — the volumes of §4.6.2, which only the fake back holds (`NO_VOLUME_IN_SERVICE`), and
// the risk coverage of the indicators, a provision or a risk, served at zero until EP-08 — stay
// guarded by `inService`; a short path, not guarded, reads the cards of the indicators and the link to
// the workload on a project the run creates; the paths that write play against the service on a project the run
// creates (`seedPlanning`, `bringInProgress`, #2193), the last of the file. The fake back serves
// the first example of each read, whatever it asks: the structure of the
// volumes of §4.6.2 for the nodes — its lines show here whatever `progress` asks, where the service
// renders the lines of the tasks started alone; the page tests prove what the screen asks —, the
// indicators of the remaining to commit of the witness, and its Kanban on 3 June 2026. The journey
// reads the structure by marks the generator writes (`test_the_marks_the_journeys_read`): row 3, a
// task completed; row 22, started.
const NO_VOLUME_IN_SERVICE =
  "the structure of volumes of §4.6.2, its risk coverage and its Kanban count exist only in the fake back (EP-08, EP-13)";
const FAKE_BACK_KEEPS_NOTHING =
  "the fake back keeps nothing of what a gesture writes; the path of the run below plays it against the service";
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";

/**
 * Drag an element onto another by the mouse, in the steps a browser starts a drag from: a press, a
 * move past its threshold, then the move to the target and the release: `dragTo`, which moves once,
 * started no drag on a card, whose press chooses it and makes its menu appear.
 */
async function dragByMouse(page: Page, source: Locator, target: Locator) {
  await source.scrollIntoViewIfNeeded();
  const from = await source.boundingBox();
  const to = await target.boundingBox();
  if (from === null || to === null) {
    throw new Error("nothing to drag");
  }
  await page.mouse.move(from.x + 20, from.y + 10);
  await page.mouse.down();
  await page.mouse.move(from.x + 30, from.y + 20, { steps: 5 });
  await page.mouse.move(to.x + 40, to.y + 40, { steps: 10 });
  await page.mouse.up();
}

/** Expect a column of the Kanban to hold so many cards, the first of them as given, in order. */
async function expectCards(column: Locator, count: number, first: readonly RegExp[]) {
  const cards = column.getByRole("listitem");
  await expect(cards).toHaveCount(count);
  for (const [index, card] of first.entries()) {
    await expect(cards.nth(index)).toHaveText(card);
  }
}

test("reads the remaining to commit of a revision: its indicators, its grid, the tasks not started on demand, and the Kanban of the three states without any percentage to enter @shared [WF-RAE-0030-A]", async ({
  page,
}) => {
  test.skip(inService, NO_VOLUME_IN_SERVICE);
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  // The Kanban, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/kanban`);
  // The currency now closes each amount of the cards, which wrap a line more (`FiguresGrid` sets
  // them by the width, for every screen: a layout of the cards is a lot of its own, not this
  // one's): the window is taller by that line, so that the totals of the grid stay in view.
  await page.setViewportSize({ width: 1280, height: 800 });
  await openHydrated(page, `${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await expect(page).toHaveTitle(
    "Estimation du reste à engager · Modernisation du poste de commande — Waterfall",
  );

  // The indicators in cards, dated, each figure as the server gives it, the coverage of the risks
  // in a card of its own.
  const indicators = page.getByRole("region", { name: "Indicateurs du reste à engager" });
  await expect(indicators).toContainText(/Reste à engager\s*67\s470\s133,69\s€/);
  await expect(indicators).toContainText("Calculé le");
  await expect(page.getByRole("region", { name: "Couverture des risques" })).toHaveText(
    /Réserve pour risques\s*850\s060,00\s€\s*Provisions restantes\s*500\s000,00\s€\s*Coût des risques survenus\s*200,00\s€\s*réestimé\s*Réestimé des risques survenus \(information\)\s*200,00\s€\s*Écart de couverture\s*349\s860,00\s€/,
  );
  // Each sub-project in the zone the server classes it in, named, never by its colour alone.
  // The control station, the tests and commissioning and the whole without sub-project all
  // within their budget, in nominal: the offer is projected from 2025, its margins are positive.
  const balances = page.getByRole("region", {
    name: "Reste à engager par sous-projet, et marge sur le budget",
  });
  await expect(balances.getByRole("img", { name: "Alerte" })).toHaveCount(0);
  await expect(balances.getByRole("img", { name: "Nominal" })).toHaveCount(3);

  // The grid, its amounts computed, its totals those of the answer, in the window.
  const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  for (const name of [
    "Libellé",
    "Avancement",
    "Fin",
    "Calculé Montant budgété",
    "Charge (h) à la revue précédente",
    "Calculé Réestimé à la revue précédente",
    "Charge (h)",
    "Calculé Montant réestimé",
  ]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  const totals = grid.getByRole("gridcell", { name: /^Total — 1\s000 tâches, 5\s000 lignes$/ });
  expect(await withinBox(grid, totals)).toBe(true);
  await expect(
    grid.getByRole("row", { name: /^2 .*Études de détail/ }).getByRole("img", {
      name: "Terminée",
    }),
  ).toBeVisible();
  // Row 9 may be past the rows in view under the indicators: scrolled to, so that it is checked in
  // the window whatever the height of the grid, never in the margin the grid renders around it.
  const review = await scrollToPosition(grid, 9);
  await expect(review).toHaveAccessibleName(/^9 .*Câblage des armoires/);
  await expect(review.getByRole("img", { name: "Démarrée" })).toBeVisible();
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
    { timeout: WORKING },
  );
  await expect(
    page.getByRole("link", { name: "Ne montrer que les tâches démarrées" }),
  ).toBeVisible();

  // The Kanban, in the same context: the tasks not started, started and completed, no figure to
  // enter. It reads the thousand tasks of the structure too: the same bound.
  await page.getByRole("main").getByRole("link", { name: "Kanban — démarrage des tâches" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/kanban?subproject_id=${SUBPROJECT}`, {
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Kanban — démarrage des tâches");
  // Every task of the structure that is not a summary, each column in the order of the plan: the
  // tasks of the core first, then those drawn around it (EP-14/L45b), the first of them read, the
  // others counted, as `startable_tasks` gives them. Every task not started (#425), none
  // signalled: the factory acceptance waits for the wiring.
  const notStarted = page.getByRole("region", { name: "Non démarrées" });
  await expectCards(notStarted, 925, [
    /^13\s*Jalon\s*Réception usine\s*Fin le 30\/06\/2026$/,
    /^20\s*Montage des armoires sur site\s*Fin le 18\/12\/2026$/,
    /^23\s*Mise en service\s*Fin le 01\/01\/2027$/,
    /^27\s*Préparation 1\.1\.1\s*Fin le 14\/07\/2026$/,
  ]);
  const started = page.getByRole("region", { name: "Démarrées", exact: true });
  await expectCards(started, 8, [
    /^4\s*Pupitres opérateurs\s*Fin le 24\/04\/2026/,
    /^9\s*Câblage des armoires\s*Fin le 30\/06\/2026$/,
    /^311\s*Revue 1\.2\.11\s*Fin le 10\/06\/2026$/,
  ]);
  await expect(started.getByRole("img", { name: "Fin dépassée" })).toHaveCount(1);
  // The tasks completed, each with the date it was, which the Kanban reopens (#425).
  const completed = page.getByRole("region", { name: "Terminées" });
  await expectCards(completed, 27, [
    /^2\s*Études de détail\s*Terminée le 10\/04\/2026$/,
    /^5\s*Revue de conception\s*Terminée le 24\/04\/2026$/,
    /^6\s*Jalon\s*Réception des études\s*Terminée le 24\/04\/2026$/,
    /^7\s*Dossier de conception\s*Terminée le 15\/04\/2026$/,
    /^15\s*Relance du fournisseur\s*Terminée le 08\/05\/2026$/,
    /^17\s*Transport exceptionnel\s*Terminée le 15\/05\/2026$/,
    /^247\s*Préparation 1\.2\.1\s*Terminée le 01\/05\/2026$/,
  ]);
  const main = page.getByRole("main");
  for (const role of ["textbox", "spinbutton", "slider", "combobox"] as const) {
    await expect(main.getByRole(role)).toHaveCount(0);
  }
  // The only button in main is the help button of the screen header (WF-IHM-0140).
  await expect(main.getByRole("button")).toHaveCount(1);
  await expect(main.getByRole("button", { name: "Aide", exact: true })).toHaveCount(1);

  // The filters live in the address: a label searched narrows the three columns, whatever the
  // accents, and each column that hides cards says how many it shows [WF-RAE-0030-A].
  await main.getByRole("searchbox", { name: "Rechercher une tâche" }).fill("ETUDES");
  await main.getByRole("searchbox", { name: "Rechercher une tâche" }).press("Enter");
  await expect(page).toHaveURL(/[?&]q=ETUDES(&|$)/, { timeout: WORKING });
  await expect(page.getByRole("heading", { name: /^Terminées\s+2 sur 27$/ })).toBeVisible({
    timeout: WORKING,
  });
  await expect(completed.getByRole("listitem")).toHaveCount(2);
  await expect(page.getByRole("heading", { name: /^Non démarrées\s+0 sur 925$/ })).toBeVisible();
  // The tasks ready narrow the tasks not started alone. The label lifted first, so that the count
  // of the column not started holds to the filter of the tasks ready alone: the example has none
  // ready (the factory acceptance waits for the wiring), so the 925 cards all go, and the tasks
  // started and completed, which only the label narrows, are all shown again.
  await main.getByRole("searchbox", { name: "Rechercher une tâche" }).fill("");
  await main.getByRole("searchbox", { name: "Rechercher une tâche" }).press("Enter");
  await expect(page).not.toHaveURL(/[?&]q=/, { timeout: WORKING });
  await main.getByRole("checkbox", { name: "Tâches prêtes" }).check();
  await expect(page).toHaveURL(/[?&]ready=1(&|$)/, { timeout: WORKING });
  await expect(page.getByRole("heading", { name: /^Non démarrées\s+0 sur 925$/ })).toBeVisible({
    timeout: WORKING,
  });
  await expect(page.getByRole("heading", { name: "Démarrées", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Terminées", exact: true })).toBeVisible();
});

test("completes a milestone without a line from the Kanban, from its menu, at a date entered @shared [WF-RAE-0030-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_KEEPS_NOTHING);
  // Un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. The fake back
  // keeps nothing and answers the example of its first gesture, the start of another task: what the
  // server action carries — the state the card names, the date typed, the version read — is read on
  // the request of the browser, and what the screen does with an answer is proven by
  // `kanban.dom.test.tsx`.
  test.slow();
  await compile(page.request, `${IN_REVISION}/kanban`);
  await openHydrated(page, `${IN_REVISION}/kanban`);
  const notStarted = page.getByRole("region", { name: "Non démarrées" });
  const card = notStarted.getByRole("listitem").filter({ hasText: "Réception usine" });
  await card.click();
  await expect(card).toHaveAttribute("aria-current", "true");
  await card.getByRole("button", { name: "Gestes de la tâche Réception usine" }).click();
  // The gestures the card lists, and no other: a milestone without a line is completed, never
  // started.
  const menu = page.getByRole("menu", { name: "Gestes de la tâche Réception usine" });
  await expect(menu.getByRole("menuitem")).toHaveText(["Terminer"]);
  await menu.getByRole("menuitem", { name: "Terminer" }).click();

  // The date of the event is asked, the day's proposed, and typed over.
  const date = card.getByLabel("Date de l’événement");
  await expect(date).toBeFocused();
  await expect(date).toHaveValue(/^\d{4}-\d{2}-\d{2}$/);
  await date.fill("2026-06-02");
  const sent = page.waitForRequest(
    (request) => request.method() === "POST" && (request.postData() ?? "").includes("occurred_on"),
  );
  await card.getByRole("button", { name: "Terminer" }).click();
  const body = (await sent).postData() ?? "";
  expect(body).toContain('"progress":"completed"');
  expect(body).toContain('"occurred_on":"2026-06-02"');
  expect(body).toContain('"lock_version":1');
  // The date is no longer asked, and the card, whose gesture is over, has the focus.
  await expect(card.getByLabel("Date de l’événement")).toHaveCount(0, { timeout: WORKING });
  await expect(card).toBeFocused();
});

test("carries a card by a drag and by the keys, the arrows choosing the cards from column to column, and says on the card a gesture it does not list @shared [WF-RAE-0030-A] [WF-IHM-0100-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_KEEPS_NOTHING);
  // Aucune commande ne fait passer une tâche démarrée à l'état non démarré: the cards of the
  // tasks started list no gesture to that state, and say so when one is asked. The fake back
  // answers the start of « Montage des armoires sur site », which the drag carries to the tasks
  // started, the answer replacing the card there.
  test.slow();
  await compile(page.request, `${IN_REVISION}/kanban`);
  await openHydrated(page, `${IN_REVISION}/kanban`);
  const notStarted = page.getByRole("region", { name: "Non démarrées" });
  const started = page.getByRole("region", { name: "Démarrées", exact: true });

  // The arrows choose the cards: down in a column, sideways to the card in the same place.
  await notStarted.getByRole("listitem").filter({ hasText: "Réception usine" }).click();
  await page.keyboard.press("ArrowDown");
  const mounting = notStarted.getByRole("listitem").filter({ hasText: "Montage des armoires" });
  await expect(mounting).toBeFocused();
  await page.keyboard.press("ArrowRight");
  const wiring = started.getByRole("listitem").filter({ hasText: "Câblage des armoires" });
  await expect(wiring).toBeFocused();

  // Carried to the column of the tasks not started by the keys — Shift and the left arrow — it
  // says no gesture leads there, and stays where it is.
  await page.keyboard.press("Shift+ArrowLeft");
  await expect(wiring.getByRole("alert")).toHaveText(
    "Aucun geste ne mène cette tâche vers la colonne « Non démarrées ».",
  );
  await expect(wiring).toBeFocused();

  // Dragged to the column of the tasks started, the task not started asks its date, and the answer
  // replaces the card there, the focus following it.
  await dragByMouse(page, mounting, started);
  const date = mounting.getByLabel("Date de l’événement");
  await expect(date).toBeFocused();
  await date.press("Enter");
  const moved = started.getByRole("listitem").filter({ hasText: "Montage des armoires" });
  await expect(moved).toBeVisible({ timeout: WORKING });
  await expect(moved).toBeFocused();
  await expect(
    notStarted.getByRole("listitem").filter({ hasText: "Montage des armoires" }),
  ).toHaveCount(0);
});

test("reads the cards of the remaining to commit as the service answers, the remaining by sub-project and its margin, and leads to the workload on the remaining under way @shared [WF-RAE-0030-A] [WF-DEV-0070-A]", async ({
  page,
}) => {
  // Not guarded: the cards play against the service on a project the run creates, which holds
  // nothing yet, and against the fake back on the witness; the front computes none of the figures.
  test.slow();
  let revision = IN_REVISION;
  let query = `?subproject_id=${SUBPROJECT}`;
  if (inService) {
    const own = await createOwnProject(page, "Reste lu");
    await openRevision(page, own);
    revision = `${own.path}/revisions/${new URL(page.url()).searchParams.get("revision_id") ?? ""}`;
    query = "";
  }
  await compile(page.request, `${revision}/workload`);
  await page.setViewportSize({ width: 1280, height: 800 });
  await openHydrated(page, `${revision}/remaining${query}`);
  const indicators = page.getByRole("region", { name: "Indicateurs du reste à engager" });
  await expect(indicators).toContainText(
    inService ? /Reste à engager\s*0,00\s€/ : /Reste à engager\s*67\s470\s133,69\s€/,
    { timeout: WORKING },
  );
  await expect(indicators).toContainText("Calculé le");
  const balances = page.getByRole("region", {
    name: "Reste à engager par sous-projet, et marge sur le budget",
  });
  await expect(balances).toBeVisible();
  await expect(balances.getByRole("img", { name: "Alerte" })).toHaveCount(0);
  await page.getByRole("main").getByRole("link", { name: "Plan de charge" }).click();
  await expect(page.getByLabel("Base")).toHaveValue("current_remaining", { timeout: WORKING });
  expect(new URL(page.url()).searchParams.get("basis")).toBe("current_remaining");
});

test("leads from the remaining to commit to the workload of the project, on the remaining of the revision under way, in the same context @shared [WF-DEV-0070-A]", async ({
  page,
}) => {
  test.slow();
  await compile(page.request, `${IN_REVISION}/workload`);
  // The link is an icon alone for the room of the head on a window of 1280 points; the cards,
  // with the currency closing each amount, wrap a line more (see the first test): the window is
  // 800 points high so that the title of the screen and the totals of the grid are in view.
  await page.setViewportSize({ width: 1280, height: 800 });
  await openHydrated(page, `${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await expect(page.getByRole("heading", { level: 1 })).toBeInViewport({ ratio: 1 });
  await expect(
    page
      .getByRole("treegrid", { name: "Grille de reste à engager" })
      .getByRole("gridcell", { name: /^Total — / }),
  ).toBeInViewport({ ratio: 1 });
  await page.getByRole("main").getByRole("link", { name: "Plan de charge" }).click();
  await expect(page).toHaveURL(
    `${IN_REVISION}/workload?subproject_id=${SUBPROJECT}&basis=current_remaining`,
    { timeout: WORKING },
  );
  await expect(page.getByLabel("Base")).toHaveValue("current_remaining", { timeout: WORKING });
});

test("carries a line to a sub-project from the menu of its cell, and takes it out of any, the column being shown @shared [WF-PRJ-0050-A] [WF-RAE-0040-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_KEEPS_NOTHING);
  // Le passage à un autre sous-projet d'une ligne d'une tâche non démarrée aboutit. The fake back
  // keeps nothing, and serves the first example of `updateEstimateLine` whatever was sent, the entry
  // of a figure of another line: what the grid sends, and the line answered shown in the column,
  // are proven by `choice-menu.dom.test.tsx`; the journey proves the column, the menu and the
  // sentence the screen says, in a browser. Row 24 of the example is a line of a task not started,
  // « Mise en service sur site », which names its sub-project among the fields it accepts.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/remaining`);
  const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
  // The column of the sub-project starts hidden, and is shown from the menu of the columns.
  await expect(grid.getByRole("columnheader", { name: "Sous-projet" })).toHaveCount(0);
  await page.getByRole("button", { name: "Colonnes" }).click();
  await page.getByRole("menuitemcheckbox", { name: "Sous-projet" }).click();
  await page.keyboard.press("Escape");
  const at = await columnsOf(grid, { label: "Libellé", subproject: "Sous-projet" });

  const line = await scrollToPosition(grid, 24);
  await expect(line).toHaveAccessibleName(/^24 .*Mise en service sur site/);
  const cell = line.getByRole("gridcell").nth(at.subproject);
  await expect(cell).toHaveText("Poste de commande");
  await expect(cell).toHaveAttribute("aria-readonly", "true");

  // The radio buttons: none for the sub-project, and every sub-project of the project, the line's
  // checked.
  await line.getByRole("gridcell").nth(at.label).click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Sous-projet" })
    .click();
  const radios = page.getByRole("menu", { name: "Sous-projet" });
  await expect(radios.getByRole("menuitemradio")).toHaveText([
    "Aucun sous-projet",
    "SP-CMD — Poste de commande",
    "SP-ESS — Essais et mise en service",
  ]);
  await expect(
    radios.getByRole("menuitemradio", { name: "SP-CMD — Poste de commande" }),
  ).toHaveAttribute("aria-checked", "true");
  await radios.getByRole("menuitemradio", { name: "SP-ESS — Essais et mise en service" }).click();
  const said = page.getByText("Sous-projet de « Mise en service sur site » mis à jour.");
  await expect(said).toBeVisible({ timeout: WORKING });
  await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });

  // Taken out of any: the menu offers it, the second write is the server action that carries a null
  // sub-project, and the screen says the sub-project was updated. The line of the example bears a
  // budget; the figures of the line do not take part in the write, which a line added after the
  // reference (a nil budget, WF-RAE-0040-A) would send the same, proven by the DOM tests.
  await line.getByRole("gridcell").nth(at.label).click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Sous-projet" })
    .click();
  const removal = page.waitForRequest(
    (request) =>
      isServerAction(request) && (request.postData() ?? "").includes('"subproject_id":null'),
    { timeout: WORKING },
  );
  await page
    .getByRole("menu", { name: "Sous-projet" })
    .getByRole("menuitemradio", { name: "Aucun sous-projet" })
    .click();
  expect((await removal).postData()).toContain('"lock_version"');
  await expect(said).toBeVisible({ timeout: WORKING });
  await expect(grid).not.toHaveAttribute("aria-busy", "true", { timeout: WORKING });
  await expect(page.getByRole("alert")).toBeEmpty();
});

test("starts a task from the Kanban and completes a milestone, on a project the run creates: the lines of the task started appear in the grid, the tasks not started on demand, each as the service answers @shared [WF-RAE-0030-A] [WF-RAE-0040-A]", async ({
  page,
  browser,
  playwright,
  manager,
}) => {
  // Une tâche passée à l'état démarré voit ses lignes apparaître dans la grille de reste à
  // engager ; une tâche non démarrée n'y apparaît qu'à la demande ; un jalon sans ligne de devis
  // est terminé depuis le Kanban, à une date saisie. The project is the run's own, taken In
  // progress (`bringInProgress`): the witness is never written by a path (#2193).
  test.skip(!inService, "the fake back keeps nothing: the paths above play the gestures on it");
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const seeded = await seedPlanning(page, browser, calls, manager, "Reste lancé");
    await bringInProgress(page, calls, seeded);
    await openRevision(page, seeded.own);
    const open = new URL(page.url()).searchParams.get("revision_id") ?? "";
    const revision = `${seeded.own.path}/revisions/${open}`;
    await openHydrated(page, `${revision}/kanban`);
    await expect(page.getByRole("note")).toHaveCount(0);
    const notStarted = page.getByRole("region", { name: "Non démarrées" });
    const started = page.getByRole("region", { name: "Démarrées", exact: true });
    const completed = page.getByRole("region", { name: "Terminées" });
    const card = (name: string) => notStarted.getByRole("listitem").filter({ hasText: name });
    // The gestures a card lists, and no other: a milestone is never started; a task with a line
    // in the plan is started.
    const gestures = async (name: string) => {
      await card(name).click();
      await card(name)
        .getByRole("button", { name: `Gestes de la tâche ${name}` })
        .click();
      return page.getByRole("menu", { name: `Gestes de la tâche ${name}` });
    };
    const menu = await gestures("Réception des études");
    await expect(menu.getByRole("menuitem", { name: "Terminer" })).toBeVisible();
    await expect(menu.getByRole("menuitem", { name: "Démarrer" })).toHaveCount(0);
    await menu.getByRole("menuitem", { name: "Terminer" }).click();
    const done = card("Réception des études");
    await done.getByLabel("Date de l’événement").fill("2026-06-02");
    await done.getByRole("button", { name: "Terminer" }).click();
    await expect(
      completed.getByRole("listitem").filter({ hasText: "Réception des études" }),
    ).toContainText("Terminée le 02/06/2026", { timeout: WORKING });
    expect(await notStarted.getByText("Réception des études").count()).toBe(0);
    await expect(page.getByRole("note")).toHaveCount(0);

    // Started, the task with a line is in the column of the tasks started, and its line is in the
    // grid; the tasks not started are there on demand alone.
    const starting = await gestures("Mise en service");
    await starting.getByRole("menuitem", { name: "Démarrer" }).click();
    await card("Mise en service").getByLabel("Date de l’événement").press("Enter");
    await expect(started.getByRole("listitem").filter({ hasText: "Mise en service" })).toBeVisible({
      timeout: WORKING,
    });
    await openHydrated(page, `${revision}/remaining`);
    const grid = page.getByRole("treegrid", { name: "Grille de reste à engager" });
    // The task and its line.
    await expect(grid.getByRole("row", { name: /Mise en service/ })).toHaveCount(2, {
      timeout: WORKING,
    });
    await expect(grid.getByRole("row", { name: /Études de détail/ })).toHaveCount(0);
    await page.getByRole("link", { name: "Montrer aussi les tâches non démarrées" }).click();
    await expect(page).toHaveURL(/progress=not_started%2Cstarted$/, { timeout: WORKING });
    await expect(grid.getByRole("row", { name: /Études de détail/ })).toBeVisible({
      timeout: WORKING,
    });
    await expect(page.getByRole("note")).toHaveCount(0);
  } finally {
    await calls.dispose();
  }
});
