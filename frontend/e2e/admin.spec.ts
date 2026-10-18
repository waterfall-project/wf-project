// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { expect, type Page, test } from "@playwright/test";

import { compile } from "./compile";
import { setExpanded, sortUntilAddress, WORKING } from "./hydration";

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
  ["Administration", "Journal d’audit", "/admin/audit-log"],
] as const;

/**
 * Follow a link of the navigation, opening first the block of the FBS it is in, once React
 * answers the press (`setExpanded`).
 */
async function open(page: Page, block: string, name: string) {
  const nav = page.getByRole("navigation", { name: "Fonctions" });
  await setExpanded(nav.getByRole("button", { name: block, exact: true }), true);
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

test("reads the accounts, the matrix of the permissions, the state of the platform and the backups (US-0250)", async ({
  page,
}) => {
  await page.goto("/admin/users");
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  // The header, the seven accounts, the totals: how many the server retained.
  await expect(accounts.getByRole("row")).toHaveCount(9);
  // The node before the roles (#379), which the session may attribute: the cell names its list.
  await expect(
    accounts.getByRole("row", {
      name: /^Moreau Alix alix\.moreau@example\.com Créé dans Waterfall Bureau d'études électricité Rôles de/,
    }),
  ).toHaveCount(1);
  await expect(accounts.getByRole("row").last()).toHaveText("7 comptes");

  await page.goto("/admin/access-roles");
  const matrix = page.getByRole("table", { name: "Permissions par fonction" });
  // A header, the forty-one permissions of the functions — the functions in reading alone, the
  // state of the system, the journal of audit and the views of the portfolio, have their
  // consultation alone (#739) —, and the ten permissions of their own.
  await expect(matrix.getByRole("row")).toHaveCount(52);
  await expect(
    matrix.getByRole("rowheader", { name: "Journal d’audit", exact: true }),
  ).toBeVisible();
  // The session may modify the roles: each cell is the checkbox of a permission for a role,
  // checked when the role holds it.
  const restore = matrix.getByRole("row").filter({
    has: page.getByRole("rowheader", { name: "Restaurer la plateforme", exact: true }),
  });
  await expect(restore.getByRole("checkbox")).toHaveCount(7);
  for (const [role, held] of [
    ["Administrateur", true],
    ["Auditeur", false],
    ["Chef de projet", false],
    ["Chiffreur", false],
    ["Direction de projet", true],
    ["Manager", false],
    ["Pilotage de projet", false],
  ] as const) {
    await expect(
      matrix.getByRole("checkbox", {
        name: `«\u00a0Restaurer la plateforme\u00a0» pour «\u00a0${role}\u00a0»`,
        exact: true,
      }),
    ).toBeChecked({ checked: held });
  }
  await expect(
    matrix.getByRole("rowheader", { name: "Sauvegarde et restauration", exact: true }),
  ).toBeVisible();

  await page.goto("/system");
  await expect(page.getByText(/^Version installée\s: 1\.0\.0$/)).toBeVisible();
  const operations = page.getByRole("table", { name: "Dernières opérations" });
  // Each instant in the local time of the workstation, once the browser has written it.
  await expect(
    operations.getByRole("row", { name: /^Test de restauration/ }).locator("time"),
  ).not.toBeEmpty();
  // The copy of the last backup outside the platform, verified (WF-EXP-0050, #488).
  await expect(
    operations.getByRole("row", { name: /^Copie externe de la sauvegarde/ }),
  ).toContainText("Réussie");
  await expect(page.getByText("Aucune alerte en cours.")).toBeVisible();

  await page.goto("/admin/backups");
  // The header, the eight backups, the totals: how many the server retained.
  const backups = page.getByRole("grid", { name: "Sauvegardes" });
  await expect(backups.getByRole("row")).toHaveCount(10);
  await expect(backups.getByRole("row").last()).toHaveText("8 sauvegardes");
  await expect(page.getByText("7 sauvegardes conservées")).toBeVisible();
  // Each scheduled backup copied to the location the installation declares, read only (#488).
  await expect(
    page.getByText("Vers secours-lyon, dossier waterfall/sauvegardes — 30 copies gardées"),
  ).toBeVisible();
});

test("starts a backup, marks one to be kept, downloads one and restores the platform from one, confirmed by its identifier typed [WF-ADM-0160-A]", async ({
  page,
}) => {
  await page.goto("/admin/backups");
  const backups = page.getByRole("grid", { name: "Sauvegardes" });
  const lastNight = backups.getByRole("row").nth(1);
  // A command names its backup by its date once the browser has written it: the page is hydrated.
  const keep = lastNight.getByRole("button", { name: /^Conserver la sauvegarde du \d/ });
  await expect(keep).toBeVisible();
  const told = page.getByRole("main").getByRole("status").filter({ hasText: /\S/ });
  const tasks = page.getByRole("region", { name: "Tâches de fond" });

  // A backup started now goes to the tracker of the shell, as any background task.
  await page.getByRole("button", { name: "Sauvegarder maintenant" }).click();
  await expect(told).toHaveText(/^Sauvegarde lancée/);
  await expect(tasks).toBeVisible();

  // Marked to be kept, the backup is shown as the server answered it: the fake back keeps nothing.
  await keep.click();
  await expect(told).toHaveText(/^La sauvegarde du .+ est marquée à conserver\.$/);
  await expect(
    lastNight.getByRole("button", { name: /^Ne plus conserver la sauvegarde du / }),
  ).toBeVisible();
  await expect(lastNight).toContainText("Marquée à conserver");

  // Downloaded as an attachment, by the route of the front that hands it on as a stream,
  // under the name the contract gives it (the example of Content-Disposition, L42h).
  const downloaded = page.waitForEvent("download");
  await lastNight.getByRole("link", { name: /^Télécharger la sauvegarde du / }).click();
  expect((await downloaded).suggestedFilename()).toBe("waterfall-backup-20260603T010000Z.tar");

  // Restored only once its identifier is typed, the dialog naming its date and what is lost.
  const kept = backups.getByRole("row").nth(8);
  await kept
    .getByRole("button", { name: /^Restaurer la plateforme depuis la sauvegarde du / })
    .click();
  const dialog = page.getByRole("dialog", { name: "Restaurer la plateforme" });
  await expect(dialog).toContainText(/sauvegarde du .*2026.*sans retour possible/);
  const restore = dialog.getByRole("button", { name: "Restaurer" });
  await expect(restore).toBeDisabled();
  await dialog
    .getByRole("textbox", { name: "Pour confirmer, saisissez l’identifiant de la sauvegarde" })
    .fill("01926f3a-7c00-7000-8000-000000000900");
  await restore.click();
  await expect(dialog).toBeHidden();
  // Queued, the restoration gives way to the screen of its maintenance (US-0440), which follows
  // it to its end; the tracker of the shell does not.
  await expect(
    page.getByRole("status", { name: "Restauration de la plateforme en cours" }),
  ).toBeVisible();
  await expect(tasks.getByRole("progressbar", { name: /^Restauration «/ })).toHaveCount(0);
});

test("sets the schedule of the backups whole, its time in universal time, after testing the external location of its copy", async ({
  page,
}) => {
  await page.goto("/admin/backups");
  // A command names its backup by its date once the browser has written it: the page is hydrated.
  await expect(
    page.getByRole("button", { name: /^Conserver la sauvegarde du \d/ }).first(),
  ).toBeVisible();
  const schedule = page.getByRole("region", { name: "Planification" });
  await schedule.getByRole("button", { name: "Modifier la planification" }).click();
  const form = page.getByRole("dialog", { name: "Modifier la planification" });
  // The time in universal time, as the contract gives it, the local time it stands for beside.
  await expect(form.getByLabel("Heure (UTC)")).toHaveValue("01:00");
  await expect(form.getByLabel("Heure (UTC)")).toHaveAccessibleDescription(
    /^Soit \d\d:\d\d à l’heure de ce poste\.$/,
  );
  // The location the installation declares, tested in the folder of the copies.
  await expect(form.getByLabel("Copie externe vers")).toHaveValue("secours-lyon");
  await form.getByRole("button", { name: "Tester l’emplacement" }).click();
  await expect(form.getByRole("status")).toHaveText(
    /^«\ssecours-lyon\s» éprouvé le .+, dossier waterfall\/sauvegardes\s: le fichier témoin a été écrit puis effacé\.$/,
  );
  // Fourteen kept on the platform, the thirty copies outside it at least as many (WF-EXP-0050).
  await form.getByRole("textbox", { name: "Sauvegardes conservées" }).fill("14");
  await form.getByRole("button", { name: "Enregistrer" }).click();
  await expect(form).toBeHidden();
  await expect(schedule.getByRole("status")).toHaveText("Planification enregistrée.");
  await expect(schedule).toContainText("14 sauvegardes conservées");
});

test("sorts and filters the backups by the server, under the names of the contract, back to their first page [WF-IHM-0130-A]", async ({
  page,
}) => {
  await page.goto("/admin/backups?offset=5");
  const backups = page.getByRole("grid", { name: "Sauvegardes" });
  // The most recent first unless asked (EP-14/L43f); a header asks the server for its sort, back
  // to the first page.
  await expect(backups.getByRole("columnheader", { name: /^Date/ })).toHaveAttribute(
    "aria-sort",
    "descending",
  );
  await sortUntilAddress(
    backups.getByRole("columnheader", { name: /^Taille/ }),
    backups,
    "/admin/backups?sort_by=size_bytes&sort_order=asc",
  );
  // An origin and a marking chosen keep the sort, under the names of the contract.
  const origins = page.getByRole("group", { name: "Filtrer par déclenchement" });
  await origins.getByRole("button", { name: "Planifiée" }).click();
  await expect(page).toHaveURL(
    "/admin/backups?sort_by=size_bytes&sort_order=asc&origins=scheduled",
    {
      timeout: WORKING,
    },
  );
  await expect(origins.getByRole("button", { name: "Planifiée" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  const retention = page.getByRole("combobox", { name: "Conservation" });
  await retention.selectOption({ label: "Marquées à conserver" });
  await expect(retention).toHaveValue("true");
  await expect(page).toHaveURL(/origins=scheduled&is_retained=true$/, { timeout: WORKING });
  // A bound of the size, in bytes, as the contract counts it.
  const bounds = page.getByRole("form", { name: "Bornes des sauvegardes" });
  await bounds.getByRole("textbox", { name: "Taille (octets), max." }).fill("2000000000");
  await bounds.getByRole("button", { name: "Filtrer" }).click();
  await expect(page).toHaveURL(/is_retained=true&size_bytes_max=2000000000$/, {
    timeout: WORKING,
  });
  // The fake back answers its example whatever is asked: what the screen asks is what this proves.
  await expect(backups.getByRole("row").last()).toHaveText("8 sauvegardes");
});

test("sorts, searches and filters the accounts by the server, under the names of the contract, back to their first page [WF-IHM-0060-A]", async ({
  page,
}) => {
  await page.goto("/admin/users?offset=2");
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  // A header asks the server for its sort, back to the first page.
  await sortUntilAddress(
    accounts.getByRole("columnheader", { name: "Rattachement" }),
    accounts,
    "/admin/users?sort_by=org_node&sort_order=asc",
  );
  // An origin chosen keeps the sort; a second keeps the first, in the order of the contract.
  const origins = page.getByRole("group", { name: "Filtrer par origine" });
  await origins.getByRole("button", { name: "Importé de l’annuaire" }).click();
  await expect(page).toHaveURL("/admin/users?sort_by=org_node&sort_order=asc&origins=directory", {
    timeout: WORKING,
  });
  await expect(origins.getByRole("button", { name: "Importé de l’annuaire" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await origins.getByRole("button", { name: "Créé dans Waterfall" }).click();
  await expect(page).toHaveURL(
    "/admin/users?sort_by=org_node&sort_order=asc&origins=local%2Cdirectory",
    { timeout: WORKING },
  );
  await page
    .getByRole("searchbox", { name: "Rechercher dans «\u00a0Comptes utilisateurs\u00a0»" })
    .fill("Mor");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/origins=local%2Cdirectory&search=Mor$/, { timeout: WORKING });
  // A role chosen, under the name of the contract, by its identifier.
  const roles = page.getByRole("group", { name: "Filtrer par rôle" });
  await roles.getByRole("button", { name: "Manager" }).click();
  await expect(page).toHaveURL(/search=Mor&access_role_ids=01926f3a-7c00-7000-8000-000000000702$/, {
    timeout: WORKING,
  });
  await expect(roles.getByRole("button", { name: "Manager" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // The active accounts alone, by the one choice of the state, under the name of the contract.
  const state = page.getByRole("combobox", { name: "État du compte" });
  await state.selectOption({ label: "Comptes actifs" });
  await expect(state).toHaveValue("true");
  await expect(page).toHaveURL(/access_role_ids=[\w-]+&is_active=true$/, { timeout: WORKING });
  // The fake back answers its example whatever is asked: what the screen asks is what this proves.
  await expect(accounts.getByRole("row").last()).toHaveText("7 comptes");
});

test("enters the table of the accounts — a state on its switch, the roles of an account, a local account created, a link given, a deactivated one anonymised once confirmed — and offers to delete none [WF-ADM-0060-A]", async ({
  page,
}) => {
  // The fake back answers each write by its example, and keeps nothing: the accounts written are
  // those the examples write — Noé Vidal deactivated, Alix Moreau anonymised, a role given to Sacha
  // Lefèvre, Léa Garnier created —, shown as answered over the page read anew.
  await page.goto("/admin/users");
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  const told = page.getByRole("status", { name: "Commandes des comptes" });
  await expect(page.getByRole("main").getByRole("button", { name: /Supprimer/ })).toHaveCount(0);
  // No project is opened here, nothing witnesses the hydration: the switch is pressed again until
  // React answers.
  const vidal = accounts.getByRole("switch", { name: "Compte de «\u00a0Noé Vidal\u00a0» actif" });
  await expect(async () => {
    await vidal.click();
    await expect(told).toHaveText("«\u00a0Noé Vidal\u00a0» désactivé.", { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(vidal).not.toBeChecked();

  // A deactivated account lists its anonymisation — Alix Moreau, and Noé Vidal once deactivated —;
  // the active ones do not. Irreversible, it is confirmed first (WF-ADM-0060).
  await expect(accounts.getByRole("button", { name: /^Anonymiser «/ })).toHaveCount(2);
  await accounts.getByRole("button", { name: "Anonymiser «\u00a0Alix Moreau\u00a0»" }).click();
  const confirmation = page.getByRole("alertdialog", {
    name: "Anonymiser «\u00a0Alix Moreau\u00a0»\u00a0?",
  });
  await expect(confirmation).toContainText("est irréversible");
  await confirmation.getByRole("button", { name: "Anonymiser" }).click();
  await expect(told).toHaveText("Compte anonymisé.");

  // The last administrator, as the account lists its commands: her deactivation unavailable,
  // naming the condition she lacks (WF-ADM-0120).
  const camille = accounts.getByRole("switch", {
    name: "Compte de «\u00a0Camille Martin\u00a0» actif",
  });
  await expect(camille).toHaveAttribute("aria-disabled", "true");
  await expect(camille).toHaveAccessibleDescription(
    "Condition non remplie\u00a0: un autre compte actif portant les permissions d’administration.",
  );

  // A role of the installation given to an account that held none, in its cell.
  await accounts.getByRole("button", { name: "Rôles de «\u00a0Sacha Lefèvre\u00a0»" }).click();
  const roles = page.getByRole("group", { name: "Rôles de «\u00a0Sacha Lefèvre\u00a0»" });
  await roles.getByRole("checkbox", { name: "Chiffreur" }).click();
  await expect(told).toHaveText("Rôles de «\u00a0Sacha Lefèvre\u00a0» attribués.");
  await expect(roles.getByRole("checkbox", { name: "Chiffreur" })).toBeChecked();
  await page.keyboard.press("Escape");

  // A local account created from its names and its address.
  await page.getByRole("button", { name: "Créer un compte local" }).click();
  const creation = page.getByRole("form", { name: "Créer un compte local" });
  await creation.getByLabel("Nom", { exact: true }).fill("Garnier");
  await creation.getByLabel("Prénom", { exact: true }).fill("Léa");
  await creation.getByLabel("Adresse électronique").fill("lea.garnier@example.com");
  await creation.getByRole("button", { name: "Créer", exact: true }).click();
  // No invitation went, as the fake back answers: the link is offered at once (#816).
  await expect(told).toHaveText(/^Compte «\u00a0Léa Garnier\u00a0» créé\u00a0; aucune invitation/);
  await page.getByRole("button", { name: "Remettre le lien" }).click();
  const given = page.getByRole("dialog", {
    name: "Lien de fixation du mot de passe de «\u00a0Léa Garnier\u00a0»",
  });
  await expect(given.getByRole("textbox", { name: "Lien" })).toHaveValue(/^https:\/\//);
  await given.getByRole("button", { name: "Fermer" }).click();
  await expect(given).toHaveCount(0);

  // The link of a local account, given once, to hand over by another channel (WF-ADM-0140).
  await accounts
    .getByRole("button", {
      name: "Lien de fixation du mot de passe de «\u00a0Camille Martin\u00a0»",
    })
    .click();
  const link = page.getByRole("dialog", {
    name: "Lien de fixation du mot de passe de «\u00a0Camille Martin\u00a0»",
  });
  await expect(link.getByRole("textbox", { name: "Lien" })).toHaveValue(
    /^https:\/\/auth\.waterfall\.example\.net\/realms\/waterfall\//,
  );
  await link.getByRole("button", { name: "Fermer" }).click();
  await expect(link).toHaveCount(0);
});

test("deletes an access role from its row once confirmed, its deletion unavailable while an account holds it, and sorts the roles by the server", async ({
  page,
}) => {
  await page.goto("/admin/access-roles");
  const roles = page.getByRole("grid", { name: "Rôles d’habilitation" });
  await sortUntilAddress(
    roles.getByRole("columnheader", { name: "Comptes porteurs" }),
    roles,
    "/admin/access-roles?sort_by=holder_count&sort_order=asc",
  );
  // A role an account holds is not deleted: its deletion is unavailable.
  await expect(
    roles.getByRole("button", { name: "Supprimer «\u00a0Chiffreur\u00a0»" }),
  ).toHaveAttribute("aria-disabled", "true");
  // Final, the deletion is confirmed first. The fake back answers it, and keeps nothing: the page
  // read anew lists the role still.
  await roles.getByRole("button", { name: "Supprimer «\u00a0Administrateur\u00a0»" }).click();
  const confirmation = page.getByRole("alertdialog", {
    name: "Supprimer «\u00a0Administrateur\u00a0»\u00a0?",
  });
  await expect(confirmation).toContainText("est définitive");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(page.getByRole("status", { name: "Commandes des rôles d’habilitation" })).toHaveText(
    "«\u00a0Administrateur\u00a0» supprimé.",
  );
  await expect(page.getByRole("form", { name: "Création d’un rôle" })).toBeVisible();
  // A column of the matrix for each role the table retains, each cell a checkbox.
  const matrix = page.getByRole("table", { name: "Permissions par fonction" });
  await expect(matrix.getByRole("columnheader")).toHaveCount(9);
  await expect(
    matrix.getByRole("checkbox", {
      name: "«\u00a0Restaurer la plateforme\u00a0» pour «\u00a0Administrateur\u00a0»",
    }),
  ).toBeChecked();
});

test("filters the access roles by their kind and between bounds of their holders, under the names of the contract [WF-IHM-0130-A]", async ({
  page,
}) => {
  await page.goto("/admin/access-roles");
  const roles = page.getByRole("grid", { name: "Rôles d’habilitation" });
  // Nothing witnesses the hydration: the sort is pressed again until React answers it.
  await sortUntilAddress(
    roles.getByRole("columnheader", { name: "Libellé" }),
    roles,
    "/admin/access-roles?sort_by=label&sort_order=asc",
  );
  const kind = page.getByRole("combobox", { name: "Nature" });
  await kind.selectOption({ label: "Rôles composés" });
  await expect(kind).toHaveValue("false");
  await expect(page).toHaveURL(
    "/admin/access-roles?sort_by=label&sort_order=asc&is_predefined=false",
    {
      timeout: WORKING,
    },
  );
  const bounds = page.getByRole("form", { name: "Bornes des rôles d’habilitation" });
  await bounds.getByRole("textbox", { name: "Comptes porteurs, max." }).fill("0");
  await bounds.getByRole("button", { name: "Filtrer" }).click();
  await expect(page).toHaveURL(/is_predefined=false&holder_count_max=0$/, { timeout: WORKING });
  // The fake back answers its example whatever is asked: what the screen asks is what this proves.
  await expect(roles.getByRole("row").last()).toHaveText("7 rôles");
});

test("sorts the access roles by the author of their last modification, names each author — the platform by its own label — and filters them on the author of their creation, under the names of the contract [WF-IHM-0060-A]", async ({
  page,
}) => {
  await page.goto("/admin/access-roles");
  const roles = page.getByRole("grid", { name: "Rôles d’habilitation" });
  await sortUntilAddress(
    roles.getByRole("columnheader", { name: "Modifié par" }),
    roles,
    "/admin/access-roles?sort_by=updated_by&sort_order=asc",
  );
  // A role delivered with the installation, by the platform; one composed since, by its account.
  await expect(roles.getByRole("row", { name: /^Administrateur/ })).toContainText("La plateforme");
  await expect(roles.getByRole("row", { name: /^Auditeur/ })).toContainText("Camille Martin");
  const author = page.getByRole("combobox", { name: "Créé par" });
  await author.selectOption({ label: "La plateforme" });
  await expect(page).toHaveURL(
    "/admin/access-roles?sort_by=updated_by&sort_order=asc&created_by_kind=platform",
    { timeout: WORKING },
  );
});
