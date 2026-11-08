// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";
import { inService, test } from "./mode";
import { createOwnProject, openRevision } from "./own-project";
import { rowAt } from "./scroll";

// The reading context of the screens of a project, against the fake back and, tagged `@shared`,
// against the service. The service plays the banner on the screens it serves: those of a project
// created, its settings, its revisions and, since EP-06 (US-1470), its planning. The screens of the
// remaining to commit, the risks and the indicators wait for their EPIC, each lifting its own entry.
const BEFORE_THE_REMAINING = "EP-09 serves the remaining to commit, EP-08 the risks";
const BEFORE_THE_INDICATORS = "EP-10 serves the indicators the banner filters";
const BEFORE_THE_DIFFERENTIALS = "EP-08 serves the differential structures of a revision";

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

test("each screen of the data of a project names the project and the revision shown @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Against the service, the planning alone: the page of a project leads to the planning of its
  // revision in progress, which names the project and the revision (the last path below).
  test.skip(inService, BEFORE_THE_REMAINING);
  // The risks, a screen of its own reached by a click, and the planning the page of the project
  // leads to, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/risks`, `${IN_REVISION}/planning`);
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

  // The page of the project itself leads to its revision in progress, which names it too (US-0720).
  await page.goto(`/projects/${PROJECT}`);
  await expect(page).toHaveURL(`${IN_REVISION}/planning`);
  await expect(banner(page).getByRole("definition").first()).toHaveText(
    "Modernisation du poste de commande",
  );
});

test("an active filter is visible without opening the panel of filters @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_THE_INDICATORS);
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

test("a grid opened on a differential structure names it, chosen in the banner, and the main structure again @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  test.skip(inService, BEFORE_THE_DIFFERENTIALS);
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
  // (US-0500): a task modified, a task added, a task modified again. The planning asks for tasks
  // alone (`kinds`): the lines of the amendment, one unchanged and one removed, are not among its
  // rows. The first five tasks, in this order, are those
  // `test_the_ranks_among_the_tasks_the_planning_journeys_read` holds (tools/tests/
  // test_mockstructure.py), with the difference each bears.
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const mark = (row: number) => rowAt(grid, row).getByRole("gridcell").first();
  await expect(grid.getByRole("columnheader").first()).toHaveAccessibleName("Écart");
  await expect(mark(1)).toHaveText("MModifié");
  await expect(mark(2)).toHaveText("MModifié");
  await expect(mark(3)).toHaveText("+Ajouté");
  await expect(mark(4)).toHaveText("+Ajouté");
  await expect(mark(5)).toHaveText("MModifié");
  // The head of the grid names it too.
  await expect(page.getByRole("main")).toContainText("Avenant 2 — reprise des essais ·");

  // The main structure is read by default: chosen, the address no longer names one.
  await named("Avenant 2 — reprise des essais").click();
  await menu.getByRole("menuitemradio", { name: "Structure principale" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
  await expect(facts.filter({ hasText: /^Avenant$/ })).toHaveCount(0);
});

test("the screens of a project created name the project, then the revision opened, in the reading context, as the service keeps them @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the project it is asked to create");
  test.slow();
  const own = await createOwnProject(page, "Contexte");
  await openHydrated(page, `${own.path}/settings`);
  await expect(banner(page).getByRole("definition").first()).toHaveText(own.label);

  await openRevision(page, own);
  await expect(banner(page).getByRole("definition").first()).toHaveText(own.label);
  await expect(banner(page)).toContainText("Révision en cours");
});

test("the planning of a project created names the project and the revision in progress it leads to, as the service keeps them @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the project it is asked to create");
  test.slow();
  const own = await createOwnProject(page, "Contexte du planning");
  await openRevision(page, own);
  // The page of the project leads to the planning of its revision in progress (US-0720).
  await page.goto(own.path);
  await expect(page).toHaveURL(new RegExp(`${own.path}/revisions/[^/]+/planning$`), {
    timeout: WORKING,
  });
  await expect(banner(page).getByRole("definition").first()).toHaveText(own.label);
  await expect(banner(page)).toContainText("Révision en cours");
  await expect(page.getByRole("treegrid", { name: "Grille de planning" })).toBeVisible({
    timeout: WORKING,
  });
});
