// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

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

test("opens the grid of the planning: its icons named, the critical path marked, the predecessors by row number", async ({
  page,
}) => {
  await page.goto(`/projects/${PROJECT}/revisions/${REVISION}/planning`);
  await expect(page).toHaveTitle("Planification · Modernisation du poste de commande — Waterfall");
  const grid = page.getByRole("grid", { name: "Grille de planning" });
  for (const name of ["N°", "Libellé", "Mode de planification", "Avancement", "Calculé Marge"]) {
    await expect(grid.getByRole("columnheader", { name })).toBeVisible();
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
  const follower = grid.getByRole("row", { name: /^22 .*Réalisation 1\.1\.4/ });
  await expect(follower.getByRole("img", { name: "Démarrée" })).toBeVisible();
  await expect(follower.getByRole("gridcell").last()).toHaveText("3");

  // Further down, the critical path: marked by its icon, whatever the colour.
  const critical = await scrollToPosition(grid, 453);
  await expect(critical).toHaveAccessibleName(/^453 .*Préparation 1\.3\.9/);
  await expect(critical.getByRole("img", { name: "Tâche", exact: true })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Automatique" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Non démarrée" })).toBeVisible();
  await expect(critical.getByRole("img", { name: "Chemin critique" })).toBeVisible();
  await expect(critical.getByRole("gridcell").last()).toHaveText("434");

  // A header asks the server for its sort: the address says it.
  await grid
    .getByRole("columnheader", { name: "Mode de planification" })
    .getByRole("button")
    .click();
  await expect(page).toHaveURL(/sort_by=scheduling_mode&sort_order=asc/);
});
