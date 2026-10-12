// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The access roles against the service (US-0380, #833), as the administrator of the installation
 * meets them: on their screen, a role created, renamed in its cell, given a permission in the
 * matrix, then deleted, and the administration taken from the role of the last administrator
 * refused, its role not offered to delete; on the screen of the accounts, its deactivation and the
 * withdrawal of its role refused. Nothing is destroyed: every refusal leaves the platform as it was,
 * and a predefined role is never renamed nor changed — the other paths of the run, beside, act
 * through it. The role of the path is its own, by its label, and no other path gives an account the
 * administration (`Administrator.give`), which would lift the refusals.
 *
 * Of WF-ADM-0010-A, the third sentence alone: a predefined role renamed, its permissions changed, or
 * deleted, would change the platform under the paths beside; the tests of the service hold the
 * second (US-0380). Of WF-ADM-0120-A, the first sentence: the acceptance once a second account holds
 * the administration would lift the refusals of the paths beside; the tests of the service hold it.
 */
import { randomBytes } from "node:crypto";

import { expect, type Locator, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu, WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { ADMINISTRATOR, grantRole, signIn, waterfallAccount } from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
// The table under no search nor filter: an address that says nothing of it would restore those the
// administrator kept on another path.
const ROLES = "/admin/access-roles?search=";
// The table of the accounts, on the administrator of the installation alone.
const USERS = `/admin/users?search=${encodeURIComponent(ADMINISTRATOR.email)}`;
// The refusal of a write that would take the administration from the last account holding it.
const LAST_ADMINISTRATOR = "Au moins un compte actif doit garder les permissions d’administration.";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, ROLES, USERS);
});

/** A label between the quotes of the screen. */
function quoted(label: string): string {
  return `«\u00a0${label}\u00a0»`;
}

/**
 * Press a command on a page that may not be hydrated yet, nothing witnessing it (défaut n° 19):
 * again until React answers the press — the command busy with what it asked, or its answer shown —,
 * never while it is busy. Never until the server answers: its write may wait behind the other
 * actions of the page (défaut n° 15), and a second press would write again.
 */
async function pressUntilAnswered(
  command: Locator,
  answered: Locator,
  press: () => Promise<void> = () => command.click({ timeout: 1_000 }),
): Promise<void> {
  const busy = command.and(command.page().locator('[aria-busy="true"]'));
  await expect(async () => {
    if ((await busy.count()) === 0 && (await answered.count()) === 0) {
      await press();
    }
    await expect(busy.or(answered).first()).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

test("an administrator creates a role, renames it, gives it a permission in the matrix and deletes it, and is refused the administration taken from the role of the last administrator, which is not offered to delete — of WF-ADM-0010-A, its third sentence alone, no predefined role renamed (#833) [WF-ADM-0010-A]", async ({
  page,
}) => {
  // Five writes, each answered and the page read anew: a path of one piece.
  test.slow();
  const suffix = randomBytes(4).toString("hex");
  const created = `Parcours ${suffix}`;
  const renamed = `Parcours renommé ${suffix}`;
  await signIn(page, ADMINISTRATOR, ACCOUNT);
  await page.goto(ROLES);
  const roles = page.getByRole("grid", { name: "Rôles d’habilitation" });
  const told = page.getByRole("status", { name: "Commandes des rôles d’habilitation" });

  // Created from its label alone; no project is opened here, nothing witnesses the hydration: the
  // label is typed and the command pressed again until React answers it.
  const label = page.getByRole("textbox", { name: "Nouveau rôle" });
  const create = page.getByRole("button", { name: "Créer un rôle" });
  const createdTold = told.filter({ hasText: `${quoted(created)} créé.` });
  await pressUntilAnswered(create, createdTold, async () => {
    await label.fill(created);
    await create.click({ timeout: 1_000 });
  });
  await expect(told).toHaveText(`${quoted(created)} créé.`, { timeout: WORKING });
  const cell = roles.getByRole("gridcell", { name: created, exact: true });
  await expect(cell).toBeVisible({ timeout: WORKING });

  // Renamed in its cell, the label typed over the one shown.
  await cell.click();
  await page.keyboard.type(renamed);
  await page.keyboard.press("Enter");
  await expect(roles.getByRole("gridcell", { name: renamed, exact: true })).toBeVisible({
    timeout: WORKING,
  });

  // A permission given in the matrix, which the page read anew keeps.
  const matrix = page.getByRole("table", { name: "Permissions par fonction" });
  const audit = matrix.getByRole("checkbox", {
    name: `${quoted("Consulter le journal d’audit")} pour ${quoted(renamed)}`,
  });
  await expect(audit).not.toBeChecked({ timeout: WORKING });
  await audit.click();
  await expect(audit).toBeChecked();
  // Read anew once the write is answered: the box shows it asked at once, busy until the answer,
  // and a page read before would show the role as it was.
  await expect(audit).toHaveAttribute("aria-busy", "false", { timeout: WORKING });
  await page.reload();
  await expect(audit).toBeChecked({ timeout: WORKING });

  // The administrator of the installation is the last account that holds the administration: its
  // role deprived of the modification of the accounts is refused, and shown as it was. The page read
  // anew may not be hydrated yet, and nothing witnesses it: the box is pressed again until React
  // answers.
  const users = matrix.getByRole("checkbox", {
    name: `${quoted("Modifier les utilisateurs")} pour ${quoted("Administrateur")}`,
  });
  await expect(users).toBeChecked();
  try {
    const refused = page
      .getByRole("main")
      .getByRole("alert")
      .filter({ hasText: LAST_ADMINISTRATOR });
    await pressUntilAnswered(users, refused);
    await expect(refused).toHaveCount(1, { timeout: WORKING });
    await expect(users).toBeChecked({ timeout: WORKING });
  } finally {
    // Once the write is answered — the box shows it asked at once —, accepted, the refusal gone,
    // the role is given back what the paths beside act through.
    await expect(users).toHaveAttribute("aria-busy", "false", { timeout: WORKING });
    if (!(await users.isChecked())) {
      await users.click();
      await expect(users).toBeChecked({ timeout: WORKING });
    }
  }
  // Its role, which it holds, is not offered to delete.
  await expect(
    roles.getByRole("button", { name: `Supprimer ${quoted("Administrateur")}` }),
  ).toHaveAttribute("aria-disabled", "true");

  // Deleted once confirmed, the role leaves the table and the matrix.
  await roles.getByRole("button", { name: `Supprimer ${quoted(renamed)}` }).click();
  const confirmation = page.getByRole("alertdialog", {
    name: `Supprimer ${quoted(renamed)}\u00a0?`,
  });
  await expect(confirmation).toContainText("est définitive");
  await confirmation.getByRole("button", { name: "Supprimer" }).click();
  await expect(told).toHaveText(`${quoted(renamed)} supprimé.`, { timeout: WORKING });
  await expect(roles.getByRole("gridcell", { name: renamed, exact: true })).toHaveCount(0, {
    timeout: WORKING,
  });
  await expect(audit).toHaveCount(0);
});

test("the last administrator is refused its deactivation, presented unavailable, and the withdrawal of its role, on the screen of the accounts, nothing written [WF-ADM-0120-A]", async ({
  page,
}) => {
  // Its sign-in waits its turn behind those of the other workers (`oneAtATime`), then a write.
  test.slow();
  await signIn(page, ADMINISTRATOR, ACCOUNT);
  await page.goto(USERS);
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  await expect(accounts.getByRole("row").last()).toHaveText("1 compte", { timeout: WORKING });
  const name = quoted(ADMINISTRATOR.name);

  // Its deactivation, unavailable as the account lists it, says the condition it lacks; pressed —
  // again until React answers —, it asks nothing, says so above the table, and the account stays
  // active.
  const state = accounts.getByRole("switch", { name: `Compte de ${name} actif` });
  const unmet =
    "Condition non remplie : un autre compte actif portant les permissions d’administration.";
  await expect(state).toHaveAttribute("aria-disabled", "true");
  await expect(state).toHaveAccessibleDescription(unmet);
  const told = page
    .getByRole("main")
    .getByRole("status")
    .filter({ hasText: `La désactivation de ${name} est indisponible. ${unmet}` });
  await expect(async () => {
    // Unavailable, it is no target Playwright would press of itself.
    await state.click({ force: true, timeout: 1_000 });
    await expect(told).toHaveCount(1, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
  await expect(state).toBeChecked();

  // The withdrawal of its role is refused by the server, and the role shown as it was.
  const held = page.getByRole("group", { name: `Rôles de ${name}` });
  const roles = accounts.getByRole("button", { name: `Rôles de ${name}` });
  await openMenu(roles, held);
  const administration = held.getByRole("checkbox", { name: "Administrateur", exact: true });
  await expect(administration).toBeChecked();
  try {
    await administration.click();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(LAST_ADMINISTRATOR, {
      timeout: WORKING,
    });
    await expect(administration).toBeChecked();
  } finally {
    // Once the write is answered — its cell busy until then —, accepted, the refusal gone, the
    // account would hold no role, and could not give it back to itself: the role is given back in
    // the database, for the runs to come on the platform kept.
    await expect(roles).toHaveAttribute("aria-busy", "false", { timeout: WORKING });
    if (waterfallAccount(ADMINISTRATOR.email)?.roles === 0) {
      grantRole(ADMINISTRATOR.email, "Administrateur", []);
    }
  }
});
