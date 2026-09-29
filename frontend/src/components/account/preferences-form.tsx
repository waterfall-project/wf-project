// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The display preferences on the screen of the account (WF-ADM-0040): the language of the
 * interface (WF-INTF-0160) and the mode, each a choice among its values, recorded together when
 * the user saves them — the same fields of the account the menu of the account writes one at a
 * time (`updateMyPreferences`). Moving through the values sends nothing; saving renders the page
 * again with what the account now holds, without signing in again.
 *
 * The page rendered again gives the preferences the account holds: a choice made in the menu
 * meanwhile shows here too. While a choice is recorded, the values are held: none chosen then
 * would be lost without a word.
 */
"use client";

import { Languages, type LucideIcon, Save, SunMoon } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { updateDisplay } from "@/api/actions/preferences";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { type LanguagePreference, PREFERENCES } from "@/i18n/locale";
import { THEME_PREFERENCES, type ThemePreference } from "@/theme/theme";

import { DoneNotice } from "./done-notice";
import { WAITING } from "./form";

/** The preferences the account holds: `default` when it never chose. */
export interface PreferencesFormProps {
  readonly language: LanguagePreference;
  readonly theme: ThemePreference;
}

/** A choice among the values of a preference, named by its legend. */
interface ChoiceProps<V extends string> {
  readonly icon: LucideIcon;
  readonly legend: string;
  readonly value: V;
  readonly options: readonly { readonly value: V; readonly label: string }[];
  readonly onChange: (value: V) => void;
}

/** Render the choice of a preference. */
function Choice<V extends string>({
  icon: Icon,
  legend,
  value,
  options,
  onChange,
}: ChoiceProps<V>) {
  const id = useId();
  return (
    <fieldset className="grid gap-2">
      <legend id={`${id}-legend`} className="mb-2 flex items-center gap-2 text-sm font-medium">
        <Icon aria-hidden="true" className="size-4 text-muted-foreground" />
        {legend}
      </legend>
      <RadioGroup
        aria-labelledby={`${id}-legend`}
        value={value}
        onValueChange={(chosen) => {
          const option = options.find((candidate) => candidate.value === chosen);
          if (option !== undefined) {
            onChange(option.value);
          }
        }}
      >
        {options.map((option) => (
          <div key={option.value} className="flex items-center gap-2">
            <RadioGroupItem id={`${id}-${option.value}`} value={option.value} />
            <Label htmlFor={`${id}-${option.value}`} className="font-normal">
              {option.label}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </fieldset>
  );
}

/** Render the preferences of the account, and record them when saved. */
export function PreferencesForm({ language, theme }: PreferencesFormProps) {
  const t = useTranslations();
  const [held, setHeld] = useState({ language, theme });
  const [chosen, setChosen] = useState({ language, theme });
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  // The page rendered again holds other preferences — saved here, or chosen in the menu —: the
  // choice starts again from them.
  if (held.language !== language || held.theme !== theme) {
    setHeld({ language, theme });
    setChosen({ language, theme });
  }
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    startTransition(async () => {
      setOutcome(await updateDisplay(chosen));
    });
  };
  return (
    <form aria-busy={pending} onSubmit={submit} className="grid gap-5">
      {/* Held while the choice is recorded: a value chosen meanwhile would be lost unsaid. */}
      <fieldset disabled={pending} className="grid gap-6 sm:grid-cols-2">
        <Choice
          icon={Languages}
          legend={t("languageSelector.label")}
          value={chosen.language}
          options={PREFERENCES.map((value) => ({
            value,
            label: t(`enums.DisplayPreferences.language.${value}`),
          }))}
          onChange={(value) => {
            setChosen({ ...chosen, language: value });
          }}
        />
        <Choice
          icon={SunMoon}
          legend={t("themeSelector.label")}
          value={chosen.theme}
          options={THEME_PREFERENCES.map((value) => ({
            value,
            label: t(`enums.DisplayPreferences.theme.${value}`),
          }))}
          onChange={(value) => {
            setChosen({ ...chosen, theme: value });
          }}
        />
      </fieldset>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <DoneNotice title={outcome?.kind === "done" ? t("account.saved") : undefined} />
      <div>
        <Button type="submit" aria-disabled={pending} className={WAITING}>
          <Save aria-hidden="true" />
          {t("account.save")}
        </Button>
      </div>
    </form>
  );
}
