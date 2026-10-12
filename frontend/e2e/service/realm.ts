// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the paths against the service ask of the platform around the front (US-0350): the sign-in
 * page of the realm, where a person gives her identifiers; the administration of the realm, to
 * shorten a lifetime the time of a path or to close the sessions of an account, as an
 * administrator would in its console; and, until the bootstrap of an installation (US-0420), the
 * one way to make an administrator of Waterfall — a role written in its database, the service
 * offering none.
 *
 * The person of the test directory and the one of the test external provider are those of
 * `deploy/keycloak/development/`, with their development passwords.
 */
import { createHash, randomBytes } from "node:crypto";
import { execFileSync } from "node:child_process";

import { type APIRequestContext, type Browser, expect, type Page } from "@playwright/test";

/** Where the browser reaches Keycloak, as `make e2e-service` says it. */
export const KEYCLOAK = process.env.WATERFALL_KEYCLOAK_ADDRESS ?? "https://localhost:8443/auth";
/** The realm of Waterfall, under it. */
export const REALM = `${KEYCLOAK}/realms/waterfall`;
/** The API, through the proxy of the contract. */
const API = `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1`;

/** A person who signs in at the realm: by her address and her password, or by a provider. */
export interface Person {
  /** What she types in the field of her identifier. */
  readonly login: string;
  /** Her address, by which Waterfall knows her. */
  readonly email: string;
  readonly password: string;
  /** The name the menu of her account gives her. */
  readonly name: string;
  /** The provider she signs in by, if not the realm itself. */
  readonly provider?: string;
}

/** The person of the test directory, admitted at her first request (WF-ADM-0180). */
export const DIRECTORY: Person = {
  login: "dominique.annuaire@waterfall.test",
  email: "dominique.annuaire@waterfall.test",
  password: "development-only-directory-password",
  name: "Dominique",
};

/** The person of the test external provider, unknown to Waterfall before she signs in. */
export const EXTERNAL: Person = {
  login: "camille.externe",
  email: "camille.externe@external.test",
  password: "development-only-external-password",
  name: "Camille Externe",
  provider: "External provider (development)",
};

/** An address under a prefix, as `toHaveURL` waits for it across navigations. */
export function under(prefix: string): RegExp {
  return new RegExp(`^${prefix.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&")}`);
}

/** The sign-in page of the realm, where a person gives her identifiers. */
export async function expectSignInPage(page: Page): Promise<void> {
  await expect(page).toHaveURL(under(`${REALM}/`));
  await expect(page.getByRole("button", { name: "Connexion" })).toBeVisible();
}

/** Give the identifiers of a person on the sign-in page of the realm, or of her provider. */
export async function giveIdentifiers(page: Page, person: Person): Promise<void> {
  await expectSignInPage(page);
  if (person.provider === undefined) {
    await page.getByLabel("Courriel").fill(person.login);
    await page.getByLabel("Mot de passe", { exact: true }).fill(person.password);
    await page.getByRole("button", { name: "Connexion" }).click();
    return;
  }
  await page.getByRole("link", { name: person.provider }).click();
  // The provider of the platform is another realm, in English.
  await page.getByLabel("Username or email").fill(person.login);
  await page.getByLabel("Password", { exact: true }).fill(person.password);
  await page.getByRole("button", { name: "Sign In" }).click();
}

/** Sign a person in from `/login`, aiming at a screen, and land on it, whole. */
export async function signIn(page: Page, person: Person, screen: string): Promise<void> {
  await page.goto(`/login?next=${encodeURIComponent(screen)}`);
  await giveIdentifiers(page, person);
  await expect(page).toHaveURL(screen);
  await expect(accountButton(page, person)).toBeVisible();
}

/** The button of the menu of the account of a person, in the bar of the shell. */
export function accountButton(page: Page, person: Person) {
  return page.getByRole("button", { name: new RegExp(`^Compte de ${person.name}`) });
}

/** The headers that carry a token of the administrator of Keycloak, from the realm `master`. */
async function administrator(request: APIRequestContext): Promise<Record<string, string>> {
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
  const { access_token: token } = (await answer.json()) as { access_token: string };
  return { Authorization: `Bearer ${token}` };
}

/** The administration API of a realm — that of Waterfall by default —, as its administrator. */
async function administering(request: APIRequestContext, realm = "waterfall") {
  const headers = await administrator(request);
  const admin = `${KEYCLOAK}/admin/realms/${realm}`;
  return {
    get: (path: string, params?: Record<string, string>) =>
      request.get(`${admin}${path}`, { headers, ...(params === undefined ? {} : { params }) }),
    put: (path: string, data: unknown) => request.put(`${admin}${path}`, { headers, data }),
    post: (path: string, data?: unknown) =>
      request.post(`${admin}${path}`, { headers, ...(data === undefined ? {} : { data }) }),
    delete: (path: string) => request.delete(`${admin}${path}`, { headers }),
  };
}

/** The identifier of an account in a realm — that of Waterfall by default —, if it holds one. */
async function realmUserIfAny(
  request: APIRequestContext,
  email: string,
  name = "waterfall",
): Promise<string | undefined> {
  const realm = await administering(request, name);
  const users = await realm.get("/users", { email, exact: "true" });
  expect(users.ok()).toBe(true);
  const [user] = (await users.json()) as { id: string }[];
  return user?.id;
}

/** The identifier of an account in a realm — that of Waterfall by default —, by its address. */
async function realmUser(
  request: APIRequestContext,
  email: string,
  name = "waterfall",
): Promise<string> {
  const id = await realmUserIfAny(request, email, name);
  expect(id, `the account ${email} in the realm`).toBeDefined();
  return id ?? "";
}

/**
 * A local account of the realm that Waterfall did not create — made in the console of Keycloak —,
 * with a password: the person Waterfall does not admit (#664). Its identifier in the realm.
 */
export async function accountOfTheRealmAlone(
  request: APIRequestContext,
): Promise<{ person: Person; id: string }> {
  const email = `paul.${randomBytes(6).toString("hex")}@waterfall.test`;
  const made = await (
    await administering(request)
  ).post("/users", {
    username: email,
    email,
    firstName: "Paul",
    lastName: "Durand",
    enabled: true,
    emailVerified: true,
    credentials: [{ type: "password", value: LOCAL_PASSWORD, temporary: false }],
  });
  expect(made.status()).toBe(201);
  const person = { login: email, email, password: LOCAL_PASSWORD, name: "Paul Durand" };
  return { person, id: await realmUser(request, email) };
}

/**
 * A person new to the external provider, and so to Waterfall, whatever the platform saw before:
 * made in the realm of the provider, as its administration would.
 */
export async function newToTheProvider(request: APIRequestContext): Promise<Person> {
  const login = `camille.${randomBytes(6).toString("hex")}`;
  const email = `${login}@external.test`;
  const made = await (
    await administering(request, "external")
  ).post("/users", {
    username: login,
    email,
    firstName: "Camille",
    lastName: "Nouvelle",
    enabled: true,
    emailVerified: true,
    credentials: [{ type: "password", value: EXTERNAL.password, temporary: false }],
  });
  expect(made.status()).toBe(201);
  return { ...EXTERNAL, login, email, name: "Camille Nouvelle" };
}

/**
 * Remove a person new to the provider from its realm, the account it brought to Waterfall's, and
 * the account of Waterfall her first request created — on a platform used again, her name would
 * otherwise stay in its lists. Each only if it is there: a path that failed before her first
 * sign-in leaves none of them, and its own failure is the one to tell.
 */
export async function removeFromTheProvider(
  request: APIRequestContext,
  person: Person,
): Promise<void> {
  const provided = await realmUserIfAny(request, person.email, "external");
  if (provided !== undefined) {
    const removed = await (await administering(request, "external")).delete(`/users/${provided}`);
    expect(removed.ok()).toBe(true);
  }
  const brought = await realmUserIfAny(request, person.email);
  if (brought !== undefined) {
    await removeFromRealm(request, brought);
  }
  removeFromWaterfall(person.email);
}

/** Remove an account from the realm, as its administration does. */
export async function removeFromRealm(request: APIRequestContext, id: string): Promise<void> {
  expect((await (await administering(request)).delete(`/users/${id}`)).ok()).toBe(true);
}

/** Close every session of an account in the realm, as its administration does. */
export async function closeInTheRealm(request: APIRequestContext, email: string): Promise<void> {
  const id = await realmUser(request, email);
  const closed = await (await administering(request)).post(`/users/${id}/logout`);
  expect(closed.ok()).toBe(true);
}

/** Lift the lock of an account the realm locked after its failures, as its administration does. */
export async function unlock(request: APIRequestContext, email: string): Promise<void> {
  const id = await realmUser(request, email);
  const lifted = await (
    await administering(request)
  ).delete(`/attack-detection/brute-force/users/${id}`);
  expect(lifted.ok()).toBe(true);
}

/** The settings of the realm a path reads or changes: its lifetimes and its lock. */
export type RealmSettings = Readonly<Record<string, number | boolean | string>>;

/** Read settings of the realm. */
export async function realmSettings(
  request: APIRequestContext,
  names: readonly string[],
): Promise<RealmSettings> {
  const realm = (await (await (await administering(request)).get("")).json()) as RealmSettings;
  return Object.fromEntries(names.map((name) => [name, realm[name] ?? Number.NaN]));
}

/** Give the realm settings while `run` runs, then the values it had. */
export async function withRealm<T>(
  request: APIRequestContext,
  settings: RealmSettings,
  run: () => Promise<T>,
): Promise<T> {
  const kept = await realmSettings(request, Object.keys(settings));
  const changed = await (await administering(request)).put("", settings);
  expect(changed.status()).toBe(204);
  try {
    return await run();
  } finally {
    // A token of the administrator lives a minute: a path may have outlived the first one.
    const restored = await (await administering(request)).put("", kept);
    expect(restored.status()).toBe(204);
  }
}

/**
 * Run SQL on the database of the platform, its values given as variables of psql, which quotes
 * them (`:'name'`); a statement refused fails the path, rather than leave it half done.
 */
function sql(script: string, values: Readonly<Record<string, string>>): string {
  const container = process.env.E2E_SERVICE_DATABASE;
  if (container === undefined || container === "") {
    throw new Error(
      "E2E_SERVICE_DATABASE must name the database of the platform: run make e2e-service",
    );
  }
  const variables = Object.entries(values).flatMap(([name, value]) => ["-v", `${name}=${value}`]);
  const psql = ["psql", "-U", "waterfall", "-d", "waterfall", "-q", "-At", "-v", "ON_ERROR_STOP=1"];
  return execFileSync("docker", ["exec", "-i", container, ...psql, ...variables], {
    input: script,
    encoding: "utf8",
    stdio: ["pipe", "pipe", "pipe"],
  }).trim();
}

/** The origin of the account of an address in Waterfall, and the roles it holds; none unknown. */
export function waterfallAccount(email: string): { origin: string; roles: number } | undefined {
  const row = sql(
    `select origin, (select count(*) from user_access_role where user_account_id = account.id)
  from user_account account where account.email = :'email';
`,
    { email },
  );
  const [origin, roles] = row.split("|");
  return origin === undefined || origin === "" ? undefined : { origin, roles: Number(roles) };
}

/**
 * Give an account a role of the permissions given — the same role each time, made once —, as an
 * administrator would once the bootstrap has made one (US-0420): written in the database, the
 * service offering no other way before it. The account must exist — Waterfall creates it at its
 * first request —: a role given to none fails the path, rather than leave it without the role.
 */
export function grantRole(email: string, label: string, permissions: readonly string[]): void {
  const held = sql(
    `insert into access_role (id, label, is_predefined, created_at, updated_at)
  select gen_random_uuid(), :'label', false, now(), now()
  where not exists (select 1 from access_role where label = :'label' and deleted_at is null);
insert into access_role_permission (access_role_id, permission_id)
  select role.id, permission.id from access_role role, permission
  where role.label = :'label' and permission.code = any(string_to_array(:'permissions', ','))
  on conflict do nothing;
insert into user_access_role (user_account_id, access_role_id)
  select account.id, role.id from user_account account, access_role role
  where account.email = :'email' and role.label = :'label'
  on conflict do nothing;
select count(*) from user_access_role held
  join user_account account on account.id = held.user_account_id
  join access_role role on role.id = held.access_role_id
  where account.email = :'email' and role.label = :'label';
`,
    { label, email, permissions: permissions.join(",") },
  );
  if (held !== "1") {
    throw new Error(`${email} holds no role ${label}: has Waterfall created its account?`);
  }
}

/**
 * Remove the account of an address from Waterfall, if any, with the roles it holds: what a path
 * made, and that the service offers no way to delete. An account another references — one it
 * created, a task it asked — is refused, and the path fails rather than leave it half done: both
 * deletions are one transaction, the roles kept when the account is.
 */
function removeFromWaterfall(email: string): void {
  sql(
    `begin;
delete from user_access_role
  where user_account_id in (select id from user_account where email = :'email');
delete from user_account where email = :'email';
commit;
`,
    { email },
  );
}

/** Withdraw the roles of an account, as an administrator would. */
export function withdrawRoles(email: string): void {
  sql(
    `delete from user_access_role
  where user_account_id in (select id from user_account where email = :'email');
`,
    { email },
  );
}

/** A PKCE verifier, and its challenge. */
function pkce(): { verifier: string; challenge: string } {
  const verifier = randomBytes(32).toString("base64url");
  return { verifier, challenge: createHash("sha256").update(verifier).digest("base64url") };
}

/**
 * The access token the front would obtain for a person: the code flow of the client of the front,
 * with its secret, played in a browser of its own — the client of test of the platform gives
 * tokens that are not for the API. For the path to call the API itself, as the screens of US-0360
 * will once they are wired (#449).
 */
export async function frontToken(browser: Browser, person: Person): Promise<string> {
  const callback = `${process.env.WATERFALL_FRONT_ADDRESS ?? ""}/auth/callback`;
  const { verifier, challenge } = pkce();
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  try {
    const page = await context.newPage();
    // A redirect the realm answers is not routed: its request is watched for, the front left to
    // answer it — without the cookie of a sign-in of its own, it exchanges nothing.
    const returned = page.waitForRequest((asked) => asked.url().startsWith(`${callback}?`));
    const query = new URLSearchParams({
      client_id: "waterfall-front",
      response_type: "code",
      scope: "openid",
      redirect_uri: callback,
      state: randomBytes(16).toString("base64url"),
      code_challenge: challenge,
      code_challenge_method: "S256",
    });
    await page.goto(`${REALM}/protocol/openid-connect/auth?${query.toString()}`);
    await giveIdentifiers(page, person);
    const code = new URL((await returned).url()).searchParams.get("code") ?? "";
    const answer = await context.request.post(`${REALM}/protocol/openid-connect/token`, {
      form: {
        grant_type: "authorization_code",
        code,
        redirect_uri: callback,
        code_verifier: verifier,
        client_id: "waterfall-front",
        client_secret: process.env.WATERFALL_FRONT_CLIENT_SECRET ?? "",
      },
    });
    expect(answer.ok()).toBe(true);
    return ((await answer.json()) as { access_token: string }).access_token;
  } finally {
    await context.close();
  }
}

/** The API, as the front calls it with a token: a write, and the object it answers. */
async function posted<T>(
  request: APIRequestContext,
  token: string,
  path: string,
  data?: unknown,
): Promise<T> {
  const answer = await request.post(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    ...(data === undefined ? {} : { data }),
  });
  expect(answer.status(), `POST ${path}`).toBe(201);
  return (await answer.json()) as T;
}

/** The label of the role that makes the person of the directory administer the accounts. */
const ADMINISTRATION = "Administration des comptes (parcours)";

/**
 * An administrator of the accounts, who creates local accounts and gives their links (`createUser`,
 * `createPasswordSetupLink`): the person of the directory, given the role, as the screens of
 * US-0360 will call the API once wired (#449). Her account is Waterfall's once she has called it
 * (`getMe`): the role is given then, the first path of a platform new finding none.
 */
export async function accountAdministrator(browser: Browser, request: APIRequestContext) {
  const token = await frontToken(browser, DIRECTORY);
  const me = await request.get(`${API}/me`, { headers: { Authorization: `Bearer ${token}` } });
  expect(me.status(), "GET /me").toBe(200);
  grantRole(DIRECTORY.login, ADMINISTRATION, ["users.read", "users.write"]);
  return {
    /** Create a local account, Jeanne Montgolfier's, at an address of its own. */
    create: async (): Promise<{ id: string; email: string }> => {
      const email = `jeanne.${randomBytes(6).toString("hex")}@waterfall.test`;
      const body = { last_name: "Montgolfier", first_name: "Jeanne", email };
      const { user_id: id } = await posted<{ user_id: string }>(request, token, "/users", body);
      return { id, email };
    },
    /** The link that sets the password of a local account, each new one replacing the one before. */
    link: async (id: string): Promise<string> =>
      (await posted<{ url: string }>(request, token, `/users/${id}/password-link`)).url,
    /** Withdraw the role the person of the directory was given. */
    done: () => {
      withdrawRoles(DIRECTORY.login);
    },
  };
}

/** An administrator of the accounts, for the time of a file. */
export type Administrator = Awaited<ReturnType<typeof accountAdministrator>>;

/** The password a local account sets by its link: twelve characters, neither its address nor its name. */
export const LOCAL_PASSWORD = "k7#Qw2ZpX9vR";

/** Set a password on the page of a link, opened: whether the realm took it is for the path to see. */
export async function setPassword(page: Page, password: string): Promise<void> {
  await page.getByLabel("Nouveau mot de passe").fill(password);
  await page.getByLabel("Confirmation du mot de passe").fill(password);
  await page.getByRole("button", { name: "Soumettre" }).click();
}

/** Open the link of a local account, as its holder does, up to the form of its password. */
export async function openLink(page: Page, link: string): Promise<void> {
  await page.goto(link);
  await page.getByRole("link", { name: "» Cliquez ici pour continuer" }).click();
  await expect(page.getByRole("heading", { name: "Mise à jour du mot de passe" })).toBeVisible();
}

/**
 * A local account created by the administrator, whose holder has set her password by her link:
 * the person who signs in with it.
 */
export async function localAccount(
  browser: Browser,
  administrator: Administrator,
): Promise<Person> {
  const { id, email } = await administrator.create();
  const page = await browser.newPage({ locale: "fr-FR", ignoreHTTPSErrors: true });
  await openLink(page, await administrator.link(id));
  await setPassword(page, LOCAL_PASSWORD);
  await expect(page.getByRole("heading", { name: "Votre compte a été mis à jour." })).toBeVisible();
  await page.close();
  return { login: email, email, password: LOCAL_PASSWORD, name: "Jeanne Montgolfier" };
}
