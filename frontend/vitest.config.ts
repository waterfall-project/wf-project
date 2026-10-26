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
 *   multipart body never finishes streaming, whatever the version of jsdom;
 * - `lint`, for the guards that run ESLint on code, typed, which take a minute or more each: a
 *   project of their own, which the chain plays on a runner of its own while the two others are
 *   spread over two more (`make check-front-tests`, `.github/workflows/front.yml`).
 *
 * A worker for each processor but one, as Vitest takes by itself outside watch mode, four at most
 * (`workers`, #1474). The one left is the main process's, which gathers the results, and under
 * coverage the coverage of every worker. The workstation, a laptop of twelve processors, gained
 * nothing beyond four, and each test only ran slower: the coverage of the whole suite took 325 s on
 * twelve workers, 319 s on six and 300 s on four, its slowest test of a component 5.4 s — past its
 * five seconds —, 4.4 s and 1.9 s. A runner of the chain, four processors, plays on three: on four
 * of the workstation's cores, the coverage of the half `2/2` took 121 s on four workers and 131 s
 * on three, but 29 of its tests passed the second on four, 11 on three.
 */
import { availableParallelism } from "node:os";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// `server-only` refuses to load outside the server bundle of Next; every test empties it.
const SERVER_ONLY = "src/test/setup.ts";
const DOM = "src/**/*.dom.test.{ts,tsx}";
const LINT = [
  "src/api/network-guard.test.ts",
  "src/i18n/text-guard.test.ts",
  "src/theme/colour-guard.test.ts",
];

/**
 * The workers of a run on so many processors: one for each but one, as Vitest takes by itself
 * outside watch mode, the one left to the main process, which gathers the results and the coverage
 * of the workers; four at most (#1474).
 */
export function workers(processors: number): number {
  return Math.min(4, Math.max(1, processors - 1));
}

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    maxWorkers: workers(availableParallelism()),
    projects: [
      {
        extends: true,
        test: {
          name: "node",
          include: ["src/**/*.test.{ts,tsx}"],
          exclude: [DOM, ...LINT],
          environment: "node",
          setupFiles: [SERVER_ONLY],
        },
      },
      {
        extends: true,
        test: {
          name: "lint",
          include: LINT,
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
