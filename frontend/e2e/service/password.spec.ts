// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The password of a local account, as its holder meets it (US-0350, WF-ADM-0140): Waterfall asks
 * for none; the account an administrator creates signs in once its holder has set it on the page
 * of the realm, by the link the administrator was given — once, within its hour, the one before
 * it no longer valid —, and the realm holds it to its rules and locks the account after ten
 * failures. The administrator is the one of the installation, which the bootstrap made (US-0420),
 * calling the API as the screen of the accounts does (`accounts.spec.ts`).
 */
import { type APIRequestContext, expect, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  type Administrator,
  expectSignInPage,
  giveIdentifiers,
  LOCAL_PASSWORD,
  localAccount,
  openLink,
  type Person,
  realmSettings,
  setPassword,
  signIn,
  unlock,
  withRealm,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
// What the realm says of a link already used, and of one a newer link replaced (#655).
const SPENT = "Ce lien a déjà servi : demandez-en un nouveau.";
const REPLACED = "Ce lien a été remplacé par un plus récent : utilisez le dernier lien reçu.";
// What the sign-in page says of identifiers it refuses — a lock included, which it does not tell.
const REFUSED = "Nom d'utilisateur ou mot de passe invalide.";

let administrator: Administrator;
let calls: APIRequestContext;

// The administrator for the whole file, by a request context of its own: a path's is its own.
test.beforeAll(async ({ browser, playwright }) => {
  calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  administrator = await accountAdministrator(browser, calls);
});

test.afterAll(async () => {
  await calls.dispose();
});

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT);
});

/** Try to sign a person in from the front, and see the realm refuse her. */
async function refusedSignIn(page: Page, person: Person): Promise<void> {
  await page.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
  await giveIdentifiers(page, person);
  await expectSignInPage(page);
  await expect(page.getByRole("main")).toContainText(REFUSED);
}

test("an account an administrator creates signs in only once its holder has set its password by the link given, which holds it to the rules of the realm and serves once [WF-ADM-0140-A] [WF-ADM-0180-A]", async ({
  page,
}) => {
  const { id, email } = await administrator.create();
  const jeanne: Person = { login: email, email, password: LOCAL_PASSWORD, name: "Jeanne" };
  await refusedSignIn(page, jeanne);

  // Two links asked for: the first no longer valid, the second sets the password.
  const replaced = await administrator.link(id);
  const link = await administrator.link(id);
  await page.goto(replaced);
  await expect(page.getByRole("main")).toContainText(REPLACED);
  await openLink(page, link);
  await setPassword(page, "k7#Qw2ZpX9v");
  await expect(page.getByRole("main")).toContainText("longueur minimale de 12");
  await setPassword(page, email);
  await expect(page.getByRole("main")).toContainText("ne doit pas être identique");
  await setPassword(page, LOCAL_PASSWORD);
  await expect(page.getByRole("heading", { name: "Votre compte a été mis à jour." })).toBeVisible();
  // The page of the realm leads back to Waterfall (#645).
  await page.getByRole("link", { name: "« Revenir à l'application" }).click();
  await expect(page).toHaveURL("/");

  await signIn(page, jeanne, ACCOUNT);
  await expect(page.getByRole("main")).toContainText(email);
  await expect(page.getByRole("main")).toContainText("Créé dans Waterfall");
  // Waterfall shows no field of a password, for her as for anyone (WF-ADM-0140).
  await expect(page.locator("input[type=password]")).toHaveCount(0);
  await page.goto(link);
  await expect(page.getByRole("main")).toContainText(SPENT);
});

// The hour of a link is the lifespan of the action tokens of the realm, a second here: the link of
// any account made meanwhile would expire with it (`playwright.config.ts`, the project `realm`).
test(
  "a link of setting a password opened after its hour is refused [WF-ADM-0140-A]",
  {
    tag: "@realm-wide",
  },
  async ({ page, request }) => {
    const { id } = await administrator.create();
    const link = await withRealm(request, { actionTokenGeneratedByAdminLifespan: 1 }, async () => {
      const made = await administrator.link(id);
      await new Promise((resolve) => setTimeout(resolve, 2_100));
      return made;
    });
    await page.goto(link);
    const said = page.getByRole("main");
    await expect(said).toContainText("Nous sommes désolés");
    await expect(said).not.toContainText(SPENT);
    await expect(said).not.toContainText(REPLACED);
    await expect(page.getByRole("link", { name: "» Cliquez ici pour continuer" })).toHaveCount(0);
  },
);

/** Lock a local account: ten failures on the sign-in page. */
async function failTenTimes(page: Page, person: Person): Promise<void> {
  for (let failure = 0; failure < 10; failure += 1) {
    await refusedSignIn(page, { ...person, password: "not-the-password" });
  }
}

test("ten failures lock the account, which the realm unlocks after fifteen minutes, never for good [WF-ADM-0140-A]", async ({
  browser,
  page,
  request,
}) => {
  const jeanne = await localAccount(browser, administrator);
  await failTenTimes(page, jeanne);
  // Locked, the account refuses its own password.
  await refusedSignIn(page, jeanne);
  // The lock lasts fifteen minutes, which a path does not wait: the realm says so — a lock of
  // fifteen minutes per ten failures, never more —, and lifts none for good.
  expect(
    await realmSettings(request, [
      "bruteForceProtected",
      "permanentLockout",
      "failureFactor",
      "bruteForceStrategy",
      "waitIncrementSeconds",
      "maxFailureWaitSeconds",
    ]),
  ).toEqual({
    bruteForceProtected: true,
    permanentLockout: false,
    failureFactor: 10,
    bruteForceStrategy: "MULTIPLE",
    waitIncrementSeconds: 900,
    maxFailureWaitSeconds: 900,
  });
  await unlock(request, jeanne.email);
  await signIn(page, jeanne, ACCOUNT);
});
