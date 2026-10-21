// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The backups of the platform (FBS-1.4, US-0250, EP-02/L43c, EP-14/L42h, US-0440), outside any
 * project: their schedule, their retention and their external copy (WF-ADM-0170), set whole by a
 * form to a session that may modify the backups, from the locations the installation declares
 * (EP-14/L43d) — the schedule left out when the API does not find it, the form when it does not find
 * the locations: the service does not serve them yet (EP-13) —, and a page of their list the server
 * pages, on the dense grid, each dated, sized and verified (WF-ADM-0150), sorted, filtered and paged
 * by the server as the address asks under the names of the contract (`sort_by`, `sort_order`,
 * `from`, `to`, `origins`, `verifications`, `is_retained`, `size_bytes_min`, `size_bytes_max`,
 * `offset`; WF-IHM-0130) — the most recent first when the address and the account say nothing of
 * the sort. Every figure as the API gives it: the front sorts, filters and pages nothing. The
 * commands are those each backup lists (`available_commands`, WF-IHM-0090) — mark it to be kept or
 * no longer, download it, restore the platform from it, confirmed —, and, to a session that may
 * modify the backups (WF-ADM-0100), the one that starts one now; to a session that may restore the
 * platform, the deposit of a backup copied out of another installation, in parts, then its
 * restoration (US-0440, #350). A restoration started replaces the screen by that of its maintenance
 * (`Restoration`). The screen says nothing of the fake back, which keeps none of what is written: it
 * is wired to the service of EP-03 (decision of the author, 2026-10-18). A download the route
 * refused comes back here, the refusal in the address, told above the list. Filters the API refuses (422) — a period that ends before it starts, a size
 * at most below the least — leave the list unread, said at their field; any other read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrRefused, readUnlessRefused } from "@/api/problem";
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
import { BackupDeposit } from "@/components/admin/backup-commands";
import { BackupScheduleSection } from "@/components/admin/backup-schedule";
import { BackupList, type BackupsRead } from "@/components/admin/platform-lists";
import { Restoration } from "@/components/admin/restoration";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { CONTRACT_ADDRESS, type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** The refusal of filters the server cannot apply — a period or bounds inverted (`listBackups`, 422). */
const FILTERS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** A read the screen does without: the service does not serve it yet (EP-13), and answers 404. */
const NOT_SERVED = [{ status: 404 }] as const;

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
  const preferences = session?.display_preferences?.grids?.[BACKUP_GRID_KEY] ?? undefined;
  // The address is the truth; then the sort the account keeps; then the server's: newest first.
  const query = readGridQuery(
    search,
    BACKUP_SORTS,
    preferences?.sort ?? NEWEST_FIRST,
    CONTRACT_ADDRESS,
    preferences?.page_size,
  );
  const filters = readBackupFilters(search);
  const permissions = session?.permissions;
  const startable = platformOffer(permissions, "backups") !== undefined;
  const restorable = platformOffer(permissions, "platform_restore") !== undefined;
  const [schedule, locations, backups] = await Promise.all([
    readUnlessRefused("getBackupSchedule", NOT_SERVED, () =>
      serverClient().GET("/backup-schedule"),
    ),
    // The locations a copy may go to, for the form of the schedule: read for who may set it alone.
    startable
      ? readUnlessRefused("listExternalBackupLocations", NOT_SERVED, () =>
          serverClient().GET("/external-backup-locations"),
        )
      : undefined,
    readBackups(filters, query, offsetOf(search.get(OFFSET_PARAMETER))),
  ]);
  // The screen does not fill the window (`Screen fill`): the deposit comes under the list, and a
  // grid shrunk to what the window leaves it, down to its floor, would spill over the deposit in a
  // window too low for both — at 150 % and less. The page grows with its content, and scrolls; the
  // grid is never taller than the window (`DenseGrid`).
  return (
    <Screen density={FUNCTION_DENSITY.backups}>
      <Restoration>
        {/* The filters, the grid and the pages compose the changes they make to the address. */}
        <PendingAddress>
          <BackupsHeader />
          {schedule === undefined ? null : (
            <BackupScheduleSection schedule={schedule} locations={locations} />
          )}
          <BackupList
            read={backups}
            filters={filters}
            query={query}
            preferences={preferences}
            startable={startable}
            refused={readDownloadRefusal(search)}
          />
          {restorable ? <BackupDeposit /> : null}
        </PendingAddress>
      </Restoration>
    </Screen>
  );
}
