// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The change of the password (US-0320), for a local account only: an account of the directory or
 * of the identity provider has no password in Waterfall, and the API would refuse to change it
 * (WF-ADM-0140) — the screen says where it is changed rather than offer the form.
 */
import { Info } from "lucide-react";
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { type Me, readMe } from "@/components/account/me";
import { PasswordForm } from "@/components/account/password-form";
import { ACCOUNT_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";

import { screenMetadata } from "../../title";

/** Title the tab with the change of the password. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("accountMenu.password");
}

/** The form of a local account, or where the password of another is changed. */
function PasswordScreen({ account }: { readonly account: Me }) {
  const t = useTranslations();
  return (
    <Screen>
      <PageHeader title={t("accountMenu.password")} icon={ACCOUNT_ICONS.password} />
      <div className="max-w-3xl">
        {account.origin === "local" ? (
          <Card>
            <CardContent>
              <PasswordForm />
            </CardContent>
          </Card>
        ) : (
          <Alert>
            <Info aria-hidden="true" />
            <AlertTitle className="font-normal">{t("account.password.external")}</AlertTitle>
          </Alert>
        )}
      </div>
    </Screen>
  );
}

/** Render the change of the password. */
export default async function PasswordPage() {
  return <PasswordScreen account={await readMe()} />;
}
