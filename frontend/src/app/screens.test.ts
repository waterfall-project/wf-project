// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { appFiles } from "@/test/app-files";

import { OTHER_SCREENS, REDIRECTS, tableScreens } from "../../e2e/routes";

/** A segment of a route that intercepts another (`(.)x`, `(..)x`, `(...)x`). */
const INTERCEPTING = /^\(\.{1,3}\)/;

describe("the pages of the application", () => {
  it("are each a screen the paths of accessibility check, or a page that only redirects", () => {
    const known = [
      ...tableScreens().map((screen) => screen.route),
      ...OTHER_SCREENS.map((screen) => screen.route),
      ...REDIRECTS,
    ];
    expect(
      appFiles("page")
        .map((page) => page.route)
        .sort(),
    ).toEqual(known.sort());
  });

  it("intercept no route: the screen a route intercepts would show in place of one the paths check", () => {
    const intercepting = appFiles("page").filter((page) =>
      page.segments.some((part) => INTERCEPTING.test(part)),
    );
    expect(
      intercepting.map((page) => page.route),
      "a route that intercepts another needs its own screen in e2e/routes.ts",
    ).toEqual([]);
  });

  it.each(REDIRECTS)("only redirect, by the redirect of Next and no markup: %s", (route) => {
    const page = appFiles("page").find((each) => each.route === route);
    const source = readFileSync(page?.file ?? "", "utf8");
    expect(source).toMatch(
      /import\s*\{[^}]*\b(redirect|permanentRedirect)\b[^}]*\}\s*from\s*["']next\/navigation["']/,
    );
    expect(source).toMatch(/\b(redirect|permanentRedirect)\(/);
    expect(source).not.toMatch(/<\/[A-Za-z][\w.]*>|\/>/);
  });
});
