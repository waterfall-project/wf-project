// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of the display mode, in the shell: the workstation's setting, light or dark,
 * recorded in the account like the language (WF-ADM-0040), and applied by the next render,
 * which forces the mode of the document or lets the workstation decide.
 */
"use client";

import { useTranslations } from "next-intl";

import { updateTheme } from "@/api/actions/preferences";
import { isThemePreference, THEME_PREFERENCES, type ThemePreference } from "@/theme/theme";

import { PreferenceSelector } from "./preference-selector";

/** What the selector shows: the preference of the account, `default` included. */
export interface ThemeSelectorProps {
  readonly preference: ThemePreference;
}

/** Offer the three values of the mode preference, and record the one applied. */
export function ThemeSelector({ preference }: ThemeSelectorProps) {
  const t = useTranslations();
  return (
    <PreferenceSelector
      preference={preference}
      options={THEME_PREFERENCES.map((value) => ({
        value,
        label: t(`enums.DisplayPreferences.theme.${value}`),
      }))}
      accepts={isThemePreference}
      label={t("themeSelector.label")}
      applyLabel={t("themeSelector.apply")}
      apply={updateTheme}
    />
  );
}
