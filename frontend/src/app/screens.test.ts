// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readdirSync, readFileSync } from "node:fs";
import { join, sep } from "node:path";

import { describe, expect, it } from "vitest";

import { OTHER_SCREENS, REDIRECTS, tableScreens } from "../../e2e/routes";

/** The directory of the routes of the application. */
const APP = import.meta.dirname;

/** The file of a page, in any extension Next takes for one. */
const PAGE = /^page\.(tsx?|jsx?|mdx)$/;

/** A segment of a route that intercepts another (`(.)x`, `(..)x`, `(...)x`). */
const INTERCEPTING = /^\(\.{1,3}\)/;

/** Every page of the application: its file, and its route — groups and slots left out. */
function pages(): { readonly file: string; readonly route: string; readonly segments: string[] }[] {
  return readdirSync(APP, { recursive: true, encoding: "utf8" })
    .filter((file) => PAGE.test(file.split(sep).at(-1) ?? ""))
    .map((file) => {
      const segments = file.split(sep).slice(0, -1);
      const shown = segments.filter((part) => !/^\(.*\)$/.test(part) && !part.startsWith("@"));
      return { file: join(APP, file), route: `/${shown.join("/")}`, segments };
    });
}

describe("the pages of the application", () => {
  it("are each a screen the paths of accessibility check, or a page that only redirects", () => {
    const known = [
      ...tableScreens().map((screen) => screen.route),
      ...OTHER_SCREENS.map((screen) => screen.route),
      ...REDIRECTS,
    ];
    expect(
      pages()
        .map((page) => page.route)
        .sort(),
    ).toEqual(known.sort());
  });

  it("intercept no route: the screen a route intercepts would show in place of one the paths check", () => {
    const intercepting = pages().filter((page) =>
      page.segments.some((part) => INTERCEPTING.test(part)),
    );
    expect(
      intercepting.map((page) => page.route),
      "a route that intercepts another needs its own screen in e2e/routes.ts",
    ).toEqual([]);
  });

  it.each(REDIRECTS)("only redirect, by the redirect of Next and no markup: %s", (route) => {
    const page = pages().find((each) => each.route === route);
    const source = readFileSync(page?.file ?? "", "utf8");
    expect(source).toMatch(
      /import\s*\{[^}]*\b(redirect|permanentRedirect)\b[^}]*\}\s*from\s*["']next\/navigation["']/,
    );
    expect(source).toMatch(/\b(redirect|permanentRedirect)\(/);
    expect(source).not.toMatch(/<\/[A-Za-z][\w.]*>|\/>/);
  });
});
