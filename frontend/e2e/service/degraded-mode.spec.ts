// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The two lines of the table of the degraded modes that only the platform of the service can hold
 * (US-2860, WF-EXP-0040-A, tableau 12): the front and the realm, whose component is a container
 * stopped for the time of a path (`components.ts`), then started again, whatever the path found.
 *
 * Redis stopped: every request of the front is refused, since its session can be neither read nor
 * created again — the screen names the cache, never an unexpected error, never a screen read as
 * if it had succeeded —, and the front serves again once Redis is back.
 *
 * The directory of the enterprise stopped: the local accounts go on — the connection in progress
 * keeps its screen, and a local account signs in —, while the account of the directory is refused
 * at the realm, and signs in again once the directory is back.
 *
 * Both stop a component every path beside reads: they play alone, last (`@platform-wide`).
 */
import { type Browser, expect, type Page, type PlaywrightWorkerArgs, test } from "@playwright/test";

import { START_ALL_AGAIN_TIMEOUT, startAllAgain, whileStopped } from "./components";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  type Administrator,
  DIRECTORY,
  giveIdentifiers,
  localAccount,
  REALM,
  type Person,
  signIn,
  under,
} from "./realm";

heldToTheContract();

const ACCOUNT = "/account";
// The cookie of the session of the front (`src/session/tokens.ts`).
const SESSION_COOKIE = "__Host-wf_session";

// A worker killed on a timeout never runs the `finally` of `whileStopped`: Playwright runs this
// in a new worker then, so that no component stays stopped for the paths after. Each component
// is waited for up to 60 s (`startAllAgain`): the hook gets the time of all of them.
test.afterAll(async () => {
  test.setTimeout(START_ALL_AGAIN_TIMEOUT);
  await startAllAgain();
});

/** A page of a workstation of its own, in French, which trusts the front end of Keycloak. */
async function workstation(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ locale: "fr-FR", ignoreHTTPSErrors: true });
  return context.newPage();
}

/** Whether the workstation of a page holds a session of the front. */
async function holdsSession(page: Page): Promise<boolean> {
  return (await page.context().cookies()).some(({ name }) => name === SESSION_COOKIE);
}

/** A local account of the path, its own, made by the administrator of the installation. */
async function ownAccount(
  browser: Browser,
  playwright: PlaywrightWorkerArgs["playwright"],
): Promise<Person> {
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const administrator: Administrator = await accountAdministrator(browser, calls);
    return await localAccount(browser, administrator);
  } finally {
    await calls.dispose();
  }
}

test(
  "Redis stopped, every request of the front is refused naming the cache, never as an unexpected error nor as a success, and the front serves again once Redis is back [US-2860] [WF-EXP-0040-A]",
  { tag: "@platform-wide" },
  async ({ browser, playwright, request }) => {
    test.setTimeout(240_000);
    const person = await ownAccount(browser, playwright);
    const page = await workstation(browser);
    await signIn(page, person, ACCOUNT);
    await expect(page.getByRole("main")).toContainText(person.email);

    await whileStopped("cache", async () => {
      // A request of the front, its session unreadable: the screen says the cache is down.
      await page.goto(ACCOUNT);
      // Beside the alert of the screen, Next keeps an empty one for its route announcer.
      const alert = page.getByRole("alert").filter({ hasText: "Composant indisponible : Cache" });
      await expect(alert).toBeVisible();
      await expect(alert).not.toContainText("Erreur inattendue");
      // Nothing of the account is shown as if the read had succeeded.
      await expect(page.getByRole("main")).not.toContainText(person.email);

      // A session cannot be created again either: the sign-in is refused, with the way to try
      // again — not a blank page, not a sign-in. Only the screen of failure names the cache: the
      // page of the sign-in that could not be made (`/login/unavailable`) is shared by every cause
      // — the realm, Redis, a silent store — and says the service does not answer, whichever it
      // is; naming the cause there asks a parameter the route would forward to a page anyone can
      // open, which is not this lot's. That screen has no "what remains possible" to say either:
      // it offers to try again, as the page of the sign-in does.
      const another = await workstation(browser);
      await another.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
      await expect(another.getByText("la connexion n’a pas pu se faire")).toBeVisible();
      expect(await holdsSession(another)).toBe(false);
      await another.context().close();
    });

    // Redis back, and empty: its sessions were its alone. The front reaches it again — a sign-in
    // that opens is the proof — and serves the screen.
    await expect
      .poll(
        async () => (await request.get("/login", { maxRedirects: 0 })).headers().location ?? "",
        { timeout: 30_000 },
      )
      .not.toContain("/login/unavailable");
    // A front that answers has not reached its session store again: sign in on a new page each
    // time, for 60 s at most.
    await expect(async () => {
      const again = await workstation(browser);
      try {
        await signIn(again, person, ACCOUNT);
        await expect(again.getByRole("main")).toContainText(person.email, { timeout: 5_000 });
      } finally {
        await again.context().close();
      }
    }).toPass({ timeout: 60_000 });
    await page.context().close();
  },
);

test(
  "the directory of the enterprise stopped, the local accounts go on, their connection in progress and their sign-in, and the account of the directory is refused at the realm until the directory is back [US-2860] [WF-EXP-0040-A]",
  { tag: "@platform-wide" },
  async ({ browser, playwright }) => {
    test.setTimeout(240_000);
    const staying = await ownAccount(browser, playwright);
    const arriving = await ownAccount(browser, playwright);
    const inProgress = await workstation(browser);
    await signIn(inProgress, staying, ACCOUNT);

    await whileStopped("directory", async () => {
      // The connection in progress goes on.
      await inProgress.goto(ACCOUNT);
      await expect(inProgress.getByRole("main")).toContainText(staying.email);

      // A local account signs in.
      const local = await workstation(browser);
      await signIn(local, arriving, ACCOUNT);
      await expect(local.getByRole("main")).toContainText(arriving.email);
      await local.context().close();

      // Not proven here: the line also stops "the update of the attributes of those accounts by
      // the reading of the accounts" (WF-ADM-0070). The reading asked from the screen while the
      // directory is down was tried: it ends as a success and the report shows no account
      // updated, but that proves nothing without an account of the directory whose attribute
      // changed in the directory itself, which the seed of this platform does not offer. The
      // sub-line stays untested here (said in the report of the lot).
      //
      // The account of the directory is refused: the realm keeps it on its sign-in page, and the
      // front opens no session.
      const refused = await workstation(browser);
      await refused.goto(`/login?next=${encodeURIComponent(ACCOUNT)}`);
      await giveIdentifiers(refused, DIRECTORY);
      // The realm answers its own page of refusal, never the screen of the account.
      await expect(refused).toHaveURL(under(`${REALM}/`));
      await expect(refused.getByRole("heading", { name: "Nous sommes désolés..." })).toBeVisible();
      expect(await holdsSession(refused)).toBe(false);
      await refused.context().close();
    });

    // A healthy directory container is not the realm reaching it again: sign in on a new page each
    // time, for 60 s at most.
    await expect(async () => {
      const restored = await workstation(browser);
      try {
        await signIn(restored, DIRECTORY, ACCOUNT);
      } finally {
        await restored.context().close();
      }
    }).toPass({ timeout: 60_000 });
    await inProgress.context().close();
  },
);
