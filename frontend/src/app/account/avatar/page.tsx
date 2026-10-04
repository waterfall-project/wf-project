// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of the account (US-0320, WF-ADM-0080): the image it has — read by the server and
 * written into the page (`avatarSource`) — or its initials, and the form that puts, replaces or
 * withdraws it, bounded by the size the installation admits (`getInstallation`, §4.4.1).
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { AvatarForm } from "@/components/account/avatar-form";
import { AvatarPicture } from "@/components/account/avatar-picture";
import { avatarSource } from "@/components/account/avatar-source";
import { type Me, readMe } from "@/components/account/me";
import { ACCOUNT_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { screenMetadata } from "../../title";

/** Title the tab with the avatar. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("accountMenu.avatar");
}

/** The avatar of the account, and the form that changes it. */
function AvatarScreen({
  account,
  source,
  maxBytes,
}: {
  readonly account: Me;
  readonly source: string | undefined;
  readonly maxBytes: number;
}) {
  const t = useTranslations();
  return (
    <Screen>
      <PageHeader title={t("accountMenu.avatar")} icon={ACCOUNT_ICONS.avatar} />
      <Card className="max-w-3xl">
        <CardHeader>
          <CardTitle>{t("account.avatar.current")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5">
          <AvatarPicture account={account} source={source} />
          <AvatarForm hasAvatar={account.has_avatar === true} maxBytes={maxBytes} />
        </CardContent>
      </Card>
    </Screen>
  );
}

/** Render the avatar of the account. */
export default async function AvatarPage() {
  const [account, installation] = await Promise.all([
    readMe(),
    readOrFail("getInstallation", () => serverClient().GET("/installation")),
  ]);
  const source = account.has_avatar === true ? await avatarSource(account.user_id) : undefined;
  return (
    <AvatarScreen account={account} source={source} maxBytes={installation.avatar_max_bytes} />
  );
}
