// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The display mode of the interface, a preference of the account like the language
 * (WF-ADM-0040): `default` follows the workstation (`prefers-color-scheme`), `light` and
 * `dark` force a mode. The tokens of `globals.css` carry both values of every colour; the
 * shell only says which one applies, by the `data-theme` attribute of the document.
 */
import type { components } from "@/api/generated/schema";

/** The mode preference of an account: `default` follows the workstation. */
export type ThemePreference = NonNullable<components["schemas"]["DisplayPreferences"]["theme"]>;

/** A mode the document can be forced into. */
export type Theme = Exclude<ThemePreference, "default">;

/** The three values of the preference, in the order the selector offers them. */
export const THEME_PREFERENCES = [
  "default",
  "light",
  "dark",
] as const satisfies readonly ThemePreference[];

/**
 * The mode the document is forced into, for its `data-theme` attribute: none when the
 * preference follows the workstation, or when there is no account to have one.
 */
export function forcedTheme(preference: ThemePreference | undefined): Theme | undefined {
  return preference === "light" || preference === "dark" ? preference : undefined;
}

/**
 * The mode preference of an account: `default` when it never chose — the field absent —,
 * `undefined` without an account.
 */
export function themePreference(
  account: components["schemas"]["UserSelf"] | undefined,
): ThemePreference | undefined {
  return account === undefined ? undefined : (account.display_preferences?.theme ?? "default");
}
