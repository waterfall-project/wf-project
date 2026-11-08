// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

test("leads from the planning to its task tree, read only, its depth in the address @shared [WF-PLA-0110-A]", async ({
  page,
}) => {
  // Three bounds of a screen of grid (`WORKING`): more than the thirty seconds of a test.
  test.slow();
  // The leaf, a screen of its own reached by a click, compiled first (`e2e/compile.ts`). The tree
  // asks the server for the summaries down to its depth (`summaries_only`, `max_level`) and applies
  // no criterion to the answer (#496).
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
  const depths = page.getByRole("navigation", { name: "Niveau affiché" });
  if (inService) {
    // The service selects the summaries down to the level asked: nothing deeper is drawn.
    await expect(tree.getByRole("treeitem", { level: 2 }).first()).toBeVisible({
      timeout: WORKING,
    });
    await expect(tree.getByRole("treeitem", { level: 4 })).toHaveCount(0);
    await expect(depths.getByRole("link").first()).toHaveText("Niveau 1");
  } else {
    // The fake back renders the structure whatever the tree asks, and the screen keeps none of it
    // aside (#496): the three roots of the core, then the nine phases drawn about it.
    await expect(tree.getByRole("treeitem", { level: 2 })).toHaveCount(12, { timeout: WORKING });
    await expect(tree.getByRole("treeitem", { name: /^8 Poste de commande/ })).toBeVisible();
    // The levels the structure has, as the server says them, and not one more (#494).
    await expect(depths.getByRole("link")).toHaveText(["Niveau 1", "Niveau 2"]);
  }
  // One stop of the tabulation, whose arrows go through it.
  await tree.getByRole("treeitem").first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(tree.getByRole("treeitem", { name: /^1 Études/ })).toBeFocused();
  // The first level alone, by the address: the structure read anew, in the bound of a grid.
  await page.getByRole("link", { name: "Niveau 1" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/task-tree?depth=1`, { timeout: WORKING });
  if (inService) {
    await expect(tree.getByRole("treeitem", { level: 3 })).toHaveCount(0);
  }
  // The image is asked from the head, at the level shown: a task of the shell, followed.
  await page.getByRole("button", { name: "Exporter l’image de l’arborescence de tâches" }).click();
  await page.getByRole("button", { name: /^Tâches et messages\s:/ }).click();
  const tasks = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Tâches de fond" });
  await expect(
    tasks
      .getByRole("listitem")
      .filter({ hasText: /Export/ })
      .first(),
  ).toBeVisible();
});
