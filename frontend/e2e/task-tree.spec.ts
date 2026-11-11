// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type Browser, expect } from "@playwright/test";

import type { components } from "../src/api/generated/schema";
import { DEFAULT_DEPTH } from "../src/components/tree/summaries";
import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { API, frontToken, type LocalPerson } from "./service/realm";

type Schemas = components["schemas"];

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

/** The depth of the summaries of the planning, as the service says it for the request of the tree. */
async function summaryDepth(browser: Browser, manager: LocalPerson | undefined): Promise<number> {
  if (manager === undefined) {
    throw new Error("a path in the service has its manager");
  }
  const context = await browser.newContext();
  try {
    const headers = { Authorization: `Bearer ${await frontToken(browser, manager)}` };
    const revision = `${API}/projects/${PROJECT}/revisions/${REVISION}`;
    const structures = await context.request.get(`${revision}/structures`, { headers });
    expect(structures.status(), "GET structures").toBe(200);
    const main = ((await structures.json()) as Schemas["CostStructure"][]).find(
      ({ kind }) => kind === "main",
    );
    expect(main, "a main structure").toBeDefined();
    const nodes = await context.request.get(
      `${revision}/structures/${main?.structure_id ?? ""}/nodes`,
      {
        headers,
        params: {
          kinds: "task",
          summaries_only: true,
          max_level: DEFAULT_DEPTH,
          fields: "parent_id",
        },
      },
    );
    expect(nodes.status(), "GET nodes").toBe(200);
    return ((await nodes.json()) as { meta: Schemas["NodeListMeta"] }).meta.summary_depth;
  } finally {
    await context.close();
  }
}

test("leads from the planning to its task tree, read only, its depth in the address @shared [WF-PLA-0110-A] [WF-PLA-0120-A]", async ({
  page,
  browser,
  manager,
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
  // Against the service the tree has the depth the service says (`meta.summary_depth`, #494), read
  // from the service itself, with the request the screen makes (the server of Next makes it, out of
  // reach of the browser): the screen draws as many levels as it says, none being the project alone.
  let summarized = false;
  if (inService) {
    const says = await summaryDepth(browser, manager);
    summarized = says > 0;
    await expect(tree.getByRole("treeitem", { level: 1 })).toBeVisible({ timeout: WORKING });
    await expect(depths.getByRole("link")).toHaveCount(says);
    if (summarized) {
      await expect(tree.getByRole("treeitem", { level: 2 }).first()).toBeVisible();
      await expect(tree.getByRole("treeitem", { level: 4 })).toHaveCount(0);
      await expect(depths.getByRole("link").first()).toHaveText("Niveau 1");
    } else {
      await expect(tree.getByRole("treeitem")).toHaveCount(1);
      await expect(page.getByText("Ce planning n’a aucune tâche récapitulative")).toBeVisible();
    }
  } else {
    // The fake back renders the structure whatever the tree asks, and the screen keeps none of it
    // aside (#496): the three roots of the core, then the nine phases drawn about it.
    await expect(tree.getByRole("treeitem", { level: 2 })).toHaveCount(12, { timeout: WORKING });
    await expect(tree.getByRole("treeitem", { name: /^8 Poste de commande/ })).toBeVisible();
    // The levels the structure has, as the server says them, and not one more (#494).
    await expect(depths.getByRole("link")).toHaveText(["Niveau 1", "Niveau 2"]);
  }
  if (!inService || summarized) {
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
