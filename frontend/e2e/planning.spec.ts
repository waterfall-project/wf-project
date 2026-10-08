// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { columnsOf } from "./columns";
import { compile } from "./compile";
import { scrollToPosition, withinBox } from "./scroll";

// The fake back serves the first example of `listNodes` whatever `kinds` asks — the structure of
// the volumes of §4.6.2 (EP-02/L2), a thousand tasks and their lines —: its lines show here too,
// where the service renders the tasks alone — the component and page tests prove that the
// planning asks for them. The journey reads the structure by marks the generator writes, which
// `test_the_marks_the_journeys_read` (tools/tests/test_mockstructure.py) holds: row 3, a task
// completed off the critical path; row 22, started, which follows it; row 453, a task of the
// critical path not started, which follows row 434, further down — where the fake back numbers
// the rows as it orders them.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

test("opens the grid of the planning: its icons named, the critical path marked, the predecessors by row number", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/planning`);
  await expect(page).toHaveTitle("Planification · Modernisation du poste de commande — Waterfall");
  const grid = page.getByRole("grid", { name: "Grille de planning" });
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
  const completed = grid.getByRole("row", { name: /^3 .*Préparation 1\.1\.1/ });
  await expect(completed.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Terminée" })).toBeVisible();
  await expect(completed.getByRole("img", { name: "Chemin critique" })).toHaveCount(0);
  const at = await columnsOf(grid, { predecessors: "Prédécesseurs" });
  const follower = grid.getByRole("row", { name: /^22 .*Réalisation 1\.1\.4/ });
  await expect(follower.getByRole("img", { name: "Démarrée" })).toBeVisible();
  await expect(follower.getByRole("gridcell").nth(at.predecessors)).toHaveText("3");

  // Further down, the critical path: marked by its icon, whatever the colour.
  const critical = await scrollToPosition(grid, 453);
  await expect(critical).toHaveAccessibleName(/^453 .*Préparation 1\.3\.9/);
  await expect(critical.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Chemin critique" })).toBeVisible();
  await expect(critical.getByRole("gridcell").nth(at.predecessors)).toHaveText("434");

  // A header asks the server for its sort: the address says it.
  await grid
    .getByRole("columnheader", { name: "Mode de planification" })
    .getByRole("button")
    .click();
  await expect(page).toHaveURL(/sort_by=scheduling_mode&sort_order=asc/);
});

test("draws the Gantt beside the grid, row for row, the critical path told in words, and modifies no task [WF-PLA-0090-A]", async ({
  page,
}) => {
  await page.goto(`${IN_REVISION}/planning`);
  const grid = page.getByRole("grid", { name: "Grille de planning" });
  const at = await columnsOf(grid, { gantt: "Gantt" });
  // Its axis, in its header, the months of the plan.
  await expect(grid.getByRole("columnheader", { name: "Gantt" })).toContainText("janv. 27");
  // Each bar by the dates the API gives, on the row of its task.
  const completed = grid.getByRole("row", { name: /^3 .*Préparation 1\.1\.1/ });
  const bar = completed.getByRole("gridcell").nth(at.gantt).getByRole("img");
  await expect(bar).toHaveAccessibleName("Du 02/03/2026 au 13/03/2026");
  const critical = await scrollToPosition(grid, 453);
  const criticalBar = critical.getByRole("gridcell").nth(at.gantt).getByRole("img");
  await expect(criticalBar).toHaveAccessibleName("Du 24/03/2026 au 06/04/2026 — critique");

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
  await expect(criticalBar).toHaveAccessibleName("Du 24/03/2026 au 06/04/2026 — critique");
  expect(sent).toEqual([]);
});

test("leads from the planning to its task tree, read only, its depth in the address", async ({
  page,
}) => {
  // The leaf, a screen of its own reached by a click, compiled first (`e2e/compile.ts`). The tree
  // asks the server for the summaries down to its depth (`summaries_only`, `max_level`), and keeps
  // them once more of what the fake back renders, the volumes whole (#463).
  await compile(page.request, `${IN_REVISION}/task-tree`);
  await page.goto(`${IN_REVISION}/planning`);
  await page.getByRole("link", { name: "Arborescence de tâches" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/task-tree`);
  await expect(page).toHaveTitle(
    "Arborescence de tâches · Modernisation du poste de commande — Waterfall",
  );
  // The summaries of the first two levels, under the project; no leaf, no milestone.
  const tree = page.getByRole("tree", { name: "Arborescence des tâches récapitulatives" });
  await expect(tree.getByRole("treeitem", { level: 2 })).toHaveCount(10);
  await expect(tree.getByRole("treeitem", { name: /^2 Études — Poste de commande/ })).toBeVisible();
  await expect(tree.getByText("Préparation 1.1.1")).toHaveCount(0);
  // One stop of the tabulation, whose arrows go through it.
  await tree.getByRole("treeitem").first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(tree.getByRole("treeitem", { name: /^1 Études/ })).toBeFocused();
  // The first level alone, by the address.
  await page.getByRole("link", { name: "Niveau 1" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/task-tree?depth=1`);
  await expect(tree.getByRole("treeitem", { level: 3 })).toHaveCount(0);
});

test("leads from the planning to the timelines of the project, read only", async ({ page }) => {
  await compile(page.request, `${IN_REVISION}/timelines`);
  await page.goto(`${IN_REVISION}/planning`);
  await page.getByRole("link", { name: "Chronologies" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/timelines`);
  await expect(page).toHaveTitle("Chronologies · Modernisation du poste de commande — Waterfall");
  await expect(page.getByRole("region", { name: "Contexte de lecture" })).toContainText(
    "Modernisation du poste de commande",
  );
  // The timelines of the project; the screen asks the tasks of the one shown (`timeline_id`), and
  // keeps those inscribed to it of what the fake back renders: the volumes inscribe none (#463).
  await expect(page.getByRole("link", { name: "Comité de pilotage" })).toHaveAttribute(
    "aria-current",
    "true",
  );
  await page.getByRole("link", { name: "Revue client" }).click();
  await expect(page.getByRole("link", { name: "Revue client" })).toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(
    page.getByText("Aucune tâche de cette révision n’est inscrite à cette chronologie."),
  ).toBeVisible();
});
