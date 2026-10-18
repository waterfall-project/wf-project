// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The screen of the accounts against the service (US-0360, #881), as the administrator of the
 * installation enters it: a local account created, given a role in its cell and its link, which its
 * holder sets her password by; deactivated, she is refused; reactivated, she signs in again with
 * the role she held; deactivated and anonymised, no screen names her any more. The account of the
 * path is its own, found by a search on its name; the role it is given carries no administration,
 * which would lift the refusal the screen of the roles proves beside it.
 */
import { randomBytes } from "node:crypto";

import { type Browser, expect, type Locator, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu, WORKING } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  accountButton,
  ADMINISTRATOR,
  expectPasswordSet,
  giveIdentifiers,
  LOCAL_PASSWORD,
  openLink,
  type Person,
  setPassword,
  signIn,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const USERS = "/admin/users";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, USERS);
});

/** What the holder of the account meets, on a workstation of her own: the screen she lands on. */
async function holderSignsIn(browser: Browser, holder: Person): Promise<Page> {
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await page.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
  await giveIdentifiers(page, holder);
  await expect(page).toHaveURL(ACCOUNT);
  return page;
}

/**
 * Turn a switch of the table, on a page that may not be hydrated yet: pressed only while it says
 * the state it had, and again until it says the other — a press React answered is never undone.
 */
async function turn(state: Locator, from: boolean): Promise<void> {
  await expect(async () => {
    if ((await state.getAttribute("aria-checked")) === String(from)) {
      await state.click();
    }
    await expect(state).toHaveAttribute("aria-checked", String(!from), { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

test("an administrator creates a local account, gives it a role and its link; deactivated, it is refused, reactivated, it signs in with its role, and anonymised, no screen names it — none offered to delete [WF-ADM-0060-A]", async ({
  page,
  browser,
}) => {
  // Seven writes, and the holder signed in three times: a path of one piece.
  test.slow();
  const suffix = randomBytes(4).toString("hex");
  const lastName = `Garnier ${suffix}`;
  const email = `lea.${suffix}@waterfall.test`;
  const holder: Person = { login: email, email, password: LOCAL_PASSWORD, name: `Léa ${lastName}` };
  const name = `«\u00a0${holder.name}\u00a0»`;
  // The table under no search nor filter: an address that says nothing of it would restore those
  // the administrator kept on another path.
  await signIn(page, ADMINISTRATOR, ACCOUNT);
  await page.goto(`${USERS}?search=`);
  const told = page.getByRole("status", { name: "Commandes des comptes" });
  const accounts = page.getByRole("grid", { name: "Comptes utilisateurs" });
  // The table shown, its count under its rows, before none of them is found to offer a deletion.
  await expect(accounts.getByRole("row").last()).toHaveText(/^[\d\s]+ comptes?$/, {
    timeout: WORKING,
  });
  await expect(page.getByRole("main").getByRole("button", { name: /Supprimer/ })).toHaveCount(0);

  // Created from its names and its address.
  const creation = page.getByRole("form", { name: "Créer un compte local" });
  await openMenu(page.getByRole("button", { name: "Créer un compte local" }), creation);
  await creation.getByLabel("Nom", { exact: true }).fill(lastName);
  await creation.getByLabel("Prénom", { exact: true }).fill("Léa");
  await creation.getByLabel("Adresse électronique").fill(email);
  await creation.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(told).toHaveText(new RegExp(`^Compte ${name} créé`), { timeout: WORKING });

  // Found by its name, the one account of the search.
  await page.goto(`${USERS}?search=${suffix}`);
  await expect(accounts.getByRole("row").last()).toHaveText("1 compte", { timeout: WORKING });

  // A role in its cell.
  const roles = page.getByRole("group", { name: `Rôles de ${name}` });
  const rolesButton = accounts.getByRole("button", { name: `Rôles de ${name}` });
  await openMenu(rolesButton, roles);
  await roles.getByRole("checkbox", { name: "Manager" }).click();
  await expect(told).toHaveText(`Rôles de ${name} attribués.`, { timeout: WORKING });
  await page.keyboard.press("Escape");

  // Its link, given once, which its holder sets her password by.
  const linkDialog = page.getByRole("dialog", {
    name: `Lien de fixation du mot de passe de ${name}`,
  });
  await accounts
    .getByRole("button", { name: `Lien de fixation du mot de passe de ${name}` })
    .click();
  const link = await linkDialog.getByRole("textbox", { name: "Lien" }).inputValue();
  await linkDialog.getByRole("button", { name: "Fermer" }).click();
  const setting = await browser.newPage({ locale: "fr-FR", ignoreHTTPSErrors: true });
  await openLink(setting, link);
  await setPassword(setting, LOCAL_PASSWORD);
  await expectPasswordSet(setting);
  await setting.close();
  const signedIn = await holderSignsIn(browser, holder);
  await expect(accountButton(signedIn, holder)).toBeVisible();
  await signedIn.context().close();

  // Deactivated on its switch: its holder is refused.
  const state = accounts.getByRole("switch", { name: `Compte de ${name} actif` });
  await turn(state, true);
  await expect(told).toHaveText(`${name} désactivé.`, { timeout: WORKING });
  const refused = await holderSignsIn(browser, holder);
  await expect(refused.getByRole("heading", { level: 1 })).toHaveText("Compte désactivé");
  await refused.context().close();

  // Reactivated, it signs in again, with the role it held.
  await turn(state, false);
  await expect(told).toHaveText(`${name} réactivé.`, { timeout: WORKING });
  await openMenu(rolesButton, roles);
  await expect(roles.getByRole("checkbox", { name: "Manager" })).toBeChecked();
  await expect(roles.getByRole("checkbox", { checked: true })).toHaveCount(1);
  await page.keyboard.press("Escape");
  const again = await holderSignsIn(browser, holder);
  await expect(accountButton(again, holder)).toBeVisible();
  await again.context().close();

  // Deactivated, then anonymised once confirmed: the search on its name finds it no more.
  await turn(state, true);
  await expect(told).toHaveText(`${name} désactivé.`, { timeout: WORKING });
  await accounts.getByRole("button", { name: `Anonymiser ${name}` }).click();
  const confirmation = page.getByRole("alertdialog", { name: `Anonymiser ${name}\u00a0?` });
  await expect(confirmation).toContainText("est irréversible");
  await confirmation.getByRole("button", { name: "Anonymiser" }).click();
  await expect(told).toHaveText("Compte anonymisé.", { timeout: WORKING });
  await page.goto(`${USERS}?search=${suffix}`);
  await expect(page.getByRole("main")).toContainText("Aucun compte", { timeout: WORKING });
  await expect(page.getByRole("main")).not.toContainText(lastName);
});
