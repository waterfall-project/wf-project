// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * Signing in and out against the real service (US-0340): the front of the harness, the realm of
 * Keycloak behind its front end in HTTPS, and the API through Prism as a proxy, which holds every
 * answer the paths traverse to the contract (`contract.ts`).
 *
 * Until the bootstrap of an installation (US-0420), the account that signs in is the person of the
 * test directory (`deploy/keycloak/development/directory.ldif`), whom the API admits without a
 * role at the first request (WF-ADM-0180): `/account`, which reads the account alone (`getMe`),
 * is the screen it signs in to.
 */
import {
  type APIRequestContext,
  type BrowserContext,
  expect,
  type Page,
  test,
} from "@playwright/test";

import { heldToTheContract } from "./contract";

heldToTheContract();

const EMAIL = "dominique.annuaire@waterfall.test";
const PASSWORD = "development-only-directory-password";
const ACCOUNT = "/account";
// The cookie of the session of the front, its opaque identifier alone (`src/session/tokens.ts`).
const SESSION_COOKIE = "wf_session";
// Where the browser reaches Keycloak, as `make e2e-service` says it, by default as the platform does.
const KEYCLOAK = process.env.WATERFALL_KEYCLOAK_ADDRESS ?? "https://localhost:8443/auth";
const REALM = `${KEYCLOAK}/realms/waterfall/`;
// A token of the realm, whatever its kind: three parts in base64url, the first two JSON objects.
const TOKEN = /eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+/;

/** An address under a prefix, as `toHaveURL` waits for it across navigations. */
function under(prefix: string): RegExp {
  return new RegExp(`^${prefix.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&")}`);
}

/** The sign-in page of the realm, where the person gives the identifiers of the directory. */
async function expectSignInPage(page: Page): Promise<void> {
  await expect(page).toHaveURL(under(REALM));
  await expect(page.getByRole("button", { name: "Connexion" })).toBeVisible();
}

/** Sign in from `/login`, aiming at the screen of the account, and land on it. */
async function signIn(page: Page): Promise<void> {
  await page.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
  await expectSignInPage(page);
  await page.getByLabel("Courriel").fill(EMAIL);
  await page.getByLabel("Mot de passe", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Connexion" }).click();

  // The screen aimed at, as the service answered it: the email of the account it read.
  await expect(page).toHaveURL(ACCOUNT);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");
  await expect(page.getByRole("main")).toContainText(EMAIL);
}

test("signing in through the realm and out again, every answer of the service held to the contract [WF-ARC-0060-A]", async ({
  page,
  context,
}) => {
  const holdsSession = async () =>
    (await context.cookies()).some(({ name }) => name === SESSION_COOKIE);
  await signIn(page);
  expect(await holdsSession()).toBe(true);

  await page.getByRole("button", { name: /^Compte de Dominique/ }).click();
  await page.getByRole("menuitem", { name: "Se déconnecter" }).click();

  // The sessions closed, in the front and in the realm: the account, opened again, asks for a
  // session, and the sign-in page of the realm for the identifiers. Opened in another tab: the
  // screen the menu leads to at once is not what this path proves (#724).
  await expect.poll(holdsSession).toBe(false);
  const again = await context.newPage();
  await again.goto(ACCOUNT);
  await expect(again.getByRole("heading", { level: 1 })).toHaveText("Session requise");
  await again.getByRole("link", { name: "Se connecter" }).click();
  await expectSignInPage(again);
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

  await signIn(page);

  // The front keeps an opaque identifier of its session in a cookie, and nothing else of it.
  const cookies = await context.cookies(front.origin);
  expect(cookies.filter(({ value }) => TOKEN.test(value))).toEqual([]);
  const stored = await page.evaluate(() =>
    [window.localStorage, window.sessionStorage].flatMap((storage) =>
      Object.keys(storage).map((key) => storage.getItem(key) ?? ""),
    ),
  );
  expect(stored.filter((value) => TOKEN.test(value))).toEqual([]);
  expect((await Promise.all(answers)).filter((text) => TOKEN.test(text))).toEqual([]);
});

/** A token of the administrator of Keycloak, from the realm `master`. */
async function administratorToken(request: APIRequestContext): Promise<string> {
  const password = process.env.WATERFALL_KEYCLOAK_ADMIN_PASSWORD;
  expect(password, "WATERFALL_KEYCLOAK_ADMIN_PASSWORD, a secret of the platform").toBeTruthy();
  const answer = await request.post(`${KEYCLOAK}/realms/master/protocol/openid-connect/token`, {
    form: {
      grant_type: "password",
      client_id: "admin-cli",
      username: "admin",
      password: password ?? "",
    },
  });
  expect(answer.ok()).toBe(true);
  return ((await answer.json()) as { access_token: string }).access_token;
}

/** Close every session of the account in the realm, as its administration does. */
async function closeInTheRealm(request: APIRequestContext): Promise<void> {
  const token = await administratorToken(request);
  const headers = { Authorization: `Bearer ${token}` };
  const users = await request.get(`${KEYCLOAK}/admin/realms/waterfall/users`, {
    headers,
    params: { email: EMAIL, exact: "true" },
  });
  expect(users.ok()).toBe(true);
  const [user] = (await users.json()) as { id: string }[];
  expect(user).toBeDefined();
  const closed = await request.post(
    `${KEYCLOAK}/admin/realms/waterfall/users/${user?.id ?? ""}/logout`,
    { headers },
  );
  expect(closed.ok()).toBe(true);
}

/** The page of a workstation, signed in on a context of its own. */
async function workstation(context: BrowserContext): Promise<Page> {
  const page = await context.newPage();
  await signIn(page);
  return page;
}

test("the sessions the realm closes are closed on every workstation at their next request, by the back channel", async ({
  browser,
  request,
}) => {
  // Two workstations of the same account. Their tokens stay valid five minutes at the API, which
  // the realm does not tell: only the back channel can close their sessions in the front (#681).
  const first = await browser.newContext();
  const second = await browser.newContext();
  const pages = [await workstation(first), await workstation(second)];

  await closeInTheRealm(request);

  for (const page of pages) {
    await page.goto(ACCOUNT);
    await expectSignInPage(page);
  }
  await first.close();
  await second.close();
});
