// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The display preferences on the screen of the account (WF-ADM-0040): the language of the
 * interface (WF-INTF-0160) and the mode, each a choice among its values — the same fields of the
 * account the menu of the account writes one at a time —, and the patterns of the series of the
 * charts, a switch off until the account asks for them (WF-IHM-0070), which every chart and the
 * image it exports follow; all recorded together when the user saves them
 * (`updateMyPreferences`). Moving through the values sends nothing; saving renders the page again
 * with what the account now holds, without signing in again.
 *
 * The page rendered again gives the preferences the account holds: a choice made in the menu
 * meanwhile shows here too. While a choice is recorded, the values are held: none chosen then
 * would be lost without a word.
 */
"use client";

import { ChartColumnStacked, Languages, type LucideIcon, Save, SunMoon } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState } from "react";

import { updateDisplay } from "@/api/actions/preferences";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice, useReadAnew } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { type LanguagePreference, PREFERENCES } from "@/i18n/locale";
import { THEME_PREFERENCES, type ThemePreference } from "@/theme/theme";

import { DoneNotice } from "@/components/notices/done-notice";
import { WAITING } from "./form";

/** The preferences the account holds: `default` when it never chose, no patterns unless asked. */
export interface PreferencesFormProps {
  readonly language: LanguagePreference;
  readonly theme: ThemePreference;
  /** Whether the series of the charts are drawn with their patterns (`chart_series_patterns`). */
  readonly patterns: boolean;
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

/** Render the switch of the patterns of the series of the charts, its effect said under it. */
function PatternsSwitch({
  checked,
  onChange,
}: {
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
}) {
  const t = useTranslations("account.chartPatterns");
  const id = useId();
  return (
    <fieldset className="grid gap-2 sm:col-span-2">
      <legend className="mb-2 flex items-center gap-2 text-sm font-medium">
        <ChartColumnStacked aria-hidden="true" className="size-4 text-muted-foreground" />
        {t("legend")}
      </legend>
      <div className="flex items-center gap-2">
        <Switch
          id={id}
          checked={checked}
          aria-describedby={`${id}-help`}
          onCheckedChange={onChange}
        />
        <Label htmlFor={id} className="font-normal">
          {t("label")}
        </Label>
      </div>
      <p id={`${id}-help`} className="text-sm text-muted-foreground">
        {t("help")}
      </p>
    </fieldset>
  );
}

/** Render the preferences of the account, and record them when saved. */
export function PreferencesForm({ language, theme, patterns }: PreferencesFormProps) {
  const t = useTranslations();
  const [read, setRead] = useState({ language, theme, patterns });
  const [chosen, setChosen] = useState({ language, theme, patterns });
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // Busy from the press to the answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page, the tasks of the
  // shell's tracker among them (#1484).
  const [busy, setBusy] = useState(false);
  // A write lost once sent: the form waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  const waiting = busy || reading;
  // A link clicked while the choice is recorded waits for it, and is not followed when refused.
  const held = useHeldCommand();
  // The page rendered again holds other preferences — saved here, or chosen in the menu —: the
  // choice starts again from them.
  if (read.language !== language || read.theme !== theme || read.patterns !== patterns) {
    setRead({ language, theme, patterns });
    setChosen({ language, theme, patterns });
  }
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (waiting) {
      return;
    }
    // The language only when it changed: the API reports it to the identity provider (#877).
    const changed = chosen.language === read.language ? {} : { language: chosen.language };
    setBusy(true);
    const display = { theme: chosen.theme, chart_series_patterns: chosen.patterns, ...changed };
    void held(updateDisplay(display)).then((outcome) => {
      setBusy(false);
      setOutcome(outcome);
    });
  };
  return (
    <form aria-busy={waiting} onSubmit={submit} className="grid gap-5">
      {/* Held while the choice is recorded: a value chosen meanwhile would be lost unsaid. */}
      <fieldset disabled={waiting} className="grid gap-6 sm:grid-cols-2">
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
        <PatternsSwitch
          checked={chosen.patterns}
          onChange={(checked) => {
            setChosen({ ...chosen, patterns: checked });
          }}
        />
      </fieldset>
      <OutcomeNotice
        outcome={outcome}
        reading={reading}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <DoneNotice title={outcome?.kind === "done" ? t("account.saved") : undefined} of={outcome} />
      <div>
        <Button type="submit" aria-disabled={waiting} className={WAITING}>
          <Save aria-hidden="true" />
          {t("account.save")}
        </Button>
      </div>
    </form>
  );
}
