// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pages of the account whose screens are still to come (`ACCOUNT_PAGES`): the menu of the
 * account leads to each from the shell on, and the lot of a screen (US-0320) replaces it by a
 * page of its own — a route written out wins over this one. An address under `/account` that
 * leads to no page of the account is not found.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ComingSoon } from "@/components/shell/coming-soon";
import { ACCOUNT_ICONS } from "@/components/shell/function-display";
import { findAccountPage } from "@/navigation/account";

import { screenMetadata } from "../../title";

/** The segments of the address after `/account`, none for the account itself. */
export interface AccountParams {
  readonly section?: readonly string[];
}

/** The page of the account the segments lead to. */
function pageOf({ section = [] }: AccountParams) {
  return findAccountPage(["/account", ...section].join("/"));
}

/** Title the tab with the page of the account. */
export async function generateMetadata({
  params,
}: {
  params: Promise<AccountParams>;
}): Promise<Metadata> {
  const entry = pageOf(await params);
  return entry === undefined ? {} : screenMetadata(entry.label);
}

/** Render the page of the account the address leads to, whose screen is to come. */
export default async function AccountPageToCome({ params }: { params: Promise<AccountParams> }) {
  const entry = pageOf(await params);
  if (entry === undefined) {
    notFound();
  }
  return <ComingSoon label={entry.label} icon={ACCOUNT_ICONS[entry.page]} />;
}
