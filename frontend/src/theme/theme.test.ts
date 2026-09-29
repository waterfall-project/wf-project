// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { forcedTheme, THEME_PREFERENCES, themePreference } from "./theme";

type Session = components["schemas"]["Session"];

/** The account of a session of the contract. */
function account(name: string) {
  return (example(name) as Session).user;
}

describe("the display mode", () => {
  it("offers the three values of the preference of the contract", () => {
    expect(THEME_PREFERENCES).toEqual(["default", "light", "dark"]);
  });

  it("forces the document into light or dark, and lets the workstation decide otherwise", () => {
    expect(forcedTheme("light")).toBe("light");
    expect(forcedTheme("dark")).toBe("dark");
    expect(forcedTheme("default")).toBeUndefined();
    expect(forcedTheme(undefined)).toBeUndefined();
  });

  it("reads the preference of the account, the workstation's when it never chose", () => {
    expect(themePreference(account("session_dark"))).toBe("dark");
    expect(themePreference(account("session"))).toBe("default");
    expect(themePreference(account("session_without_preferences"))).toBe("default");
    expect(themePreference(undefined)).toBeUndefined();
  });
});
