// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of the language of the interface, in the shell (WF-INTF-0160): the browser's,
 * French or English. The choice is written to the account by a server action, which renders
 * the page again in the language it now resolves to — no new session.
 */
"use client";

import { useLocale, useMessages, useTranslations } from "next-intl";
import { type ChangeEvent, useId, useOptimistic, useState, useTransition } from "react";

import { updateLanguage } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import { isLanguagePreference, type LanguagePreference, PREFERENCES } from "@/i18n/locale";
import { problemMessage } from "@/i18n/problem";

/** What the selector shows: the preference of the account, `default` included. */
export interface LanguageSelectorProps {
  readonly preference: LanguagePreference;
}

/** Offer the three values of the language preference, and record the one chosen. */
export function LanguageSelector({ preference }: LanguageSelectorProps) {
  const t = useTranslations();
  const locale = useLocale();
  const messages = useMessages();
  const id = useId();
  // The choice shows at once, and the preference the next render reads replaces it.
  const [shown, show] = useOptimistic(preference);
  const [pending, startTransition] = useTransition();
  const [problem, setProblem] = useState<components["schemas"]["Problem"]>();

  const choose = (event: ChangeEvent<HTMLSelectElement>) => {
    const language = event.target.value;
    if (!isLanguagePreference(language)) {
      return;
    }
    startTransition(async () => {
      show(language);
      const outcome = await updateLanguage(language);
      setProblem(outcome.problem);
    });
  };

  return (
    <div>
      <label htmlFor={id}>{t("languageSelector.label")}</label>
      <select id={id} value={shown} disabled={pending} onChange={choose}>
        {PREFERENCES.map((value) => (
          <option key={value} value={value}>
            {t(`enums.DisplayPreferences.language.${value}`)}
          </option>
        ))}
      </select>
      {problem === undefined ? null : (
        <p role="alert">{problemMessage(problem, { locale, messages })}</p>
      )}
    </div>
  );
}
