// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The mode of a path shared by the fake back and the service (EP-05, US-0810/L1): a path that both
 * play imports `test` from here, not from `@playwright/test`, and is tagged `@shared` once the
 * service serves its screen — the project `shared` plays it then against the service, after
 * `installation`, while `chromium` keeps playing it against the fake back (`playwright.config.ts`).
 *
 * Against the fake back, nothing changes: it grants the session itself. With `WATERFALL_API_ADDRESS`
 * set (`inService`), each path first signs in a local account of the run that holds the roles
 * « Manager » and « Chef de projet », made by the administrator of the installation
 * (`accountAdministrator`), one for each worker; and the paths are held to the contract, as
 * `heldToTheContract()` holds a file of `e2e/service/` — by fixtures rather than hooks: a hook declared in a module the files import is
 * declared once in a worker, for the first of its files alone.
 */
import { test as base } from "@playwright/test";

import { expectNothingRefused, startReading } from "./service/contract";
import { accountAdministrator, localAccount, type LocalPerson, signIn } from "./service/realm";

/** Whether the path plays against the service, whose API the environment names. */
export const inService = process.env.WATERFALL_API_ADDRESS !== undefined;

/**
 * The predefined role a shared path acts with, which every installation holds (WF-EXP-0020,
 * `installation.setup.ts`): its permissions are the installation's, none given here.
 */
const MANAGER = "Manager";

/**
 * The predefined role beside it that creates a project and writes, marks and abandons its revisions
 * (WF-EXP-0020, EP-04): the account of the run is the project manager of the projects it creates
 * (`revision-cycle.spec.ts`).
 */
const PROJECT_MANAGER = "Chef de projet";

/**
 * The role beside it that writes the settings of the risks and of the indicators: the contract gives
 * both permissions to the manager (WF-INTF-0020), but the back does not seed them in its predefined
 * role before EP-04 (`TO_SEED_BY_EP04`, #1457), so the administrator of the installation composes
 * them (WF-ADM-0020). Made once, kept by the installation, found again by its label on a replay: the
 * search and the creation are held one at a time across the workers (`giveRoles`), so that none
 * makes a double.
 */
export const SETTINGS_WRITER = "Paramètres des risques et des indicateurs (parcours)";

/** The screen a shared path signs in at, before it opens its own: any account reaches it. */
const SIGNED_IN_AT = "/account";

/** How long a worker is given to make its manager: a token, an account, its link, its role. */
const MAKING_THE_MANAGER = 60_000;

interface WorkerFixtures {
  /** The manager of the worker, against the service; none against the fake back. */
  manager: LocalPerson | undefined;
}

interface TestFixtures {
  /** The path signed in as the manager of the worker and held to the contract, in the service. */
  served: undefined;
}

/** The `test` of Playwright, the path signed in and held to the contract when in the service. */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  manager: [
    async ({ browser, playwright }, use) => {
      if (!inService) {
        await use(undefined);
        return;
      }
      // Read from here: the making of the manager is held to the contract too.
      startReading();
      const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
      let manager: LocalPerson;
      try {
        const administrator = await accountAdministrator(browser, calls);
        manager = await localAccount(browser, administrator);
        await administrator.giveAlso(manager.id, [
          [MANAGER, []],
          [PROJECT_MANAGER, []],
          [SETTINGS_WRITER, ["risk_settings.write", "indicator_settings.write"]],
        ]);
      } finally {
        await calls.dispose();
      }
      await use(manager);
    },
    { scope: "worker", timeout: MAKING_THE_MANAGER },
  ],
  served: [
    async ({ page, manager }, use) => {
      if (manager === undefined) {
        await use(undefined);
        return;
      }
      await signIn(page, manager, SIGNED_IN_AT);
      await use(undefined);
      expectNothingRefused();
    },
    { auto: true },
  ],
});
