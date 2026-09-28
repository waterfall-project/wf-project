// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of the language of the interface, in the shell (WF-INTF-0160): the browser's,
 * French or English. Choosing changes nothing until it is applied — a keyboard user goes
 * through the options without a request at each (WCAG 3.2.2) —; applied, the choice is
 * written to the account by a server action, which renders the page again in the language
 * it now resolves to — no new session.
 */
"use client";

import { useLocale, useMessages, useTranslations } from "next-intl";
import { type ChangeEvent, type SubmitEvent, useId, useState, useTransition } from "react";

import { updateLanguage } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import { isLanguagePreference, type LanguagePreference, PREFERENCES } from "@/i18n/locale";
import { problemMessage } from "@/i18n/problem";

/** What the selector shows: the preference of the account, `default` included. */
export interface LanguageSelectorProps {
  readonly preference: LanguagePreference;
}

/** Offer the three values of the language preference, and record the one applied. */
export function LanguageSelector({ preference }: LanguageSelectorProps) {
  const t = useTranslations();
  const locale = useLocale();
  const messages = useMessages();
  const id = useId();
  const [chosen, choose] = useState(preference);
  const [pending, startTransition] = useTransition();
  const [problem, setProblem] = useState<components["schemas"]["Problem"]>();

  const change = (event: ChangeEvent<HTMLSelectElement>) => {
    const language = event.target.value;
    if (isLanguagePreference(language)) {
      choose(language);
    }
  };

  // Nothing is disabled while the choice is written: a disabled control would lose the
  // focus. The form says it is busy.
  const apply = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      const outcome = await updateLanguage(chosen);
      setProblem(outcome.problem);
    });
  };

  return (
    <form onSubmit={apply} aria-busy={pending}>
      <label htmlFor={id}>{t("languageSelector.label")}</label>
      <select id={id} value={chosen} onChange={change}>
        {PREFERENCES.map((value) => (
          <option key={value} value={value}>
            {t(`enums.DisplayPreferences.language.${value}`)}
          </option>
        ))}
      </select>
      <button type="submit">{t("languageSelector.apply")}</button>
      {problem === undefined ? null : (
        <p role="alert">{problemMessage(problem, { locale, messages })}</p>
      )}
    </form>
  );
}
