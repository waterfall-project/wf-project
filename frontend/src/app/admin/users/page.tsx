// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The accounts of the installation (FBS-1.1, US-0250), outside any project: a page of the list the
 * server pages, deactivated accounts included — they stay listed, and may be reactivated
 * (WF-ADM-0060) —, each with its access roles and the node it is attached to, named by the server.
 * Read only: no screen offers to delete an account, and the forms belong to the epic of the
 * administration. A read the API refuses, or cannot answer, is thrown for the pages of the shell to
 * say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { UserList } from "@/components/admin/account-lists";
import { ListPages, type ListPage, offsetOf } from "@/components/admin/list-pages";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { functionOf } from "@/navigation/functions";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.users");
}

/** The title of the screen, and how many accounts the list holds. */
function UsersHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader title={t("users")} icon={FUNCTION_ICONS.users} density={FUNCTION_DENSITY.users} />
  );
}

/** How many accounts the list holds, and the way through its pages. */
function UserPages({ page, shown }: { readonly page: ListPage; readonly shown: number }) {
  const t = useTranslations("admin.users");
  return (
    <ListPages
      path={functionOf("users").route}
      page={page}
      shown={shown}
      count={t("count", { count: page.total })}
    />
  );
}

/** Render the accounts of the page the address asks for. */
export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const offset = offsetOf(pageSearch(await searchParams));
  const users = await readOrFail("listUsers", () =>
    serverClient().GET("/users", {
      params: { query: { include_inactive: true, ...(offset === undefined ? {} : { offset }) } },
    }),
  );
  return (
    <Screen density={FUNCTION_DENSITY.users}>
      <UsersHeader />
      <UserList users={users.items} />
      <UserPages page={users.meta} shown={users.items.length} />
    </Screen>
  );
}
