// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Configuration of the unit tests of the front, and of their coverage.
 *
 * Two projects, told apart by the name of the file, never by a comment in a test:
 *
 * - `node`, for `*.test.ts` and `*.test.tsx`: the logic, and the server components of
 *   `src/app/`, which render where they run in production — without a document, so that
 *   one touching `window` fails its test;
 * - `dom`, for `*.dom.test.ts` and `*.dom.test.tsx`: the client components, which Testing
 *   Library renders into a document. happy-dom provides it: under jsdom, Vitest hands the
 *   `Request` of Node a `Blob` of jsdom, which jsdom 30.1 no longer lets it read, and a
 *   multipart body never finishes streaming, whatever the version of jsdom.
 */
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// `server-only` refuses to load outside the server bundle of Next; every test empties it.
const SERVER_ONLY = "src/test/setup.ts";
const DOM = "src/**/*.dom.test.{ts,tsx}";

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
          include: ["src/**/*.test.{ts,tsx}"],
          exclude: [DOM],
          environment: "node",
          setupFiles: [SERVER_ONLY],
        },
      },
      {
        extends: true,
        test: {
          name: "dom",
          include: [DOM],
          environment: "happy-dom",
          setupFiles: [SERVER_ONLY, "src/test/setup-dom.ts"],
        },
      },
    ],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      // The generated client is types only, and src/test/ is the tooling of the tests —
      // setup, the fake client —, not code of the front: the thresholds measure the code
      // written by hand that ships.
      exclude: ["src/**/*.test.{ts,tsx}", "src/api/generated/**", "src/test/**"],
      reporter: ["text", "json-summary"],
    },
  },
});
