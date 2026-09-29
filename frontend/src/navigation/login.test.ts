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

  it.each([
    ["another site", "https://elsewhere.example/"],
    ["another site without its scheme", "//elsewhere.example/"],
    ["another site behind a backslash", "/\\elsewhere.example/"],
    ["another site behind a tab", "/\t/elsewhere.example/"],
    ["another site behind a line feed", "/\n/elsewhere.example/"],
    ["another site behind a carriage return and a backslash", "/\r\\elsewhere.example/"],
    ["a relative path", "projects"],
    ["nothing", null],
    ["no parameter", undefined],
  ])("leads home rather than to %s", (_, next) => {
    expect(returnTarget(next)).toBe("/");
  });

  it("keeps on the front a path whose slashes are encoded", () => {
    expect(returnTarget("/%2F%2Felsewhere.example")).toBe("/%2F%2Felsewhere.example");
  });

  it("never names another site as the screen to come back to", () => {
    expect(loginHref("//elsewhere.example/")).toBe("/login?next=%2F");
  });
});
