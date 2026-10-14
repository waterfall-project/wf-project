// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The backups of the platform (FBS-1.4, US-0250), outside any project: their schedule and retention
 * (WF-ADM-0170), and a page of their list the server pages, each dated, sized and verified
 * (WF-ADM-0150), as the contract gives them. And their commands (US-0440), each to whom the session
 * permits it (`platformOffer`): a backup asked, a verified one downloaded — the refusal of a
 * download carried back in the address — or restored, and a backup copied out of another
 * installation deposited, then restored; a restoration replaces the screen by that of its
 * maintenance (`Restoration`). A read the API refuses, or cannot answer, is thrown for the pages of
 * the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { BACKUPS_LIST, DOWNLOAD_REFUSAL } from "@/components/admin/backup-address";
import { BackupDeposit, DownloadRefusal, StartBackup } from "@/components/admin/backup-commands";
import { BackupList, BackupScheduleFacts } from "@/components/admin/platform-lists";
import { Restoration } from "@/components/admin/restoration";
import { platformOffer } from "@/components/commands/offer";
import { ListPages } from "@/components/grid/list-pages";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, searchQuery } from "@/navigation/context";
import { type ListPage, OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { heardRefusal } from "@/components/tasks/result-refusal";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.backups");
}

/** The title of the screen, and the command that asks a backup, to whom may modify them. */
function BackupsHeader({ startable }: { readonly startable: boolean }) {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("backups")}
      icon={FUNCTION_ICONS.backups}
      density={FUNCTION_DENSITY.backups}
      actions={startable ? <StartBackup /> : undefined}
    />
  );
}

/** How many backups the list holds, and the way through its pages; nothing for an empty list. */
function BackupPages({ page, shown }: { readonly page: ListPage; readonly shown: number }) {
  const t = useTranslations("admin.backups");
  if (page.total === 0) {
    // The list holds nothing, which the list itself says.
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <p className="text-muted-foreground">{t("count", { count: page.total })}</p>
      <ListPages list={BACKUPS_LIST} texts="admin.pages" page={page} shown={shown} />
    </div>
  );
}

/** Render the schedule of the backups, and the page of their list the address asks for. */
export default async function BackupsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const query = searchQuery(await searchParams);
  const offset = offsetOf(query.get(OFFSET_PARAMETER));
  const client = serverClient();
  const [schedule, backups, session] = await Promise.all([
    readOrFail("getBackupSchedule", () => client.GET("/backup-schedule")),
    readOrFail("listBackups", () =>
      client.GET("/backups", { params: { query: offset === undefined ? {} : { offset } } }),
    ),
    requestSession(),
  ]);
  const permissions = session?.permissions;
  const modifiable = platformOffer(permissions, "backups") !== undefined;
  const restorable = platformOffer(permissions, "platform_restore") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.backups}>
      <Restoration>
        <BackupsHeader startable={modifiable} />
        <DownloadRefusal refusal={heardRefusal(query.get(DOWNLOAD_REFUSAL))} />
        <BackupScheduleFacts schedule={schedule} />
        <BackupList
          backups={backups.items}
          page={backups.meta}
          commands={{ download: modifiable, restore: restorable }}
        />
        <BackupPages page={backups.meta} shown={backups.items.length} />
        {restorable ? <BackupDeposit /> : null}
      </Restoration>
    </Screen>
  );
}
