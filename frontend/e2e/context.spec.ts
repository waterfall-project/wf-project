// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page } from "@playwright/test";

import { CONTEXT_PATH_IN_SERVICE, WORKING } from "./bounds";
import { compile } from "./compile";
import { openHydrated } from "./hydration";
import { inService, test } from "./mode";
import { checkOpened, type Opener } from "./opened";
import { createOwnProject, openRevision } from "./own-project";
import { rowAt } from "./scroll";

// The reading context of the screens of a project, against the fake back and, tagged `@shared`,
// against the service. The service plays the banner on the screens it serves: those of a project
// created, its settings, its revisions, its planning (EP-06, US-1470), its estimate (EP-07, US-1560),
// its remaining to commit (EP-09), its indicators (EP-10, US-1730), its risks and its differential
// structures (EP-08, US-2640).

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
  // Against the service, the screens of revision 102 read in it (`CONTEXT_PATH_IN_SERVICE`, #4911).
  if (inService) test.setTimeout(CONTEXT_PATH_IN_SERVICE);
  // The risks, a screen of its own reached by a click, and the planning the page of the project
  // leads to, compiled first (`e2e/compile.ts`).
  await compile(page.request, `${IN_REVISION}/risks`, `${IN_REVISION}/planning`);
  await page.goto(`${IN_REVISION}/remaining`);
  // The definition of the button of the base is empty: the facts are the definitions with a text.
  await expect(banner(page).getByRole("definition").filter({ hasText: /\S/ })).toHaveText([
    "Modernisation du poste de commande",
    "Révision en cours",
    "En cours d’élaboration",
    "Copie de « Référence »",
  ]);
  // The choice of a base, a button alone while the grid compares nothing, named for a screen reader
  // (US-2330).
  await expect(
    banner(page).getByRole("button", { name: "Choisir une base de comparaison" }),
  ).toBeVisible();

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
  // (US-0500). The planning asks for tasks alone (`kinds`): the lines of the amendment are not among
  // its rows. The fake back marks its first five tasks, in this order, as
  // `test_the_ranks_among_the_tasks_the_planning_journeys_read` holds (tools/tests/
  // test_mockstructure.py): a task modified, a task added, a task modified again. The service marks
  // the tasks the amendment 2 touches among the thousand of the witness: modified from the seventh
  // row, two added at the fifteenth, a task modified again at the seventeenth.
  const grid = page.getByRole("treegrid", { name: "Grille de planning" });
  const mark = (row: number) => rowAt(grid, row).getByRole("gridcell").first();
  await expect(grid.getByRole("columnheader").first()).toHaveAccessibleName("Écart");
  const marks: readonly (readonly [row: number, shown: string])[] = inService
    ? [
        [6, ""],
        [7, "MModifié"],
        [8, "MModifié"],
        [9, ""],
        [15, "+Ajouté"],
        [16, "+Ajouté"],
        [17, "MModifié"],
      ]
    : [
        [1, "MModifié"],
        [2, "MModifié"],
        [3, "+Ajouté"],
        [4, "+Ajouté"],
        [5, "MModifié"],
      ];
  for (const [row, shown] of marks) {
    await expect(mark(row)).toHaveText(shown, { timeout: WORKING });
  }
  // The head of the grid names it too.
  await expect(page.getByRole("main")).toContainText("Avenant 2 — reprise des essais ·");

  // The main structure is read by default: chosen, the address no longer names one.
  await named("Avenant 2 — reprise des essais").click();
  await menu.getByRole("menuitemradio", { name: "Structure principale" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/planning`, { timeout: WORKING });
  await expect(facts.filter({ hasText: /^Avenant$/ })).toHaveCount(0);
});

test("from the same grid, another revision of the project opens without going through the history, the sub-project filtered kept [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Depuis la même grille, il ouvre une autre révision du projet sans passer par l'historique. The
  // fake back lists the revisions of the witness (`revisions`), and answers any of them by its first
  // example: the address says the revision opened, the same screen with the same sub-project.
  const reference = "01926f3a-7c00-7000-8000-000000000101";
  await openHydrated(page, `${IN_REVISION}/remaining?subproject_id=${SUBPROJECT}`);
  await banner(page)
    .getByRole("button", { name: "Changer de révision, «\u00a0Révision en cours\u00a0» lue" })
    .click();
  const menu = page.getByRole("menu");
  await expect(menu.getByRole("menuitemradio")).toHaveText([
    "Révision en cours",
    "Référence (référence)",
    "Offre v1.0",
  ]);
  await expect(menu.getByRole("menuitemradio", { checked: true })).toHaveText("Révision en cours");
  await menu.getByRole("menuitemradio", { name: "Référence (référence)" }).click();
  await expect(page).toHaveURL(
    `/projects/${PROJECT}/revisions/${reference}/remaining?subproject_id=${SUBPROJECT}`,
    { timeout: WORKING },
  );
  await expect(page.getByRole("treegrid", { name: "Grille de reste à engager" })).toBeVisible({
    timeout: WORKING,
  });
  await expect(banner(page).getByRole("list", { name: "Filtres actifs" })).toContainText(
    "SP-CMD — Poste de commande",
  );
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

test("the estimate of a project created names the project and the revision in progress, in the reading context, and shows no note of the mock-up, as the service keeps them @shared [WF-IHM-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, "the fake back keeps nothing of the project it is asked to create");
  test.slow();
  const own = await createOwnProject(page, "Contexte du devis");
  await openRevision(page, own);
  const revision = new URL(page.url()).searchParams.get("revision_id");
  expect(revision, "the revision opened").not.toBeNull();
  await openHydrated(page, `${own.path}/revisions/${revision ?? ""}/estimate`);
  await expect(banner(page).getByRole("definition").first()).toHaveText(own.label);
  await expect(banner(page)).toContainText("Révision en cours");
  await expect(page.getByRole("treegrid", { name: "Grille de devis" })).toBeVisible({
    timeout: WORKING,
  });
  await expect(page.getByRole("main").getByRole("note")).toHaveCount(0);
});

// The base of a comparison, chosen in the banner of the three grids (US-2330). The fake back lists
// the revisions of the witness (`revisions`) — the current one, a copy of the reference, the
// reference and the offer v1.0 —, and answers any comparison by its first example (`comparison`).
const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
const COMPARED = `base_revision_id=${REFERENCE}`;
const CHOOSE_BASE = "Choisir une base de comparaison";
const CHANGE_BASE = "Changer de base, «\u00a0Référence\u00a0» comparée";
const COMPARED_TO = "Comparée à «\u00a0Référence\u00a0»";

test("from the estimate of the revision under way, a marked revision is chosen for base without leaving the screen, which names it, and the comparison is lifted without opening any panel [WF-IHM-0020-A]", async ({
  page,
}) => {
  // Depuis la grille de devis de la révision en cours, l'utilisateur choisit une révision marquée
  // pour base sans quitter l'écran ; l'écran la nomme, et la comparaison se lève sans ouvrir aucun
  // panneau.
  await openHydrated(page, `${IN_REVISION}/estimate`);
  await banner(page).getByRole("button", { name: CHOOSE_BASE }).click();
  const menu = page.getByRole("menu");
  await expect(menu.getByRole("menuitemradio")).toHaveText(["Référence (référence)", "Offre v1.0"]);
  await menu.getByRole("menuitemradio", { name: "Référence (référence)" }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/estimate?${COMPARED}`, { timeout: WORKING });
  const compared = banner(page).getByRole("definition").filter({ hasText: COMPARED_TO });
  await expect(compared).toBeVisible();
  await expect(page.getByRole("treegrid", { name: "Grille de devis" })).toBeVisible({
    timeout: WORKING,
  });

  // A link of the banner lifts the comparison: no menu, no panel.
  await banner(page)
    .getByRole("link", { name: "Lever la comparaison avec «\u00a0Référence\u00a0»" })
    .click();
  await expect(page).toHaveURL(`${IN_REVISION}/estimate`, { timeout: WORKING });
  await expect(compared).toHaveCount(0);
  await expect(banner(page).getByRole("button", { name: CHOOSE_BASE })).toBeVisible();
});

test("a comparison active on the planning is still active on the estimate, then on the remaining to commit, with the same base [WF-IHM-0010-A]", async ({
  page,
}) => {
  // Une comparaison active sur le planning l'est encore sur le devis puis sur le reste à engager,
  // avec la même base.
  await openHydrated(page, `${IN_REVISION}/planning?${COMPARED}`);
  const functions = page.getByRole("navigation", { name: "Fonctions" });
  const compared = banner(page).getByRole("definition").filter({ hasText: COMPARED_TO });
  await expect(compared).toBeVisible();
  await functions.getByRole("link", { name: "Chiffrage et devis", exact: true }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/estimate?${COMPARED}`, { timeout: WORKING });
  await expect(compared).toBeVisible();
  await functions.getByRole("link", { name: "Estimation du reste à engager", exact: true }).click();
  await expect(page).toHaveURL(`${IN_REVISION}/remaining?${COMPARED}`, { timeout: WORKING });
  await expect(compared).toBeVisible();
  await expect(page.getByRole("treegrid", { name: "Grille de reste à engager" })).toBeVisible({
    timeout: WORKING,
  });
});

// The windows and the modes of the harness of the screens (`accessibility.spec.ts`): 1366 points and
// 911, what a zoom of 150 % leaves of it, in light and in dark mode.
const WINDOWS = [
  { width: 1366, height: 768 },
  { width: 911, height: 512 },
] as const;

for (const mode of ["light", "dark"] as const) {
  test.describe(`in ${mode} mode`, () => {
    test.use({ colorScheme: mode });
    testChoices();
  });
}

function testChoices(): void {
  test(`the two choices of the banner, the revision read and the base, open their menus at the keyboard, the focus in each, and pass axe's rules for WCAG A and AA at 1366 and at 911 points (#3759) [WF-IHM-0020-A]`, async ({
    page,
  }) => {
    // Les deux choix se font au clavier comme au pointeur, et la révision lue comme la base se disent
    // à un lecteur d'écran (US-2330). The banner is outside `main`: the harness of the screens plays
    // its triggers on the screen of reference alone, which names no revision (`opened.ts`).
    const address = `${IN_REVISION}/planning?${COMPARED}`;
    for (const size of WINDOWS) {
      const width = `${String(size.width)} points`;
      const reopen = async (): Promise<void> => {
        await page.setViewportSize(size);
        await openHydrated(page, address);
      };
      await reopen();
      for (const name of [
        "Changer de révision, «\u00a0Révision en cours\u00a0» lue",
        CHANGE_BASE,
      ]) {
        const at = banner(page).getByRole("button", { name });
        await expect(at).toHaveAttribute("aria-haspopup", "menu");
        const opener: Opener = { opens: "menu", said: `the menu « ${name} »`, at, shell: true };
        await checkOpened(page, opener, width, reopen);
      }
    }
  });
}
