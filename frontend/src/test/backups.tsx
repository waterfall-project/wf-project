// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The list of the backups as the tests of its commands render it (`backup-commands.dom.test.tsx`,
 * `restore-dialog.dom.test.tsx`): the backups of the examples the fake back serves, and the list
 * within the shell that follows the tasks and the screen that follows a restoration, as the page
 * renders it; and what those tests read of it — a row by the date of its backup, the regions that
 * announce, the bodies sent.
 */
import { screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { NEWEST_FIRST, readBackupFilters } from "@/components/admin/backup-address";
import { BackupList } from "@/components/admin/platform-lists";
import { Restoration } from "@/components/admin/restoration";
import { PendingAddress } from "@/components/grid/pending-address";
import type { ResultRefusal } from "@/components/tasks/result-refusal";
import { TaskPanel, TasksButton, TaskTracker } from "@/components/tasks/task-tracker";
import { CATALOGUES } from "@/i18n/catalogues";
import { formatTimestamp } from "@/i18n/format";
import type { ListPage } from "@/navigation/pages";

import { example, type FakeClient } from "./fixtures";

type Backup = components["schemas"]["Backup"];

/** The backups of the witness, as the fake back serves their list. */
export const backups = example("backups") as {
  items: Backup[];
  meta: components["schemas"]["PaginationMeta"];
};

/** A backup of the witness, by its place in the list. */
function backupAt(at: number): Backup {
  const found = backups.items[at];
  if (found === undefined) {
    throw new Error(`the witness lists a backup at ${String(at)}`);
  }
  return found;
}

/** The backup of last night, the first of the list, and the one kept since January, the last. */
export const LAST_NIGHT = backupAt(0);
export const KEPT = backupAt(7);
/** The backup taken by hand today, read before its verification: neither downloads nor restores. */
export const PENDING = example("backup_pending") as Backup;
/** The backups read by a session that may neither modify them nor restore the platform. */
export const READ_ALONE = (example("backups_reader") as { items: Backup[] }).items;
/** The backups read while a backup runs: none restores. */
export const DURING_BACKUP = (example("backups_during_backup") as { items: Backup[] }).items;

/** A date of a backup as the browser writes it, in the time zone of the workstation. */
export const dated = (backup: Backup) => formatTimestamp(backup.taken_at, "fr");

/**
 * The list of the backups, within the shell that follows the tasks and the screen that follows a
 * restoration, as the page renders it: the rows given, filtered as the address given asks, for a
 * session that may start a backup unless said otherwise.
 */
export function backupList(
  rows: readonly Backup[] = backups.items,
  options: {
    readonly startable?: boolean;
    readonly refused?: { readonly id: string; readonly refusal: ResultRefusal };
    readonly page?: ListPage;
    readonly search?: string;
  } = {},
): ReactNode {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <TaskTracker>
        <TasksButton />
        <TaskPanel />
        <main>
          <Restoration>
            <PendingAddress>
              <BackupList
                read={{ kind: "read", items: rows, page: options.page ?? backups.meta }}
                filters={readBackupFilters(new URLSearchParams(options.search ?? ""))}
                query={{ sort: NEWEST_FIRST, search: undefined, size: undefined }}
                preferences={undefined}
                startable={options.startable ?? true}
                refused={options.refused}
              />
            </PendingAddress>
          </Restoration>
        </main>
      </TaskTracker>
    </NextIntlClientProvider>
  );
}

/** The grid of the backups. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Sauvegardes" });
}

/** The row of a backup in the grid, found by its date. */
export function row(backup: Backup): HTMLElement {
  const found = within(grid())
    .getAllByRole("row")
    .find((each) => each.querySelector(`time[datetime="${backup.taken_at}"]`) !== null);
  if (found === undefined) {
    throw new Error(`no row of the backup of ${backup.taken_at}`);
  }
  return found;
}

/** What the regions of the list announce. */
export function announced(): (string | null)[] {
  return screen.getAllByRole("status").map((status) => status.textContent);
}

/** The bodies of the calls made of an operation. */
export function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}
