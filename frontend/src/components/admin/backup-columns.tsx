// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the dense grid of the backups (FBS-1.4, EP-02/L43c, EP-14/L42h): a page of
 * the list the server pages, each backup with its date, its size, its verification, its origin and
 * its retention (WF-ADM-0150), a flat table whose every column the server sorts both ways
 * (WF-IHM-0060), the most recent first unasked, and whose columns of commands follow what the
 * backups of the page list (`available_commands`, WF-IHM-0090): the marking in the column of the
 * retention, the download and the restoration in columns of their own, each present when a backup
 * of the page lists the command — the front deduces none of it from the session.
 *
 * Neither server nor client, so that the configuration of the grid reads on both sides: the page,
 * on the server, reads the keys, the columns sorted and which commands the backups list; the grid,
 * in the browser, the rest — a module with a directive would hand the page a reference to the client
 * (défaut n° 12 de `typescript.md`). The key of the settings of the grid is `backup-address.ts`'s.
 */
import { useLocale, useTranslations } from "next-intl";

import { type GridColumn, type GridConfig, sortColumns } from "@/components/grid/columns";
import { LocalTime } from "@/components/local-time";
import { formatBytes } from "@/i18n/format";
import type { ListPage } from "@/navigation/pages";

import { type Backup, BACKUP_GRID_KEY, type BackupSort } from "./backup-address";
import { DownloadCell, RestoreCell, RetentionCell } from "./backup-commands";

/** A column of the grid of the backups. */
type BackupColumn = GridColumn<Backup, BackupSort, ListPage>;

/** The commands the backups of a page list, which decide the columns of the grid. */
export interface ListedCommands {
  /** Whether a backup of the page lists its marking, to keep or no longer. */
  readonly marks: boolean;
  readonly downloads: boolean;
  readonly restores: boolean;
}

/** No command listed: the grid of a session that reads the backups alone, or of an empty page. */
export const NONE_LISTED: ListedCommands = { marks: false, downloads: false, restores: false };

/** The commands the backups of a page list, each by one backup at least. */
export function listedCommands(backups: readonly Backup[]): ListedCommands {
  const lists = (...commands: readonly Backup["available_commands"][number]["command"][]) =>
    backups.some((backup) =>
      backup.available_commands.some((offer) => commands.includes(offer.command)),
    );
  return {
    marks: lists("retain", "release"),
    downloads: lists("download"),
    restores: lists("restore"),
  };
}

/** The size of a backup, in the unit it fills. */
function Size({ bytes }: { readonly bytes: number }) {
  return formatBytes(bytes, useLocale());
}

/** The verification of a backup, in words. */
function Verification({ backup }: { readonly backup: Backup }) {
  return useTranslations("enums.BackupVerification")(backup.verification);
}

/** Whether a backup was taken by hand or on schedule, in words. */
function Origin({ backup }: { readonly backup: Backup }) {
  return useTranslations("enums.BackupOrigin")(backup.origin);
}

/** The width of a column of a command, its button. */
const COMMAND_WIDTH = 130;

/** The column of the download, for a page whose backups list it. */
const DOWNLOAD_COLUMN: BackupColumn = {
  key: "download",
  label: "download",
  format: "text",
  width: COMMAND_WIDTH,
  value: () => null,
  render: (backup) => <DownloadCell backup={backup} />,
};

/** The column of the restoration, for a page whose backups list it. */
const RESTORE_COLUMN: BackupColumn = {
  key: "restore",
  label: "restore",
  format: "text",
  width: COMMAND_WIDTH,
  value: () => null,
  render: (backup) => <RestoreCell backup={backup} />,
};

/**
 * The grid of the backups, every column sorted by the server, the most recent first unasked, and
 * the columns of the commands the backups of the page list.
 */
export function backupGrid(listed: ListedCommands): GridConfig<Backup, BackupSort, ListPage> {
  return {
    key: BACKUP_GRID_KEY,
    name: "backups",
    searched: false,
    lifts: false,
    rowKey: (backup) => backup.backup_id,
    columns: [
      {
        key: "taken_at",
        label: "takenAt",
        format: "text",
        width: 180,
        pinned: true,
        contract: "taken_at",
        descendingFirst: true,
        value: (backup) => backup.taken_at,
        render: (backup) => <LocalTime value={backup.taken_at} />,
      },
      {
        key: "size_bytes",
        label: "size",
        format: "text",
        align: "end",
        width: 130,
        contract: "size_bytes",
        value: (backup) => String(backup.size_bytes),
        render: (backup) => <Size bytes={backup.size_bytes} />,
      },
      {
        key: "verification",
        label: "verification",
        format: "text",
        width: 190,
        contract: "verification",
        value: (backup) => backup.verification,
        render: (backup) => <Verification backup={backup} />,
      },
      {
        key: "origin",
        label: "backupOrigin",
        format: "text",
        width: 140,
        contract: "origin",
        value: (backup) => backup.origin,
        render: (backup) => <Origin backup={backup} />,
      },
      {
        key: "is_retained",
        label: "retention",
        format: "text",
        width: listed.marks ? 300 : 190,
        contract: "is_retained",
        value: (backup) => String(backup.is_retained),
        render: (backup) => <RetentionCell backup={backup} />,
      },
      ...(listed.downloads ? [DOWNLOAD_COLUMN] : []),
      ...(listed.restores ? [RESTORE_COLUMN] : []),
    ],
  };
}

/** The columns of the contract the server sorts the backups by. */
export const BACKUP_SORTS = sortColumns(backupGrid(NONE_LISTED));
