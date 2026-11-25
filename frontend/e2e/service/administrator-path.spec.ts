// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The path of the administrator against the service (US-2890/L2, WF-INTF-0030-A): the holder of the
 * predefined role « Administrateur » creates a local account and gives it a role (FBS-1.1, FBS-1.2),
 * opens the state of the system (FBS-1.3), opens the journal of audit and filters it (FBS-1.5), and
 * starts a backup, which the tracker follows to its end (FBS-1.4). Each screen is reached from the
 * navigation of the administration. The state is asserted on what it holds whatever the platform
 * measures: its sections, not their values.
 */
import { randomBytes } from "node:crypto";

import { expect, type Page, test } from "@playwright/test";

import { ADMINISTRATOR_PATH, BACKUP_DONE, WORKING } from "../bounds";
import { openFilters, pick } from "../check-menu";
import { compileAnswered } from "../compile";
import { openMenu, setExpanded, untilHydrated } from "../hydration";
import { heldToTheContract } from "./contract";
import { accountAdministrator, ADMINISTRATOR, signIn } from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const USERS = "/admin/users";
const SYSTEM = "/system";
const JOURNAL = "/admin/audit-log";
const BACKUPS = "/admin/backups";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, USERS, SYSTEM, JOURNAL, BACKUPS);
});

/** Follow a link of the block « Administration » of the navigation; the screen names its function. */
async function open(page: Page, name: string): Promise<void> {
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await setExpanded(nav.getByRole("button", { name: "Administration", exact: true }), true);
  await nav.getByRole("link", { name }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(name, { timeout: WORKING });
}

test("an administrator creates an account and gives it a role, reads the state of the system, filters the journal of audit and starts a backup [WF-INTF-0030-A]", async ({
  page,
  browser,
  request,
}) => {
  // Four screens, three writes and a backup by the worker: a path of one piece.
  test.setTimeout(ADMINISTRATOR_PATH);
  const suffix = randomBytes(4).toString("hex");
  const lastName = `Perrin ${suffix}`;
  const name = `«\u00a0Éva ${lastName}\u00a0»`;
  const email = `eva.${suffix}@waterfall.test`;
  const administrator = await accountAdministrator(browser, request);
  try {
    await signIn(page, ADMINISTRATOR, ACCOUNT);

    // FBS-1.1, FBS-1.2: an account created, then a role in its cell.
    await open(page, "Gestion des utilisateurs");
    await expect(page).toHaveURL(new RegExp(`^[^?]*${USERS}`));
    const creation = page.getByRole("form", { name: "Créer un compte local" });
    await openMenu(page.getByRole("button", { name: "Créer un compte local" }), creation);
    await creation.getByLabel("Nom", { exact: true }).fill(lastName);
    await creation.getByLabel("Prénom", { exact: true }).fill("Éva");
    await creation.getByLabel("Adresse électronique").fill(email);
    await creation.getByRole("button", { name: "Créer", exact: true }).click();
    const told = page.getByRole("status", { name: "Commandes des comptes" });
    await expect(told).toHaveText(new RegExp(`^Compte ${name} créé`), { timeout: WORKING });
    await page.goto(`${USERS}?search=${suffix}`);
    const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
    await expect(accounts.getByRole("row").last()).toHaveText("1 compte", { timeout: WORKING });
    const roles = page.getByRole("group", { name: `Rôles de ${name}` });
    await openMenu(accounts.getByRole("button", { name: `Rôles de ${name}` }), roles);
    await roles.getByRole("checkbox", { name: "Manager" }).click();
    await expect(told).toHaveText(`Rôles de ${name} attribués.`, { timeout: WORKING });
    await page.keyboard.press("Escape");

    // FBS-1.3: the state of the system.
    await open(page, "Surveillance de l’état du système");
    await expect(page).toHaveURL(SYSTEM);
    await expect(page.getByText(/^Version installée\s: \S+/)).toBeVisible();
    for (const section of ["Alertes en cours", "Composants", "Dernières opérations"]) {
      await expect(page.getByRole("region", { name: section, exact: true })).toBeVisible();
    }

    // FBS-1.5: the journal, filtered on the action of the attribution made above.
    await open(page, "Journal d’audit");
    await untilHydrated(page);
    await openFilters(page);
    await pick(page, "Action", "Attribution des rôles d’un compte");
    await expect(page).toHaveURL(/actions=user_access_roles_set/, { timeout: WORKING });
    const journal = page.getByRole("grid", { name: "Journal d’audit" });
    await expect(
      journal.getByRole("row").filter({ hasText: "Attribution des rôles d’un compte" }).first(),
    ).toBeVisible({ timeout: WORKING });
    // The filter filters: no row of data names another action (the foot, « N inscriptions », apart).
    const rows = journal.getByRole("row");
    await expect(rows.last()).toHaveText(/inscriptions?$/);
    const others = rows
      .filter({ hasNot: page.getByRole("columnheader") })
      .filter({ hasNotText: /inscriptions?$/ })
      .filter({ hasNotText: "Attribution des rôles d’un compte" });
    await expect(others).toHaveCount(0);

    // FBS-1.4: a backup started, followed by the tracker until the worker has taken it.
    await open(page, "Sauvegarde et restauration");
    await expect(page).toHaveURL(BACKUPS);
    await untilHydrated(page);
    await page.getByRole("button", { name: "Sauvegarder maintenant" }).click();
    await expect(
      page
        .getByRole("main")
        .getByRole("status")
        .filter({ hasText: /^Sauvegarde lancée/ }),
    ).toBeVisible({ timeout: WORKING });
    const followed = page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ });
    await followed.click();
    const entries = page.getByRole("region", { name: "Tâches de fond" }).getByRole("listitem");
    await expect(entries.getByText("Réussie")).toBeVisible({ timeout: BACKUP_DONE });
  } finally {
    // The account is left anonymised, whatever the path reached. A cleanup that fails is told,
    // never thrown: it would hide the error of the path (#963).
    try {
      await administrator.retire(email);
    } catch (failure) {
      console.error("The cleanup of the administrator path failed:", failure);
    }
  }
});
