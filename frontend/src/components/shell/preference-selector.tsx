// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of a display preference of the account, in the shell: the language
 * (WF-INTF-0160), the mode (WF-ADM-0040). Choosing changes nothing until it is applied — a
 * keyboard user goes through the options without a request at each (WCAG 3.2.2) —; applied,
 * the choice is written to the account by a server action, which renders the page again
 * with the preference it now reads — no new session.
 */
"use client";

import { useLocale, useMessages } from "next-intl";
import { type ChangeEvent, type SubmitEvent, useId, useState, useTransition } from "react";

import type { Outcome } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";

/** One value of the preference, and what the selector says of it. */
export interface PreferenceOption<V extends string> {
  readonly value: V;
  readonly label: string;
}

/** What a selector shows, and how it records the value applied. */
export interface PreferenceSelectorProps<V extends string> {
  /** The preference of the account, `default` included. */
  readonly preference: V;
  /** The values, in the order they are offered. */
  readonly options: readonly PreferenceOption<V>[];
  /** Whether a value the control gives is one of them. */
  readonly accepts: (value: string) => value is V;
  readonly label: string;
  readonly applyLabel: string;
  /** The server action that writes the value to the account. */
  readonly apply: (value: V) => Promise<Outcome<components["schemas"]["DisplayPreferences"]>>;
}

/** Offer the values of a preference, and record the one applied. */
export function PreferenceSelector<V extends string>({
  preference,
  options,
  accepts,
  label,
  applyLabel,
  apply,
}: PreferenceSelectorProps<V>) {
  const locale = useLocale();
  const messages = useMessages();
  const id = useId();
  const [chosen, choose] = useState(preference);
  // A new render may read another preference — the one just applied, or one changed from
  // another workstation —: the selector shows it. Adjusted while rendering, not by
  // remounting (a key), which would take the focus from the button just pressed.
  const [shown, show] = useState(preference);
  if (preference !== shown) {
    show(preference);
    choose(preference);
  }
  const [pending, startTransition] = useTransition();
  const [problem, setProblem] = useState<components["schemas"]["Problem"]>();

  const change = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (accepts(value)) {
      choose(value);
    }
  };

  // Nothing is disabled while the choice is written: a disabled control would lose the
  // focus. The form says it is busy.
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      const outcome = await apply(chosen);
      setProblem(outcome.problem);
    });
  };

  return (
    <form onSubmit={submit} aria-busy={pending} className="flex items-center gap-2 text-sm">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={chosen}
        onChange={change}
        className="h-8 rounded-md border border-input bg-background px-2 text-foreground"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <Button type="submit" variant="outline" size="sm">
        {applyLabel}
      </Button>
      {problem === undefined ? null : (
        <p role="alert" className="text-destructive">
          {problemMessage(problem, { locale, messages })}
        </p>
      )}
    </form>
  );
}
