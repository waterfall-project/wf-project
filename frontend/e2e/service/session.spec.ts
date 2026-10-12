// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * Signing in and out against the real service (US-0340, US-0350): the front of the harness, the
 * realm of Keycloak behind its front end in HTTPS, and the API through Prism as a proxy, which
 * holds the body of every answer the paths traverse to the contract (`contract.ts`) — not yet its
 * status (#726).
 *
 * The account that signs in is the person of the test directory (`realm.ts`), whom the API admits
 * without a role at the first request (WF-ADM-0180): `/account`, which reads the account alone
 * (`getMe`), is the screen it signs in to.
 */
import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  accountButton,
  closeInTheRealm,
  closeSessionsMissedByTheRealm,
  DIRECTORY,
  expectSignInPage,
  giveIdentifiers,
  signIn,
} from "./realm";

heldToTheContract();

// The routes a sign-in, a sign-out and a closing in the realm reach by a redirect or by Keycloak,
// compiled before the paths wait for them: the return of a sign-in, the screen of the account under
// the shell, the back channel.
test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, "/auth/backchannel-logout");
});

const ACCOUNT = "/account";
// The cookie of the session of the front, its opaque identifier alone (`src/session/tokens.ts`).
const SESSION_COOKIE = "__Host-wf_session";
// A token of the realm, whatever its kind: three parts in base64url, the first two JSON objects.
const TOKEN = /eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+/;

/** Sign out from the menu of the account, reached by a redirect: it opens once React hydrated it. */
async function signOut(page: Page): Promise<void> {
  await openMenu(accountButton(page, DIRECTORY), page.getByRole("menu"));
  await page.getByRole("menuitem", { name: "Se déconnecter" }).click();
}

test("signing in through the realm and out again, the bodies the service answers held to the contract, the sign-out leading to the sign-in page [WF-ARC-0060-A]", async ({
  page,
  context,
}) => {
  const holdsSession = async () =>
    (await context.cookies()).some(({ name }) => name === SESSION_COOKIE);
  await signIn(page, DIRECTORY, ACCOUNT);
  await expect(page.getByRole("main")).toContainText(DIRECTORY.email);
  expect(await holdsSession()).toBe(true);

  await signOut(page);

  // The sign-in page of the realm at once, which asks for the identifiers anew: the sessions are
  // closed in the front and in the realm, and the cookie forgotten (#724).
  await expectSignInPage(page);
  expect(await holdsSession()).toBe(false);
  const again = await context.newPage();
  await again.goto(ACCOUNT);
  await expect(again.getByRole("heading", { level: 1 })).toHaveText("Session requise");
});

test("the browser holds none of the tokens the front obtains [WF-ARC-0030-A]", async ({
  page,
  context,
  baseURL,
}) => {
  // Every answer of the front to the browser, read once the path is done.
  const front = new URL(baseURL ?? "");
  const answers: Promise<string>[] = [];
  page.on("response", (response) => {
    if (new URL(response.url()).origin === front.origin) {
      answers.push(response.text().catch(() => ""));
    }
  });

  await signIn(page, DIRECTORY, ACCOUNT);

  // The front keeps an opaque identifier of its session in a cookie, and nothing else of it.
  // Those of its host, all of them: read for its address, the secure ones would be left out on HTTP.
  const cookies = (await context.cookies()).filter(({ domain }) => domain === front.hostname);
  expect(cookies.map(({ name }) => name)).toContain(SESSION_COOKIE);
  expect(cookies.filter(({ value }) => TOKEN.test(value))).toEqual([]);
  const stored = await page.evaluate(() =>
    [window.localStorage, window.sessionStorage].flatMap((storage) =>
      Object.keys(storage).map((key) => storage.getItem(key) ?? ""),
    ),
  );
  expect(stored.filter((value) => TOKEN.test(value))).toEqual([]);
  const texts = await Promise.all(answers);
  // Among them, the screen of the account, which the session read.
  expect(texts.some((text) => text.includes(DIRECTORY.email))).toBe(true);
  expect(texts.filter((text) => TOKEN.test(text))).toEqual([]);
});

/** Two workstations of the same account, each a context of its own, signed in. */
async function twoWorkstations(
  newContext: () => Promise<BrowserContext>,
): Promise<{ pages: [Page, Page]; close: () => Promise<void> }> {
  const contexts = [await newContext(), await newContext()];
  const pages: Page[] = [];
  for (const context of contexts) {
    const page = await context.newPage();
    await signIn(page, DIRECTORY, ACCOUNT);
    pages.push(page);
  }
  const [first, second] = pages;
  if (first === undefined || second === undefined) {
    throw new Error("two workstations");
  }
  return {
    pages: [first, second],
    close: async () => {
      await Promise.all(contexts.map((context) => context.close()));
    },
  };
}

/** The next request of a workstation leads it to the sign-in page: it can no longer act. */
async function expectClosed(page: Page): Promise<void> {
  await page.goto(ACCOUNT);
  await expectSignInPage(page);
}

test("the sessions the realm closes are closed on every workstation at their next request, by the back channel", async ({
  browser,
  request,
}) => {
  // Their tokens stay valid five minutes at the API, which the realm does not tell: only the back
  // channel can close their sessions in the front (#681).
  const { pages, close } = await twoWorkstations(() => browser.newContext());
  await closeInTheRealm(request, DIRECTORY.email);
  for (const page of pages) {
    await expectClosed(page);
  }
  await close();
});

test("a user who signs out can no longer act, on any of her workstations [WF-SEC-0020-A]", async ({
  browser,
}) => {
  const { pages, close } = await twoWorkstations(() => browser.newContext());
  const [here, elsewhere] = pages;
  await signOut(here);
  await expectSignInPage(here);
  await expectClosed(elsewhere);
  await close();
});

test("a user whose session the front lost signs out of every workstation all the same, by a silent sign-in at the realm (#689) [WF-SEC-0020-A]", async ({
  browser,
}) => {
  const { pages, close } = await twoWorkstations(() => browser.newContext());
  const [here, elsewhere] = pages;
  // The session of the front lost — Redis emptied, say —, that of the realm alive: the cookie of
  // the screen shown names a session the front no longer keeps.
  const front = new URL(here.url());
  await here.context().addCookies([
    {
      name: SESSION_COOKIE,
      value: "lost",
      domain: front.hostname,
      path: "/",
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
    },
  ]);
  await signOut(here);
  await expectSignInPage(here);
  await expectClosed(elsewhere);
  await close();
});

/**
 * Wait until a sign-in made now falls in a later second than a closing of the sessions: the API
 * refuses a sign-in of the very second of the closing (`auth_time`, in seconds, #855).
 */
async function pastTheSecondOf(closed: number): Promise<void> {
  const next = (Math.floor(closed / 1000) + 1) * 1000;
  await expect.poll(() => Date.now()).toBeGreaterThanOrEqual(next);
}

test("a user whose sessions were closed while the realm missed it signs in again by giving her identifiers anew, never to the same refusal (#855) [WF-SEC-0020-A]", async ({
  page,
}) => {
  await signIn(page, DIRECTORY, ACCOUNT);
  const closed = closeSessionsMissedByTheRealm(DIRECTORY.email);
  await page.goto(ACCOUNT);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Session fermée");
  await pastTheSecondOf(closed);
  await page.getByRole("link", { name: "Se connecter" }).click();
  // The session of the realm lives, and yet the realm asks for the identifiers.
  await giveIdentifiers(page, DIRECTORY);
  await expect(page).toHaveURL(ACCOUNT);
  await expect(page.getByRole("main")).toContainText(DIRECTORY.email);
});

test("a user whose session the front lost, and whose sessions were closed while the realm missed it, signs out all the same: to the sign-in page, which asks for her identifiers, nothing looping (#689, #855) [WF-SEC-0020-A]", async ({
  page,
}) => {
  await signIn(page, DIRECTORY, ACCOUNT);
  const closed = closeSessionsMissedByTheRealm(DIRECTORY.email);
  const front = new URL(page.url());
  await page.context().addCookies([
    {
      name: SESSION_COOKIE,
      value: "lost",
      domain: front.hostname,
      path: "/",
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
    },
  ]);
  // The silent sign-in brings a token of the session the realm kept, which the API refuses.
  await signOut(page);
  await expectSignInPage(page);
  await pastTheSecondOf(closed);
  await giveIdentifiers(page, DIRECTORY);
  await expect(accountButton(page, DIRECTORY)).toBeVisible();
});
