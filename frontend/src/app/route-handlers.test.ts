// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { appFiles } from "@/test/app-files";

import { OTHER_SCREENS, path, REDIRECTS, tableScreens } from "../../e2e/routes";
import { EXEMPT_HANDLERS, WARMED_HANDLERS, warmedAddresses } from "../../e2e/warm-up";

/** Whether an address is one of a route: each segment the same, or any one for a dynamic one. */
function isOf(address: string, route: string): boolean {
  const asked = address.split("/");
  const named = route.split("/");
  return (
    asked.length === named.length &&
    named.every((part, index) => /^\[[^.\]]+\]$/.test(part) || part === asked[index])
  );
}

describe("the route handlers of the application (#1145)", () => {
  it("are each warmed before the paths, or exempt from it", () => {
    const declared = [...Object.keys(WARMED_HANDLERS), ...Object.keys(EXEMPT_HANDLERS)];
    expect(
      appFiles("route")
        .map((handler) => handler.route)
        .sort(),
    ).toEqual(declared.sort());
    expect(new Set(declared).size).toBe(declared.length);
  });

  it.each(Object.entries(EXEMPT_HANDLERS))("are exempt with a reason: %s", (_route, reason) => {
    expect(reason.trim()).not.toBe("");
  });

  it.each(Object.entries(WARMED_HANDLERS))(
    "are warmed at an address of their own: %s",
    (route, address) => {
      expect(isOf(address, route)).toBe(true);
    },
  );
});

describe("the warm-up of the paths (#1145)", () => {
  it("asks once for each page of src/app and each route handler warmed, and nothing else", () => {
    const screens = new Map([
      ...tableScreens().map((screen) => [screen.route, screen.address] as const),
      ...OTHER_SCREENS.map((screen) => [screen.route, screen.address] as const),
      ...REDIRECTS.map((route) => [route, path(route)] as const),
    ]);
    const pages = appFiles("page").map((page) => screens.get(page.route) ?? page.route);
    const expected = [...pages, ...Object.values(WARMED_HANDLERS)];
    const addresses = warmedAddresses();
    expect(new Set(addresses).size).toBe(addresses.length);
    expect([...addresses].sort()).toEqual(expected.sort());
  });
});
