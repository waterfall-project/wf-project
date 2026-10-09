// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of the backups reads of its address: its page alone (`offset`), the contract
 * neither sorting, searching nor filtering it. And the way of a download: the route of the front
 * that hands a backup on as a stream, and the address of the screen it sends the browser back to
 * with a refusal, as the result of a task does (`result-refusal.ts`).
 *
 * Pure, and neither server nor client: the page and the route read, the pages and the cells write.
 */
import {
  FROM,
  readRefusal,
  refusedHref,
  type ResultRefusal,
  withoutRefusal,
} from "@/components/tasks/result-refusal";
import type { SearchParameters } from "@/navigation/context";
import { returnTarget } from "@/navigation/login";
import { OFFSET_PARAMETER, type PagedList } from "@/navigation/pages";

/** The key of the settings of the grid of the backups in the account: stable. */
export const BACKUP_GRID_KEY = "backups";

/** The list of the backups, which reads nothing of the address but its page. */
export const BACKUPS_LIST: PagedList = { page: OFFSET_PARAMETER, reads: [] };

/** What a refusal of a command of the list is told on: its page (`Reactivations`). */
export const BACKUPS_READS: readonly string[] = [OFFSET_PARAMETER];

/** The screen of the backups. */
const BACKUPS_PATH = "/admin/backups";

/** The parameter of the address of the screen that names the backup whose download was refused. */
const REFUSED_BACKUP = "refused_backup";

/** The address of the download of a backup, which leaves from the screen given. */
export function downloadHref(backupId: string, from: string): string {
  const query = new URLSearchParams({ [FROM]: from });
  return `${BACKUPS_PATH}/${encodeURIComponent(backupId)}/content?${query.toString()}`;
}

/**
 * The address of the screen of the backups the download left from — that screen alone, its page
 * kept —, with the backup and the refusal of its download.
 */
export function downloadRefusedHref(
  from: string | null,
  backupId: string,
  refusal: ResultRefusal,
): string {
  const back = returnTarget(from);
  const screen = back === BACKUPS_PATH || back.startsWith(`${BACKUPS_PATH}?`) ? back : BACKUPS_PATH;
  return refusedHref(screen, backupId, refusal, REFUSED_BACKUP);
}

/** The refusal of a download the address carries, and the backup it is about; or none. */
export function readDownloadRefusal(
  search: SearchParameters,
): { readonly id: string; readonly refusal: ResultRefusal } | undefined {
  return readRefusal(search, REFUSED_BACKUP);
}

/** The address without the refusal of a download it carried. */
export function withoutDownloadRefusal(location: {
  readonly pathname: string;
  readonly search: string;
}): string {
  return withoutRefusal(location, REFUSED_BACKUP);
}
