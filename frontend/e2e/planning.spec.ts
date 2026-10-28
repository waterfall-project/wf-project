// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Download, expect, type Locator, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { rowAt, scrollToPosition, withinBox } from "./scroll";

// The fake back serves the first example of `listNodes` whatever `kinds` asks — the structure of
// the witness at the sizes of §4.6.2, its core first, a thousand tasks and their lines (#376) —:
// its lines show here too, where the service renders the tasks alone — the component and page
// tests prove that the planning asks for them. The journey reads the structure by marks the
// generator writes, which `test_the_marks_the_journeys_read` (tools/tests/test_mockstructure.py)
// holds: row 7, a task of the core completed off the critical path; row 311, started, which follows
// row 291; row 39, a task of the critical path not started, which follows the factory acceptance of
// row 18; row 13, a summary of the second level over the task of row 14, before row 18 — where the
// fake back numbers the rows as it orders them.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

test("opens the grid of the planning: its icons named, the critical path marked, the predecessors by row number, no header offering a sort [WF-IHM-0060-A]", async ({
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
  ]) {
    await expect(grid.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  // The grid holds in the window as it opens: its totals are in view.
  expect(
    await withinBox(grid, grid.getByRole("gridcell", { name: /^Total — 1\s000 tâches$/ })),
  ).toBe(true);
  const completed = grid.getByRole("row", { name: /^7 .*Dossier de conception/ });
  await expect(completed.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Terminée" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Chemin critique" })).toHaveCount(0);
  const at = await columnsOf(grid, { predecessors: "Prédécesseurs" });
  // Row 39 is past the rows in view as the grid opens: scrolled to, so that it is checked in the
  // window whatever the height of the grid, never in the margin the grid renders around it. The
  // critical path, marked by its icon, whatever the colour.
  const critical = await scrollToPosition(grid, 39);
  await expect(critical).toHaveAccessibleName(/^39 .*Revue 1\.1\.3/);
  await expect(critical.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Chemin critique" })).toBeVisible();
  await expect(critical.getByRole("gridcell").nth(at.predecessors)).toHaveText("18");

  // Further down, a task started, which follows another by its row number.
  const follower = await scrollToPosition(grid, 311);
  await expect(follower).toHaveAccessibleName(/^311 .*Revue 1\.2\.11/);
  await expect(follower.getByRole("img", { name: "Démarrée" })).toBeVisible();
  await expect(follower.getByRole("gridcell").nth(at.predecessors)).toHaveText("291");

  // Dans la grille de planning, aucun en-tête de colonne ne propose de tri: of its thirteen headers,
  // the number and the twelve columns, none holds a button but the three of the zoom and the export
  // in that of the Gantt, none says a sort.
  const headers = grid.getByRole("columnheader");
  await expect(headers).toHaveCount(13);
  await expect(headers.getByRole("button")).toHaveCount(4);
  await expect(
    headers.getByRole("group", { name: "Zoom du Gantt" }).getByRole("button"),
  ).toHaveCount(3);
  for (const header of await headers.all()) {
    await expect(header).not.toHaveAttribute("aria-sort");
  }
});

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

test("holds the totals of the planning in the window as the grid lays out anew on hydration, measured on either side of it [WF-IHM-0060-A]", async ({
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
  await page.route("**/_next/static/chunks/**", async (route) => {
    // On a connection of its own: one kept open across the held script was closed by the front as
    // idle while the journey reused it (ECONNRESET, under load).
    const response = await page.request.get(route.request().url(), {
      headers: { connection: "close" },
    });
    if ((await response.text()).includes("data-day-off")) {
      held += 1;
      await released;
    }
    await route.fulfill({ response });
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
    // The scripts the page loads once hydrated are still being fetched: the page waits for them.
    await page.unrouteAll({ behavior: "wait" });
  }
});

test("attaches the leaf under the task of « Lot 1 » to its post « Poste 1.1 » from its cell, by the letter typed, which the server answers, and says the fake back keeps nothing [WF-PLA-0170-A]", async ({
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
  await expect(page.getByRole("note")).toContainText("Maquette");
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
  const sent = page.waitForRequest((request) => request.method() === "POST");
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
  // that one places the cursor on row 10, at the label the row was started from. The fake back
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
  const sent = page.waitForRequest((request) => request.method() === "POST");
  await page.keyboard.press("Tab");
  await sent;
  for (const column of [at.description, at.mode, at.duration, at.predecessors, at.attachment]) {
    await expect(cell(column)).toBeFocused();
    await page.keyboard.press("F2");
    await page.keyboard.press("Tab");
  }
  const next = grid.getByRole("row", { name: /^10 / });
  await expect(next.getByRole("gridcell").nth(at.label)).toBeFocused();
  await expect(
    grid.getByRole("row", { name: /^9 .*Câblage et repérage des armoires/ }),
  ).toBeVisible();
});

test("enters a duration with its unit, then the predecessors « 18FD+2 j » of the mounting, and the successor the server redated takes its place in the grid [WF-PLA-0030-A] [WF-PLA-0020-A]", async ({
  page,
}) => {
  // The fake back keeps nothing and answers each write by its first example (`updateTaskFacet`: the
  // task of row 9 renamed; `setPredecessors`: the mounting of row 20, which follows the factory
  // acceptance of row 18 two days later, written on 3 July 2026, and « Mise en service » of row 23,
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
  const durationSent = page.waitForRequest((request) => request.method() === "POST");
  await page.keyboard.press("Enter");
  await durationSent;
  // The duration is a task's own: its cell is entered, and the answer takes its place.
  await expect(cableRow.getByRole("gridcell").nth(at.duration)).not.toHaveAttribute("aria-invalid");

  const mounting = grid.getByRole("row", { name: /^20 .*Montage des armoires sur site/ });
  const commissioning = grid.getByRole("row", { name: /^23 .*Mise en service/ });
  await expect(mounting.getByRole("gridcell").nth(at.predecessors)).toHaveText("18");
  await expect(commissioning.getByRole("gridcell").nth(at.start)).toContainText("21/12/2026");
  const links = mounting.getByRole("gridcell").nth(at.predecessors);
  await links.click();
  await page.keyboard.press("F2");
  const field = grid.getByRole("textbox", { name: "Prédécesseurs" });
  await expect(field).toHaveValue("18");
  await field.fill("18FD+2 j");
  const linksSent = page.waitForRequest((request) => request.method() === "POST");
  await page.keyboard.press("Enter");
  await linksSent;
  await expect(mounting.getByRole("gridcell").nth(at.predecessors)).toHaveText(/^18FD\+2\s*j$/);
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

test("filters the planning by the post « Poste 1.1 » chosen among the work breakdown, the filter shown active in the banner and lifted from it [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Un filtre actif est visible sans avoir à ouvrir le panneau de filtres.
  // The choices are the work breakdown of the witness read whole, the lot then its post, each named
  // by its kind. The fake back serves the first example of `listNodes` whatever the filter asks —
  // the contract has no reading filtered by a lot or a post —: the grid stays the structure whole
  // here, and what the page sends is proven by `planning/page.test.tsx`. The subtree and the
  // ancestors the server retains are its own, and are not checked here.
  await openHydrated(page, `${IN_REVISION}/planning`);
  const filter = page.getByRole("combobox", { name: "Lot ou poste" });
  await expect(filter.getByRole("option")).toHaveText([
    "Tous les lots et postes",
    "Lot : Lot 1",
    "Poste : Poste 1.1",
  ]);
  await filter.selectOption({ label: "Poste\u00a0: Poste 1.1" });
  await expect(page).toHaveURL(
    `${IN_REVISION}/planning?order_item_id=01926f3a-7c00-7000-8000-000000000712`,
    { timeout: WORKING },
  );
  await expect(filter).toHaveValue("01926f3a-7c00-7000-8000-000000000712");
  const chips = page
    .getByRole("region", { name: "Contexte de lecture" })
    .getByRole("list", { name: "Filtres actifs" })
    .getByRole("listitem");
  await expect(chips).toHaveText(["Poste : Poste 1.1"]);
  await chips.getByRole("link", { name: "Lever le filtre « Poste : Poste 1.1 »" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
  await expect(filter).toHaveValue("");
  await expect(chips).toHaveCount(0);
});

test("offers no skeleton above the grid of the witness, whose structure bears its tasks [WF-PRJ-0030-A]", async ({
  page,
}) => {
  // The fake back serves the revision of the witness, whose main structure bears its tasks: the
  // grid is not empty, and the command « Engendrer le squelette de planning » is not proposed above
  // it. What it offers in the empty grid, once generated, is proven on the examples by
  // `planning-writes.dom.test.tsx`.
  await openHydrated(page, `${IN_REVISION}/planning`);
  await expect(page.getByRole("treegrid", { name: "Grille de planning" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Engendrer le squelette de planning" }),
  ).toHaveCount(0);
});

test("draws the Gantt beside the grid, row for row, the critical path told in words, and modifies no task [WF-PLA-0090-A]", async ({
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
  const completed = grid.getByRole("row", { name: /^7 .*Dossier de conception/ });
  const bar = completed.getByRole("gridcell").nth(at.gantt).getByRole("img");
  await expect(bar).toHaveAccessibleName("Du 09/04/2026 au 15/04/2026");
  const critical = await scrollToPosition(grid, 39);
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

test("tints the days off of each task in the Gantt, hatched, with a legend [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { gantt: "Gantt" });
  // Zoomed to the weeks, a day is wide enough: the weekends of the task are bands under its bar.
  await page.getByRole("button", { name: "Zoom avant" }).click();
  const completed = grid.getByRole("row", { name: /^7 .*Dossier de conception/ });
  const cell = completed.getByRole("gridcell").nth(at.gantt);
  await expect(cell.locator("rect[data-day-off]").first()).toBeAttached();
  // The hatching tells them without their colour, and the legend names them.
  await expect(cell.locator("pattern line").first()).toBeAttached();
  await expect(page.getByRole("group", { name: "Légende du Gantt" })).toContainText("Jour chômé");
});

test("folds a summary in the grid and the Gantt follows, unfolds it from the Gantt and the grid follows, and keeps the fold for the session [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { label: "Libellé", gantt: "Gantt" });
  // A summary of the core at the second level, over the task of row 14, before its next sibling,
  // the factory acceptance of row 18.
  const summary = grid.getByRole("row", { name: /^13 .*Risque survenu — Retard de livraison/ });
  const task = grid.getByRole("row", { name: /^14 .*Relance du fournisseur/ });
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(summary).toHaveAttribute("aria-level", "2");
  await expect(task.getByRole("gridcell").nth(at.gantt).getByRole("img")).toBeVisible();

  // Une récapitulative pliée dans la grille l'est dans le Gantt: the rows under it leave both,
  // the row after it is its next sibling, and its bracket in the Gantt offers to unfold it.
  await summary.getByRole("gridcell").nth(at.label).getByRole("button", { name: "Plier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "false");
  await expect(task).toHaveCount(0);
  await expect(rowAt(grid, 14)).toHaveAccessibleName(/^18 .*Réception usine/);
  await expect(rowAt(grid, 14)).toHaveAttribute("aria-level", "2");
  await expect(grid).not.toHaveAttribute("aria-rowcount", "6002");
  const ganttOfSummary = summary.getByRole("gridcell").nth(at.gantt);
  await expect(ganttOfSummary.getByRole("img")).toBeVisible();

  // Et réciproquement: unfolded from the Gantt, the grid unfolds.
  await ganttOfSummary.getByRole("button", { name: "Déplier" }).click();
  await expect(summary).toHaveAttribute("aria-expanded", "true");
  await expect(task.getByRole("gridcell").nth(at.gantt).getByRole("img")).toBeVisible();
  await expect(grid).toHaveAttribute("aria-rowcount", "6002");

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

test("leads from the planning to its task tree, read only, its depth in the address", async ({
  page,
}) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  // The leaf, a screen of its own reached by a click, compiled first (`e2e/compile.ts`). The tree
  // asks the server for the summaries down to its depth (`summaries_only`, `max_level`), and keeps
  // them once more of what the fake back renders, the volumes whole (#463).
  await compile(page.request, `${IN_REVISION}/task-tree`);
  // Hydrated, the planning follows its link in the browser: the tree arrives answering the keys.
  await openHydrated(page, `${IN_REVISION}/planning`);
  await page.getByRole("main").getByRole("link", { name: "Arborescence de tâches" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/task-tree`, { timeout: WORKING });
  await expect(page).toHaveTitle(
    "Arborescence de tâches · Modernisation du poste de commande — Waterfall",
  );
  // The summaries of the first two levels, under the project; no leaf, no milestone. The tree
  // reads the structure of a thousand tasks: the bound of a grid.
  const tree = page.getByRole("tree", { name: "Arborescence des tâches récapitulatives" });
  // The three roots of the core, then the nine phases drawn about it.
  await expect(tree.getByRole("treeitem", { level: 2 })).toHaveCount(12, { timeout: WORKING });
  await expect(tree.getByRole("treeitem", { name: /^8 Poste de commande/ })).toBeVisible();
  await expect(tree.getByText("Préparation 1.1.1")).toHaveCount(0);
  // The levels the structure has, as the server says them, and not one more (#494).
  const depths = page.getByRole("navigation", { name: "Niveau affiché" });
  await expect(depths.getByRole("link")).toHaveText(["Niveau 1", "Niveau 2"]);
  // One stop of the tabulation, whose arrows go through it.
  await tree.getByRole("treeitem").first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(tree.getByRole("treeitem", { name: /^1 Études/ })).toBeFocused();
  // The first level alone, by the address: the structure read anew, in the bound of a grid.
  await page.getByRole("link", { name: "Niveau 1" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/task-tree?depth=1`, { timeout: WORKING });
  await expect(tree.getByRole("treeitem", { level: 3 })).toHaveCount(0);
});

test("leads from the planning to the timelines of the project, read only", async ({ page }) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  await compile(page.request, `${IN_REVISION}/timelines`);
  await openHydrated(page, `${IN_REVISION}/planning`);
  await page.getByRole("main").getByRole("link", { name: "Chronologies" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/timelines`, { timeout: WORKING });
  await expect(page).toHaveTitle("Chronologies · Modernisation du poste de commande — Waterfall");
  await expect(page.getByRole("region", { name: "Contexte de lecture" })).toContainText(
    "Modernisation du poste de commande",
  );
  // The timelines of the project; the screen asks the tasks of the one shown (`timeline_id`), and
  // keeps those inscribed to it of what the fake back renders (#463): those of the core.
  // They read the structure of a thousand tasks: the bound of a grid.
  await expect(page.getByRole("link", { name: "Comité de pilotage" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
  // Another timeline, by the address: the structure read anew, in the bound of a grid.
  await page.getByRole("link", { name: "Revue client" }).click();
  await expect(page.getByRole("link", { name: "Revue client" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
  // The customer follows the two receptions of the core, the structure its first rows (#376).
  await expect(page.getByRole("main")).toContainText("Réception usine");
  await expect(
    page.getByText("Aucune tâche de cette révision n’est inscrite à cette chronologie."),
  ).toHaveCount(0);
});

test("creates a timeline by its name, and deletes the one shown once confirmed, the screen showing the first one left (EP-14/L44f)", async ({
  page,
}) => {
  // Two readings of the structure of a thousand tasks, each in the bound of a grid.
  test.slow();
  await openHydrated(page, `${IN_REVISION}/timelines`);
  const steering = page.getByRole("link", { name: "Comité de pilotage" });
  await expect(steering).toHaveAttribute("aria-current", "true", { timeout: WORKING });
  await expect(page.getByRole("note")).toContainText("Maquette");
  await page.getByRole("button", { name: "Nouvelle chronologie" }).click();
  const form = page.getByRole("dialog", { name: "Nouvelle chronologie" });
  await form.getByRole("textbox", { name: "Nom" }).fill("Réunion de chantier");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  await expect(page.getByText("Chronologie « Réunion de chantier » créée.")).toBeVisible();

  await page
    .getByRole("button", { name: "Supprimer la chronologie «\u00a0Comité de pilotage\u00a0»" })
    .click();
  const confirmation = page.getByRole("dialog", { name: /^Supprimer la chronologie/ });
  await expect(confirmation).toContainText("les tâches et les jalons gardent leurs dates");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(page.getByText("Chronologie « Comité de pilotage » supprimée.")).toBeVisible();
  await expect(steering).toHaveCount(0);
  await expect(page).toHaveURL(
    `${IN_REVISION}/timelines?timeline=01926f3a-7c00-7000-8000-000000001001`,
    { timeout: WORKING },
  );
  await expect(page.getByRole("link", { name: "Revue client" })).toHaveAttribute(
    "aria-current",
    "true",
    { timeout: WORKING },
  );
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
test("keeps the date at the centre of the frame of the Gantt when it zooms in, its header scrolled to it", async ({
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
test("keeps the date at the centre of the column when it zooms in from the Gantt fitted to the project", async ({
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
test("exports the Gantt as a PNG image over its whole extent at the level chosen, each of its tasks a row", async ({
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
  expect(width).toBe((drawing?.width ?? 0) + 32);
  expect(height).toBe(fittedHeight + 24);
});
