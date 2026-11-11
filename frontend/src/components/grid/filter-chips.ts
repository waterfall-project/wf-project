// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters a flat table has on, told as chips under its bar (WF-IHM-0020, #2916): each a name
 * and a value, built from what the address says (`filters.ts`, `period.ts`) and lifted by changing
 * that address, the server filtering still (WF-ARC-0020). A chip names the parameters of the
 * address it lifts — a filter read from several, a period's two bounds, a state and the parameter
 * it prevails over —, and the number of chips is the number the button of the filters shows.
 *
 * Pure, and neither server nor client: the screen builds its chips, the bar lifts them.
 */
import { withoutParameters } from "./filters";

/** A filter on, as a chip says it: « Origine : Local ». */
export interface FilterChip {
  /** Tells the chip among the others of its table. */
  readonly key: string;
  /** What the filter is on: the heading of its column. */
  readonly name: string;
  /** What it keeps, translated. */
  readonly value: string;
  /** The parameters of the address that lifting it removes. */
  readonly params: readonly string[];
}

/**
 * The address of the same screen with the filters of some chips lifted, the rest of its query kept,
 * back to the first page of the list the server pages (`page`).
 */
export function liftedHref(
  pathname: string,
  query: URLSearchParams,
  chips: readonly FilterChip[],
  page: string | undefined,
): string {
  const lifted = chips.flatMap((chip) => chip.params);
  return withoutParameters(pathname, query, page === undefined ? lifted : [...lifted, page]);
}
