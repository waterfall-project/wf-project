// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { forcedTheme, isThemePreference, THEME_PREFERENCES, themePreference } from "./theme";

type Account = components["schemas"]["UserSelf"];

describe("the display mode", () => {
  it("offers the three values of the preference of the contract", () => {
    expect(THEME_PREFERENCES).toEqual(["default", "light", "dark"]);
    expect(THEME_PREFERENCES.every(isThemePreference)).toBe(true);
    expect(["", "Dark", "auto", undefined].some(isThemePreference)).toBe(false);
  });

  it("forces the document into light or dark, and lets the workstation decide otherwise", () => {
    expect(forcedTheme("light")).toBe("light");
    expect(forcedTheme("dark")).toBe("dark");
    expect(forcedTheme("default")).toBeUndefined();
    expect(forcedTheme(undefined)).toBeUndefined();
  });

  it("reads the preference of the account, the workstation's when it never chose", () => {
    expect(themePreference(example("me_dark") as Account)).toBe("dark");
    expect(themePreference(example("me") as Account)).toBe("default");
    expect(themePreference(example("me_without_preferences") as Account)).toBe("default");
    expect(themePreference(undefined)).toBeUndefined();
  });
});
