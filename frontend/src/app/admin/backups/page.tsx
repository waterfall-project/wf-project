// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The backups of the platform (FBS-1.4, US-0250, EP-02/L43c, EP-14/L42h), outside any project:
 * their schedule and retention (WF-ADM-0170), read only, and a page of their list the server pages,
 * on the dense grid, each dated, sized and verified (WF-ADM-0150), sorted, filtered and paged by the
 * server as the address asks under the names of the contract (`sort_by`, `sort_order`, `from`,
 * `to`, `origins`, `verifications`, `is_retained`, `size_bytes_min`, `size_bytes_max`, `offset`;
 * WF-IHM-0130) — the most recent first when the address and the account say nothing of the sort.
 * Every figure as the API gives it: the front sorts, filters and pages nothing. The commands are
 * those each backup lists (`available_commands`, WF-IHM-0090) — mark it to be kept or no longer,
 * download it, restore the platform from it, confirmed —, and, to a session that may modify the
 * backups (WF-ADM-0100), the one that starts one now. The fake back keeps none of what is written,
 * which the screen says to who may write (`MockupNotice`). A download the route refused comes back
 * here, the refusal in the address, told above the list. Filters the API refuses (422) — a period
 * that ends before it starts, a size at most below the least — leave the list unread, said at their
 * field; any other read the API refuses, or cannot answer, is thrown for the pages of the shell to
 * say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  BACKUP_GRID_KEY,
  type BackupFilters,
  backupsQuery,
  type BackupSort,
  NEWEST_FIRST,
  readBackupFilters,
  readDownloadRefusal,
} from "@/components/admin/backup-address";
import { BACKUP_SORTS } from "@/components/admin/backup-columns";
import {
  BackupList,
  BackupScheduleFacts,
  type BackupsRead,
} from "@/components/admin/platform-lists";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** The refusal of filters the server cannot apply — a period or bounds inverted (`listBackups`, 422). */
const FILTERS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.backups");
}

/** The title of the screen, and, for who writes, that the fake back keeps nothing. */
function BackupsHeader({ writes }: { readonly writes: boolean }) {
  const t = useTranslations("functions");
  return (
    <>
      <PageHeader
        title={t("backups")}
        icon={FUNCTION_ICONS.backups}
        density={FUNCTION_DENSITY.backups}
      />
      {writes ? <MockupNotice /> : null}
    </>
  );
}

/** Read the page of the backups the address asks; or the refusal of its filters (422). */
async function readBackups(
  filters: BackupFilters,
  query: GridQuery<BackupSort>,
  offset: number | undefined,
): Promise<BackupsRead> {
  const read = await readOrRefused("listBackups", FILTERS_REFUSED, () =>
    serverClient().GET("/backups", { params: { query: backupsQuery(filters, query, offset) } }),
  );
  return read.kind === "read"
    ? { kind: "read", items: read.data.items, page: read.data.meta }
    : { kind: "refused", problem: read.problem };
}

/** Render the schedule of the backups, and the page of their list the address asks for. */
export default async function BackupsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const preferences = session?.user.display_preferences?.grids?.[BACKUP_GRID_KEY] ?? undefined;
  // The address is the truth; then the sort the account keeps; then the server's: newest first.
  const query = readGridQuery(search, BACKUP_SORTS, preferences?.sort ?? NEWEST_FIRST);
  const filters = readBackupFilters(search);
  const startable = platformOffer(session?.permissions, "backups") !== undefined;
  const [schedule, backups] = await Promise.all([
    readOrFail("getBackupSchedule", () => serverClient().GET("/backup-schedule")),
    readBackups(filters, query, offsetOf(search.get(OFFSET_PARAMETER))),
  ]);
  // Who writes: who may start a backup, or whose backups list a command.
  const writes =
    startable ||
    (backups.kind === "read" &&
      backups.items.some((backup) => backup.available_commands.length > 0));
  return (
    <Screen density={FUNCTION_DENSITY.backups} fill>
      {/* The filters, the grid and the pages compose the changes they make to the address. */}
      <PendingAddress>
        <BackupsHeader writes={writes} />
        <BackupScheduleFacts schedule={schedule} />
        <BackupList
          read={backups}
          filters={filters}
          query={query}
          preferences={preferences}
          startable={startable}
          refused={readDownloadRefusal(search)}
        />
      </PendingAddress>
    </Screen>
  );
}
