// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * Signing in with the account one has (US-0350, WF-ARC-0030, WF-ADM-0180): a local account, one of
 * the directory, one of the external provider the realm relays — each signs in at the realm, is
 * admitted by Waterfall, and acts as its roles allow, which the database of the platform gives
 * until the bootstrap of an installation (US-0420). A session left idle beyond the life of its
 * refresh token leads back to the sign-in page, then to the screen aimed at, its address whole.
 */
import { type Browser, expect, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  accountOfTheRealmAlone,
  DIRECTORY,
  expectSignInPage,
  EXTERNAL,
  giveIdentifiers,
  grantRole,
  localAccount,
  newToTheProvider,
  type Person,
  REALM,
  removeFromRealm,
  removeFromTheProvider,
  signIn,
  under,
  waterfallAccount,
  withdrawRoles,
  withRealm,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const USERS = "/admin/users";

let local: Person;

// The local account of the file, which an administrator creates and its holder sets the password of.
test.beforeAll(async ({ browser, playwright }) => {
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  local = await localAccount(browser, administrator);
  administrator.done();
  await calls.dispose();
});

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", "/auth/sign-out", ACCOUNT, USERS);
});

/** A page of a workstation of its own, in French, which trusts the front end of Keycloak. */
async function workstation(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  return context.newPage();
}

/** The table of the accounts, as a person reads it: refused without a role, which says nothing. */
async function readsTheAccounts(page: Page): Promise<boolean> {
  await page.goto(USERS);
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toHaveText(/^(Gestion des utilisateurs|Introuvable)$/);
  return (await heading.textContent()) === "Gestion des utilisateurs";
}

test("a local account, an account of the directory and one of the external provider each sign in, and act as their roles in Waterfall allow — none without one [WF-ARC-0030-A] [WF-ADM-0180-A]", async ({
  browser,
  request,
}) => {
  // Three people, each signed in at the realm and her screens read twice: a path of one piece.
  test.setTimeout(90_000);
  // A person new to the provider, whom Waterfall has never seen, whatever the platform saw before:
  // her first sign-in creates her account, from the provider, without a role.
  const external = await newToTheProvider(request);
  expect(waterfallAccount(external.email)).toBeUndefined();
  const origins = new Map([
    [local, "Créé dans Waterfall"],
    [DIRECTORY, "Importé de l’annuaire"],
    [external, "Créé par le fournisseur d’identité"],
  ]);
  try {
    for (const [person, origin] of origins) {
      const page = await workstation(browser);
      await signIn(page, person, ACCOUNT);
      await expect(page.getByRole("main")).toContainText(origin);
      expect(waterfallAccount(person.email)?.roles).toBe(0);
      expect(await readsTheAccounts(page)).toBe(false);
      grantRole(person.email, "Consultation des comptes (parcours)", ["users.read"]);
      expect(await readsTheAccounts(page)).toBe(true);
      await page.context().close();
    }
    expect(waterfallAccount(external.email)?.origin).toBe("identity_provider");
  } finally {
    // The roles withdrawn once asserted, never before: an account the path found with a role says so.
    for (const person of origins.keys()) {
      withdrawRoles(person.email);
    }
    await removeFromTheProvider(request, external);
  }
});

test("an account of the directory signs in with its identifiers of the directory, and Waterfall shows it no screen of a password [WF-ADM-0140-A]", async ({
  page,
}) => {
  await signIn(page, DIRECTORY, ACCOUNT);
  await expect(page.getByRole("main")).toContainText("Importé de l’annuaire");
  await expect(page.locator("input[type=password]")).toHaveCount(0);
  await expect(page.getByRole("main")).not.toContainText(/mot de passe/i);
});

/** Sign a person in again on the sign-in page: the provider remembers her, and asks for nothing. */
async function again(page: Page, person: Person): Promise<void> {
  if (person.provider === undefined) {
    await giveIdentifiers(page, person);
    return;
  }
  await page.getByRole("link", { name: person.provider }).click();
}

test("a session left idle beyond the life of its refresh token leads back to the sign-in page, then, signed in again, to the screen aimed at, its address whole, for each kind of account [WF-SEC-0020-A]", async ({
  browser,
  request,
}) => {
  // Three people signed in twice, and the life of a session waited for: a path of one piece.
  test.setTimeout(90_000);
  // Signed in under the idle life shortened to three seconds — not shortened once signed in, as the
  // test of the service does (#860): the session of the front lives in Redis as long as the realm
  // said at the sign-in (`refresh_expires_in`), and its access token for its own five minutes, which
  // a shorter idle life given afterwards changes for neither — the screen would read on, without
  // the front asking the realm anything. Three seconds leave the exchange of the code the margin the
  // single second of #860 does not.
  const people = [local, DIRECTORY, EXTERNAL];
  // The screen aimed at, with its query.
  const aimed = `${ACCOUNT}?section=preferences&from=idle`;
  await withRealm(request, { ssoSessionIdleTimeout: 3 }, async () => {
    const pages: Page[] = [];
    for (const person of people) {
      const page = await workstation(browser);
      await signIn(page, person, ACCOUNT);
      pages.push(page);
    }
    // The two hours of a session left idle, three seconds here: a real wait, the realm's clock.
    await new Promise((resolve) => setTimeout(resolve, 4_000));
    for (const [at, page] of pages.entries()) {
      const person = people[at] ?? DIRECTORY;
      await page.goto(aimed);
      await expectSignInPage(page);
      await again(page, person);
      await expect(page).toHaveURL(aimed);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");
      await page.context().close();
    }
  });
});

test("a return to another site after the sign-in is refused, and leads home", async ({ page }) => {
  await page.goto(`/login?next=${encodeURIComponent("https://elsewhere.example/projects")}`);
  await giveIdentifiers(page, DIRECTORY);
  await expect(page).toHaveURL("/");
});

test("an account of the realm Waterfall did not create is refused as not admitted, never as deactivated, is not led back to the sign-in, and signs out of the realm, whose sign-in page asks for the identifiers anew (#664)", async ({
  page,
  request,
}) => {
  const { person, id } = await accountOfTheRealmAlone(request);
  try {
    await page.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
    await giveIdentifiers(page, person);
    await expect(page).toHaveURL(ACCOUNT);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Compte non admis");
    await expect(page.getByRole("link", { name: "Se connecter" })).toHaveCount(0);
    // The way out: the session of the realm ends — the realm, given no ID token, asks to confirm —
    // and the sign-in asks for the identifiers, where it signed the account in again silently.
    const signOut = page.getByRole("link", { name: "Se déconnecter" });
    await expect(signOut).toHaveAttribute("href", "/auth/sign-out");
    await signOut.click();
    await expect(page).toHaveURL(under(`${REALM}/protocol/openid-connect/logout`));
    await page.getByRole("button", { name: /déconnexion/i }).click();
    await expectSignInPage(page);
  } finally {
    await removeFromRealm(request, id);
  }
});
