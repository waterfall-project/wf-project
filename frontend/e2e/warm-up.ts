// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The warm-up of the paths (#1145): every screen of the application asked once of the development
 * server before the first path starts. The development server compiles a route the first time it is
 * asked for; under the load of four workers, that compilation outlasts the five seconds of an
 * assertion that awaits the screen a click reaches. Compiled here, each route is warm when a path
 * reaches it, however it does — rather than each path compiling what it reaches (`compile`), or an
 * assertion waiting longer.
 *
 * The screens are those the paths of accessibility check (`e2e/routes.ts`), which a test of the
 * front holds to every page of `src/app` (`src/app/screens.test.ts`), with the pages that only
 * redirect: a page added is warmed with them. A few at a time, as the workers will ask. A screen is
 * asked as a page is, its redirect not followed; what it answers is the paths' to judge, but an
 * error of the server is written in the output of the run. The development server out of reach
 * fails the run. The time the warm-up took is written too.
 */
import { type FullConfig, request } from "@playwright/test";

import { OTHER_SCREENS, path, REDIRECTS, tableScreens } from "./routes";

/** How many screens are asked at once: as many as the workers of a run on a workstation. */
const AT_ONCE = 4;

/** How long a screen is given to compile and answer, the first of a cold `.next` included. */
const COMPILING = 180_000;

/** The address of every page of the application, in the project and revision of the examples. */
export function warmedAddresses(): string[] {
  return [
    ...tableScreens().map((screen) => screen.address),
    ...OTHER_SCREENS.map((screen) => screen.address),
    ...REDIRECTS.map(path),
  ];
}

/** Ask the development server for every screen once, before the paths. */
export default async function warmUp(config: FullConfig): Promise<void> {
  const baseURL = config.projects.find((project) => project.name === "chromium")?.use.baseURL;
  if (baseURL === undefined) {
    throw new Error("the warm-up asks the development server of the paths: no chromium project");
  }
  const started = performance.now();
  const context = await request.newContext({ baseURL });
  const waiting = warmedAddresses();
  const failed: string[] = [];
  const asking = async (): Promise<void> => {
    for (let address = waiting.shift(); address !== undefined; address = waiting.shift()) {
      const response = await context.get(address, { maxRedirects: 0, timeout: COMPILING });
      if (response.status() >= 500) {
        failed.push(`${address} answered ${String(response.status())}`);
      }
    }
  };
  try {
    const count = waiting.length;
    await Promise.all(Array.from({ length: AT_ONCE }, asking));
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    console.log(`Warm-up: ${String(count)} screens asked in ${seconds} s`);
    for (const failure of failed) {
      console.warn(`Warm-up: ${failure}`);
    }
  } finally {
    await context.dispose();
  }
}
