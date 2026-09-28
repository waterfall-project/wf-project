// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The end-to-end harness (US-0080): Playwright starts the fake back and the front, then
 * plays the paths of `e2e/` in a browser. Each path cites the requirement it covers in its
 * title (WF-QUA-0010). From EP-03, the same paths run against the real service by pointing
 * `WATERFALL_API_ADDRESS` at it.
 */
import { defineConfig, devices } from "@playwright/test";

const API = process.env.WATERFALL_API_ADDRESS ?? "http://127.0.0.1:4010";
const FRONT = "http://127.0.0.1:3000";
const onWorkstation = process.env.CI === undefined;

export default defineConfig({
  testDir: "e2e",
  forbidOnly: !onWorkstation,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: FRONT, trace: "retain-on-failure" },
  // A French browser by default, the language of the reference catalogue: a path that needs
  // another language sets its own (`test.use({ locale })`).
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], locale: "fr-FR" } }],
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
  ],
});
