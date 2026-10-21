// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The files of the routes of the application, as the tests that hold them to the paths read them:
 * its pages (`src/app/screens.test.ts`) and its route handlers (`src/app/route-handlers.test.ts`).
 */
import { readdirSync } from "node:fs";
import { join, sep } from "node:path";

/** The directory of the routes of the application. */
const APP = join(import.meta.dirname, "../app");

/** A file of a route: where it lies, its route — groups and slots left out —, and its segments. */
export interface AppFile {
  readonly file: string;
  readonly route: string;
  readonly segments: string[];
}

/** Every file of `src/app` of a kind — `page`, `route` —, in any extension Next takes for one. */
export function appFiles(kind: "page" | "route"): AppFile[] {
  const name = new RegExp(`^${kind}\\.(tsx?|jsx?|mdx)$`);
  return readdirSync(APP, { recursive: true, encoding: "utf8" })
    .filter((file) => name.test(file.split(sep).at(-1) ?? ""))
    .map((file) => {
      const segments = file.split(sep).slice(0, -1);
      const shown = segments.filter((part) => !/^\(.*\)$/.test(part) && !part.startsWith("@"));
      return { file: join(APP, file), route: `/${shown.join("/")}`, segments };
    });
}
