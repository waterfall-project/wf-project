// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grid of the backups (FBS-1.4, EP-02/L43c): a page of the list the server pages, each
 * backup with its date, its size, its verification, its origin and its retention (WF-ADM-0150), and
 * the commands the session may exercise (WF-ADM-0100). It neither sorts nor searches, the contract
 * doing neither (#519). Configured here, in the browser: a configuration reads the rows by
 * functions, which never cross from a server component.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";

import type { GridColumn, GridConfig } from "@/components/grid/columns";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridPreferences } from "@/components/grid/settings";
import { LocalTime } from "@/components/local-time";
import { formatBytes } from "@/i18n/format";
import type { ListPage } from "@/navigation/pages";

import { BACKUP_GRID_KEY } from "./backup-address";
import {
  type Backup,
  DownloadCell,
  RestoreCell,
  RetentionCell,
  useShownBackups,
} from "./backup-commands";

/** The commands the session may exercise on the backups. */
export interface BackupOffers {
  /** Whether it may modify the backups (`backups.write`): start one, mark them. */
  readonly editable: boolean;
  /** Whether it may restore the platform (`platform_restore`): download them, restore from one. */
  readonly restorable: boolean;
}

/** A column of the grid of the backups, which sorts nothing. */
type BackupColumn = GridColumn<Backup, never, ListPage>;

/** The size of a backup, in the unit it fills. */
function Size({ bytes }: { readonly bytes: number }) {
  return formatBytes(bytes, useLocale());
}

/** The verification of a backup, in words. */
function Verification({ backup }: { readonly backup: Backup }) {
  return useTranslations("enums.Backup.verification")(backup.verification);
}

/** Whether a backup was taken by hand or on schedule, in words; nothing when the server says not. */
function Origin({ backup }: { readonly backup: Backup }) {
  const t = useTranslations("enums.Backup.origin");
  return backup.origin === undefined ? null : t(backup.origin);
}

/** The width of a column of a command, its button. */
const COMMAND_WIDTH = 130;

/** The columns of the commands of the restoration's permission: the download, the restoration. */
const RESTORE_COLUMNS: readonly BackupColumn[] = [
  {
    key: "download",
    label: "download",
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (backup) => <DownloadCell backup={backup} />,
  },
  {
    key: "restore",
    label: "restore",
    format: "text",
    width: COMMAND_WIDTH,
    value: () => null,
    render: (backup) => <RestoreCell backup={backup} />,
  },
];

/** The grid of the backups, and the columns of the commands the session may exercise. */
export function backupGrid({
  editable,
  restorable,
}: BackupOffers): GridConfig<Backup, never, ListPage> {
  return {
    key: BACKUP_GRID_KEY,
    name: "backups",
    searched: false,
    sorts: false,
    rowKey: (backup) => backup.backup_id,
    columns: [
      {
        key: "taken_at",
        label: "takenAt",
        format: "text",
        width: 180,
        pinned: true,
        value: (backup) => backup.taken_at,
        render: (backup) => <LocalTime value={backup.taken_at} />,
      },
      {
        key: "size_bytes",
        label: "size",
        format: "text",
        align: "end",
        width: 130,
        value: (backup) => String(backup.size_bytes),
        render: (backup) => <Size bytes={backup.size_bytes} />,
      },
      {
        key: "verification",
        label: "verification",
        format: "text",
        width: 190,
        value: (backup) => backup.verification,
        render: (backup) => <Verification backup={backup} />,
      },
      {
        key: "origin",
        label: "backupOrigin",
        format: "text",
        width: 140,
        value: (backup) => backup.origin,
        render: (backup) => <Origin backup={backup} />,
      },
      {
        key: "is_retained",
        label: "retention",
        format: "text",
        width: editable ? 300 : 190,
        value: (backup) => String(backup.is_retained),
        render: (backup) => <RetentionCell backup={backup} editable={editable} />,
      },
      ...(restorable ? RESTORE_COLUMNS : []),
    ],
  };
}

/** The query of a grid that neither sorts nor searches. */
const NO_QUERY = { sort: undefined, search: undefined };

/**
 * Render the grid of a page of the backups, each shown as the server answered its marking, its
 * totals row the number the server retained, with the commands the session may exercise.
 */
export function BackupGrid({
  backups,
  page,
  preferences,
  offers,
}: {
  readonly backups: readonly Backup[];
  readonly page: ListPage;
  readonly preferences: GridPreferences | undefined;
  readonly offers: BackupOffers;
}) {
  const t = useTranslations("admin.backups");
  const { editable, restorable } = offers;
  const config = useMemo(() => backupGrid({ editable, restorable }), [editable, restorable]);
  const shown = useShownBackups(backups);
  return (
    <DenseGrid
      config={config}
      rows={shown}
      totals={page}
      totalsCaption={(retained) => t("count", { count: retained.total })}
      query={NO_QUERY}
      preferences={preferences}
    />
  );
}
