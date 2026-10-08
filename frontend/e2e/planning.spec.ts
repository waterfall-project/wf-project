// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

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

  // Dans la grille de planning, aucun en-tête de colonne ne propose de tri: of its twelve headers,
  // the number and the eleven columns, none holds a button, none says a sort.
  const headers = grid.getByRole("columnheader");
  await expect(headers).toHaveCount(12);
  await expect(headers.getByRole("button")).toHaveCount(0);
  for (const header of await headers.all()) {
    await expect(header).not.toHaveAttribute("aria-sort");
  }
});

test("draws the Gantt beside the grid, row for row, the critical path told in words, and modifies no task [WF-PLA-0090-A]", async ({
  page,
}) => {
  await openHydrated(page, `${IN_REVISION}/planning`);
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { gantt: "Gantt" });
  // Its axis, in its header, the months of the plan.
  await expect(grid.getByRole("columnheader", { name: "Gantt" })).toContainText("janv. 27");
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
  expect(sent).toEqual([]);
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
  await page.getByRole("link", { name: "Arborescence de tâches" }).click();
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
  await page.getByRole("link", { name: "Chronologies" }).click();
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
