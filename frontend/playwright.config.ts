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
 */
import { defineConfig, devices } from "@playwright/test";

const API = process.env.WATERFALL_API_ADDRESS ?? "http://127.0.0.1:4010";
const FRONT = "http://127.0.0.1:3000";
const PRODUCTION = "http://127.0.0.1:3001";
const MEASURES = /opening\.spec\.ts$/;
const onWorkstation = process.env.CI === undefined;

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
      use: { ...devices["Desktop Chrome"], locale: "fr-FR", baseURL: PRODUCTION },
    },
  ],
  webServer: [
    {
      command: "make -C .. mock",
      url: `${API}/api/v1/health`,
      reuseExistingServer: onWorkstation,
      timeout: 120_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
    {
      command: "pnpm dev --hostname 127.0.0.1 --port 3000",
      url: FRONT,
      env: { WATERFALL_API_ADDRESS: API },
      reuseExistingServer: onWorkstation,
      timeout: 120_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
    {
      // Built after the fake back is up: the servers start one after the other. The build
      // writes `.next`, the development server `.next/dev`: the two live side by side.
      command: "pnpm build && pnpm start --hostname 127.0.0.1 --port 3001",
      url: PRODUCTION,
      env: { WATERFALL_API_ADDRESS: API },
      reuseExistingServer: onWorkstation,
      timeout: 300_000,
      // Signal the whole process group: make and pnpm start the servers as children.
      gracefulShutdown: { signal: "SIGTERM", timeout: 5_000 },
    },
  ],
});
