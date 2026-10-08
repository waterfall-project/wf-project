// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, test } from "@playwright/test";

import { compile } from "./compile";
import { openHydrated, WORKING } from "./hydration";

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
  const list = page.getByRole("table", { name: "Liste des projets" });
  await expect(list.getByRole("row")).toHaveCount(3);
  await expect(
    list.getByRole("link", { name: "Modernisation du poste de commande" }),
  ).toBeVisible();

  await filter.getByRole("link", { name: "N’afficher que mes projets" }).click();
  await expect(page).toHaveURL("/");
  await expect(filter).toContainText("Projets dont vous êtes contributeur");
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
