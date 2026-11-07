// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * Two contributors of the same project against the service (US-1000, WF-ADM-0040-A): one reads in
 * French and keeps every column, the other reads in English and keeps other columns; both read the
 * same project and the same revisions, each presented by her own settings, and neither changes the
 * settings of the other.
 *
 * The accounts are local accounts the administrator of the installation creates, each holding the
 * roles « Manager » and « Chef de projet ». The first creates the project and opens a revision, as a
 * user does; the contributors are written by the API under her token, the screen of the contributors
 * proposing the accounts of the estimate alone (`listContributorSuggestions`).
 */
import {
  type APIRequestContext,
  type Browser,
  expect,
  type Locator,
  type Page,
  test,
} from "@playwright/test";

import { openHydrated, openMenu } from "../hydration";
import { createOwnProject, inscribe, openRevision, type OwnProject } from "../own-project";
import { heldToTheContract } from "./contract";
import {
  type Administrator,
  accountAdministrator,
  giveIdentifiers,
  gridPreferences,
  localAccount,
  type LocalPerson,
  type Person,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
const ROLES = [
  ["Manager", []],
  ["Chef de projet", []],
] as const;

let administrator: Administrator;
let calls: APIRequestContext;
let french: LocalPerson;
let english: LocalPerson;

// The administrator of the file, and two local accounts, each with its password set by its link.
test.beforeAll(async ({ browser, playwright }) => {
  calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  administrator = await accountAdministrator(browser, calls);
  french = await localAccount(browser, administrator);
  english = await localAccount(browser, administrator);
  for (const person of [french, english]) {
    await administrator.giveAlso(person.id, ROLES);
  }
});

test.afterAll(async () => {
  await calls.dispose();
});

/**
 * The names of the two contributors a grid lists: the cell of the column `name` of each row of its
 * body, after the header and before the totals.
 */
async function namesOf(grid: Locator): Promise<string[]> {
  const rows = grid.getByRole("row");
  await expect(rows).toHaveCount(4);
  const names = await rows.evaluateAll((all) =>
    all
      .slice(1, -1)
      .map((row) => (row.querySelector('[data-column="name"]')?.textContent ?? "").trim()),
  );
  expect(names).toHaveLength(2);
  expect(names.every((name) => name !== "")).toBe(true);
  return names;
}

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

test("two contributors of a project read the same project and the same revisions, one in French with every column, the other in English with other columns kept [WF-ADM-0040-A]", async ({
  browser,
}) => {
  test.slow();
  const pages: Page[] = [];
  try {
    const mine = await workstation(browser, "fr-FR");
    const hers = await workstation(browser, "en-US");
    pages.push(mine, hers);
    await signInAt(mine, french, ACCOUNT);
    await signInAt(hers, english, ACCOUNT);
    await expect(mine.locator("html")).toHaveAttribute("lang", "fr");
    await expect(hers.locator("html")).toHaveAttribute("lang", "en");

    // The first creates the project and opens a revision, then inscribes the other.
    const own: OwnProject = await createOwnProject(mine, "Deux lecteurs");
    await inscribe(browser, calls, french, english, own);
    await openRevision(mine, own);

    // The second hides a column of the contributors in her own language.
    await openHydrated(hers, `${own.path}/settings`);
    await expect(hers.getByRole("main").getByRole("heading", { level: 1 })).toHaveText(
      "Project settings",
    );
    const theirs = hers.getByRole("main").getByRole("grid", { name: "Contributors" });
    await expect(theirs.getByRole("columnheader", { name: "Capacity" })).toBeVisible();
    const menu = hers.getByRole("menu");
    await openMenu(hers.getByRole("button", { name: "Columns of “Contributors”" }), menu);
    await menu.getByRole("menuitemcheckbox", { name: "Capacity" }).click();
    await hers.keyboard.press("Escape");
    await expect(theirs.getByRole("columnheader", { name: "Capacity" })).toHaveCount(0);
    await expect
      .poll(() => gridPreferences(english.email, "contributors"))
      .toMatchObject({ hidden_columns: ["kind"] });

    // The first reads the same contributors in French, every column kept, her own settings
    // untouched by the other's.
    await openHydrated(mine, `${own.path}/settings`);
    await expect(mine.getByRole("main").getByRole("heading", { level: 1 })).toHaveText(
      "Paramètres de projets",
    );
    const ours = mine.getByRole("main").getByRole("grid", { name: "Contributeurs" });
    await expect(ours.getByRole("columnheader", { name: "Qualité" })).toBeVisible();
    await expect(ours.getByRole("row", { name: /Chef de projet/ })).toBeVisible();
    await expect(ours.getByRole("row", { name: /Contributeur/ })).toBeVisible();
    await expect(ours.getByRole("row").last()).toHaveText("2 contributeurs");
    const peopleOfMine = await namesOf(ours);
    expect(gridPreferences(french.email, "contributors")).toBeNull();

    // The second finds her columns again, and the same two contributors in English.
    await hers.reload();
    await expect(theirs.getByRole("columnheader", { name: "Capacity" })).toHaveCount(0);
    await expect(theirs.getByRole("columnheader", { name: "Name" })).toBeVisible();
    await expect(theirs.getByRole("row").last()).toHaveText("2 contributors");
    // The same two people, whatever the language and the columns shown.
    expect(await namesOf(theirs)).toEqual(peopleOfMine);

    // Both read the same revision, the one the first opened, each in her language.
    await openHydrated(mine, `${own.path}/revisions`);
    await openHydrated(hers, `${own.path}/revisions`);
    const history = (page: Page, name: string) =>
      page.getByRole("main").getByRole("table", { name });
    const french_history = history(mine, "Historique des révisions");
    const english_history = history(hers, "Revision history");
    await expect(french_history.getByRole("row")).toHaveCount(2);
    await expect(english_history.getByRole("row")).toHaveCount(2);
    await expect(french_history.getByRole("row").nth(1)).toContainText("En cours d’élaboration");
    await expect(english_history.getByRole("row").nth(1)).toContainText("Draft");
    await expect(mine.getByRole("region", { name: "Contexte de lecture" })).toContainText(
      own.label,
    );
    await expect(hers.getByRole("region", { name: "Reading context" })).toContainText(own.label);
  } finally {
    for (const page of pages) {
      await page.context().close();
    }
  }
});
