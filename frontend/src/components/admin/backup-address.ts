// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of the backups reads of its address (WF-IHM-0130, EP-14/L42h), under the names of
 * the contract: the sort of its grid (`sort_by`, `sort_order`, `query.ts`), its page (`offset`), and
 * its filters — the period the backups were taken in, `from` included and `to` excluded, two
 * instants drawn from the local days of the reader (`period.ts`, `day`); their origins, `origins`,
 * and the outcomes of their verification, `verifications`, each a list of values of the contract
 * separated by commas; their marking, `is_retained`; and the bounds of their size in bytes, both
 * included, `size_bytes_min` and `size_bytes_max` (`filters.ts`). A filter chosen only changes the
 * address, back to the first page, and the page reads anew: the server filters and sorts, never the
 * front (WF-ARC-0020); without a sort, it gives the most recent first. And the way of a download:
 * the route of the front that hands a backup on as a stream, and the address of the screen it sends
 * the browser back to with a refusal, as the result of a task does (`result-refusal.ts`).
 *
 * Pure, and neither server nor client: the page and the route read, the filters, the pages and the
 * cells write.
 */
import type { components, operations } from "@/api/generated/schema";
import {
  type Bounds,
  boundNames,
  readBoolean,
  readBounds,
  readValues,
} from "@/components/grid/filters";
import { PERIOD, type Period, readPeriod } from "@/components/grid/period";
import { asked, type GridQuery, type GridSort, SORT_BY, SORT_ORDER } from "@/components/grid/query";
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

/** A backup, as the contract gives it. */
export type Backup = components["schemas"]["Backup"];

/** The origin of a backup, as the contract names it: by hand, or on schedule. */
export type BackupOrigin = components["schemas"]["BackupOrigin"];

/** The outcome of the verification of a backup, as the contract names it. */
export type BackupVerification = components["schemas"]["BackupVerification"];

/** The column of the contract the server sorts the backups by. */
export type BackupSort = NonNullable<NonNullable<BackupsQuery["sort_by"]>>;

/** What the page asks `listBackups`: the query of the contract. */
type BackupsQuery = NonNullable<operations["listBackups"]["parameters"]["query"]>;

/** The key of the settings of the grid of the backups in the account: stable. */
export const BACKUP_GRID_KEY = "backups";

/** The parameter of the address the origins filtered on go by, as the contract names it. */
export const ORIGINS = "origins";

/** The parameter of the address the verifications filtered on go by, as the contract names it. */
export const VERIFICATIONS = "verifications";

/** The parameter of the address the marking filtered on goes by, as the contract names it. */
export const IS_RETAINED = "is_retained";

/** The column of the size, whose bounds the address carries (`size_bytes_min`, `size_bytes_max`). */
export const SIZE_BYTES = "size_bytes";

/**
 * Every origin of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_ORIGIN: Readonly<Record<BackupOrigin, number>> = { manual: 0, scheduled: 1 };

/** The origins a backup may have, in the order of the contract. */
export const BACKUP_ORIGINS = Object.keys(EVERY_ORIGIN) as readonly BackupOrigin[];

/** Every outcome of a verification, in the order of the contract: one added fails the type check. */
const EVERY_VERIFICATION: Readonly<Record<BackupVerification, number>> = {
  pending: 0,
  passed: 1,
  failed: 2,
};

/** The outcomes a verification may have, in the order of the contract. */
export const BACKUP_VERIFICATIONS = Object.keys(
  EVERY_VERIFICATION,
) as readonly BackupVerification[];

/** The sort the server gives unasked: the most recent backups first (`listBackups`). */
export const NEWEST_FIRST: GridSort<BackupSort> = { column: "taken_at", order: "desc" };

/** The list of the backups: its sort, its filters and its page — no search, the contract has none. */
export const BACKUPS_LIST: PagedList = {
  page: OFFSET_PARAMETER,
  reads: [
    SORT_BY,
    SORT_ORDER,
    PERIOD.from,
    PERIOD.to,
    ORIGINS,
    VERIFICATIONS,
    IS_RETAINED,
    boundNames(SIZE_BYTES).min,
    boundNames(SIZE_BYTES).max,
  ],
};

/** What a refusal of a command of the list is told on: what the list reads, its page too. */
export const BACKUPS_READS: readonly string[] = [...BACKUPS_LIST.reads, OFFSET_PARAMETER];

/** The filters of the backups, as the address asks them. */
export interface BackupFilters {
  /** The period they were taken in, each side an instant of the contract; none, no bound. */
  readonly period: Period;
  /** The origins they are restricted to; none, every one. */
  readonly origins: readonly BackupOrigin[];
  /** The outcomes of verification they are restricted to; none, every one. */
  readonly verifications: readonly BackupVerification[];
  /** Whether they are restricted to the ones marked to keep, or to the others; none, every one. */
  readonly retained: boolean | undefined;
  /** The bounds of their size in bytes, both included. */
  readonly size: Bounds;
}

/**
 * The filters the address sets on the backups, each as the contract takes it; a value the server
 * would refuse — an instant that is none, an origin it does not know — is not asked.
 */
export function readBackupFilters(search: SearchParameters): BackupFilters {
  return {
    period: readPeriod(search, "day"),
    origins: readValues(search, ORIGINS, BACKUP_ORIGINS),
    verifications: readValues(search, VERIFICATIONS, BACKUP_VERIFICATIONS),
    retained: readBoolean(search, IS_RETAINED),
    size: readBounds(search, SIZE_BYTES, "bytes"),
  };
}

/** Whether the filters narrow the list: an empty page is then no empty list. */
export function narrows(filters: BackupFilters): boolean {
  return (
    filters.period.from !== undefined ||
    filters.period.to !== undefined ||
    filters.origins.length > 0 ||
    filters.verifications.length > 0 ||
    filters.retained !== undefined ||
    filters.size.min !== undefined ||
    filters.size.max !== undefined
  );
}

/**
 * The query of the list of the backups, as the address asks it: its sort, its filters and its page
 * — every parameter but the page read from `BACKUPS_LIST`, which says when two addresses read the
 * same list. A size is an integer of the contract, written as a number.
 */
export function backupsQuery(
  filters: BackupFilters,
  query: GridQuery<BackupSort>,
  offset: number | undefined,
): BackupsQuery {
  const { period, origins, verifications, retained, size } = filters;
  return {
    ...asked(query, offset),
    ...(period.from === undefined ? {} : { from: period.from }),
    ...(period.to === undefined ? {} : { to: period.to }),
    ...(origins.length === 0 ? {} : { origins: [...origins] }),
    ...(verifications.length === 0 ? {} : { verifications: [...verifications] }),
    ...(retained === undefined ? {} : { is_retained: retained }),
    ...(size.min === undefined ? {} : { size_bytes_min: Number(size.min) }),
    ...(size.max === undefined ? {} : { size_bytes_max: Number(size.max) }),
  };
}

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
 * and its filters kept —, with the backup and the refusal of its download.
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
