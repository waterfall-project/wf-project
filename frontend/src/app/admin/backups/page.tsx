// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The backups of the platform (FBS-1.4, US-0250, EP-02/L43c), outside any project: their schedule
 * and retention (WF-ADM-0170), read only, and a page of their list the server pages, on the dense
 * grid, each dated, sized and verified (WF-ADM-0150), as the contract gives them — which neither
 * sorts, searches nor filters them (#519). The commands follow the permissions of the catalogue
 * (WF-ADM-0100): to a session that may modify the backups, start one now, mark one to be kept or no
 * longer, download one; to a session that may restore the platform, restore it from one, confirmed;
 * to another, none (WF-IHM-0090). The fake back keeps none of what is written, which the screen says
 * to who writes (`MockupNotice`). A download the route refused comes back here, the refusal in the
 * address, told above the list. A read the API refuses, or cannot answer, is thrown for the pages
 * of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { BACKUP_GRID_KEY, readDownloadRefusal } from "@/components/admin/backup-address";
import { BackupList, BackupScheduleFacts } from "@/components/admin/platform-lists";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

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
  const offset = offsetOf(search.get(OFFSET_PARAMETER));
  const offers = {
    editable: platformOffer(session?.permissions, "backups") !== undefined,
    restorable: platformOffer(session?.permissions, "platform_restore") !== undefined,
  };
  const client = serverClient();
  const [schedule, backups] = await Promise.all([
    readOrFail("getBackupSchedule", () => client.GET("/backup-schedule")),
    readOrFail("listBackups", () =>
      client.GET("/backups", { params: { query: offset === undefined ? {} : { offset } } }),
    ),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.backups} fill>
      {/* The grid and the pages compose the changes they make to the address. */}
      <PendingAddress>
        <BackupsHeader writes={offers.editable || offers.restorable} />
        <BackupScheduleFacts schedule={schedule} />
        <BackupList
          backups={backups.items}
          page={backups.meta}
          preferences={session?.user.display_preferences?.grids?.[BACKUP_GRID_KEY] ?? undefined}
          offers={offers}
          refused={readDownloadRefusal(search)}
        />
      </PendingAddress>
    </Screen>
  );
}
