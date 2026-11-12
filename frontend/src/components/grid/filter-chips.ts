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
  /**
   * What lifting it writes in their place: a filter applied by default — the states of the home —
   * is lifted by naming that it is none, not by saying nothing.
   */
  readonly instead?: Readonly<Record<string, string>> | undefined;
}

/** The parameters of the address that lifting some chips removes, each once. */
export function liftedParams(chips: readonly FilterChip[]): string[] {
  return [...new Set(chips.flatMap((chip) => chip.params))];
}

/** What lifting some chips writes in the place of what they removed, the last chip prevailing. */
export function liftedInstead(chips: readonly FilterChip[]): Record<string, string> {
  return Object.assign({}, ...chips.map((chip) => chip.instead ?? {}));
}

/**
 * The address of the same screen with some parameters lifted, the rest of its query kept, back to
 * the first page of the list the server pages (`page`).
 */
export function liftedHref(
  pathname: string,
  query: URLSearchParams,
  params: readonly string[],
  page: string | undefined,
  instead: Readonly<Record<string, string>> = {},
): string {
  const lifted = withoutParameters(
    pathname,
    query,
    page === undefined ? params : [...params, page],
  );
  const written = Object.entries(instead);
  if (written.length === 0) {
    return lifted;
  }
  const [path = pathname, rest = ""] = lifted.split("?");
  const next = new URLSearchParams(rest);
  for (const [name, value] of written) {
    next.set(name, value);
  }
  return `${path}?${next.toString()}`;
}
