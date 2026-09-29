// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of the account on the screen of its avatar: the image the account has, written into
 * the page by the server (`avatarSource`), or its initials, the default image of an account
 * without one (WF-ADM-0080) — shown too while the image loads.
 */
import { useLocale, useTranslations } from "next-intl";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

import { initials, type NamedAccount } from "./initials";

/** The account, and the image of its avatar as an address of the page, if it has one. */
export interface AvatarPictureProps {
  readonly account: NamedAccount;
  readonly source: string | undefined;
}

/** Render the avatar of the account, large, named after the account. */
export function AvatarPicture({ account, source }: AvatarPictureProps) {
  const t = useTranslations();
  const locale = useLocale();
  const name = t("accountMenu.name", { first: account.first_name, last: account.last_name });
  return (
    <div className="flex items-center gap-4">
      <Avatar className="size-24 border">
        {source === undefined ? null : <AvatarImage src={source} alt={name} />}
        <AvatarFallback className="text-2xl">{initials(account, locale)}</AvatarFallback>
      </Avatar>
      {source === undefined ? (
        <p className="text-sm text-muted-foreground">{t("account.avatar.initials")}</p>
      ) : null}
    </div>
  );
}
