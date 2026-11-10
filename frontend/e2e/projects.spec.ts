// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Locator, type Page } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, sortUntilAddress, WORKING } from "./hydration";
import { inService, test } from "./mode";
import {
  attachToService,
  createOwnProject,
  employRole,
  inscribe,
  openRevision,
  renameAccount,
  wiringService,
} from "./own-project";
import { seedPlanning } from "./planning-seed";
import { withinBox } from "./scroll";
import {
  accountAdministrator,
  gridPreferences,
  localAccount,
  type LocalPerson,
} from "./service/realm";

// The projects, against the fake back and, tagged `@shared`, against the service.
//
// The fake back serves the first example of each operation: the two projects of the witness,
// which it lists whatever the filter asks — the filter is the server's to apply —, the project
// in progress, its sub-projects, its contributors and the history of its states; its exit
// answers the project completed, its creation the project created, its modification the witness
// with its description, a write of a sub-project or of the contributors the example of its success
// — and it keeps nothing: any project it is asked is the witness.
//
// The service keeps what is written, and the account of the run is no project manager of the witness
// (`mode.ts`, #2193): the paths read PRJ-001 and PRJ-002 as the loader wrote them, and the paths that
// write have a twin, played in the service alone, on a project the account creates (`own-project.ts`):
// created, then in pricing once a revision is opened, its sub-projects, its work breakdown and its
// exits written, and read anew.
const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";
const CREATED = "/projects/01926f3a-7c00-7000-8000-000000000003";
const CURRENT = "01926f3a-7c00-7000-8000-000000000102";

/**
 * Lift the sort of the home, which the account keeps (WF-IHM-0060) and applies to an address that
 * says nothing: the paths that follow, played with the same account, find the list as they expect.
 */
async function liftSort(list: Locator): Promise<void> {
  const header = list.getByRole("columnheader", { name: "Code" });
  await expect(async () => {
    const [sorted, busy] = await Promise.all([
      header.getAttribute("aria-sort"),
      list.getAttribute("aria-busy"),
    ]);
    if ((sorted === "ascending" || sorted === "descending") && busy !== "true") {
      await header.getByRole("button").click();
    }
    await expect(header).not.toHaveAttribute("aria-sort", /^(ascending|descending)$/, {
      timeout: 1_000,
    });
  }).toPass({ timeout: 2 * WORKING });
}

/**
 * Give the home back as the paths that follow expect it, against the service, where the account of
 * the run keeps the sort and the states it chose (WF-IHM-0060): the defaults pressed again, the sort
 * lifted, and the preference read in the database until it says so. Run whatever became of the path.
 */
async function restoreHome(
  page: Page,
  list: Locator,
  manager: LocalPerson | undefined,
): Promise<void> {
  if (manager === undefined) {
    return;
  }
  await page.goto("/");
  const states = page.getByRole("group", { name: "Filtre par état" });
  await expect(states).toBeVisible({ timeout: WORKING });
  await states.getByRole("button", { name: "Tous les états" }).click();
  await states.getByRole("button", { name: "Créé" }).click();
  await states.getByRole("button", { name: "Chiffrage" }).click();
  await states.getByRole("button", { name: "En cours" }).click();
  await expect(states.getByRole("button", { name: "En cours" })).toHaveAttribute(
    "aria-pressed",
    "true",
    { timeout: WORKING },
  );
  await liftSort(list);
  // What the account keeps of the home: no sort, and no state chosen, the default being unwritten.
  await expect
    .poll(
      () => {
        const kept = gridPreferences(manager.email, "projects");
        if (typeof kept !== "object" || kept === null) {
          return { sort: null, filters: {} };
        }
        return {
          sort: "sort" in kept ? kept.sort : null,
          filters: "filters" in kept ? kept.filters : {},
        };
      },
      { timeout: WORKING },
    )
    .toEqual({ sort: null, filters: {} });
}

const FAKE_BACK_ONLY =
  "the fake back serves the witness, which the service keeps for the other paths; the twin plays in the service on a project of the run";
// The twin of a path that the fake back, which keeps nothing, cannot play.
const SERVICE_ONLY = "the fake back keeps nothing of what is written";

test("the home lists the projects the user contributes to, a filter shown and lifted, never a restriction of reading @shared [WF-IHM-0120-A]", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projets");
  const filter = page.getByRole("main").getByRole("region", { name: "Filtre de la liste" });
  await expect(filter).toContainText("Projets dont vous êtes contributeur");

  await filter.getByRole("link", { name: "Voir tous les projets" }).click();
  await expect(page).toHaveURL("/?is_contributor=false");
  await expect(filter.getByRole("link", { name: "N’afficher que mes projets" })).toBeVisible();
  const list = page.getByRole("grid", { name: "Liste des projets" });
  // Its header, the two projects of the example and its totals; the service lists, besides the two
  // projects of the witness, those other paths created.
  if (!inService) {
    await expect(list.getByRole("row")).toHaveCount(4);
  }
  if (inService) {
    // The loader writes PRJ-001 in pricing and PRJ-002 created, neither with a code yet (US-0990).
    // The other paths create projects of their own, which a page of the list may no longer leave
    // room for the two of the witness: each is reached by the search of the screen, on its label.
    for (const [search, name] of [
      ["Modernisation", /Modernisation du poste de commande/],
      ["Extension", /Extension de la ligne d.essais/],
    ] as const) {
      await page.goto(`/?is_contributor=false&search=${search}`);
      await expect(list.getByRole("row", { name })).toBeVisible();
    }
    await page.goto("/?is_contributor=false");
  } else {
    await expect(
      list.getByRole("link", { name: "Modernisation du poste de commande" }),
    ).toBeVisible();
    await expect(list.getByRole("row", { name: /PRJ-002/ })).toContainText("Chiffrage");
  }
  await expect(list.getByRole("row").last()).toContainText(
    inService ? /\d+ projets?/ : "2 projets",
  );

  await filter.getByRole("link", { name: "N’afficher que mes projets" }).click();
  await expect(page).toHaveURL("/");
  await expect(filter).toContainText("Projets dont vous êtes contributeur");
});

test("the home sorts its projects and filters them by state on the server, from the address (#522) @shared [WF-IHM-0130-A]", async ({
  page,
  manager,
}) => {
  await page.goto("/");
  const list = page.getByRole("grid", { name: "Liste des projets" });
  try {
    // Nothing witnesses the hydration: the sort is pressed again until React answers it.
    await sortUntilAddress(
      list.getByRole("columnheader", { name: "Code" }),
      list,
      "/?sort_by=code&sort_order=asc",
    );
    const states = page.getByRole("group", { name: "Filtre par état" });
    // The filter by default is said, Créé, Chiffrage and En cours pressed (US-0660/L4, #1401;
    // US-1030, #1748).
    await expect(
      page.getByRole("region", { name: "Filtre par défaut de la liste par état" }),
    ).toBeVisible();
    await expect(states.getByRole("button", { name: "Créé" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(states.getByRole("button", { name: "Chiffrage" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(states.getByRole("button", { name: "Perdu" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    // « Tous les états » lifts it, the rest of the address kept, and says so in the address.
    await states.getByRole("button", { name: "Tous les états" }).click();
    await expect(page).toHaveURL("/?sort_by=code&sort_order=asc&states=all", { timeout: WORKING });
    await expect(states.getByRole("button", { name: "Tous les états" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await states.getByRole("button", { name: "Chiffrage" }).click();
    await expect(page).toHaveURL("/?sort_by=code&sort_order=asc&states=pricing", {
      timeout: WORKING,
    });
    // The state the address names stays pressed, whatever the fake back says it retained.
    await expect(states.getByRole("button", { name: "Chiffrage" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    // The grid holds in the window: its totals in view.
    const total = list.getByRole("gridcell", { name: inService ? /^\d+ projets?$/ : "2 projets" });
    expect(await withinBox(list, total)).toBe(true);
  } finally {
    await restoreHome(page, list, manager);
  }
});

test("the home filters its projects by the period of their last modification on the server, from the address, the focus kept (#522) @shared [WF-IHM-0130-A]", async ({
  page,
  manager,
}) => {
  await page.goto("/");
  const list = page.getByRole("grid", { name: "Liste des projets" });
  try {
    // Nothing witnesses the hydration: the sort is pressed again until React answers it.
    await sortUntilAddress(
      list.getByRole("columnheader", { name: "Code" }),
      list,
      "/?sort_by=code&sort_order=asc",
    );
    const period = page.getByRole("form", { name: "Période de modification" });
    await period.getByLabel("Du").fill("2026-03-01");
    await period.getByLabel("Au").fill("2026-03-16");
    const apply = period.getByRole("button", { name: "Filtrer" });
    await apply.click();
    // Two instants under the names of the contract, drawn in the time zone of the browser: the start
    // of the first day, the start of the day after the last; the sort kept, back to the first page.
    const [from, to] = await page.evaluate(() => [
      new Date(2026, 2, 1).toISOString(),
      new Date(2026, 2, 17).toISOString(),
    ]);
    const asked = new URLSearchParams({ sort_by: "code", sort_order: "asc", from, to });
    await expect(page).toHaveURL(`/?${asked.toString()}`, { timeout: WORKING });
    // The form is never remounted: the period shows, and the button keeps the focus.
    await expect(period.getByLabel("Du")).toHaveValue("2026-03-01");
    await expect(period.getByLabel("Au")).toHaveValue("2026-03-16");
    await expect(apply).toBeFocused();
  } finally {
    await restoreHome(page, list, manager);
  }
});

test("a project, its settings and its lifecycle show what the fake back serves, and offer the commands the project lists: its modification, those of its lists, and the exits @shared [WF-CYC-0060]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_ONLY);
  // Every screen after the first is reached by a click, and awaited five seconds: compiled
  // first (`e2e/compile.ts`).
  await compile(
    page.request,
    `${PROJECT}/revisions/${CURRENT}/planning`,
    `${PROJECT}/settings`,
    `${PROJECT}/lifecycle`,
  );
  // The screen of a project leads to its revision in progress, the fake back serving every project
  // as the witness, which has one (US-0720, WF-IHM-0010-A); the project itself is named by the
  // banner of its reading context.
  await page.goto(PROJECT);
  const main = page.getByRole("main");
  await expect(page).toHaveURL(`${PROJECT}/revisions/${CURRENT}/planning`, { timeout: WORKING });
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Planification");
  await expect(page.getByRole("region", { name: "Contexte de lecture" })).toContainText(
    "Modernisation du poste de commande",
  );

  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await nav.getByRole("link", { name: "Paramètres de projets" }).click();
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Paramètres de projets");
  const subprojects = main.getByRole("grid", { name: "Sous-projets" });
  await expect(subprojects.getByRole("row", { name: /^SP-CMD Poste de commande/ })).toBeVisible();
  const contributors = main.getByRole("grid", { name: "Contributeurs" });
  await expect(
    contributors.getByRole("row", { name: /Alix Moreau\s+Contributeur\s+Désactivé/ }),
  ).toBeVisible();
  await expect(main.getByRole("treegrid", { name: "Lotissement" })).toBeVisible();
  // The commands the project lists: its modification, those of its sub-projects and of its
  // contributors.
  await expect(main.getByRole("button", { name: "Modifier le projet" })).toBeVisible();
  await expect(main.getByRole("button", { name: "Nouveau sous-projet" })).toBeVisible();
  await expect(main.getByRole("button", { name: "Modifier les contributeurs" })).toBeVisible();

  await nav.getByRole("link", { name: "Cycle de vie du projet" }).click();
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  const history = main.getByRole("table", { name: "Historique des états" });
  await expect(history.getByRole("row")).toHaveCount(4);
  await expect(main.getByRole("region", { name: "Prochain état" })).toContainText(
    "seules les sorties du cycle de vie restent",
  );
  // Déclarer perdu depuis En cours n'y figure pas : la perte n'est possible que depuis Chiffrage.
  const exits = main.getByRole("region", { name: "Commandes" });
  await expect(exits.getByRole("button")).toHaveText([
    "Terminer le projet",
    "Abandonner le projet",
  ]);
  await expect(exits.getByRole("button", { name: "Déclarer le projet perdu" })).toHaveCount(0);
});

test("creates a project from the home, then modifies the identity of a project on its settings, which keep no note of the mock-up (EP-02/L44a) @shared [WF-PRJ-0080-A]", async ({
  page,
}) => {
  test.slow();
  if (!inService) {
    await compile(page.request, CREATED);
  }
  await page.goto("/");
  const main = page.getByRole("main");

  // No project is opened here, nothing witnesses the hydration: the creation is pressed again
  // until React opens its form, and never once it is open.
  const creation = page.getByRole("dialog", { name: "Créer un projet" });
  await expect(async () => {
    if (!(await creation.isVisible())) {
      await main.getByRole("button", { name: "Créer un projet" }).click();
    }
    await expect(creation).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  // Without a label, refused before anything is asked.
  await creation.getByRole("button", { name: "Créer" }).click();
  await expect(creation.getByRole("textbox", { name: "Libellé" })).toBeFocused();
  await creation.getByRole("textbox", { name: "Libellé" }).fill("Rénovation du poste de livraison");
  await creation.getByRole("button", { name: "Créer" }).click();
  // The screen of the project the server created — which the fake back serves at its own address,
  // with no revision. The screen stays, with the encart that starts the planning (#1358).
  if (inService) {
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/, { timeout: WORKING });
  } else {
    await expect(page).toHaveURL(CREATED, { timeout: WORKING });
  }
  await expect(main.getByRole("heading", { level: 1 })).toHaveText(
    "Rénovation du poste de livraison",
  );
  if (!inService) {
    // The encart is offered to who may write a planning, which the service lists with the structures
    // (EP-06): the account of the run is offered the imports of no project before.
    await expect(main.getByRole("region", { name: "Démarrer le projet" })).toBeVisible();
  }

  // The modification is played on the witness against the fake back, which keeps nothing of what is
  // written; against the service, on the project just created, the account being its project
  // manager.
  const target = inService ? new URL(page.url()).pathname : PROJECT;
  const targetLabel = inService
    ? "Rénovation du poste de livraison"
    : "Modernisation du poste de commande";
  await openHydrated(page, `${target}/settings`);
  await expect(main.getByRole("note")).toHaveCount(0);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", { name: `Modifier «\u00a0${targetLabel}\u00a0»` });
  const winning = identity.getByRole("textbox", { name: /Probabilité de gain/ });
  if (inService) {
    // Created, not yet in progress: the probability of winning is entered.
    await expect(winning).not.toHaveAttribute("readonly");
  } else {
    // In progress, the probability of winning is frozen, as the project lists its command, and the
    // form says the condition it lacks.
    await expect(winning).toHaveAttribute("readonly");
    await expect(identity).toContainText("projet non encore en cours");
  }
  await identity
    .getByRole("textbox", { name: "Description" })
    .fill("Remplacement des automates et de la supervision du poste de commande.");
  await identity.getByRole("button", { name: "Enregistrer" }).click();
  await expect(identity).toBeHidden({ timeout: WORKING });
  // The facts show what the server answered, and keep it once the page is read anew.
  await expect(main.getByText("Paramètres du projet enregistrés.")).toBeVisible();
  await expect(main.getByLabel("Paramètres du projet")).toContainText(
    "Remplacement des automates et de la supervision du poste de commande.",
  );
  await expect(main.getByRole("alert")).toHaveCount(0);
  if (inService) {
    // What the service kept, read anew.
    await page.reload();
    await expect(main.getByLabel("Paramètres du projet")).toContainText(
      "Remplacement des automates et de la supervision du poste de commande.",
    );
  }
});

test("an exit of the lifecycle is confirmed, naming the state it leads to and asking what becomes of the current revision, before the API applies it @shared [WF-CYC-0090] [WF-CYC-0090-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_ONLY);
  await openHydrated(page, `${PROJECT}/lifecycle`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Terminer le projet" }).click();
  const confirmation = commands.getByRole("form", { name: "Terminer le projet" });
  await expect(confirmation).toContainText("Cette sortie est définitive");
  await expect(confirmation).toContainText("Terminé");
  await expect(confirmation).toContainText("passeront en lecture seule");
  await confirmation.getByRole("textbox", { name: "Motif (facultatif)" }).fill("Recette prononcée");
  // The project carries the current revision 102: marking it asks for a version name, abandoning
  // it does not. The fake back answers the first example of the exit, a 200: the marking, which
  // answers a task (202), is proved by the tests of the component (`exit-command.dom.test.tsx`).
  await confirmation.getByRole("radio", { name: /^Marquer la révision en cours/ }).check();
  await expect(confirmation.getByRole("textbox", { name: "Nom de version" })).toBeVisible();
  await confirmation.getByRole("radio", { name: /^Abandonner la révision en cours/ }).check();
  await expect(confirmation.getByRole("textbox", { name: "Nom de version" })).toHaveCount(0);
  await confirmation.getByRole("button", { name: "Confirmer la sortie" }).click();
  await expect(commands.getByRole("status").filter({ hasText: /./ })).toHaveText(
    /^Le projet est passé à l’état «\s?Terminé\s?»\.$/,
  );
  await expect(confirmation).toHaveCount(0);
});

test("the settings of a project search the sub-projects, filter the contributors and fold the work breakdown, each grid under its own names @shared [WF-PRJ-0020-A] [WF-PRJ-0050-A]", async ({
  page,
}) => {
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  const tree = main.getByRole("treegrid", { name: "Lotissement" });
  const item = tree.getByRole("row", { name: /Lot 1/ });
  await item.getByRole("button", { name: "Plier" }).click();
  // The header, the work package, the totals.
  await expect(tree.getByRole("row")).toHaveCount(3);
  await item.getByRole("button", { name: "Déplier" }).click();
  await expect(tree.getByRole("row")).toHaveCount(5);
  // Searched on its labels and filtered on its kinds by the server, under the names of its grid.
  await main
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Lotissement\u00a0»" })
    .fill("Armoires");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${PROJECT}/settings?breakdown_search=Armoires`, {
    timeout: WORKING,
  });
  await main
    .getByRole("group", { name: "Filtrer par nature" })
    .getByRole("button", { name: "Lot" })
    .click();
  await expect(page).toHaveURL(
    `${PROJECT}/settings?breakdown_search=Armoires&breakdown_kinds=work_package`,
    { timeout: WORKING },
  );
  // The fake back answers its whole reading, with its counter, whatever is asked: nothing says the
  // tree partial, which only a reading without a counter is.
  await expect(main.getByText("Les lots et les postes ne montrent que ce que")).toHaveCount(
    inService ? 1 : 0,
  );
  // Back to the whole screen, for the filters of the other grids.
  await openHydrated(page, `${PROJECT}/settings`);

  await main
    .getByRole("group", { name: "Filtrer par qualité" })
    .getByRole("button", { name: "Chef de projet" })
    .click();
  await expect(page).toHaveURL(`${PROJECT}/settings?contributor_kinds=project_manager`, {
    timeout: WORKING,
  });
  await main
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Sous-projets\u00a0»" })
    .fill("SP-C");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(
    `${PROJECT}/settings?contributor_kinds=project_manager&subproject_search=SP-C`,
    { timeout: WORKING },
  );
  // The fake back answers its example whatever is asked: what the screen asks is what this proves.
  await expect(main.getByRole("grid", { name: "Sous-projets" }).getByRole("row").last()).toHaveText(
    inService ? "1 sous-projet" : "2 sous-projets",
  );
});

test("the settings of a project sort the sub-projects and the contributors, search the contributors and filter both on their other columns, each grid under its own names @shared [WF-PRJ-0050-A] [WF-PRJ-0060-A]", async ({
  page,
}) => {
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  const subprojects = main.getByRole("grid", { name: "Sous-projets" });
  await sortUntilAddress(
    subprojects.getByRole("columnheader", { name: "Libellé" }),
    subprojects,
    `${PROJECT}/settings?subproject_sort_by=label&subproject_sort_order=asc`,
  );
  const charged = main.getByRole("combobox", { name: "Coûts réels" });
  await charged.selectOption({ label: "Avec coûts réels imputés" });
  await expect(charged).toHaveValue("true");
  await expect(page).toHaveURL(
    `${PROJECT}/settings?subproject_sort_by=label&subproject_sort_order=asc&subproject_has_actual_costs=true`,
    { timeout: WORKING },
  );
  const contributors = main.getByRole("grid", { name: "Contributeurs" });
  await sortUntilAddress(
    contributors.getByRole("columnheader", { name: "Qualité" }),
    contributors,
    `${PROJECT}/settings?subproject_sort_by=label&subproject_sort_order=asc&subproject_has_actual_costs=true&contributor_sort_by=kind&contributor_sort_order=asc`,
  );
  const account = main.getByRole("combobox", { name: "État du compte" });
  await account.selectOption({ label: "Comptes actifs" });
  await expect(account).toHaveValue("true");
  await expect(page).toHaveURL(/&contributor_sort_order=asc&contributor_is_active=true$/, {
    timeout: WORKING,
  });
  await main
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Contributeurs\u00a0»" })
    .fill("Mar");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/&contributor_is_active=true&contributor_search=Mar$/, {
    timeout: WORKING,
  });
});

test("the settings of a project create and modify a sub-project, present unavailable the deletion of those charged with actual costs or cited by a marked revision, and write the contributors, a proposal confirmed @shared [WF-PRJ-0050-A] [WF-PRJ-0070-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_ONLY);
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  await expect(main.getByRole("note")).toHaveCount(0);
  const section = main.getByRole("region", { name: "Sous-projets" });
  const subprojects = section.getByRole("grid", { name: "Sous-projets" });

  // La suppression d'un sous-projet portant des coûts réels est refusée : both sub-projects of
  // the witness bear the invoices of the tasks drawn around its core and are cited by the reference
  // revision (EP-14/L45a), lines of the current revision bear them, and each lists its deletion
  // unavailable, lacking the three conditions (EP-14/L42l, EP-14/L42q) — presented so, the
  // conditions it lacks given; pressed, nothing is asked.
  // Playwright clicks no element marked `aria-disabled`: the press is dispatched.
  const unmet =
    "Conditions non remplies : sous-projet cité par aucune révision marquée, aucun coût réel " +
    "imputé au sous-projet et aucune ligne de devis de la révision en cours portant le " +
    "sous-projet.";
  for (const code of ["SP-CMD", "SP-ESS"]) {
    const deletion = subprojects.getByRole("button", { name: new RegExp(`^Supprimer.+${code}`) });
    await expect(deletion).toHaveAttribute("aria-disabled", "true");
    await expect(deletion).toHaveAccessibleDescription(unmet);
  }
  await subprojects.getByRole("button", { name: /^Supprimer.+SP-ESS/ }).dispatchEvent("click");
  await expect(section.getByRole("status").filter({ hasText: /./ }).first()).toContainText(
    `Supprimer « SP-ESS » : indisponible. ${unmet}`,
  );
  // Cited and charged, it lacks more than the passing of its lines, which the estimate alone
  // lifts: no link leads there (EP-14/L53).
  await expect(section.getByRole("link", { name: /^Voir au devis/ })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(subprojects.getByRole("row", { name: /^SP-ESS/ })).toHaveCount(1);

  await subprojects.getByRole("button", { name: /^Modifier.+SP-ESS/ }).click();
  let form = page.getByRole("dialog", { name: /^Modifier.+SP-ESS/ });
  await form.getByRole("textbox", { name: "Libellé" }).fill("Essais, mise en service et réception");
  await form.getByRole("button", { name: "Enregistrer" }).click();
  await expect(form).toHaveCount(0);
  await expect(subprojects.getByRole("row", { name: /^SP-ESS/ })).toContainText(
    "Essais, mise en service et réception",
  );

  await section.getByRole("button", { name: "Nouveau sous-projet" }).click();
  form = page.getByRole("dialog", { name: "Nouveau sous-projet" });
  await form.getByRole("textbox", { name: "Code ERP" }).fill("SP-REC");
  await form.getByRole("textbox", { name: "Libellé" }).fill("Réception sur site");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(section.getByRole("status").filter({ hasText: /./ }).first()).toContainText(
    "SP-REC",
  );

  // A proposal is applied only once confirmed, and the list saved.
  const contributors = main.getByRole("region", { name: "Contributeurs" });
  await contributors.getByRole("button", { name: "Modifier les contributeurs" }).click();
  const list = page.getByRole("dialog", { name: "Modifier les contributeurs" });
  await list.getByRole("button", { name: "Inscrire Sacha Lefèvre" }).click();
  await list
    .getByRole("combobox", { name: "Qualité de Inès Roux" })
    .selectOption("project_manager");
  await list.getByRole("button", { name: "Enregistrer" }).click();
  await expect(list).toHaveCount(0);
  const grid = contributors.getByRole("grid", { name: "Contributeurs" });
  await expect(grid.getByRole("row", { name: /Sacha Lefèvre/ })).toBeVisible();
  await expect(grid.getByRole("row", { name: /Inès Roux/ })).toContainText("Chef de projet");
});

test("the settings of a project edit the work breakdown in its grid: an order item added from the menu of a cell, an element deleted from the bar once confirmed (EP-14/L44c) @shared [WF-PRJ-0020-A]", async ({
  page,
}) => {
  test.skip(inService, FAKE_BACK_ONLY);
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  const section = main.getByRole("region", { name: "Lotissement" });
  const tree = section.getByRole("treegrid", { name: "Lotissement" });
  const said = section.getByRole("status").filter({ hasText: /./ }).first();
  // The totals count the elements the reading retains, by kind (#574).
  await expect(tree.getByRole("row").last()).toHaveText("1 lot, 1 poste et 1 livrable");

  // An order item added under the work package, from the menu of its cell: the work breakdown
  // answered — the fake back's, whatever is typed — takes the place of the rows.
  await tree.getByText("Lot 1", { exact: true }).click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Ajouter un poste au lot «\u00a0Lot 1\u00a0»" })
    .click();
  const form = page.getByRole("dialog", { name: /^Nouveau poste du lot/ });
  await form.getByRole("textbox", { name: "Libellé" }).fill("Mise en service sur site");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  await expect(said).toHaveText("Poste « Mise en service sur site » ajouté.");
  await expect(tree.getByText("Procès-verbal de mise en service", { exact: true })).toBeVisible();
  await expect(tree.getByRole("row").last()).toHaveText("1 lot, 2 postes et 2 livrables");

  // The deletion of an order item, from the bar on the row of the active cell, confirmed first,
  // saying that the tasks that bear it stay.
  await tree.getByText("Poste 1.1", { exact: true }).click();
  await section.getByRole("button", { name: "Supprimer le poste «\u00a0Poste 1.1\u00a0»" }).click();
  const confirmation = page.getByRole("dialog", {
    name: "Supprimer le poste «\u00a0Poste 1.1\u00a0»\u00a0?",
  });
  await expect(confirmation).toContainText("restent et perdent leur rattachement");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(confirmation).toHaveCount(0);
  await expect(said).toHaveText("Poste « Poste 1.1 » supprimé.");
});

// The twins, in the service alone: the paths above that write, played on a project the account of
// the run creates, which it manages as its creator and no other path reads.

test("a project created shows its settings and its lifecycle as the service keeps them, and offers the commands its creator is given @shared [WF-CYC-0060] [WF-PRJ-0060-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Paramètres");
  await openHydrated(page, `${own.path}/settings`);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Paramètres de projets");
  await expect(main.getByRole("note")).toHaveCount(0);
  await expect(main.getByLabel("Paramètres du projet")).toContainText(own.label);
  // No sub-project yet; the creator is the one contributor, a project manager.
  await expect(main.getByRole("region", { name: "Sous-projets" })).toContainText(
    "Ce projet n’a aucun sous-projet.",
  );
  const contributors = main.getByRole("grid", { name: "Contributeurs" });
  await expect(contributors.getByRole("row", { name: /Chef de projet/ })).toBeVisible();
  await expect(main.getByRole("button", { name: "Modifier le projet" })).toBeVisible();
  await expect(main.getByRole("button", { name: "Nouveau sous-projet" })).toBeVisible();
  await expect(main.getByRole("button", { name: "Modifier les contributeurs" })).toBeVisible();

  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await nav.getByRole("link", { name: "Cycle de vie du projet" }).click();
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  // The history holds the creation alone.
  const history = main.getByRole("table", { name: "Historique des états" });
  await expect(history.getByRole("row")).toHaveCount(2);
  await expect(history.getByRole("row").nth(1)).toContainText("Créé");
  await expect(main.getByRole("region", { name: "Commandes" }).getByRole("button")).not.toHaveCount(
    0,
  );
});

test("the sub-projects of a project created are written, modified and deleted, each kept by the service and read anew @shared [WF-PRJ-0050-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Sous-projets");
  await openHydrated(page, `${own.path}/settings`);
  const main = page.getByRole("main");
  const section = main.getByRole("region", { name: "Sous-projets" });
  const subprojects = section.getByRole("grid", { name: "Sous-projets" });
  const code = `SP-${own.label.slice(-4).toUpperCase()}`;

  await section.getByRole("button", { name: "Nouveau sous-projet" }).click();
  let form = page.getByRole("dialog", { name: "Nouveau sous-projet" });
  await form.getByRole("textbox", { name: "Code ERP" }).fill(code);
  await form.getByRole("textbox", { name: "Libellé" }).fill("Réception sur site");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  // A creation adds no row: the page, read anew, lists what the service kept.
  await expect(subprojects.getByRole("row", { name: new RegExp(`^${code}`) })).toContainText(
    "Réception sur site",
  );

  await subprojects.getByRole("button", { name: new RegExp(`^Modifier.+${code}`) }).click();
  form = page.getByRole("dialog", { name: new RegExp(`^Modifier.+${code}`) });
  await form.getByRole("textbox", { name: "Libellé" }).fill("Réception et mise en service");
  await form.getByRole("button", { name: "Enregistrer" }).click();
  await expect(form).toHaveCount(0);
  await page.reload();
  await expect(subprojects.getByRole("row", { name: new RegExp(`^${code}`) })).toContainText(
    "Réception et mise en service",
  );

  // Cited by no marked revision, charged with nothing, estimated nowhere: it deletes.
  await subprojects.getByRole("button", { name: new RegExp(`^Supprimer.+${code}`) }).click();
  const confirmation = page.getByRole("dialog");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(confirmation).toHaveCount(0);
  await page.reload();
  await expect(subprojects.getByRole("row", { name: new RegExp(`^${code}`) })).toHaveCount(0);
});

test("the work breakdown of a project created is written, element by element, kept by the service and read anew @shared [WF-PRJ-0020-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Lotissement");
  await openHydrated(page, `${own.path}/settings`);
  const main = page.getByRole("main");
  const section = main.getByRole("region", { name: "Lotissement" });
  const said = section.getByRole("status").filter({ hasText: /./ }).first();

  await section.getByRole("button", { name: "Nouveau lot" }).click();
  let form = page.getByRole("dialog", { name: "Nouveau lot" });
  await form.getByRole("textbox", { name: "Libellé" }).fill("Armoires");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  await expect(said).toHaveText("Lot « Armoires » ajouté.");

  const tree = section.getByRole("treegrid", { name: "Lotissement" });
  await tree.getByText("Armoires", { exact: true }).click({ button: "right" });
  await page
    .getByRole("menu", { name: "Menu de la cellule" })
    .getByRole("menuitem", { name: "Ajouter un poste au lot «\u00a0Armoires\u00a0»" })
    .click();
  form = page.getByRole("dialog", { name: /^Nouveau poste du lot/ });
  await form.getByRole("textbox", { name: "Libellé" }).fill("Mise en service sur site");
  await form.getByRole("button", { name: "Créer" }).click();
  await expect(form).toHaveCount(0);
  await expect(said).toHaveText("Poste « Mise en service sur site » ajouté.");

  // What the service kept, read anew.
  await openHydrated(page, `${own.path}/settings`);
  await expect(tree.getByText("Armoires", { exact: true })).toBeVisible();
  await expect(tree.getByText("Mise en service sur site", { exact: true })).toBeVisible();
  // The service gives a project a lot and an order item of its own at its creation (WF-PRJ-0020).
  await expect(tree.getByRole("row").last()).toHaveText("2 lots et 2 postes");
});

test("an exit of the lifecycle of a project in pricing is confirmed, naming the state it leads to and asking what becomes of the current revision, and is kept by the service @shared [WF-CYC-0090] [WF-CYC-0090-A]", async ({
  page,
}) => {
  test.skip(!inService, SERVICE_ONLY);
  test.slow();
  const own = await createOwnProject(page, "Sortie");
  // A revision opened takes the project to pricing, with a current revision to leave (WF-CYC-0090).
  await openRevision(page, own);

  await openHydrated(page, `${own.path}/lifecycle`);
  const main = page.getByRole("main");
  const commands = main.getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Déclarer le projet perdu" }).click();
  const confirmation = commands.getByRole("form", { name: "Déclarer le projet perdu" });
  await expect(confirmation).toContainText("Cette sortie est définitive");
  await expect(confirmation).toContainText("Perdu");
  await confirmation.getByRole("textbox", { name: "Motif (facultatif)" }).fill("Offre non retenue");
  await confirmation.getByRole("radio", { name: /^Marquer la révision en cours/ }).check();
  await expect(confirmation.getByRole("textbox", { name: "Nom de version" })).toBeVisible();
  await confirmation.getByRole("radio", { name: /^Abandonner la révision en cours/ }).check();
  await expect(confirmation.getByRole("textbox", { name: "Nom de version" })).toHaveCount(0);
  await confirmation.getByRole("button", { name: "Confirmer la sortie" }).click();
  // The note of the exit goes with the commands, which the project, terminal, no longer lists: the
  // history of the messages, in the shell, keeps what was told.
  await page.getByRole("button", { name: /^Tâches et messages/ }).click();
  const told = page
    .getByRole("dialog", { name: "Tâches et messages" })
    .getByRole("region", { name: "Messages" })
    .getByRole("listitem")
    .filter({ hasText: /Le projet est passé à l’état «\s?Perdu\s?»\./ });
  await expect(told).toHaveCount(1);
  await page.keyboard.press("Escape");

  // The service kept the transition and its reason, and the project is terminal.
  await page.reload();
  const history = main.getByRole("table", { name: "Historique des états" });
  await expect(history.getByRole("row").last()).toContainText("Perdu");
  await expect(history.getByRole("row").last()).toContainText("Offre non retenue");
  await expect(commands.getByRole("button")).toHaveCount(0);
});

test("the contributors of a project created are written on the screen, the quality of another account changed, kept by the service and read anew @shared [WF-PRJ-0060-A]", async ({
  browser,
  page,
  playwright,
  manager,
}) => {
  if (!inService || manager === undefined) {
    test.skip(true, SERVICE_ONLY);
    return;
  }
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const own = await createOwnProject(page, "Contributeurs");
    // The screen proposes the accounts of the estimate alone: the other account is inscribed by the
    // API, then her quality is changed on the screen.
    const administrator = await accountAdministrator(browser, calls);
    const other = await localAccount(browser, administrator);
    await inscribe(browser, calls, manager, other, own);
    await openHydrated(page, `${own.path}/settings`);
    const contributors = page.getByRole("main").getByRole("region", { name: "Contributeurs" });
    const grid = contributors.getByRole("grid", { name: "Contributeurs" });
    await expect(grid.getByRole("row").last()).toHaveText("2 contributeurs", { timeout: WORKING });
    await expect(grid.getByRole("row", { name: /Contributeur/ })).toHaveCount(1);

    await contributors.getByRole("button", { name: "Modifier les contributeurs" }).click();
    const list = page.getByRole("dialog", { name: "Modifier les contributeurs" });
    // Both accounts bear the same name: the one who contributes is the one whose quality changes.
    await list
      .getByRole("combobox", { name: `Qualité de ${other.name}` })
      .filter({ has: page.locator('option[value="contributor"]:checked') })
      .selectOption("project_manager");
    await list.getByRole("button", { name: "Enregistrer" }).click();
    await expect(list).toHaveCount(0);

    // What the service kept, read anew: both are project managers.
    await page.reload();
    await expect(grid.getByRole("row", { name: /Chef de projet/ })).toHaveCount(2, {
      timeout: WORKING,
    });
    await expect(grid.getByRole("row", { name: /Contributeur/ })).toHaveCount(0);
    await expect(grid.getByRole("row").last()).toHaveText("2 contributeurs");
  } finally {
    await calls.dispose();
  }
});

test("a labour line of a role of a service proposes the accounts of the service on the settings, the list unchanged until the proposal is confirmed and saved @shared [WF-PRJ-0070-A] [WF-PRJ-0060-A]", async ({
  browser,
  page,
  playwright,
  manager,
}) => {
  if (!inService || manager === undefined) {
    test.skip(true, SERVICE_ONLY);
    return;
  }
  test.slow();
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    // A project of its own with its tasks, and an account of its own attached to the service of the
    // witness: it is the one the proposal is read for, the witness holding accounts of that service.
    const seeded = await seedPlanning(page, browser, calls, manager, "Proposition");
    const administrator = await accountAdministrator(browser, calls);
    // The local accounts all bear one name, and the installation is shared: this one is renamed
    // with a token of its own, so that the screen tells it from every other of the service.
    const created = await localAccount(browser, administrator);
    const other = await renameAccount(browser, calls, created);
    const service = wiringService();
    await attachToService(browser, calls, other, service);
    const settings = `${seeded.own.path}/settings`;
    const contributors = page.getByRole("main").getByRole("region", { name: "Contributeurs" });
    const grid = contributors.getByRole("grid", { name: "Contributeurs" });
    const proposed = contributors.getByText(/^Proposés? d’après les rôles du devis, à confirmer/);

    // No line employs a role yet: nobody is proposed.
    await openHydrated(page, settings);
    await expect(grid.getByRole("row").last()).toHaveText("1 contributeur", { timeout: WORKING });
    await expect(proposed).toHaveCount(0);

    // A labour line of the role of the service is created: its account is proposed, with the list
    // unchanged (WF-PRJ-0070).
    await employRole(calls, seeded.headers, seeded.ids, seeded.nodes[6] ?? "", service);
    await openHydrated(page, settings);
    await expect(proposed).toBeVisible({ timeout: WORKING });
    await expect(proposed).toContainText(other.name);
    await expect(grid.getByRole("row").last()).toHaveText("1 contributeur");

    // The proposal names the node and the role; confirmed, and the list saved, it is written.
    await contributors.getByRole("button", { name: "Modifier les contributeurs" }).click();
    const list = page.getByRole("dialog", { name: "Modifier les contributeurs" });
    const offered = list
      .getByRole("region", { name: "Contributeurs proposés" })
      .getByRole("listitem")
      .filter({ hasText: other.name });
    await expect(offered).toHaveCount(1, { timeout: WORKING });
    await expect(offered).toContainText(service.node.label);
    await expect(offered).toContainText(service.role.label);
    await offered.getByRole("button", { name: `Inscrire ${other.name}` }).click();
    await list.getByRole("button", { name: "Enregistrer" }).click();
    await expect(list).toHaveCount(0);
    await expect(grid.getByRole("row").last()).toHaveText("2 contributeurs");

    // Read anew, the service kept both and proposes this account no more.
    await page.reload();
    await expect(grid.getByRole("row").last()).toHaveText("2 contributeurs", { timeout: WORKING });
    // The account is inscribed — in the grid of the contributors, drawn once the list is read — and
    // no longer proposed; the absence alone would also hold before the proposals are drawn (#2673).
    await expect(grid.getByRole("row").filter({ hasText: other.name })).toHaveCount(1);
    await expect(proposed.filter({ hasText: other.name })).toHaveCount(0);
  } finally {
    await calls.dispose();
  }
});
