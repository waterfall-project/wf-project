// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The menu of the account, at the right of the bar of the shell: the button shows the avatar of
 * the user, and opens the name and the address of the account; its display preferences — the
 * language of the interface (WF-INTF-0160) and the mode (WF-ADM-0040) —; the pages of the
 * account (`ACCOUNT_PAGES`); and the way out.
 *
 * A preference is a choice among its values, in a menu within the menu: moving through them
 * changes nothing — a keyboard user goes through the options without a request at each (WCAG
 * 3.2.2) —; choosing one writes it to the account by a server action, which renders the page
 * again with the preference it now reads — no new session. The outcome is told under the bar,
 * once the menu has closed: a refusal, the way to sign in again, the API out of reach.
 *
 * Signing out waits for the connection (US-0320), and for EP-03 which opens real sessions: the
 * entry is shown, unavailable.
 */
"use client";

import { ChevronDown, Languages, LogOut, type LucideIcon, SunMoon } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useId, useState, useTransition } from "react";

import { updateLanguage, updateTheme } from "@/api/actions/preferences";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { type LanguagePreference, PREFERENCES } from "@/i18n/locale";
import { ACCOUNT_PAGES } from "@/navigation/account";
import { THEME_PREFERENCES, type ThemePreference } from "@/theme/theme";

import { ACCOUNT_ICONS } from "./function-display";

/** What the menu shows of the account: the name and the address of the user. */
export type MenuAccount = Pick<
  components["schemas"]["Session"]["user"],
  "first_name" | "last_name" | "email"
>;

/** The account, and its display preferences: `default` included. */
export interface AccountMenuProps {
  readonly account: MenuAccount;
  readonly language: LanguagePreference | undefined;
  readonly theme: ThemePreference | undefined;
}

/** The outcome of writing a preference to the account. */
type Written = Outcome<components["schemas"]["DisplayPreferences"]>;

/** The initials of a name, as the avatar shows them: a letter of each part. */
function initials(account: MenuAccount, locale: string): string {
  const first = (text: string) => Array.from(text.trim())[0] ?? "";
  return `${first(account.first_name)}${first(account.last_name)}`.toLocaleUpperCase(locale);
}

/** What a preference offers, and how its choice is written. */
interface PreferenceProps<V extends string> {
  readonly icon: LucideIcon;
  readonly label: string;
  /** The preference of the account, as the page was rendered with it. */
  readonly preference: V;
  /** The values, in the order they are offered, each with what the menu says of it. */
  readonly options: readonly { readonly value: V; readonly label: string }[];
  readonly choose: (value: V) => void;
}

/**
 * A preference: its name and the value of the account, opening on its values. The menu closes
 * on a choice, and opens again on what the account holds: the value applied, which the page
 * rendered again reads, or the value it kept when the API refused the choice.
 */
function Preference<V extends string>({
  icon: Icon,
  label,
  preference,
  options,
  choose,
}: PreferenceProps<V>) {
  const current = options.find((option) => option.value === preference);
  return (
    <DropdownMenuSub>
      <DropdownMenuSubTrigger>
        <Icon aria-hidden="true" />
        <span className="flex-1">{label}</span>
        <span className="text-xs whitespace-nowrap text-muted-foreground">{current?.label}</span>
      </DropdownMenuSubTrigger>
      <DropdownMenuSubContent>
        <DropdownMenuRadioGroup value={preference}>
          {options.map((option) => (
            <DropdownMenuRadioItem
              key={option.value}
              value={option.value}
              onSelect={() => {
                choose(option.value);
              }}
            >
              {option.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuSubContent>
    </DropdownMenuSub>
  );
}

/** The preferences of the account the page was rendered with, each a choice. */
function Preferences({
  language,
  theme,
  write,
}: Omit<AccountMenuProps, "account"> & {
  readonly write: (apply: () => Promise<Written>) => void;
}) {
  const t = useTranslations();
  const label = useId();
  if (language === undefined && theme === undefined) {
    return null;
  }
  return (
    <>
      <DropdownMenuSeparator />
      <DropdownMenuGroup aria-labelledby={label}>
        <DropdownMenuLabel id={label} className="text-xs text-muted-foreground">
          {t("accountMenu.preferences")}
        </DropdownMenuLabel>
        {language === undefined ? null : (
          <Preference
            icon={Languages}
            label={t("languageSelector.label")}
            preference={language}
            options={PREFERENCES.map((value) => ({
              value,
              label: t(`enums.DisplayPreferences.language.${value}`),
            }))}
            choose={(value) => {
              write(() => updateLanguage(value));
            }}
          />
        )}
        {theme === undefined ? null : (
          <Preference
            icon={SunMoon}
            label={t("themeSelector.label")}
            preference={theme}
            options={THEME_PREFERENCES.map((value) => ({
              value,
              label: t(`enums.DisplayPreferences.theme.${value}`),
            }))}
            choose={(value) => {
              write(() => updateTheme(value));
            }}
          />
        )}
      </DropdownMenuGroup>
    </>
  );
}

/** Render the button of the avatar, its menu, and the outcome of the last preference written. */
export function AccountMenu({ account, language, theme }: AccountMenuProps) {
  const t = useTranslations();
  const locale = useLocale();
  const [pending, startTransition] = useTransition();
  const [outcome, setOutcome] = useState<Written>();
  const name = t("accountMenu.name", { first: account.first_name, last: account.last_name });
  const mark = initials(account, locale);
  const write = (apply: () => Promise<Written>) => {
    startTransition(async () => {
      setOutcome(await apply());
    });
  };
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            className="h-9 gap-1.5 px-1"
            aria-label={t("accountMenu.label", { name })}
            aria-busy={pending}
          >
            <Avatar>
              <AvatarFallback>{mark}</AvatarFallback>
            </Avatar>
            <ChevronDown aria-hidden="true" className="text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-80">
          <DropdownMenuLabel className="flex items-center gap-2.5 font-normal">
            <Avatar className="size-9">
              <AvatarFallback>{mark}</AvatarFallback>
            </Avatar>
            <span className="grid min-w-0">
              <span className="truncate font-semibold">{name}</span>
              <span className="truncate text-xs text-muted-foreground">{account.email}</span>
            </span>
          </DropdownMenuLabel>
          <Preferences language={language} theme={theme} write={write} />
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            {ACCOUNT_PAGES.map(({ page, route, label }) => {
              const Icon = ACCOUNT_ICONS[page];
              return (
                <DropdownMenuItem key={page} asChild>
                  <Link href={route}>
                    <Icon aria-hidden="true" />
                    {t(label)}
                  </Link>
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled>
            <LogOut aria-hidden="true" />
            {t("accountMenu.signOut")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <div className="order-last basis-full empty:hidden">
        <OutcomeNotice
          outcome={outcome}
          onClear={() => {
            setOutcome(undefined);
          }}
        />
      </div>
    </>
  );
}
