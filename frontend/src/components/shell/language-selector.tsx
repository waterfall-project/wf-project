// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of the language of the interface, in the shell (WF-INTF-0160): the browser's,
 * French or English, recorded in the account and applied without a new session.
 */
"use client";

import { useTranslations } from "next-intl";

import { updateLanguage } from "@/api/actions/preferences";
import { isLanguagePreference, type LanguagePreference, PREFERENCES } from "@/i18n/locale";

import { PreferenceSelector } from "./preference-selector";

/** What the selector shows: the preference of the account, `default` included. */
export interface LanguageSelectorProps {
  readonly preference: LanguagePreference;
}

/** Offer the three values of the language preference, and record the one applied. */
export function LanguageSelector({ preference }: LanguageSelectorProps) {
  const t = useTranslations();
  return (
    <PreferenceSelector
      preference={preference}
      options={PREFERENCES.map((value) => ({
        value,
        label: t(`enums.DisplayPreferences.language.${value}`),
      }))}
      accepts={isLanguagePreference}
      label={t("languageSelector.label")}
      applyLabel={t("languageSelector.apply")}
      apply={updateLanguage}
    />
  );
}
