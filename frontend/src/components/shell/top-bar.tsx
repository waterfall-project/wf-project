// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bar of the shell, above the page: the button that folds the side bar, and where the page
 * sits (`Breadcrumbs`); at the right, the search, the button of the background tasks, and the
 * menu of the account. Without a side bar — no session —, the logo takes the place of its
 * button; without an account, there is no menu of the account.
 *
 * The search is in place, and does nothing yet: what it searches — the functions, the projects —
 * comes with the screens that list them.
 */
import { Search } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useId } from "react";

import { TasksButton } from "@/components/tasks/task-tracker";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import type { LanguagePreference } from "@/i18n/locale";
import type { ThemePreference } from "@/theme/theme";

import { AccountMenu, type MenuAccount } from "./account-menu";
import { Breadcrumbs } from "./breadcrumbs";
import { Logo } from "./logo";

/** What the bar offers: the side bar to fold, and the account and its preferences. */
export interface TopBarProps {
  /** Whether a side bar stands beside the page, which the bar folds and unfolds. */
  readonly navigable: boolean;
  readonly account: MenuAccount | undefined;
  readonly language: LanguagePreference | undefined;
  readonly theme: ThemePreference | undefined;
}

/** Render the bar of the shell. */
export function TopBar({ navigable, account, language, theme }: TopBarProps) {
  const t = useTranslations();
  const soon = useId();
  return (
    <header className="flex min-h-13 flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-2">
      {navigable ? (
        <SidebarTrigger />
      ) : (
        <Link href="/" className="rounded-md">
          <Logo theme={theme} />
        </Link>
      )}
      <Separator orientation="vertical" className="h-4!" />
      <Breadcrumbs />
      <div role="search" className="relative hidden w-64 md:block">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          type="search"
          aria-label={t("search.label")}
          aria-describedby={soon}
          placeholder={t("search.placeholder")}
          className="pl-8"
        />
        <p id={soon} className="sr-only">
          {t("search.comingSoon")}
        </p>
      </div>
      <TasksButton />
      {account === undefined ? null : (
        <AccountMenu account={account} language={language} theme={theme} />
      )}
    </header>
  );
}
