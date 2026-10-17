// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of the backups reads of its address: its page alone (`offset`, as the contract
 * names it), which its pages turn (`ListPages`); the list has no sort, no search, no filter. And the
 * address of the archive of a backup, which names the page of the list it leaves from, and whose
 * refusal comes back to that page in its address.
 *
 * Pure, and neither server nor client: the page and the route read, the pages write.
 */
import { FROM } from "@/components/tasks/result-refusal";
import { returnTarget } from "@/navigation/login";
import { OFFSET_PARAMETER, type PagedList } from "@/navigation/pages";

/** The list of the backups, which reads nothing of the address but its page. */
export const BACKUPS_LIST: PagedList = { page: OFFSET_PARAMETER, reads: [] };

/** The screen of the backups, which the download of one leaves from and comes back to. */
export const BACKUPS_ROUTE = "/admin/backups";

/** The parameter of the screen that says why a download was refused (`saidRefusal`). */
export const DOWNLOAD_REFUSAL = "download_refusal";

/** The page of the list of the backups that starts at the offset given, the first by default. */
export function backupsHref(offset: number): string {
  return offset > 0 ? `${BACKUPS_ROUTE}?${OFFSET_PARAMETER}=${String(offset)}` : BACKUPS_ROUTE;
}

/**
 * The address of the archive of a backup, which the front hands on (`downloadBackup`), leaving from
 * the page of the list given.
 */
export function backupContentHref(backupId: string, from: string): string {
  const query = new URLSearchParams({ [FROM]: from });
  return `${BACKUPS_ROUTE}/${encodeURIComponent(backupId)}/content?${query.toString()}`;
}

/**
 * The page of the list a download left from — a path of the front on the screen of the backups,
 * the screen itself otherwise: no other screen tells the refusal —, with the refusal said
 * (`saidRefusal`).
 */
export function refusedDownloadHref(from: string | null, said: string): string {
  const target = new URL(returnTarget(from), "http://front.invalid");
  const back = target.pathname === BACKUPS_ROUTE ? target : new URL(BACKUPS_ROUTE, target);
  back.searchParams.set(DOWNLOAD_REFUSAL, said);
  return `${back.pathname}${back.search}`;
}
