// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The shell every page renders in: the texts of the language of the request, handed to the
 * client components; the side bar, with the logo, the project open and the navigation among the
 * functions the session may read (WF-IHM-0010); the bar above the page, with where it sits, the
 * search, the background tasks and the menu of the account, where the language and the mode are
 * chosen.
 *
 * Without an account there is no preference to write, and no permission to read a function:
 * the shell then offers neither the menu of the account nor the side bar — the browser and the
 * workstation decide the language and the mode. When the session cannot be read at all — the
 * API out of reach —, the navigation still offers the status screen (WF-ADM-0130).
 *
 * The shell follows the background tasks the screens start, in a panel under its bar, whatever
 * screen the user goes to meanwhile (WF-IHM-0080).
 *
 * The way in — the sign-in page, the password forgotten — stands outside it: the texts and the
 * mode still, but neither side bar, nor bar, nor tasks (`ShellFrame`).
 */
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { TaskTracker } from "@/components/tasks/task-tracker";
import { SidebarProvider } from "@/components/ui/sidebar";
import { CATALOGUES } from "@/i18n/catalogues";
import { TIME_ZONE } from "@/i18n/format";
import type { LanguagePreference, Locale } from "@/i18n/locale";
import type { ThemePreference } from "@/theme/theme";

import type { MenuAccount } from "./account-menu";
import { Navigation, type NavigationProps } from "./navigation";
import { ShellFrame } from "./shell-frame";
import { ShownProjectProvider } from "./shown-project";
import { TopBar } from "./top-bar";

/**
 * The language of the request; the account it came from, its preferences and the permissions of
 * its session — `undefined` without an account, `unreadable` when the session could not be read
 * —; the address of the last project context the cookie keeps; whether the side bar was left
 * unfolded; and the page.
 */
export interface ShellProps {
  readonly locale: Locale;
  readonly account: MenuAccount | undefined;
  readonly preference: LanguagePreference | undefined;
  readonly theme: ThemePreference | undefined;
  readonly permissions: NavigationProps["permissions"] | undefined;
  readonly remembered: string | undefined;
  readonly sidebarOpen: boolean;
  readonly children: ReactNode;
}

/** Render a page inside the shell, in the language of the request. */
export function Shell({
  locale,
  account,
  preference,
  theme,
  permissions,
  remembered,
  sidebarOpen,
  children,
}: ShellProps) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone={TIME_ZONE}>
      <TaskTracker>
        <ShownProjectProvider>
          <SidebarProvider defaultOpen={sidebarOpen}>
            <ShellFrame
              navigation={
                permissions === undefined ? null : (
                  <Navigation permissions={permissions} remembered={remembered} theme={theme} />
                )
              }
              bar={
                <TopBar
                  navigable={permissions !== undefined}
                  account={account}
                  language={preference}
                  theme={theme}
                />
              }
            >
              {children}
            </ShellFrame>
          </SidebarProvider>
        </ShownProjectProvider>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}
