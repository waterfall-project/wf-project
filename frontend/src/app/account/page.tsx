// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the account (US-0320): what the account is — its name, its address, where it
 * comes from —, its display preferences, the language and the mode, which the menu of the
 * account offers too (WF-ADM-0040, WF-INTF-0160), and the way to its avatar.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { AccountDetails } from "@/components/account/account-details";
import { type Me, readMe } from "@/components/account/me";
import { PreferencesForm } from "@/components/account/preferences-form";
import { ACCOUNT_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ACCOUNT_PAGES } from "@/navigation/account";

import { screenMetadata } from "../title";

/** Title the tab with the account. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("accountMenu.account");
}

/** The ways from the account to its other pages, each with its icon. */
function OtherPages() {
  const t = useTranslations();
  return (
    <>
      {ACCOUNT_PAGES.filter(({ page }) => page !== "account").map(({ page, route, label }) => {
        const Icon = ACCOUNT_ICONS[page];
        return (
          <Link
            key={page}
            href={route}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            <Icon aria-hidden="true" />
            {t(label)}
          </Link>
        );
      })}
    </>
  );
}

/** The account, and its preferences to choose. */
function AccountScreen({ account }: { readonly account: Me }) {
  const t = useTranslations();
  return (
    <Screen>
      <PageHeader
        title={t("accountMenu.account")}
        icon={ACCOUNT_ICONS.account}
        actions={<OtherPages />}
      />
      <div className="grid max-w-3xl gap-5">
        <AccountDetails account={account} />
        <Card>
          <CardHeader>
            <CardTitle>{t("account.preferences")}</CardTitle>
            <CardDescription>{t("account.preferencesHelp")}</CardDescription>
          </CardHeader>
          <CardContent>
            <PreferencesForm
              language={account.display_preferences?.language ?? "default"}
              theme={account.display_preferences?.theme ?? "default"}
            />
          </CardContent>
        </Card>
      </div>
    </Screen>
  );
}

/** Render the screen of the account. */
export default async function AccountPage() {
  return <AccountScreen account={await readMe()} />;
}
