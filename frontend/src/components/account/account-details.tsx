// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the account says of it: the name and the address of the user, as the API
 * gives them, and where the account comes from — created in Waterfall, imported from the
 * directory, or created by the identity provider (WF-ADM-0050).
 */
import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { Me } from "./me";

/** Render the details of the account. */
export function AccountDetails({ account }: { readonly account: Me }) {
  const t = useTranslations();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.details")}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted-foreground">{t("account.name")}</dt>
          <dd>{t("accountMenu.name", { first: account.first_name, last: account.last_name })}</dd>
          <dt className="text-muted-foreground">{t("account.email")}</dt>
          <dd>{account.email}</dd>
          <dt className="text-muted-foreground">{t("account.origin")}</dt>
          <dd>{t(`enums.UserOrigin.${account.origin}`)}</dd>
        </dl>
      </CardContent>
    </Card>
  );
}
