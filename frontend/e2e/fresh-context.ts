// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A browser context of its own, with the configuration of the Playwright project the path plays in
 * (`playwright.config.ts`: the device, the language, the address of the front, the certificates of
 * Keycloak's local authority). A path that opens one — a second session, an account that signs in
 * on its own, a call made apart — asks for it here and names only what it changes, so that the
 * configuration is written once and its drift is not silent.
 */
import {
  type Browser,
  type BrowserContext,
  type BrowserContextOptions,
  test,
} from "@playwright/test";

/** Open a context of a browser with the options of the project of the running path, then `changes`. */
export async function freshContext(
  browser: Browser,
  changes: BrowserContextOptions = {},
): Promise<BrowserContext> {
  // The options of a project are those of a context, and a device carries its type of browser,
  // which Playwright's own documentation spreads into `newContext` as it is.
  // An option the project leaves undefined is left out, as a context asks for none.
  const set = Object.entries(test.info().project.use).filter(([, value]) => value !== undefined);
  const project = Object.fromEntries(set) as BrowserContextOptions;
  return browser.newContext({ ...project, ...changes });
}
