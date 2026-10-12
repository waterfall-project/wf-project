// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The journal of audit read against the service (US-0410, FBS-1.5): an administrator of the
 * accounts — the person of the directory — gives a local account a role by the service, which
 * inscribes the attribution as codes and identifiers, without a sentence (WF-ARC-0110); the
 * journal, filtered on its author and its action, presents it dated of the day, naming the account
 * and the role, to each reader in her language — the administrator in French, the holder of the
 * account in English, her preference —, and offers no command on it (WF-SEC-0030). The holder,
 * before she holds the consultation, does not reach the view, and the journal of a month without
 * any action presents nothing (WF-ADM-0190).
 *
 * The roles of the person of the directory are written in the database of the platform, as an
 * administrator would give them (`grantRole`); the role of the holder is given by the service, for
 * the journal to inscribe it.
 */
import { randomBytes } from "node:crypto";

import { type Browser, expect, type Locator, type Page, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { openMenu } from "../hydration";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  accountButton,
  DIRECTORY,
  grantRole,
  localAccount,
  signIn,
  withdrawRoles,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const JOURNAL = "/admin/audit-log";
/** The role that lets the person of the directory give roles and consult the journal. */
const AUDITING = "Attribution et journal (parcours)";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT, JOURNAL);
});

/** A page of a workstation of its own, in French, which trusts the front end of Keycloak. */
async function workstation(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  return context.newPage();
}

/** The journal filtered on an author and on an action, as its filters write the address. */
function filtered(author: string, action: string): string {
  return `${JOURNAL}?${new URLSearchParams({ user_id: author, actions: action }).toString()}`;
}

/** The inscription of the grid of the journal, named in a language, whose text holds a label. */
function inscription(page: Page, grid: string, label: string): Locator {
  return page.getByRole("grid", { name: grid }).getByRole("row").filter({ hasText: label });
}

/**
 * Whether an inscription is dated of the moment it was made, give or take a minute, and presents the
 * day as the browser of its reader writes today in her language — the tag `formatLocale` builds its
 * formatters with.
 */
async function datedOfTheDay(row: Locator, after: number, tag: string): Promise<void> {
  const time = row.locator("time");
  const instant = await time.getAttribute("datetime");
  const at = Date.parse(instant ?? "");
  expect(at).toBeGreaterThanOrEqual(after - 60_000);
  expect(at).toBeLessThanOrEqual(Date.now() + 60_000);
  const today = await row
    .page()
    .evaluate(
      (locale) => new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date()),
      tag,
    );
  await expect(time).toContainText(today);
}

/**
 * Choose a language in the menu of the account, as its holder does: her preference. The submenu is
 * opened and its choice made from the keyboard: under load, a pointer that leaves the item of the
 * submenu for the choice meets the page while the submenu is still placed, and the click closes the
 * menu instead (#974).
 */
async function chooseLanguage(page: Page, button: Locator, language: string): Promise<void> {
  await openMenu(button, page.getByRole("menu").first());
  await page.getByRole("menuitem", { name: /^Langue/ }).press("ArrowRight");
  const choice = page.getByRole("menuitemradio", { name: language });
  await expect(choice).toBeVisible();
  await choice.press("Enter");
}

test("an attribution of a role, the journal filtered on its author and its action, is dated of the day and names the account and the role, read in French by its author and in English by the account, which did not reach the view before; a month without any action presents nothing; no command modifies nor deletes an inscription [WF-ADM-0190-A] [WF-ARC-0110-A] [WF-SEC-0030-A]", async ({
  browser,
  playwright,
}) => {
  // Two people signed in, an account created and its password set, the journal read four times: a
  // path of one piece.
  test.setTimeout(120_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  const administrator = await accountAdministrator(browser, calls);
  const role = `Audit ${randomBytes(4).toString("hex")}`;
  let holder: string | undefined;
  try {
    grantRole(DIRECTORY.login, AUDITING, ["access_roles.write", "audit_log.read"]);
    const auditor = await localAccount(browser, administrator);
    holder = auditor.email;

    // Without the consultation of the journal, its view is out of reach, as an address that leads
    // nowhere.
    const reader = await workstation(browser);
    await signIn(reader, auditor, ACCOUNT);
    await reader.goto(JOURNAL);
    await expect(reader.getByRole("heading", { level: 1 })).toHaveText("Introuvable");

    // The administrator gives her the consultation, by the service, which inscribes it.
    const before = Date.now();
    await administrator.attribute(auditor.id, role, ["audit_log.read"]);
    const asked = filtered(administrator.self, "user_access_roles_set");

    // Its author reads it in French, the journal filtered on her and on the action.
    const author = await workstation(browser);
    await signIn(author, DIRECTORY, asked);
    const french = inscription(author, "Journal d’audit", role);
    await expect(french).toHaveCount(1);
    await expect(french).toContainText("Attribution des rôles d’un compte");
    await expect(french).toContainText(`Rôle donné : ${role}`);
    await expect(french).toContainText("Jeanne Montgolfier");
    await expect(french).toContainText("Hors projet");
    await datedOfTheDay(french, before, "fr");
    // Nothing on the view modifies nor deletes an inscription: no control in its rows, and none
    // that says so around them.
    await expect(french.getByRole("button")).toHaveCount(0);
    await expect(french.getByRole("textbox")).toHaveCount(0);
    await expect(
      author.getByRole("main").getByRole("button", { name: /Modifier|Supprimer|Effacer/ }),
    ).toHaveCount(0);

    // A month without any action — before the platform was — presents nothing.
    const month = new URLSearchParams({ from: "2000-01-01T00:00:00Z", to: "2000-02-01T00:00:00Z" });
    await author.goto(`${JOURNAL}?${month.toString()}`);
    const empty = author.getByRole("grid", { name: "Journal d’audit" });
    await expect(empty.getByRole("row").last()).toHaveText("Aucune inscription");
    await expect(empty.locator("time")).toHaveCount(0);

    // The account it names reads the same inscription in English, her language.
    await reader.goto(ACCOUNT);
    await chooseLanguage(reader, accountButton(reader, auditor), "English");
    await expect(reader.locator("html")).toHaveAttribute("lang", "en");
    await reader.goto(asked);
    const english = inscription(reader, "Audit log", role);
    await expect(english).toHaveCount(1);
    await expect(english).toContainText("Roles of an account assigned");
    await expect(english).toContainText(`Role granted: ${role}`);
    await expect(english).toContainText("Jeanne Montgolfier");
    await expect(english).toContainText("No project");
    await datedOfTheDay(english, before, "en-GB");
    await reader.context().close();
    await author.context().close();
  } finally {
    // The roles withdrawn once asserted, never before.
    if (holder !== undefined) {
      withdrawRoles(holder);
    }
    administrator.done();
    await calls.dispose();
  }
});
