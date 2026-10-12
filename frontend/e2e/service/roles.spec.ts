// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the access roles against the service (US-0380, #833), as the administrator of the
 * installation enters it: a role created, renamed in its cell, given a permission in the matrix,
 * then deleted; the administration taken from the last administrator refused. The role of the path
 * is its own, by its label: the other paths of the run, beside it, give no account the
 * administration, which would lift the refusal.
 */
import { randomBytes } from "node:crypto";

import { expect, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import { ADMINISTRATOR, signIn } from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
// The table under no search nor filter: an address that says nothing of it would restore those the
// administrator kept on another path.
const ROLES = "/admin/access-roles?search=";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, ROLES);
});

/** A label between the quotes of the screen. */
function quoted(label: string): string {
  return `«\u00a0${label}\u00a0»`;
}

test("an administrator creates a role, renames it, gives it a permission in the matrix and deletes it, and is refused the administration taken from the last administrator, whose role is not offered to delete (#833) [WF-ADM-0010-A] [WF-ADM-0120-A]", async ({
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
  // command is pressed again until React answers it.
  const label = page.getByRole("textbox", { name: "Nouveau rôle" });
  await expect(async () => {
    await label.fill(created);
    await page.getByRole("button", { name: "Créer un rôle" }).click();
    await expect(told).toHaveText(`${quoted(created)} créé.`, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
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
  await page.reload();
  await expect(audit).toBeChecked({ timeout: WORKING });

  // The administrator of the installation is the last account that holds the administration: its
  // role deprived of the modification of the accounts is refused, and shown as it was.
  const users = matrix.getByRole("checkbox", {
    name: `${quoted("Modifier les utilisateurs")} pour ${quoted("Administrateur")}`,
  });
  await expect(users).toBeChecked();
  await users.click();
  const refusal = page.getByRole("main").getByRole("alert");
  await expect(refusal).toContainText(
    "Au moins un compte actif doit garder les permissions d’administration.",
    { timeout: WORKING },
  );
  await expect(users).toBeChecked();
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
  await expect(told).toHaveText(`${quoted(renamed)} supprimé.`);
  await expect(roles.getByRole("gridcell", { name: renamed, exact: true })).toHaveCount(0, {
    timeout: WORKING,
  });
  await expect(audit).toHaveCount(0);
});
