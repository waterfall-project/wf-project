// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * My account against the service (US-0400): the language of the interface, which the browser
 * decides until the account chooses one, and which then follows the account from one workstation
 * to the next, applied without signing in again; the avatar, put, replaced and withdrawn by its
 * holder; and the settings of the tables of the administration — hidden columns, widths, filters —,
 * kept by the account and found again at the reopening, each account seeing its own.
 *
 * The accounts are local accounts an administrator creates, each signing in for the first time
 * here; the role that lets them read the tables is written in the database once their first request
 * has made their account (`grantRole`), and withdrawn at the end.
 */
import { type Browser, expect, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu, setExpanded } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  type Administrator,
  accountAdministrator,
  giveIdentifiers,
  grantRole,
  gridPreferences,
  localAccount,
  type Person,
  REALM,
  withdrawRoles,
} from "./realm";

heldToTheContract();

const API = `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1`;
const ACCOUNT = "/account";
const AVATAR = "/account/avatar";
const USERS = "/admin/users";
const ROLES = "/admin/access-roles";
// The filters of the table of the roles a path keeps: the composed roles some account holds.
const KEPT_ROLES = `${ROLES}?is_predefined=false&holder_count_min=1`;
const READER = "Lecture des comptes et des rôles (parcours)";

// Two images of one pixel, a blue one and an orange one: an avatar put, then replaced.
const BLUE =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOQizoBAAHaAUGizqgqAAAAAElFTkSuQmCC";
const ORANGE =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGO4UyECAAOcAWlG+c6hAAAAAElFTkSuQmCC";

let administrator: Administrator;
let first: Person;
let second: Person;

// The administrator of the file, and two local accounts, each with its password set by its link.
test.beforeAll(async ({ browser, playwright }) => {
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  administrator = await accountAdministrator(browser, calls);
  first = await localAccount(browser, administrator);
  second = await localAccount(browser, administrator);
});

test.afterAll(() => {
  administrator.done();
});

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, AVATAR, USERS, ROLES);
});

/** A page of a workstation of its own, its browser asking for a language. */
async function workstation(browser: Browser, locale: string): Promise<Page> {
  const context = await browser.newContext({ locale, ignoreHTTPSErrors: true });
  return context.newPage();
}

/** Sign a person in from `/login`, aiming at a screen, and land on it, in whatever language. */
async function signInAt(page: Page, person: Person, screen: string): Promise<void> {
  await page.goto(`/login?next=${encodeURIComponent(screen)}`);
  await giveIdentifiers(page, person);
  await expect(page).toHaveURL(screen);
}

/** Check a radio once React answers the click: one made before the hydration is lost. */
async function choose(page: Page, name: string): Promise<void> {
  const radio = page.getByRole("radio", { name, exact: true });
  await expect(async () => {
    await radio.click();
    await expect(radio).toBeChecked({ timeout: 500 });
  }).toPass();
}

test("a browser asking for English gets the interface in English at the first sign-in, one asking for French gets it in French, one asking for a language not offered the language of the installation [WF-INTF-0160-A]", async ({
  browser,
  request,
}) => {
  // Three accounts and three workstations, each signing in at the realm: a path of one piece.
  test.setTimeout(150_000);
  const answer = await request.get(`${API}/installation`);
  expect(answer.status()).toBe(200);
  const { default_language: installed } = (await answer.json()) as { default_language: string };
  for (const [locale, language] of [
    ["en-US", "en"],
    ["fr-FR", "fr"],
    ["de-DE", installed],
  ] as const) {
    // An account of its own for each browser: each sign-in is its first, no language chosen yet.
    const newcomer = await localAccount(browser, administrator);
    const page = await workstation(browser, locale);
    await signInAt(page, newcomer, ACCOUNT);
    await expect(page.locator("html")).toHaveAttribute("lang", language);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      language === "en" ? "My account" : "Mon compte",
    );
    await page.context().close();
  }
});

test("a user who forces French gets it at once, without signing in again, and finds it again on another workstation whose browser asks for English [WF-INTF-0160-A]", async ({
  browser,
}) => {
  test.setTimeout(60_000);
  const page = await workstation(browser, "en-US");
  await signInAt(page, first, ACCOUNT);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  // Neither the sign-in of the front nor the realm is asked from now on.
  const signIns: string[] = [];
  page.on("request", (asked) => {
    if (asked.url().includes("/login") || asked.url().startsWith(REALM)) {
      signIns.push(asked.url());
    }
  });
  await choose(page, "Français");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Mon compte");
  await expect(page.getByRole("main").getByRole("status")).toHaveText(
    "Vos préférences sont enregistrées.",
  );
  await expect(page).toHaveURL(ACCOUNT);
  expect(signIns).toEqual([]);
  await page.context().close();

  const other = await workstation(browser, "en-US");
  await signInAt(other, first, ACCOUNT);
  await expect(other.locator("html")).toHaveAttribute("lang", "fr");
  await expect(other.getByRole("radio", { name: "Français", exact: true })).toBeChecked();
  await other.context().close();
});

test("a local account leads to its page at the realm, which holds its password", async ({
  browser,
}) => {
  const page = await workstation(browser, "fr-FR");
  await signInAt(page, second, ACCOUNT);
  await expect(
    page.getByRole("link", { name: "Ouvrir mon compte du fournisseur d’identité" }),
  ).toHaveAttribute("href", `${REALM}/account`);
  await page.context().close();
});

test("an account without an avatar shows its initials without one [WF-ADM-0080-A]", async ({
  browser,
}) => {
  const page = await workstation(browser, "fr-FR");
  await signInAt(page, second, AVATAR);
  const main = page.getByRole("main");
  // No avatar: the initials, the default image. The image of an avatar is put in the page only
  // once loaded, so its absence alone proves nothing: what the server renders only for an account
  // without one — the line that says so, and no withdrawal offered — does.
  await expect(main.getByText("JM", { exact: true })).toBeVisible();
  await expect(main.getByText("Aucune image : vos initiales en tiennent lieu.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retirer l’avatar" })).toHaveCount(0);
  await expect(main.getByRole("img", { name: "Jeanne Montgolfier" })).toHaveCount(0);
  await page.context().close();
});

// TODO(#973): leave the fixme once the bench passes a binary body — Prism, the proxy of the
// contract on the service platform, reads any body that is not JSON as UTF-8 text and spoils the
// image.
test.fixme("a user puts, replaces and withdraws the avatar of the account herself [WF-ADM-0080-A]", async ({
  browser,
}) => {
  const page = await workstation(browser, "fr-FR");
  await signInAt(page, second, AVATAR);
  const main = page.getByRole("main");
  const image = main.getByRole("img", { name: "Jeanne Montgolfier" });

  const upload = page.getByRole("button", { name: "Déposer l’image" });
  for (const [colour, bytes] of [
    ["bleu", BLUE],
    ["orange", ORANGE],
  ] as const) {
    // A file chosen before React hydrated the page is not seen: chosen again until it is.
    await expect(async () => {
      await page.getByLabel("Image PNG ou JPEG").setInputFiles({
        name: `${colour}.png`,
        mimeType: "image/png",
        buffer: Buffer.from(bytes, "base64"),
      });
      await expect(upload).not.toHaveAttribute("aria-disabled", "true", { timeout: 500 });
    }).toPass();
    await upload.click();
    await expect(page.getByRole("main").getByRole("status")).toHaveText(
      "Votre avatar est enregistré.",
    );
    await expect(image).toHaveAttribute("src", `data:image/png;base64,${bytes}`);
  }

  await page.getByRole("button", { name: "Retirer l’avatar" }).click();
  await expect(page.getByRole("main").getByRole("status")).toHaveText("Votre avatar est retiré.");
  await expect(image).toHaveCount(0);
  await expect(main.getByText("JM", { exact: true })).toBeVisible();
  await page.context().close();
});

/** The table of the accounts, as its screen names it. */
function accounts(page: Page) {
  return page.getByRole("grid", { name: "Comptes utilisateurs" });
}

/** Hide a column of the table of the accounts by the menu of its columns. */
async function hide(page: Page, column: string): Promise<void> {
  const menu = page.getByRole("menu");
  await openMenu(page.getByRole("button", { name: /^Colonnes/ }), menu);
  await menu.getByRole("menuitemcheckbox", { name: column }).click();
  await page.keyboard.press("Escape");
  await expect(accounts(page).getByRole("columnheader", { name: column })).toHaveCount(0);
}

test("the hidden columns and the widths of the table of the accounts are found again at the reopening, and another user opening it sees her own [WF-IHM-0060-A] [WF-ADM-0040-A]", async ({
  browser,
}) => {
  test.setTimeout(90_000);
  const pages: Page[] = [];
  try {
    for (const person of [first, second]) {
      const page = await workstation(browser, "fr-FR");
      pages.push(page);
      await signInAt(page, person, ACCOUNT);
      grantRole(person.email, READER, ["users.read", "access_roles.read"]);
    }
    const [mine, hers] = pages as [Page, Page];

    // The first hides the address and widens the first name; the second hides the origin.
    await mine.goto(USERS);
    await hide(mine, "Adresse électronique");
    const width = mine.getByRole("separator", { name: "Largeur de la colonne Prénom" });
    const before = await width.getAttribute("aria-valuenow");
    await width.focus();
    await mine.keyboard.press("ArrowRight");
    await mine.keyboard.press("ArrowRight");
    const widened = String(Number(before) + 32);
    await expect(width).toHaveAttribute("aria-valuenow", widened);
    await expect
      .poll(() => gridPreferences(first.email, "users"))
      .toMatchObject({ hidden_columns: ["email"], column_widths: { first_name: Number(widened) } });
    await hers.goto(USERS);
    await hide(hers, "Origine");
    await expect
      .poll(() => gridPreferences(second.email, "users"))
      .toMatchObject({ hidden_columns: ["origin"] });

    // Each opens the table again: her own settings, not the other's.
    await mine.goto(USERS);
    await expect(accounts(mine).getByRole("columnheader", { name: "Origine" })).toHaveCount(1);
    await expect(
      accounts(mine).getByRole("columnheader", { name: "Adresse électronique" }),
    ).toHaveCount(0);
    await expect(width).toHaveAttribute("aria-valuenow", widened);
    await hers.goto(USERS);
    await expect(
      accounts(hers).getByRole("columnheader", { name: "Adresse électronique" }),
    ).toHaveCount(1);
    await expect(accounts(hers).getByRole("columnheader", { name: "Origine" })).toHaveCount(0);
    await expect(
      hers.getByRole("separator", { name: "Largeur de la colonne Prénom" }),
    ).toHaveAttribute("aria-valuenow", before ?? "");
  } finally {
    for (const page of pages) {
      await page.context().close();
    }
    withdrawRoles(first.email);
    withdrawRoles(second.email);
  }
});

test("the filters kept for the table of the roles are found again by an address that says nothing of them, typed or followed from the navigation, and « Précédent » never comes back to it (#848)", async ({
  browser,
}) => {
  test.setTimeout(60_000);
  const page = await workstation(browser, "fr-FR");
  try {
    await signInAt(page, first, ACCOUNT);
    grantRole(first.email, READER, ["users.read", "access_roles.read"]);
    // The filters shown are kept by the account.
    await page.goto(KEPT_ROLES);
    await expect
      .poll(() => gridPreferences(first.email, "access_roles"))
      .toMatchObject({ filters: { is_predefined: "false", holder_count_min: "1" } });

    // Typed: the page leads the address that says nothing to the filters kept.
    await page.goto(ACCOUNT);
    await page.goto(ROLES);
    await expect(page).toHaveURL(KEPT_ROLES);
    // « Précédent » goes back to the screen before, never to the address that would lead again.
    await page.goBack();
    await expect(page).toHaveURL(ACCOUNT);

    // Followed from the navigation: from another screen, then from the screen of the roles itself,
    // whose link says nothing of its filters — the development server prefetches no link, and the
    // click asks the screen anew.
    const nav = page.getByRole("navigation", { name: "Fonctions" });
    const link = nav.getByRole("link", { name: "Gestion des rôles d’habilitation" });
    await setExpanded(nav.getByRole("button", { name: "Administration", exact: true }), true);
    await link.click();
    await expect(page).toHaveURL(KEPT_ROLES);
    await page.goto(KEPT_ROLES);
    await setExpanded(nav.getByRole("button", { name: "Administration", exact: true }), true);
    const followed = page.waitForRequest((asked) => new URL(asked.url()).pathname === ROLES);
    await link.click();
    await followed;
    await expect(page).toHaveURL(KEPT_ROLES);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Gestion des rôles d’habilitation",
    );
  } finally {
    await page.context().close();
    withdrawRoles(first.email);
  }
});
