// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Download, expect, type Locator } from "@playwright/test";

import { closeMenu, menuButton, openMenu, pick } from "./check-menu";
import { columnsOf } from "./columns";
import { holdScripts, openHydrated, WORKING } from "./hydration";
import { test } from "./mode";
import { rowAt, scrollToPosition, withinBox } from "./scroll";
import { isServerAction } from "./server-action";

// The paths tagged `@shared` play against the service too, on the witness it holds (PRJ-001, loaded
// by `waterfall-api load-witness`, EP-06): they find a row by its label, or by its rank among the
// tasks, and read the numbers the grid shows; the rows are the tasks alone, the lines being EP-07's.
// The others write on the witness, whose account of the run is no contributor (#2193): they keep to
// the fake back, which is the only one to hold what they write, and `planning-service.spec.ts` plays
// their twins on a project the run creates.
//
// The fake back serves the first example of `listNodes` whatever `kinds` asks — the structure of
// the witness at the sizes of §4.6.2, its core first, a thousand tasks and their lines (#376) —:
// the page keeps the tasks alone (`projectNodes`, #1397), as the service renders them, so that the
// rows of the grid are the tasks, in the order of the fake back, and their row numbers (those of
// the structure, lines counted) are no longer their positions. The paths that write read the
// structure by marks the generator writes, which `test_the_marks_the_journeys_read` holds, and by
// their ranks among the tasks, which `test_the_ranks_among_the_tasks_the_planning_journeys_read`
// holds (both in tools/tests/test_mockstructure.py): row 7, a task of the core completed off the
// critical path; row 311, the 64th task, started, which follows row 291 — the 61st, « Validation
// 1.2.8 »; row 39, a task of the critical path not started, which follows the factory acceptance of
// row 13 — the 20th; row 14, a summary of the second level over the tasks of rows 15 and 17, the
// 11th and the 12th, before row 19 — the 13th.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

/**
 * The width the column of the names of the exported Gantt takes over the tasks of the witness:
 * the `namesWidth` of `gantt-image.ts` on them, which `gantt-image.test.ts` holds on the same rows.
 * Only its link to the PNG exported is tried here, the rule of the width not being written twice.
 */
const NAMES_WIDTH = 252;

test("opens the grid of the planning: its icons named, the critical path marked, the predecessors by row number, no header offering a sort @shared [WF-IHM-0060-A] [WF-PLA-0080-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  await expect(page).toHaveTitle("Planification · Modernisation du poste de commande — Waterfall");
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  for (const name of [
    "N°",
    "Libellé",
    "Description",
    "Mode de planification",
    "Avancement",
    "Calculé Avancement physique",
    "Calculé Marge",
    "Démarrée le",
    "Terminée le",
  ]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  // The grid holds in the window as it opens: its totals are in view.
  expect(
    await withinBox(grid, grid.getByRole("gridcell", { name: /^Total — 1\s000 tâches$/ })),
  ).toBe(true);
  const completed = grid.getByRole("row", { name: /^\d+ .*Dossier de conception/ });
  await expect(completed.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Terminée" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Chemin critique" })).toHaveCount(0);
  const at = await columnsOf(grid, { predecessors: "Prédécesseurs" });
  // The rows are found by their label, and the number a task follows is read from the grid, not
  // written: against the service the rows are numbered by the tasks alone, the lines being EP-07's,
  // while the fake back counts the lines too, as the marks below do.
  const factory = await numberOf(grid, /^\d+ .*Réception usine/);
  // Row 39 is the 20th task (`test_the_ranks_among_the_tasks_the_planning_journeys_read`), and the
  // grid renders only the rows in view and a margin around them: in a short grid the 20th lies
  // past that margin as the grid opens, so it is scrolled to, and checked in the window. The
  // critical path is marked by its icon, whatever the colour.
  const critical = await scrollToPosition(grid, 20);
  await expect(critical).toHaveAccessibleName(/^\d+ .*Revue 1\.1\.3/);
  await expect(critical.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Chemin critique" })).toBeVisible();
  await expect(critical.getByRole("gridcell").nth(at.predecessors)).toHaveText(factory);

  // Further down, a task started, which follows another by its row number.
  // It follows the 61st task, « Validation 1.2.8 » (row 291 on the fake back), whose number is read
  // where the grid shows it.
  const followed = await numberOfRow(await scrollToPosition(grid, 61));
  const follower = await scrollToPosition(grid, 64);
  await expect(follower).toHaveAccessibleName(/^\d+ .*Revue 1\.2\.11/);
  await expect(follower.getByRole("img", { name: "Démarrée" })).toBeVisible();
  await expect(follower.getByRole("gridcell").nth(at.predecessors)).toHaveText(followed);

  // Dans la grille de planning, aucun en-tête de colonne ne propose de tri: of its fifteen headers,
  // the number and the fourteen columns, none holds a button but the three of the zoom and the export
  // in that of the Gantt, none says a sort.
  const headers = grid.getByRole("columnheader");
  await expect(headers).toHaveCount(15);
  await expect(headers.getByRole("button")).toHaveCount(4);
  await expect(
    headers.getByRole("group", { name: "Zoom du Gantt" }).getByRole("button"),
  ).toHaveCount(3);
  for (const header of await headers.all()) {
    await expect(header).not.toHaveAttribute("aria-sort");
  }
});

/** The number a row bears in the first cell of the grid, as the grid shows it. */
async function numberOf(grid: Locator, name: RegExp): Promise<string> {
  return numberOfRow(grid.getByRole("row", { name }));
}

/** The number of a row already found, as the grid shows it. */
async function numberOfRow(row: Locator): Promise<string> {
  const number = await row
    .getByRole("gridcell")
    .first()
    .evaluate((cell) => /\d+/.exec(cell.textContent)?.[0] ?? "");
  expect(number).not.toBe("");
  return number;
}

/** What reads where an element lies: the gestures of a journey never pass through these. */
const READS = new Set<PropertyKey>(["boundingBox", "elementHandle", "evaluate"]);

/**
 * A locator that lets the page change, by `change`, at the first moment its element is read: what
 * reads the page before then reads it as it was, what reads the element reads it as it became.
 */
function changedAtFirstRead(locator: Locator, change: () => Promise<void>): Locator {
  let changed: Promise<void> | undefined;
  return new Proxy(locator, {
    get(target, property, receiver): unknown {
      const value: unknown = Reflect.get(target, property, receiver);
      if (!READS.has(property) || typeof value !== "function") {
        return value;
      }
      return async (...args: unknown[]): Promise<unknown> => {
        changed ??= change();
        await changed;
        return (value as (...read: unknown[]) => Promise<unknown>).apply(target, args);
      };
    },
  });
}

test("holds the totals of the planning in the window as the grid lays out anew on hydration, measured on either side of it @shared [WF-IHM-0060-A]", async ({
  page,
}) => {
  // The grid as the server renders it: fitted to the project and not yet measured, the Gantt holds
  // the legend of its days off under the grid; hydrated, it measures its column, whose days take under
  // a pixel on the witness, and the legend goes — the grid grows into its place. Under load, the
  // journey above measured the grid across that change: its box before, its totals after, each in
  // place in its own layout, out of place against each other (#1522). The script of the Gantt — the
  // one that tints the days off — is held here until the grid has been read: the order the load gave
  // by chance, given whatever the load.
  let release = (): void => undefined;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  let held = 0;
  const scripts = await holdScripts(page, async ({ body }) => {
    if (body.includes("data-day-off")) {
      held += 1;
      await released;
    }
  });
  // The page does not finish loading while a script is held: it is read from its first response on.
  await page.goto(`${IN_REVISION}/planning`, { waitUntil: "commit" });
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const legend = page.getByRole("group", { name: "Légende du Gantt" });
  try {
    await expect(legend).toBeVisible({ timeout: WORKING });
    // The script is held indeed: a script renamed or shared would let the grid lay out before it is
    // read, and the journey pass on nothing.
    await expect.poll(() => held, { timeout: WORKING }).toBeGreaterThan(0);
    const totals = grid.getByRole("gridcell", { name: /^Total — 1\s000 tâches$/ });
    expect(await withinBox(grid, totals)).toBe(true);
    // In the window before the grid lays out anew, and after; and when it does so once the box of
    // the grid is read, before its totals are — the legend still there when the box is read.
    const hydratedAtFirstRead = changedAtFirstRead(totals, async () => {
      await expect(legend).toHaveCount(1);
      release();
      await expect(legend).toHaveCount(0, { timeout: WORKING });
    });
    expect(await withinBox(grid, hydratedAtFirstRead)).toBe(true);
    expect(await withinBox(grid, totals)).toBe(true);
  } finally {
    release();
    // The scripts the page loads once hydrated are still being fetched: the route is taken away
    // once they are served (#1635).
    await scripts.remove();
  }
});

test("attaches the leaf under the task of « Lot 1 » to its post « Poste 1.1 » from its cell, by the letter typed, which the server answers [WF-PLA-0170-A]", async ({
  page,
}) => {
  // Row 8, the summary task « Poste de commande » — a name of the planning, not a post of the work
  // breakdown — bears the lot « Lot 1 »; row 9 under it, the leaf « Câblage des armoires », bears
  // nothing. The choices of its cell are the work breakdown of the witness read whole, each lot then
  // its posts: « Lot 1 », then « Poste 1.1 », the post 712 of that lot, which no task bears. The fake
  // back answers `updateTaskFacet` by its first example whatever was written: the task of row 9
  // renamed — what the grid does with an attachment answered is proven on the examples by
  // `planning-writes.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  await expect(page.getByRole("note")).toHaveCount(0);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { attachment: "Rattachement" });
  const lot = grid.getByRole("row", { name: /^8 .*Poste de commande/ });
  await expect(lot.getByRole("gridcell").nth(at.attachment)).toHaveText("Lot 1");
  // Une feuille peut être rattachée à un poste: « P » typed on the cell chooses the first choice
  // whose name starts with it, « Poste 1.1 », the lot « Lot 1 » coming before it.
  const leaf = grid.getByRole("row", { name: /^9 .*Câblage des armoires/ });
  const cell = leaf.getByRole("gridcell").nth(at.attachment);
  await cell.click();
  await expect(cell).toBeFocused();
  const sent = page.waitForRequest(isServerAction);
  await page.keyboard.press("P");
  const choice = page.getByRole("combobox", { name: "Rattachement" });
  await expect(choice).toHaveValue("01926f3a-7c00-7000-8000-000000000712");
  await expect(choice.getByRole("option", { name: "Poste 1.1", selected: true })).toBeAttached();
  await page.keyboard.press("Enter");
  await sent;
  await expect(
    grid.getByRole("row", { name: /^9 .*Câblage et repérage des armoires/ }),
  ).toBeVisible();
});

test("enters the label of a task from the keyboard, traverses the dates its mode computes, and goes on to the next row from its last cell [WF-PLA-0020-A]", async ({
  page,
}) => {
  // Row 9, « Câblage des armoires », in automatic mode: the server names its start and its finish
  // among the fields it computes. Its label written, Tab goes along the cells it takes — the
  // description, the mode, the duration —, past its dates, to its attachment, the last; validated,
  // that one places the cursor on row 13, at the label the row was started from. The fake back
  // answers `updateTaskFacet` by its first example: the task of row 9 renamed. What each other cell
  // sends is proven on the examples by `planning-entry.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, {
    label: "Libellé",
    description: "Description",
    mode: "Mode de planification",
    duration: "Durée",
    start: "Début",
    predecessors: "Prédécesseurs",
    attachment: "Rattachement",
  });
  const leaf = grid.getByRole("row", { name: /^9 .*Câblage/ });
  const cell = (column: number) => leaf.getByRole("gridcell").nth(column);
  // Les dates d'une tâche en mode automatique ne sont pas saisissables: F2 on its start opens no
  // field, and the cell says it is computed, by its accessible name.
  await cell(at.start).click();
  await page.keyboard.press("F2");
  await expect(grid.getByRole("textbox")).toHaveCount(0);
  await expect(cell(at.start)).toHaveAccessibleName(/Calculé/);
  await page.keyboard.press("Escape");
  await cell(at.label).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Libellé" }).fill("Câblage et repérage des armoires");
  const sent = page.waitForRequest(isServerAction);
  await page.keyboard.press("Tab");
  await sent;
  for (const column of [at.description, at.mode, at.duration, at.predecessors, at.attachment]) {
    await expect(cell(column)).toBeFocused();
    await page.keyboard.press("F2");
    await page.keyboard.press("Tab");
  }
  const next = grid.getByRole("row", { name: /^13 / });
  await expect(next.getByRole("gridcell").nth(at.label)).toBeFocused();
  await expect(
    grid.getByRole("row", { name: /^9 .*Câblage et repérage des armoires/ }),
  ).toBeVisible();
});

test("enters a duration with its unit, then the predecessors « 13FD+2 j » of the mounting, and the successor the server redated takes its place in the grid [WF-PLA-0030-A] [WF-PLA-0020-A]", async ({
  page,
}) => {
  // The fake back keeps nothing and answers each write by its first example (`updateTaskFacet`: the
  // task of row 9 renamed; `setPredecessors`: the mounting of row 20, which follows the factory
  // acceptance of row 13 two days later, written on 3 July 2026, and « Mise en service » of row 23,
  // which it redates without writing it, to 23 December 2026 – 5 January 2027): what each sends is
  // proven on the examples by `planning-entry.dom.test.tsx`; here the journey is the keyboard's,
  // and the grid shows what the server answered in place of what was read, the front dating nothing.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, {
    duration: "Durée",
    start: "Début",
    finish: "Fin",
    predecessors: "Prédécesseurs",
  });
  const cableRow = grid.getByRole("row", { name: /^9 .*Câblage/ });
  const duration = cableRow.getByRole("gridcell").nth(at.duration);
  await duration.click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Durée" }).fill("3 sem");
  const durationSent = page.waitForRequest(isServerAction);
  await page.keyboard.press("Enter");
  await durationSent;
  // The duration is a task's own: its cell is entered, and the answer takes its place.
  await expect(cableRow.getByRole("gridcell").nth(at.duration)).not.toHaveAttribute("aria-invalid");

  const mounting = grid.getByRole("row", { name: /^20 .*Montage des armoires sur site/ });
  const commissioning = grid.getByRole("row", { name: /^23 .*Mise en service/ });
  await expect(mounting.getByRole("gridcell").nth(at.predecessors)).toHaveText("13");
  await expect(commissioning.getByRole("gridcell").nth(at.start)).toContainText("21/12/2026");
  const links = mounting.getByRole("gridcell").nth(at.predecessors);
  await links.click();
  await page.keyboard.press("F2");
  const field = grid.getByRole("textbox", { name: "Prédécesseurs" });
  await expect(field).toHaveValue("13");
  await field.fill("13FD+2 j");
  const linksSent = page.waitForRequest(isServerAction);
  await page.keyboard.press("Enter");
  await linksSent;
  await expect(mounting.getByRole("gridcell").nth(at.predecessors)).toHaveText(/^13FD\+2\s*j$/);
  await expect(mounting.getByRole("gridcell").nth(at.start)).toContainText("03/07/2026");
  await expect(commissioning.getByRole("gridcell").nth(at.start)).toContainText("23/12/2026");
  await expect(commissioning.getByRole("gridcell").nth(at.finish)).toContainText("05/01/2027");

  // A number no task bears is refused at the cell, which stays open, saying so: row 0 is numbered by
  // none, so the grid refuses it without asking the server, whose fake back would name a task for
  // any number (the 404 of `resolveRowNumber` is proven on the examples by `planning-entry.dom.test.tsx`).
  await mounting.getByRole("gridcell").nth(at.predecessors).click();
  await page.keyboard.press("F2");
  await grid.getByRole("textbox", { name: "Prédécesseurs" }).fill("0");
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Aucune tâche de la structure ne porte l’un de ces numéros."),
  ).toBeVisible();
  await expect(grid.getByRole("textbox", { name: "Prédécesseurs" })).toHaveAttribute(
    "aria-invalid",
    "true",
  );
});

test("filters the planning by the post « Poste 1.1 » chosen among the work breakdown, the filter shown active in the banner and lifted from it @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres.
  // The choices are the work breakdown of the witness read whole, the lot then its post, each named
  // by its kind. The fake back serves the first example of `listNodes` whatever the filter asks —
  // the contract has no reading filtered by a lot or a post —: the grid stays the structure whole
  // here, and what the page sends is proven by `planning/page.test.tsx`. The subtree and the
  // ancestors the server retains are its own, and are not checked here.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const filter = menuButton(page, "Lot ou poste");
  await expect((await openMenu(page, "Lot ou poste")).getByRole("radio")).toHaveText([
    "Tous les lots et postes",
    "Lot : Lot 1",
    "Poste : Poste 1.1",
  ]);
  await closeMenu(page);
  await pick(page, "Lot ou poste", "Poste\u00a0: Poste 1.1", "radio");
  await expect(page).toHaveURL(
    `${IN_REVISION}/planning?order_item_id=01926f3a-7c00-7000-8000-000000000712`,
    { timeout: WORKING },
  );
  await expect(filter).toContainText("Poste : Poste 1.1");
  const chips = page
    .getByRole("region", { name: "Contexte de lecture" })
    .getByRole("list", { name: "Filtres actifs" })
    .getByRole("listitem");
  await expect(chips).toHaveText(["Poste : Poste 1.1"]);
  await chips.getByRole("link", { name: "Lever le filtre « Poste : Poste 1.1 »" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
  await expect(filter).toContainText("Tous les lots et postes");
  await expect(chips).toHaveCount(0);
});

test("offers no skeleton above the grid of the witness, whose structure bears its tasks @shared [WF-PRJ-0030-A]", async ({
  page,
}) => {
  // The revision of the witness, served by either back, has a main structure that bears its tasks: the
  // grid is not empty, and the command « Engendrer le squelette de planning » is not proposed above
  // it. What it offers in the empty grid, once generated, is proven on the examples by
  // `planning-writes.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  await expect(page.getByRole("treegrid", { name: "Grille de planning" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Engendrer le squelette de planning" }),
  ).toHaveCount(0);
});

test("shows the planning start date of the structure and the dates its tasks started and completed on @shared [WF-PLA-0020-A] [WF-PLA-0080-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  for (const name of ["Démarrée le", "Terminée le"]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("region", { name: "Date de début de planning" })).toContainText(
    "02/03/2026",
  );
});

test("changes the planning start date, the server answering the week before [WF-PLA-0020-A] [WF-PLA-0080-A]", async ({
  page,
}) => {
  // The fake back answers `updateCostStructure` by its first example, the date advanced by a week to
  // 23 February: the grid shows the date answered, and says it keeps nothing. The refusal of a day
  // without a working hour is proven on the examples by `planning-start.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const start = page.getByRole("region", { name: "Date de début de planning" });
  await expect(start).toContainText("02/03/2026");
  await start.getByRole("button", { name: "Modifier la date de début de planning" }).click();
  const form = start.getByRole("form", { name: "Modifier la date de début de planning" });
  await form.getByLabel("Date de début de planning").fill("2026-02-23");
  await form.getByRole("button", { name: "Confirmer la date" }).click();
  await expect(start).toContainText("23/02/2026");
  await expect(start.getByText("La date de début de planning est le 23/02/2026.")).toBeVisible();
});

test("draws the Gantt beside the grid, row for row, the critical path told in words, and modifies no task @shared [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { gantt: "Gantt" });
  // Its axis, in its header, fitted to the plan: its years over their quarters.
  const axis = grid.getByRole("columnheader", { name: "Gantt" });
  await expect(axis).toContainText("2027");
  await expect(axis).toContainText("T3");
  // Each bar by the dates the API gives, on the row of its task.
  const completed = grid.getByRole("row", { name: /^\d+ .*Dossier de conception/ });
  const bar = completed.getByRole("gridcell").nth(at.gantt).getByRole("img");
  await expect(bar).toHaveAccessibleName("Du 09/04/2026 au 15/04/2026");
  const critical = await scrollToPosition(grid, 20);
  const criticalBar = critical.getByRole("gridcell").nth(at.gantt).getByRole("img");
  await expect(criticalBar).toHaveAccessibleName("Du 01/07/2026 au 16/07/2026 — critique");

  // Aucune action de la souris ou du clavier ne modifie une tâche depuis le Gantt: no request but
  // a read leaves the page while it is handled.
  const sent: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET") {
      sent.push(`${request.method()} ${request.url()}`);
    }
  });
  const cell = critical.getByRole("gridcell").nth(at.gantt);
  await cell.click();
  await expect(cell).toBeFocused();
  await expect(cell).toHaveAttribute("aria-readonly", "true");
  for (const key of ["Enter", "F2", "5", "Delete"]) {
    await page.keyboard.press(key);
  }
  await expect(grid.getByRole("textbox")).toHaveCount(0);
  await expect(criticalBar).toHaveAccessibleName("Du 01/07/2026 au 16/07/2026 — critique");

  // Nor does the zoom: Ctrl and plus in the grid, Ctrl and the wheel on the Gantt, the bar.
  await page.keyboard.press("Control+=");
  await expect(axis).toContainText("juil.");
  await cell.hover();
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -100);
  await page.keyboard.up("Control");
  await expect(axis).toContainText("juillet 2026");
  await page.getByRole("button", { name: "Zoom arrière" }).click();
  await page.getByRole("button", { name: "Ajuster au projet" }).click();
  await expect(axis).toContainText("T3");
  await expect(criticalBar).toHaveAccessibleName("Du 01/07/2026 au 16/07/2026 — critique");
  expect(sent).toEqual([]);
});

test("tints the days off of each task in the Gantt, hatched, with a legend @shared [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { gantt: "Gantt" });
  // Zoomed to the weeks, a day is wide enough: the weekends of the task are bands under its bar.
  await page.getByRole("button", { name: "Zoom avant" }).click();
  const completed = grid.getByRole("row", { name: /^\d+ .*Dossier de conception/ });
  const cell = completed.getByRole("gridcell").nth(at.gantt);
  await expect(cell.locator("rect[data-day-off]").first()).toBeAttached();
  // The hatching tells them without their colour, and the legend names them.
  await expect(cell.locator("pattern line").first()).toBeAttached();
  await expect(page.getByRole("group", { name: "Légende du Gantt" })).toContainText("Jour chômé");
});

test("folds a summary in the grid and the Gantt follows, unfolds it from the Gantt and the grid follows, and keeps the fold for the session @shared [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { label: "Libellé", gantt: "Gantt" });
  // A summary of the core at the second level, over « Relance du fournisseur », the last of its
  // siblings: the row after it is « Installation sur site », of the first level.
  // The faux back also serves rows of other plans bearing the same labels: the summary is the one
  // that folds (it alone bears aria-expanded), the task the one under it.
  const summary = grid
    .getByRole("row", { name: /^\d+ .*Retard de livraison des armoires/ })
    .and(grid.locator("[aria-expanded]"));
  const task = grid.getByRole("row", { name: /^\d+ .*Relance du fournisseur/ });
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(summary).toHaveAttribute("aria-level", "2");
  await expect(task.getByRole("gridcell").nth(at.gantt).getByRole("img")).toBeVisible();

  // Une récapitulative pliée dans la grille l'est dans le Gantt: the rows under it leave both,
  // the row after it is that of the next task of the first level (the 11th row in view), and its bracket in the Gantt offers
  // to unfold it.
  await summary.getByRole("gridcell").nth(at.label).getByRole("button", { name: "Plier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "false");
  await expect(task).toHaveCount(0);
  await expect(rowAt(grid, 11)).toHaveAccessibleName(/^\d+ .*Installation sur site/);
  await expect(rowAt(grid, 11)).toHaveAttribute("aria-level", "1");
  await expect(grid).not.toHaveAttribute("aria-rowcount", "1002");
  const ganttOfSummary = summary.getByRole("gridcell").nth(at.gantt);
  await expect(ganttOfSummary.getByRole("img")).toBeVisible();

  // Et réciproquement: unfolded from the Gantt, the grid unfolds.
  await ganttOfSummary.getByRole("button", { name: "Déplier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(task.getByRole("gridcell").nth(at.gantt).getByRole("img")).toBeVisible();
  await expect(grid).toHaveAttribute("aria-rowcount", "1002");

  // By the keys of Microsoft Project, on the cell of the Gantt; kept for the session, read back
  // once the page is opened anew.
  await ganttOfSummary.click();
  await page.keyboard.press("Alt+Minus");
  await expect(summary).toHaveAttribute("aria-expanded", "false");
  await expect(ganttOfSummary).toBeFocused();
  await openHydrated(page, `${IN_REVISION}/planning`);
  await expect(summary).toHaveAttribute("aria-expanded", "false", { timeout: WORKING });
  await expect(task).toHaveCount(0);
  await summary.getByRole("gridcell").nth(at.label).click();
  await page.keyboard.press("Alt+Shift+Equal");
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(task).toBeVisible();
});

/** The frame of the axis of the Gantt that scrolls, in its header: how far, how wide, over what. */
async function axisFrame(header: Locator) {
  return header.evaluate((element) => {
    const frame = [...element.querySelectorAll("div")].find(
      (candidate) => candidate.scrollWidth > candidate.clientWidth,
    );
    return frame === undefined
      ? undefined
      : { left: frame.scrollLeft, frame: frame.clientWidth, width: frame.scrollWidth };
  });
}

// aucune exigence : propre à l'US (US-0530, la date du centre gardée au zoom).
test("keeps the date at the centre of the frame of the Gantt when it zooms in, its header scrolled to it @shared", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const header = page
    .getByRole("treegrid", { name: "Grille de planning" })
    .getByRole("columnheader", { name: "Gantt" });
  const zoomIn = header.getByRole("button", { name: "Zoom avant" });
  // The quarters over their months: the drawing wider than its frame, scrolled to its middle.
  await zoomIn.click();
  await expect.poll(() => axisFrame(header)).toBeDefined();
  await header.evaluate((element) => {
    for (const frame of element.querySelectorAll("div")) {
      if (frame.scrollWidth > frame.clientWidth) {
        frame.scrollLeft = (frame.scrollWidth - frame.clientWidth) / 2;
      }
    }
  });
  const before = await axisFrame(header);
  if (before === undefined) {
    throw new Error("the axis does not scroll");
  }
  const centre = (before.left + before.frame / 2) / before.width;
  await zoomIn.click();
  await expect.poll(async () => (await axisFrame(header))?.width).toBeGreaterThan(before.width);
  const after = await axisFrame(header);
  expect(after?.frame).toBe(before.frame);
  // The same date at the centre, to the pixel the scroll rounds to.
  const kept = centre * (after?.width ?? 0) - before.frame / 2;
  expect(Math.abs((after?.left ?? 0) - kept)).toBeLessThanOrEqual(1);
});

// aucune exigence : propre à l'US (US-0530, la date du centre gardée au zoom depuis « Ajusté au projet »).
test("keeps the date at the centre of the column when it zooms in from the Gantt fitted to the project @shared", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const header = page
    .getByRole("treegrid", { name: "Grille de planning" })
    .getByRole("columnheader", { name: "Gantt" });
  // Fitted to the project is the level it opens at: its command has nothing left to do.
  await expect(header.getByRole("button", { name: "Ajuster au projet" })).toBeDisabled();
  // The frame of the axis is inset from the column; the centre of the column is its date.
  await header.getByRole("button", { name: "Zoom avant" }).click();
  await expect.poll(() => axisFrame(header)).toBeDefined();
  const after = await axisFrame(header);
  const kept = 0.5 * (after?.width ?? 0) - (after?.frame ?? 0) / 2;
  // To the pixel or two the border of the column takes; the inset of the frame, unheeded, put the
  // centre eight pixels of the column, a share of the drawing wider than the frame, away.
  expect(Math.abs((after?.left ?? 0) - kept)).toBeLessThanOrEqual(4);
});

/** The width and the height of the PNG image a download saved, its signature checked. */
async function pngSize(download: Download): Promise<[number, number]> {
  const chunks: Buffer[] = [];
  for await (const chunk of await download.createReadStream()) {
    chunks.push(chunk as Buffer);
  }
  const image = Buffer.concat(chunks);
  expect(image.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  return [image.readUInt32BE(16), image.readUInt32BE(20)];
}

// aucune exigence : propre à l'US (US-0530, l'export PNG du Gantt sur toute son étendue au niveau
// choisi).
test("exports the Gantt as a PNG image over its whole extent at the level chosen, each of its tasks a row @shared", async ({
  page,
}) => {
  test.slow();
  await openHydrated(page, `${IN_REVISION}/planning`);
  const header = page
    .getByRole("treegrid", { name: "Grille de planning" })
    .getByRole("columnheader", { name: "Gantt" });
  const exported = async () => {
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      header.getByRole("button", { name: "Exporter en PNG" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("gantt-PRJ-001.png");
    return pngSize(download);
  };
  // Fitted to the project: a row of 28 points for each of the thousand tasks, as dense as the
  // screen, twice as dense passing the height a canvas holds.
  const [, fittedHeight] = await exported();
  expect(fittedHeight).toBeGreaterThan(1000 * 28);
  // Zoomed in, the whole drawing, not the frame that shows it: its width and the margins. A day
  // takes a pixel and a half: its days off are tinted, and the legend of 24 points names them,
  // which the fitted Gantt, a day under a pixel, had not.
  await header.getByRole("button", { name: "Zoom avant" }).click();
  await expect.poll(() => axisFrame(header)).toBeDefined();
  const drawing = await axisFrame(header);
  const [width, height] = await exported();
  // The column of the names takes its room to the left of the bars (#1428): what the image is wider
  // than the drawing and its margins is the width of the column of the names.
  const names = width - ((drawing?.width ?? 0) + 32);
  expect(names).toBe(NAMES_WIDTH);
  expect(height).toBe(fittedHeight + 24);
});
