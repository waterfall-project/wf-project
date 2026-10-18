// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The screen of the account (US-0320, US-0400): what the account is — its name, its address, where
 * it comes from —, its display preferences, the language and the mode, which the menu of the
 * account offers too (WF-ADM-0040, WF-INTF-0160), the way to its avatar, and, for a local account,
 * the way to its page at the identity provider, which holds its password (WF-ADM-0140): an account
 * of the directory or of an external provider has none there to change.
 */
import { KeyRound } from "lucide-react";
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
import { realmAccountPage } from "@/session/settings";

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

/** The way of a local account to its page at the realm, where its password is set and changed. */
function SignInCard({ address }: { readonly address: string }) {
  const t = useTranslations("account");
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("signIn")}</CardTitle>
        <CardDescription>{t("signInHelp")}</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Another site, in another tab: the screen of the account stays where it is. */}
        <a
          href={address}
          target="_blank"
          rel="noreferrer"
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          <KeyRound aria-hidden="true" />
          {t("realmPage")}
        </a>
      </CardContent>
    </Card>
  );
}

/** The account, its preferences to choose, and the page of a local account at the realm. */
function AccountScreen({
  account,
  realmPage,
}: {
  readonly account: Me;
  readonly realmPage: string | undefined;
}) {
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
        {account.origin === "local" && realmPage !== undefined ? (
          <SignInCard address={realmPage} />
        ) : null}
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
  return <AccountScreen account={await readMe()} realmPage={realmAccountPage()} />;
}
