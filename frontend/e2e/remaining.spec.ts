// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { scrollToPosition, withinBox } from "./scroll";

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

test("reads the remaining to commit of a revision: its indicators, its grid, the tasks not started on demand, and the Kanban of the three states without any percentage to enter [WF-RAE-0030-A]", async ({
  page,
}) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  // The Kanban, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/kanban`);
  await openHydrated(page, `${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await expect(page).toHaveTitle(
    "Estimation du reste à engager · Modernisation du poste de commande — Waterfall",
  );

  // The indicators in cards, dated, each figure as the server gives it, the coverage of the risks
  // in a card of its own.
  const indicators = page.getByRole("region", { name: "Indicateurs du reste à engager" });
  await expect(indicators).toContainText(/Reste à engager\s*67\s293\s028,72/);
  await expect(indicators).toContainText("Calculé le");
  await expect(page.getByRole("region", { name: "Couverture des risques" })).toHaveText(
    /Réserve pour risques\s*850\s060,00\s*Provisions restantes\s*500\s000,00\s*Coût des risques survenus\s*200,00\s*Écart de couverture\s*349\s860,00/,
  );
  // Each sub-project in the zone the server classes it in, named, never by its colour alone.
  // The control station, the tests and commissioning and the whole without sub-project all over
  // their budget, in alert: the tasks drawn around the core count their projected budget.
  const balances = page.getByRole("region", {
    name: "Reste à engager par sous-projet, et marge sur le budget",
  });
  await expect(balances.getByRole("img", { name: "Alerte" })).toHaveCount(3);
  await expect(balances.getByRole("img", { name: "Nominal" })).toHaveCount(0);

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
    /^18\s*Jalon\s*Réception usine\s*Fin le 30\/06\/2026$/,
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
    /^14\s*Relance du fournisseur\s*Terminée le 08\/05\/2026$/,
    /^16\s*Transport exceptionnel\s*Terminée le 15\/05\/2026$/,
    /^247\s*Préparation 1\.2\.1\s*Terminée le 01\/05\/2026$/,
  ]);
  const main = page.getByRole("main");
  for (const role of ["textbox", "spinbutton", "slider", "button", "combobox"] as const) {
    await expect(main.getByRole(role)).toHaveCount(0);
  }
});

test("completes a milestone without a line from the Kanban, from its menu, at a date entered [WF-RAE-0030-A]", async ({
  page,
}) => {
  // Un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. The fake back
  // keeps nothing and answers the example of its first gesture, the start of another task: what the
  // server action carries — the state the card names, the date typed, the version read — is read on
  // the request of the browser, and what the screen does with an answer is proven by the next
  // journey and by `kanban.dom.test.tsx`.
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

test("carries a card by a drag and by the keys, the arrows choosing the cards from column to column, and says on the card a gesture it does not list [WF-RAE-0030-A]", async ({
  page,
}) => {
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

test("leads from the remaining to commit to the workload of the project, on the remaining of the revision under way, in the same context [WF-DEV-0070-A]", async ({
  page,
}) => {
  test.slow();
  await compile(page.request, `${IN_REVISION}/workload`);
  // The link is an icon alone for the room of the head on a window of 1280 points: the title of
  // the screen and the totals of the grid are in view all the same.
  await page.setViewportSize({ width: 1280, height: 720 });
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

test("carries a line to a sub-project from the menu of its cell, and takes it out of any, the column being shown [WF-PRJ-0050-A] [WF-RAE-0040-A]", async ({
  page,
}) => {
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
      request.headers()["next-action"] !== undefined &&
      (request.postData() ?? "").includes('"subproject_id":null'),
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
