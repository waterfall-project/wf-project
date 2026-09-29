// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of the account on the screen of its avatar: the image the account has, written into
 * the page by the server (`avatarSource`), or its initials, the default image of an account
 * without one (WF-ADM-0080).
 */
import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";

import { initials, type NamedAccount } from "./initials";

/** The account, and the image of its avatar as an address of the page, if it has one. */
export interface AvatarPictureProps {
  readonly account: NamedAccount;
  readonly source: string | undefined;
}

/** Render the avatar of the account, large. */
export function AvatarPicture({ account, source }: AvatarPictureProps) {
  const t = useTranslations("account.avatar");
  const locale = useLocale();
  if (source !== undefined) {
    return (
      <Image
        src={source}
        alt={t("current")}
        width={96}
        height={96}
        unoptimized
        className="size-24 rounded-full border object-cover"
      />
    );
  }
  return (
    <div className="flex items-center gap-4">
      <Avatar className="size-24">
        <AvatarFallback className="text-2xl">{initials(account, locale)}</AvatarFallback>
      </Avatar>
      <p className="text-sm text-muted-foreground">{t("initials")}</p>
    </div>
  );
}
