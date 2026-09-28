// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Configuration of the unit tests of the front, and of their coverage.
 *
 * Two projects: `node` for the logic, `jsdom` for the components (`*.test.tsx`), which
 * Testing Library renders into a document. The environment is chosen here, by the name of
 * the file, and never by a comment in a test.
 */
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// `server-only` refuses to load outside the server bundle of Next; every test mocks it.
const SERVER_ONLY = "src/test/setup.ts";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: "node",
          include: ["src/**/*.test.ts"],
          environment: "node",
          setupFiles: [SERVER_ONLY],
        },
      },
      {
        extends: true,
        test: {
          name: "jsdom",
          include: ["src/**/*.test.tsx"],
          environment: "jsdom",
          setupFiles: [SERVER_ONLY, "src/test/setup-dom.ts"],
        },
      },
    ],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      // The generated client is types only; the tests measure the code written by hand.
      exclude: ["src/**/*.test.{ts,tsx}", "src/api/generated/**"],
      reporter: ["text", "json-summary"],
    },
  },
});
