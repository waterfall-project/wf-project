// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pages of a list the server pages (`PaginationMeta`), one rule for every list of the front
 * — the projects, the actual costs and the journal of their imports, the imports of a project,
 * the projects of the portfolio, the accounts, the backups (#317): the offset the address asks a
 * page by (`offset`, as the contract names it), and where the page shown stands in the list —
 * beyond its end, when the address asked a page the list has not, and the offsets of the pages
 * before and after it. Pure: a component draws the links from them.
 */
import type { components } from "@/api/generated/schema";

/** Where a page of a list stands in it, as the server says. */
export type ListPage = components["schemas"]["PaginationMeta"];

/** The parameter of the address that names the page of a list, as the contract names it. */
export const OFFSET_PARAMETER = "offset";

/**
 * The offset of a page of a list the address asks for (`offset`), or none when it asks for none
 * a server could take.
 */
export function offsetOf(value: string | null): number | undefined {
  const offset = Number(value);
  return value !== null && Number.isSafeInteger(offset) && offset > 0 ? offset : undefined;
}

/** Where the page shown stands: the pages around it, each by its offset when there is one. */
export interface PageOffsets {
  /**
   * Whether the address asked a page beyond the end of the list — none of its rows shown, past
   * the last one —, which is no empty list: the page before is then the last page of the list.
   */
  readonly beyond: boolean;
  /** The offset of the page before the one shown; none on the first page. */
  readonly previous: number | undefined;
  /** The offset of the page after the one shown; none on the last page, or beyond it. */
  readonly next: number | undefined;
}

/** Where the page shown, of `shown` rows, stands in its list. */
export function pageOffsets(page: ListPage, shown: number): PageOffsets {
  const beyond = shown === 0 && page.offset > 0 && page.offset >= page.total;
  const last = Math.floor(Math.max(0, page.total - 1) / page.limit) * page.limit;
  return {
    beyond,
    previous: page.offset > 0 ? (beyond ? last : Math.max(0, page.offset - page.limit)) : undefined,
    next: page.offset + shown < page.total ? page.offset + shown : undefined,
  };
}

/**
 * The address of a page of a list: its path, the parameters kept — the filters of the list, its
 * sort —, and the page by its offset, left out for the first page.
 */
export function pageHref(path: string, kept: URLSearchParams, offset: number): string {
  const query = new URLSearchParams(kept);
  query.delete(OFFSET_PARAMETER);
  if (offset > 0) {
    query.set(OFFSET_PARAMETER, String(offset));
  }
  const text = query.toString();
  return text === "" ? path : `${path}?${text}`;
}
