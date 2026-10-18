// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grid of the backups in its page (FBS-1.4, EP-02/L43c, EP-14/L42h): a page of the list
 * the server pages, sorted as the address asks (`backup-columns.tsx`), each backup shown as the
 * server answered its marking (`useShownBackups`), and the columns of the commands the backups shown
 * list (WF-IHM-0090). Configured here, in the browser: a configuration reads the rows by functions,
 * which never cross from a server component. The totals row says how many the server retained
 * (`meta.total`), never a count of the page.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import type { ListPage } from "@/navigation/pages";

import type { Backup, BackupSort } from "./backup-address";
import { backupGrid, listedCommands } from "./backup-columns";
import { useShownBackups } from "./backup-commands";

/**
 * Render the grid of a page of the backups, each shown as the server answered its marking, its
 * totals row the number the server retained, with the commands the backups list.
 */
export function BackupGrid({
  backups,
  page,
  query,
  preferences,
}: {
  readonly backups: readonly Backup[];
  readonly page: ListPage;
  readonly query: GridQuery<BackupSort>;
  readonly preferences: GridPreferences | undefined;
}) {
  const t = useTranslations("admin.backups");
  const shown = useShownBackups(backups);
  const { marks, downloads, restores } = listedCommands(shown);
  const config = useMemo(
    () => backupGrid({ marks, downloads, restores }),
    [marks, downloads, restores],
  );
  return (
    <DenseGrid
      config={config}
      rows={shown}
      totals={page}
      totalsCaption={(retained) => t("count", { count: retained.total })}
      query={query}
      preferences={preferences}
    />
  );
}
