// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The backups of the platform (FBS-1.4, US-0250), outside any project: their schedule and retention
 * (WF-ADM-0170), and a page of their list the server pages, each dated, sized and verified
 * (WF-ADM-0150), as the contract gives them. Neither a backup nor a restoration is started here:
 * those commands belong to the epic of the operation of the platform. A read the API refuses, or
 * cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ListPages, type ListPage, offsetOf } from "@/components/admin/list-pages";
import { BackupList, BackupScheduleFacts } from "@/components/admin/platform-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { functionOf } from "@/navigation/functions";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.backups");
}

/** The title of the screen. */
function BackupsHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("backups")}
      icon={FUNCTION_ICONS.backups}
      density={FUNCTION_DENSITY.backups}
    />
  );
}

/** How many backups the list holds, and the way through its pages. */
function BackupPages({ page, shown }: { readonly page: ListPage; readonly shown: number }) {
  const t = useTranslations("admin.backups");
  return (
    <ListPages
      path={functionOf("backups").route}
      page={page}
      shown={shown}
      count={t("count", { count: page.total })}
    />
  );
}

/** Render the schedule of the backups, and the page of their list the address asks for. */
export default async function BackupsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const offset = offsetOf(pageSearch(await searchParams));
  const client = serverClient();
  const [schedule, backups] = await Promise.all([
    readOrFail("getBackupSchedule", () => client.GET("/backup-schedule")),
    readOrFail("listBackups", () =>
      client.GET("/backups", { params: { query: offset === undefined ? {} : { offset } } }),
    ),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.backups}>
      <BackupsHeader />
      <BackupScheduleFacts schedule={schedule} />
      <BackupList backups={backups.items} />
      <BackupPages page={backups.meta} shown={backups.items.length} />
    </Screen>
  );
}
