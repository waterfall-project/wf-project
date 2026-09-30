// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The end-to-end harness (US-0080): Playwright starts the fake back and the front, then
 * plays the paths of `e2e/` in a browser. Each path cites the requirement it covers in its
 * title (WF-QUA-0010). From EP-03, the same paths run against the real service by pointing
 * `WATERFALL_API_ADDRESS` at it.
 *
 * The paths run against the development server; the measure of the second of §4.6.2
 * (`opening.spec.ts`, US-0110/L2) runs against the front built for production, the one users
 * open, on a port of its own: the development server compiles each route the first time it is
 * asked for, and renders with the checks of React's development build — a measure there would
 * say how fast the developer's front is.
 *
 * The harness always starts its own servers, on ports of its own — never those of `make dev`,
 * 3000 and 4010 —, and its fake back serves a variant of the contract written where `make dev`
 * does not read it: a path played against servers it did not start would judge another version
 * of the code, or another contract (#150). A port already taken fails the run, saying so. The
 * environment moves the ports, for two checkouts on one workstation. With `WATERFALL_API_ADDRESS`
 * set, the paths run against the API it names, and no fake back is started.
 *
 * The measure never fails the run on the second itself: it writes what it measured, and warns
 * when an opening overran it (`opening.spec.ts`).
 */
import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

type WebServer = Extract<
  NonNullable<PlaywrightTestConfig["webServer"]>,
  readonly unknown[]
>[number];

/** A port of the harness: the one the environment names, or its own; anything else refused. */
function port(variable: string, own: number): number {
  const named = process.env[variable];
  const chosen = named === undefined ? own : Number(named);
  if (!Number.isInteger(chosen) || chosen < 1 || chosen > 65_535) {
    throw new Error(`${variable} must be a port, a whole number from 1 to 65535: ${String(named)}`);
  }
  return chosen;
}

const API_PORT = port("E2E_API_PORT", 4110);
const FRONT_PORT = port("E2E_FRONT_PORT", 3100);
const PRODUCTION_PORT = port("E2E_PRODUCTION_PORT", 3101);
// An API named by the environment is played against as it is: no fake back is started for it.
const NAMED_API = process.env.WATERFALL_API_ADDRESS;
const API = NAMED_API ?? `http://127.0.0.1:${String(API_PORT)}`;
const FRONT = `http://127.0.0.1:${String(FRONT_PORT)}`;
const PRODUCTION = `http://127.0.0.1:${String(PRODUCTION_PORT)}`;
// From the root of the repository, where `make -C ..` runs; ignored by git.
const MOCK_SPEC = "frontend/.e2e/waterfall.mock.json";
const MEASURES = /opening\.spec\.ts$/;
const onWorkstation = process.env.CI === undefined;

/** The fake back, started on the port of the harness — unless the environment names an API. */
function fakeBack(): WebServer[] {
  if (NAMED_API !== undefined) {
    return [];
  }
  return [
    {
      command: `make -C .. mock MOCK_PORT=${String(API_PORT)} MOCK_SPEC=${MOCK_SPEC}`,
      url: `http://127.0.0.1:${String(API_PORT)}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
  ];
}

export default defineConfig({
  testDir: "e2e",
  forbidOnly: !onWorkstation,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: FRONT, trace: "retain-on-failure" },
  // A French browser by default, the language of the reference catalogue: a path that needs
  // another language sets its own (`test.use({ locale })`).
  projects: [
    {
      name: "chromium",
      testIgnore: MEASURES,
      use: { ...devices["Desktop Chrome"], locale: "fr-FR" },
    },
    {
      // After all the other paths, so that the measure has the machine to itself.
      name: "production",
      testMatch: MEASURES,
      dependencies: ["chromium"],
      // No trace: recording one would weigh on what is measured.
      use: { ...devices["Desktop Chrome"], locale: "fr-FR", baseURL: PRODUCTION, trace: "off" },
    },
  ],
  webServer: [
    ...fakeBack(),
    {
      command: `pnpm dev --hostname 127.0.0.1 --port ${String(FRONT_PORT)}`,
      url: FRONT,
      env: { WATERFALL_API_ADDRESS: API },
      reuseExistingServer: false,
      timeout: 120_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
    {
      // Built after the fake back is up — the servers start one after the other —, which the
      // build may need (#131). The build writes `.next`, the development server `.next/dev`:
      // the two live side by side.
      command: `pnpm build && pnpm start --hostname 127.0.0.1 --port ${String(PRODUCTION_PORT)}`,
      url: PRODUCTION,
      env: { WATERFALL_API_ADDRESS: API },
      reuseExistingServer: false,
      timeout: 300_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
  ],
});
