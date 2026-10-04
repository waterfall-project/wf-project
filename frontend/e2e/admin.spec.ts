// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";

// The fake back serves the first example of each read: the session, whose role grants the whole
// catalogue, so that every function is offered; the accounts, the roles, the catalogue of the
// permissions, the state of the platform and its backups of the witness. Each screen is reached
// from the navigation, no project opened. The other states — a page of a list, a backup failed —
// are proven by the tests of the pages.

/** The screens of the reference data and of the administration, as the navigation reaches them. */
const SCREENS = [
  ["Paramètres applicatifs", "Paramètres de coûts", "/reference/costs"],
  ["Paramètres applicatifs", "Paramètres de ressources", "/reference/resources"],
  ["Paramètres applicatifs", "Paramètres de risques", "/reference/risks"],
  ["Paramètres applicatifs", "Paramètres d’indicateurs", "/reference/indicators"],
  ["Administration", "Gestion des utilisateurs", "/admin/users"],
  ["Administration", "Gestion des rôles d’habilitation", "/admin/access-roles"],
  ["Administration", "Surveillance de l’état du système", "/system"],
  ["Administration", "Sauvegarde et restauration", "/admin/backups"],
] as const;

/** Follow a link of the navigation, opening first the block of the FBS it is in. */
async function open(page: Page, block: string, name: string) {
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  const button = nav.getByRole("button", { name: block, exact: true });
  if ((await button.getAttribute("aria-expanded")) === "false") {
    await button.click();
  }
  await nav.getByRole("link", { name }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name);
}

test("reaches every screen of the reference data and of the administration with no project opened (US-0250)", async ({
  page,
}) => {
  // Each screen, reached by a click, compiled first (`e2e/compile.ts`).
  await compile(page.request, ...SCREENS.map(([, , route]) => route));
  await page.goto("/");
  for (const [block, name, route] of SCREENS) {
    await open(page, block, name);
    await expect(page).toHaveURL(route);
    // No project was opened: there is none to go back to.
    await expect(page.getByRole("link", { name: "Retour au projet" })).toHaveCount(0);
  }
});

test("reads the accounts, the matrix of the permissions, the state of the platform and the backups, and starts nothing (US-0250)", async ({
  page,
}) => {
  await page.goto("/admin/users");
  const accounts = page.getByRole("table", { name: "Comptes utilisateurs" });
  await expect(accounts.getByRole("row")).toHaveCount(5);
  await expect(
    accounts.getByRole("row", {
      name: "Moreau Alix alix.moreau@example.com Créé dans Waterfall Chef de projet Bureau d'études électricité Désactivé",
    }),
  ).toHaveCount(1);
  await expect(page.getByText("4 comptes")).toBeVisible();

  await page.goto("/admin/access-roles");
  const matrix = page.getByRole("table", { name: "Permissions par fonction" });
  await expect(matrix.getByRole("row")).toHaveCount(56);
  const restore = matrix.getByRole("row", { name: /^Restaurer la plateforme/ });
  await expect(restore.getByRole("cell")).toHaveText([
    "Accordée",
    "Non accordée",
    "Accordée",
    "Non accordée",
  ]);
  await expect(
    matrix.getByRole("rowheader", { name: "FBS-1.4 Sauvegarde et restauration" }),
  ).toBeVisible();

  await page.goto("/system");
  await expect(page.getByText(/^Version installée\s: 1\.0\.0$/)).toBeVisible();
  const operations = page.getByRole("table", { name: "Dernières opérations" });
  // Each instant in the local time of the workstation, once the browser has written it.
  await expect(
    operations.getByRole("row", { name: /^Test de restauration/ }).locator("time"),
  ).not.toBeEmpty();
  await expect(page.getByText("Aucune alerte en cours.")).toBeVisible();

  await page.goto("/admin/backups");
  await expect(page.getByRole("table", { name: "Sauvegardes" }).getByRole("row")).toHaveCount(9);
  await expect(page.getByText("7 sauvegardes conservées")).toBeVisible();
  // Neither a backup nor a restoration is started from here.
  await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
});
