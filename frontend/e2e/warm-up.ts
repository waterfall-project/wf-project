// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The warm-up of the paths (#1145): every route of the application asked once of the development
 * server before the first path starts. The development server compiles a route the first time it is
 * asked for; under the load of four workers, that compilation outlasts the five seconds of an
 * assertion that awaits the screen a click reaches. Compiled here, each route is warm when a path
 * reaches it, however it does — rather than each path compiling what it reaches (`compile`), or an
 * assertion waiting longer.
 *
 * The screens are those the paths of accessibility check (`e2e/routes.ts`), which a test of the
 * front holds to every page of `src/app` (`src/app/screens.test.ts`), with the pages that only
 * redirect: a page added is warmed with them. The route handlers are asked too, each at an address
 * that changes nothing, or declared exempt with the reason why (`WARMED_HANDLERS`,
 * `EXEMPT_HANDLERS`), which a test holds to every `route.ts` of `src/app`
 * (`src/app/route-handlers.test.ts`). A few at a time, as the workers will ask. A route is asked as
 * `compileAnswered` asks it, its redirect not followed: any answer but an error of the server. An
 * error — a status of 500 or more, or no answer at all — is written as it comes, and fails the run
 * once every route has been asked, naming each address in error: a screen that does not compile
 * shows here, not in each path that reaches it. The time the warm-up took is written too.
 */
import { type FullConfig, request } from "@playwright/test";

import { OTHER_SCREENS, path, REDIRECTS, tableScreens } from "./routes";

/** How many routes are asked at once: as many as the workers of a run on a workstation. */
const AT_ONCE = 4;

/** How long a route is given to compile and answer, the first of a cold `.next` included. */
const COMPILING = 180_000;

/**
 * The route handlers of `src/app` the warm-up asks, by route, each at an address that changes
 * nothing, whatever the authentication — the fake back's, or the realm's against an API the
 * environment names.
 */
export const WARMED_HANDLERS: Readonly<Record<string, string>> = {
  // Without the state of a sign-in, nothing is taken: back to `/login`, or 404 on the fake back.
  "/auth/callback": "/auth/callback",
  // Its redirect, not followed, never reaches the realm: no session ends.
  "/auth/sign-out": "/auth/sign-out",
  // Asked by a GET, which it does not answer (405): the logout token of the realm comes by a POST.
  "/auth/backchannel-logout": "/auth/backchannel-logout",
  // An address that names no task (`isIdentifier`): 404, the API asked nothing.
  "/tasks/[taskId]/result": "/tasks/~/result",
  // An address that names no backup: 404, the API asked nothing.
  "/admin/backups/[backupId]/content": "/admin/backups/~/content",
};

/** The route handlers of `src/app` the warm-up leaves out, by route, and why. */
export const EXEMPT_HANDLERS: Readonly<Record<string, string>> = {
  "/login":
    "against an API the environment names, it starts a sign-in: a state kept in Redis, and the realm asked",
};

/** The address of every page and every warmed route handler, pages in the revision of the examples. */
export function warmedAddresses(): string[] {
  return [
    ...tableScreens().map((screen) => screen.address),
    ...OTHER_SCREENS.map((screen) => screen.address),
    ...REDIRECTS.map(path),
    ...Object.values(WARMED_HANDLERS),
  ];
}

/**
 * Ask the server at `baseURL` for each address once, a few at a time; each error written as it
 * comes, and every one of them in the error thrown once all are asked.
 */
export async function warm(baseURL: string, addresses: readonly string[]): Promise<void> {
  const context = await request.newContext({ baseURL });
  const waiting = [...addresses];
  const failed: string[] = [];
  const failing = (failure: string): void => {
    failed.push(failure);
    console.error(`Warm-up: ${failure}`);
  };
  const asking = async (): Promise<void> => {
    for (let address = waiting.shift(); address !== undefined; address = waiting.shift()) {
      try {
        const response = await context.get(address, { maxRedirects: 0, timeout: COMPILING });
        if (response.status() >= 500) {
          failing(`${address} answered ${String(response.status())}`);
        }
      } catch (error) {
        failing(`${address} failed: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  };
  try {
    await Promise.all(Array.from({ length: AT_ONCE }, asking));
  } finally {
    await context.dispose();
  }
  if (failed.length > 0) {
    const count = `${String(failed.length)} of ${String(addresses.length)}`;
    throw new Error(`Warm-up: ${count} routes in error:\n${failed.join("\n")}`);
  }
}

/** Ask the development server for every route once, before the paths. */
export default async function warmUp(config: FullConfig): Promise<void> {
  const baseURL = config.projects.find((project) => project.name === "chromium")?.use.baseURL;
  if (baseURL === undefined) {
    throw new Error("the warm-up asks the development server of the paths: no chromium project");
  }
  const started = performance.now();
  const addresses = warmedAddresses();
  try {
    await warm(baseURL, addresses);
  } finally {
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    console.log(`Warm-up: ${String(addresses.length)} routes asked in ${seconds} s`);
  }
}
