// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The family of the screen of a function is read in its table (US-2070; EP-25, « Deux familles
 * d'écrans, dites par Screen »): a screen of a function takes its density from `FUNCTION_DENSITY`
 * or `LEAF_DENSITY`, never from a literal, which would set it in one family while its header,
 * reading the table, sets it in the other (the list of the projects of the portfolio, dense under
 * an airy header).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

const SRC = join(import.meta.dirname, "..");

/**
 * The files that write their density, each a screen that is no function of the table: the home
 * and the home of an account that opens no project, the screen of a project, the account and its
 * avatar, a page not found, a session the server cannot open, the screen of a failure.
 */
const NOT_A_FUNCTION = [
  "app/(home)/page.tsx",
  "components/projects/no-openable-project.tsx",
  "app/projects/[projectId]/page.tsx",
  "app/account/page.tsx",
  "app/account/avatar/page.tsx",
  "app/not-found.tsx",
  "app/login/unavailable/page.tsx",
  "components/system/system-failure.tsx",
];

/** The source files of the screens: the routes, and the components that render a screen. */
function sources(): string[] {
  return ["app", "components"].flatMap((root) =>
    readdirSync(join(SRC, root), { recursive: true, encoding: "utf8" })
      .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file))
      .map((file) =>
        relative(SRC, join(SRC, root, file))
          .split(sep)
          .join("/"),
      ),
  );
}

describe("the density of a screen", () => {
  it("is never written as a literal on the screen of a function: the table of the densities says it", () => {
    const literal = /\bdensity=(["'`]|\{\s*["'`])/;
    const writing = sources().filter((file) => literal.test(readFileSync(join(SRC, file), "utf8")));
    expect(writing.filter((file) => !NOT_A_FUNCTION.includes(file))).toEqual([]);
  });

  it("names only exceptions that still write their density", () => {
    const literal = /\bdensity="/;
    for (const file of NOT_A_FUNCTION) {
      expect(literal.test(readFileSync(join(SRC, file), "utf8")), file).toBe(true);
    }
  });
});
