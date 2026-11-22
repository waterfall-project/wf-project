// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * Redis emptied under a platform that runs (US-2830, WF-ARC-0040-A): nothing a person made is
 * kept there, so that emptying it — as a restart with nothing kept would — loses no project data.
 *
 * What the Python tests cannot see is the session of the front, which Redis holds: the cookie of
 * the browser names a session that is gone. The user signs in again — the session of Keycloak, kept
 * in its own database, answers for her — and finds her project and its revision. A marking asked
 * while the worker is stopped, then Redis emptied, is run once the worker is back: its queue is
 * built again from the table of the tasks, and the revision is marked.
 *
 * Both empty a component every path beside reads (Redis, the worker): they play alone, last
 * (`@platform-wide`).
 */
import { type Browser, expect, type Page, type PlaywrightWorkerArgs, test } from "@playwright/test";

import { MARKING, WORKING } from "../bounds";
import { createOwnProject, openRevision, type OwnProject } from "../own-project";
import { emptyCache, start, startAllAgain, stop } from "./components";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  type Administrator,
  giveIdentifiers,
  localAccount,
  type LocalPerson,
  REALM,
} from "./realm";

heldToTheContract();

const ROLES = [
  ["Manager", []],
  ["Chef de projet", []],
] as const;

// A worker killed on a timeout never runs what follows the path: Playwright runs this in a new
// worker then, so that Redis and the worker are never left stopped for the paths after.
test.afterAll(async () => {
  test.setTimeout(150_000);
  await startAllAgain();
});

/** A page of a workstation of its own, in French, which trusts the front end of Keycloak. */
async function workstation(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  return context.newPage();
}

/** A local account of the path, its own, a manager of projects. */
async function projectManager(
  browser: Browser,
  playwright: PlaywrightWorkerArgs["playwright"],
): Promise<LocalPerson> {
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const administrator: Administrator = await accountAdministrator(browser, calls);
    const person = await localAccount(browser, administrator);
    await administrator.giveAlso(person.id, ROLES);
    return person;
  } finally {
    await calls.dispose();
  }
}

/**
 * The user goes back to a screen after Redis was emptied: her cookie names a session that is gone,
 * the front sends her to sign in, and the realm, which still holds her session, answers for her —
 * or asks her identifiers, which she gives. Either way she lands on the screen she asked for.
 */
async function reconnect(page: Page, person: LocalPerson, address: string): Promise<void> {
  await page.goto(address);
  await expect
    .poll(() => page.url().startsWith(REALM) || page.url().endsWith(address), {
      timeout: WORKING,
    })
    .toBe(true);
  if (page.url().startsWith(REALM)) {
    await giveIdentifiers(page, person);
  }
  await expect(page).toHaveURL((url) => url.pathname + url.search === address);
}

/** A project of the person with its revision in progress, as she makes them. */
async function projectWithARevision(page: Page): Promise<{ own: OwnProject; revision: string }> {
  const own = await createOwnProject(page, "Redis vidé");
  await openRevision(page, own);
  const revision = new URL(page.url()).searchParams.get("revision_id");
  expect(revision, "the revision opened is named by the address").not.toBeNull();
  return { own, revision: revision ?? "" };
}

test(
  "after Redis is emptied the platform goes on, the user signs in again and finds her project and its revision [WF-ARC-0040-A]",
  { tag: "@platform-wide" },
  async ({ browser, playwright }) => {
    test.setTimeout(240_000);
    const person = await projectManager(browser, playwright);
    const page = await workstation(browser);
    await page.goto(`/login?next=${encodeURIComponent("/")}`);
    await giveIdentifiers(page, person);
    const { own, revision } = await projectWithARevision(page);
    const screen = `${own.path}/revisions?revision_id=${revision}`;

    emptyCache();

    // Her session of the front is gone: she signs in again, and the screen she asked for is there.
    await reconnect(page, person, screen);
    const history = page
      .getByRole("main")
      .getByRole("region", { name: "Historique des révisions" });
    await expect(history).toBeVisible({ timeout: WORKING });

    // Her project is on her home, and the platform serves it as it did.
    await page.goto("/");
    await expect(page.getByRole("main").getByText(own.label)).toBeVisible({ timeout: WORKING });
    await page.context().close();
  },
);

test(
  "a marking asked before Redis is emptied and not taken is run once the worker is back [WF-ARC-0040-A]",
  { tag: "@platform-wide" },
  async ({ browser, playwright }) => {
    test.setTimeout(300_000);
    const person = await projectManager(browser, playwright);
    const page = await workstation(browser);
    await page.goto(`/login?next=${encodeURIComponent("/")}`);
    await giveIdentifiers(page, person);
    const { own, revision } = await projectWithARevision(page);
    const screen = `${own.path}/revisions?revision_id=${revision}`;
    const main = page.getByRole("main");
    const history = main.getByRole("region", { name: "Historique des révisions" });

    // No worker takes the task: it is deposited in the table of the tasks and in the queue.
    stop("worker");
    try {
      const commands = main.getByRole("region", { name: "Commandes" });
      await commands.getByRole("button", { name: "Marquer la révision" }).click();
      const marking = commands.getByRole("form");
      await marking.getByRole("textbox", { name: "Nom de version" }).fill("v1.0");
      await marking.getByRole("button", { name: "Marquer", exact: true }).click();
      await expect(commands.getByRole("form")).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: /^Tâches et messages\s: 1 tâche suivie/ }),
      ).toBeVisible();

      // The queue is gone with Redis: only the table of the tasks remembers the marking.
      emptyCache();
    } finally {
      await start("worker");
    }

    // The worker is back: the marking is run, and the user, signed in again, sees its end.
    await expect(async () => {
      await reconnect(page, person, screen);
      await expect(history.getByRole("row").filter({ hasText: "v1.0" })).toBeVisible({
        timeout: 5_000,
      });
    }).toPass({ timeout: MARKING });
    await page.context().close();
  },
);
