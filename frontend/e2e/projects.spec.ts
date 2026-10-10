// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, sortUntilAddress, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each operation: the two projects of the witness,
// which it lists whatever the filter asks — the filter is the server's to apply —, the project
// in progress, its sub-projects, its contributors and the history of its states; its exit
// answers the project completed, its creation the project created, its modification the witness
// with its description, a write of a sub-project or of the contributors the example of its success
// — and it keeps nothing: any project it is asked is the witness.
const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";
const CREATED = "/projects/01926f3a-7c00-7000-8000-000000000003";

test("the home lists the projects the user contributes to, a filter shown and lifted, never a restriction of reading", async ({
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
  // Its header, the two projects of the example and its totals.
  await expect(list.getByRole("row")).toHaveCount(4);
  await expect(
    list.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toBeVisible();
  await expect(list.getByRole("row", { name: /PRJ-002/ })).toContainText("Chiffrage");
  await expect(list.getByRole("row").last()).toContainText("2 projets");

  await filter.getByRole("link", { name: "N’afficher que mes projets" }).click();
  await expect(page).toHaveURL("/");
  await expect(filter).toContainText("Projets dont vous êtes contributeur");
});

test("the home sorts its projects and filters them by state on the server, from the address (#522)", async ({
  page,
}) => {
  await page.goto("/");
  const list = page.getByRole("grid", { name: "Liste des projets" });
  // Nothing witnesses the hydration: the sort is pressed again until React answers it.
  await sortUntilAddress(
    list.getByRole("columnheader", { name: "Code" }),
    list,
    "/?sort_by=code&sort_order=asc",
  );
  const states = page.getByRole("group", { name: "Filtre par état" });
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
  const total = list.getByRole("gridcell", { name: "2 projets" });
  expect(await withinBox(list, total)).toBe(true);
});

test("the home filters its projects by the period of their last modification on the server, from the address, the focus kept (#522)", async ({
  page,
}) => {
  await page.goto("/");
  const list = page.getByRole("grid", { name: "Liste des projets" });
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
});

test("a project, its settings and its lifecycle show what the fake back serves, and offer the commands the project lists: its modification, those of its lists, and the exits", async ({
  page,
}) => {
  // Every screen after the first is reached by a click, and awaited five seconds: compiled
  // first (`e2e/compile.ts`).
  await compile(page.request, `${PROJECT}/settings`, `${PROJECT}/lifecycle`);
  await page.goto(PROJECT);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1 })).toHaveText(
    "Modernisation du poste de commande",
  );
  await expect(main.getByRole("definition").first()).toHaveText("PRJ-001");
  await expect(main.getByRole("button")).toHaveCount(0);

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
  await expect(main.getByRole("region", { name: "Commandes" }).getByRole("button")).toHaveText([
    "Terminer le projet",
    "Déclarer le projet perdu",
    "Abandonner le projet",
  ]);
});

test("creates a project from the home, then modifies the identity of a project on its settings, the mock-up saying the fake back keeps nothing (EP-02/L44a) [WF-PRJ-0080-A]", async ({
  page,
}) => {
  test.slow();
  await compile(page.request, CREATED);
  await page.goto("/");
  const main = page.getByRole("main");
  await expect(main.getByRole("note")).toContainText("le service simulé répond");

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
  // The screen of the project the server created — which the fake back serves as the witness.
  await expect(page).toHaveURL(CREATED, { timeout: WORKING });
  await expect(main.getByRole("heading", { level: 1 })).toHaveText(
    "Modernisation du poste de commande",
  );

  await openHydrated(page, `${PROJECT}/settings`);
  await main.getByRole("button", { name: "Modifier le projet" }).click();
  const identity = page.getByRole("dialog", {
    name: "Modifier «\u00a0Modernisation du poste de commande\u00a0»",
  });
  // In progress, the probability of winning is frozen, as the project lists its command, and the
  // form says the condition it lacks.
  await expect(identity.getByRole("textbox", { name: /Probabilité de gain/ })).toHaveAttribute(
    "readonly",
  );
  await expect(identity).toContainText("projet non encore en cours");
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
});

test("an exit of the lifecycle is confirmed, naming the state it leads to, before the API applies it", async ({
  page,
}) => {
  await openHydrated(page, `${PROJECT}/lifecycle`);
  const commands = page.getByRole("main").getByRole("region", { name: "Commandes" });
  await commands.getByRole("button", { name: "Terminer le projet" }).click();
  const confirmation = commands.getByRole("form", { name: "Terminer le projet" });
  await expect(confirmation).toContainText("Cette sortie est définitive");
  await expect(confirmation).toContainText("Terminé");
  await expect(confirmation).toContainText("passeront en lecture seule");
  await confirmation.getByRole("textbox", { name: "Motif (facultatif)" }).fill("Recette prononcée");
  await confirmation.getByRole("button", { name: "Confirmer la sortie" }).click();
  await expect(commands.getByRole("status").filter({ hasText: /./ })).toHaveText(
    /^Le projet est passé à l’état «\s?Terminé\s?»\.$/,
  );
  await expect(confirmation).toHaveCount(0);
});

test("the settings of a project search the sub-projects, filter the contributors and fold the work breakdown, each grid under its own names", async ({
  page,
}) => {
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  const tree = main.getByRole("treegrid", { name: "Lotissement" });
  const item = tree.getByRole("row", { name: /Fourniture et montage des armoires/ });
  await item.getByRole("button", { name: "Plier" }).click();
  // The header, the order item, the totals.
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
  await expect(main.getByText("Les postes et les lots ne montrent que ce que")).toHaveCount(0);
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
    "2 sous-projets",
  );
});

test("the settings of a project sort the sub-projects and the contributors, search the contributors and filter both on their other columns, each grid under its own names", async ({
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

test("the settings of a project create and modify a sub-project, present unavailable the deletion of those charged with actual costs or cited by a marked revision, and write the contributors, a proposal confirmed [WF-PRJ-0050-A] [WF-PRJ-0070-A]", async ({
  page,
}) => {
  await openHydrated(page, `${PROJECT}/settings`);
  const main = page.getByRole("main");
  await expect(main.getByRole("note")).toContainText("Maquette");
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
