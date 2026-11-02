// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { rowAt } from "./scroll";

// The fake back serves the first example of each operation: the project in progress, its
// current revision — a draft, without a version name —, its structures — the main one, the
// amendment 2, a differential not merged, and the own estimates of three risks —, and its two
// sub-projects. A marked
// revision is shown by the tests of the banner, from the example the contract names.
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000801";
const IN_REVISION = `/projects/${PROJECT}/revisions/${REVISION}`;

/** The banner of the reading context of the page. */
function banner(page: Page) {
  return page.getByRole("region", { name: "Contexte de lecture" });
}

test("each screen of the data of a project names the project and the revision shown [WF-IHM-0020-A]", async ({
  page,
}) => {
  // The risks, a screen of its own reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/risks`);
  await page.goto(`${IN_REVISION}/remaining`);
  await expect(banner(page).getByRole("definition")).toHaveText([
    "Modernisation du poste de commande",
    "Révision en cours",
    "En cours d’élaboration",
    "Copie de « Référence »",
  ]);

  // From one function of the revision to the next, the banner names the same context.
  await page
    .getByRole("navigation", { name: "Fonctions" })
    .getByRole("link", { name: "Gestion des risques" })
    .click();
  await expect(page).toHaveURL(`${IN_REVISION}/risks`);
  await expect(banner(page)).toContainText("Modernisation du poste de commande");
  await expect(banner(page)).toContainText("Révision en cours");

  // The page of the project itself names it too.
  await page.goto(`/projects/${PROJECT}`);
  await expect(banner(page).getByRole("definition")).toHaveText([
    "Modernisation du poste de commande",
  ]);
});

test("an active filter is visible without opening the panel of filters [WF-IHM-0020-A]", async ({
  page,
}) => {
  // The indicators read both the sub-project and the date: their banner shows both (#302).
  await page.goto(`${IN_REVISION}/indicators?subproject_id=${SUBPROJECT}&as_of=2026-05-31`);
  const chips = banner(page).getByRole("list", { name: "Filtres actifs" }).getByRole("listitem");
  // The sub-project restricts every figure but the tracking of the milestones (WF-IND-0020).
  await expect(chips).toHaveText([
    "Sous-projet : SP-CMD — Poste de commande, hors suivi des jalons",
    "Date de calcul : 31 mai 2026",
  ]);
  await expect(chips.first()).toBeVisible();
  await expect(chips.last()).toBeVisible();

  // A chip lifts its filter, and the other one stays in the address and in the banner.
  await banner(page)
    .getByRole("link", { name: "Lever le filtre « Date de calcul : 31 mai 2026 »" })
    .click();
  await expect(page).toHaveURL(`${IN_REVISION}/indicators?subproject_id=${SUBPROJECT}`);
  await expect(chips).toHaveText([
    "Sous-projet : SP-CMD — Poste de commande, hors suivi des jalons",
  ]);
});

test("a grid opened on a differential structure names it, chosen in the banner, and the main structure again [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Une grille ouverte sur une structure différentielle nomme cette structure. The fake back serves
  // the nodes of the amendment at its address (`nodes_amendment`, #1219): what the page asks of each
  // structure is proven by `planning/page.test.tsx`.
  const amendment = "01926f3a-7c00-7000-8000-000000000203";
  const named = (structure: string) =>
    banner(page).getByRole("button", {
      name: `Changer de structure, «\u00a0${structure}\u00a0» lue`,
    });
  await openHydrated(page, `${IN_REVISION}/planning`);
  await named("Structure principale").click();
  const menu = page.getByRole("menu");
  await expect(menu.getByRole("group", { name: "Avenant" }).getByRole("menuitemradio")).toHaveText([
    "Avenant 2 — reprise des essais",
  ]);
  await menu.getByRole("menuitemradio", { name: "Avenant 2 — reprise des essais" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning?structure=${amendment}`, {
    timeout: WORKING,
  });
  const facts = banner(page).getByRole("definition");
  await expect(facts.filter({ hasText: /^Avenant 2 — reprise des essais$/ })).toBeVisible();
  await expect(facts.filter({ hasText: /^Avenant$/ })).toBeVisible();
  // The grid reads the nodes of the amendment, each marked by the difference the server renders
  // (US-0500): a task modified, a line unchanged, a line removed, read in its place, a task added.
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const mark = (row: number) => rowAt(grid, row).getByRole("gridcell").first();
  await expect(grid.getByRole("columnheader").first()).toHaveAccessibleName("Écart");
  await expect(mark(1)).toHaveText("MModifié");
  await expect(mark(3)).toHaveText("");
  await expect(mark(4)).toHaveText("-Retiré");
  await expect(mark(5)).toHaveText("+Ajouté");
  // The head of the grid names it too.
  await expect(page.getByRole("main")).toContainText("Avenant 2 — reprise des essais ·");

  // The main structure is read by default: chosen, the address no longer names one.
  await named("Avenant 2 — reprise des essais").click();
  await menu.getByRole("menuitemradio", { name: "Structure principale" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
  await expect(facts.filter({ hasText: /^Avenant$/ })).toHaveCount(0);
});
