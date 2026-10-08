// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the accounts by their state (WF-IHM-0130): the link that hides the deactivated
 * accounts, or shows them again — they are listed by default (WF-ADM-0060). It only changes the
 * address, under the name of the contract (`include_inactive=false`), back to the first page; the
 * server filters. A link, which works before the page is hydrated, and goes on from the address
 * last asked (`usePendingLink`): a sort or a filter under way is kept.
 */
"use client";

import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { filterHref } from "@/components/grid/filters";
import { usePendingLink } from "@/components/grid/pending-address";
import { OFFSET } from "@/components/grid/query";
import { buttonVariants } from "@/components/ui/button";

import { INCLUDE_INACTIVE } from "./user-address";

/** The link that hides the deactivated accounts, or shows them again. */
export function AccountStateSwitch({ shown }: { readonly shown: boolean }) {
  const t = useTranslations("admin.users");
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) =>
    filterHref(pathname, query, INCLUDE_INACTIVE, shown ? "false" : undefined, OFFSET),
  );
  return (
    <Link
      href={href}
      onClick={onClick}
      scroll={false}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      {shown ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
      {shown ? t("hideInactive") : t("showInactive")}
    </Link>
  );
}
