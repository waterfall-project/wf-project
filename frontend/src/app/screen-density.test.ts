// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The family of the screen of a function is read in its table (US-2070; EP-25, « Deux familles
 * d'écrans, dites par Screen »): a screen of a function takes its density from `FUNCTION_DENSITY`
 * or `LEAF_DENSITY`, never from a literal, which would set it in one family while its header,
 * reading the table, sets it in the other (the list of the projects of the portfolio, dense under
 * an airy header), and an airy screen is airy up to its header: `PageHeader` keeps `dense` by
 * default, so a file that writes an airy screen and leaves its header at the default would set a
 * tight title above an airy column (#3268, #3397).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

const SRC = join(import.meta.dirname, "..");

/**
 * The files that write their density, each a screen that is no function of the table: the home
 * and the home of an account that opens no project, the screen of a project, the account and its
 * avatar, a page not found, a session the server cannot open, the screen of a failure — and the
 * skeletons of the segments of the home, of the account and of an address no screen answers
 * (#3269).
 */
const NOT_A_FUNCTION = [
  "app/(home)/page.tsx",
  "app/(home)/loading.tsx",
  "app/account/loading.tsx",
  "app/[...path]/loading.tsx",
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

/** A screen written airy. */
const airyScreen = /<Screen\s+density="airy"/;

/** The headers a file writes without the airy density on them: each `<PageHeader … />`. */
function forgottenHeaders(source: string): string[] {
  return (source.match(/<PageHeader\b[\s\S]*?\/>/g) ?? []).filter(
    (header) => !/\bdensity="airy"/.test(header),
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

  it("is airy on the header of every screen written airy: no PageHeader left at its default [WF-IHM-0100-A]", () => {
    const airy = sources().filter((file) => airyScreen.test(readFileSync(join(SRC, file), "utf8")));
    // Not vacuous: the home, the account and the pages of failure write an airy screen.
    expect(airy.length).toBeGreaterThanOrEqual(5);
    expect(
      airy.filter((file) => forgottenHeaders(readFileSync(join(SRC, file), "utf8")).length > 0),
    ).toEqual([]);
  });

  it("finds the header of an airy screen left at the density of its default [WF-IHM-0100-A]", () => {
    const forgotten = `<Screen density="airy"><PageHeader title="x" icon={I} /></Screen>`;
    const written = `<Screen density="airy"><PageHeader title="x" icon={I} density="airy" /></Screen>`;
    expect(airyScreen.test(forgotten)).toBe(true);
    expect(forgottenHeaders(forgotten)).toHaveLength(1);
    expect(forgottenHeaders(written)).toEqual([]);
    expect(forgottenHeaders(`<PageHeader density={FUNCTION_DENSITY.users} />`)).toHaveLength(1);
  });
});
