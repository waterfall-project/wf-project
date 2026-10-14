// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of the backups reads of its address: its page alone (`offset`, as the contract
 * names it), which its pages turn (`ListPages`); the list has no sort, no search, no filter. And the
 * address of the archive of a backup, whose refusal comes back to the screen in its address.
 *
 * Pure, and neither server nor client: the page and the route read, the pages write.
 */
import { OFFSET_PARAMETER, type PagedList } from "@/navigation/pages";

/** The list of the backups, which reads nothing of the address but its page. */
export const BACKUPS_LIST: PagedList = { page: OFFSET_PARAMETER, reads: [] };

/** The screen of the backups, which the download of one leaves from and comes back to. */
export const BACKUPS_ROUTE = "/admin/backups";

/** The parameter of the screen that says why a download was refused (`saidRefusal`). */
export const DOWNLOAD_REFUSAL = "download_refusal";

/** The address of the archive of a backup, which the front hands on (`downloadBackup`). */
export function backupContentHref(backupId: string): string {
  return `${BACKUPS_ROUTE}/${encodeURIComponent(backupId)}/content`;
}
