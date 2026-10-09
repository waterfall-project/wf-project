// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { loginHref, returnTarget } from "./login";

const SCREEN =
  "/projects/01926f3a-7c00-7000-8000-000000000001/revisions/01926f3a-7c00-7000-8000-000000000102/remaining?as_of=2026-05-31";

describe("the way back from the sign-in page", () => {
  it("names the screen aimed at, its query included", () => {
    const href = new URL(loginHref(SCREEN), "http://front.invalid");
    expect(href.pathname).toBe("/login");
    expect(href.searchParams.get("next")).toBe(SCREEN);
    expect(returnTarget(href.searchParams.get("next"))).toBe(SCREEN);
  });

  const ELSEWHERE: readonly (readonly [string, string | null | undefined])[] = [
    ["another site", "https://elsewhere.example/"],
    ["another site without its scheme", "//elsewhere.example/"],
    ["another site behind a backslash", "/\\elsewhere.example/"],
    ["another site behind a tab", "/\t/elsewhere.example/"],
    ["another site behind a line feed", "/\n/elsewhere.example/"],
    ["another site behind a carriage return and a backslash", "/\r\\elsewhere.example/"],
    ["an address that cannot be read", "//["],
    ["an address with a space in its host", "//a b"],
    ["an address with a bare percent in its host", "//%"],
    ["an address that cannot be read behind a tab", "/\t/[x"],
    ["a relative path", "projects"],
    ["nothing", null],
    ["no parameter", undefined],
    ["another site behind a dot segment", "/.//elsewhere.example"],
    ["another site behind an encoded dot segment", "/%2e//elsewhere.example"],
    ["another site behind a parent segment", "/a/..//elsewhere.example"],
    ["another site behind a dot segment and a backslash", "/./\\elsewhere.example"],
  ];

  it.each(ELSEWHERE)("leads home rather than to %s", (_, next) => {
    expect(returnTarget(next)).toBe("/");
  });

  it("gives back only a path that a browser resolves on this front, whatever it is given", () => {
    for (const next of [...ELSEWHERE.map(([, value]) => value), SCREEN, "/%2F%2Fx", "/a/../b"]) {
      const target = returnTarget(next);
      expect(target.startsWith("/"), String(next)).toBe(true);
      expect(new URL(target, "http://front.invalid").origin, String(next)).toBe(
        "http://front.invalid",
      );
    }
  });

  it("keeps on the front a path whose slashes are encoded", () => {
    expect(returnTarget("/%2F%2Felsewhere.example")).toBe("/%2F%2Felsewhere.example");
  });

  it("never names another site as the screen to come back to", () => {
    expect(loginHref("//elsewhere.example/")).toBe("/login?next=%2F");
  });
});
