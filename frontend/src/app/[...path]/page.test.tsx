// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { existsSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { FUNCTION_GROUPS } from "@/navigation/functions";

import NoScreen from "./page";

/** The directory of the routes of the application. */
const APP = join(import.meta.dirname, "..");

/** Every route of the table of functions: each function, and each leaf with a screen of its own. */
const ROUTES = FUNCTION_GROUPS.flatMap((group) => group.functions).flatMap((fn) => [
  fn.route,
  ...(fn.leaves ?? []).map((leaf) => leaf.route),
]);

describe("an address no screen answers", () => {
  it.each(ROUTES)("is never a function of the navigation: %s has its own page", (route) => {
    const page = join(APP, ...route.split("/").filter((segment) => segment !== ""), "page.tsx");
    expect(existsSync(page), page).toBe(true);
  });

  it("is not found, the one screen an object not found leads to as well", () => {
    expect(() => NoScreen()).toThrow(
      expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
    );
  });
});
