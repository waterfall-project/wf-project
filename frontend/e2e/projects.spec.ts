// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, sortUntilAddress, WORKING } from "./hydration";
import { withinBox } from "./scroll";

// The fake back serves the first example of each operation: the two projects of the witness,
// which it lists whatever the filter asks — the filter is the server's to apply —, the project
// in progress, its sub-projects, its contributors and the history of its states; its exit
// answers the project completed.
const PROJECT = "/projects/01926f3a-7c00-7000-8000-000000000001";

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

test("a project, its settings and its lifecycle show what the fake back serves, and offer nothing but the exits", async ({
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
  // Nothing to create nor modify: the buttons of the grids and of the filter alone.
  await expect(main.getByRole("button", { name: /Créer|Ajouter|Modifier|Supprimer/ })).toHaveCount(
    0,
  );

  await nav.getByRole("link", { name: "Cycle de vie du projet" }).click();
  await expect(main.getByRole("heading", { level: 1 })).toHaveText("Cycle de vie du projet");
  const history = main.getByRole("table", { name: "Historique des états" });
  await expect(history.getByRole("row")).toHaveCount(4);
  await expect(main.getByRole("region", { name: "Commandes" }).getByRole("button")).toHaveText([
    "Terminer le projet",
    "Déclarer le projet perdu",
    "Abandonner le projet",
  ]);
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
