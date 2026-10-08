// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the page of the settings of the costs and the grid of the hourly rates both read of the grid
 * (#509): the key of its settings in the account, the columns the server sorts it by — the code,
 * the label, the state, and the rate of each year (`rate.<year>`, as `getHourlyRateGrid` names
 * them), for every year the contract takes, since the page checks the address before it knows the
 * years of the answer —, and the names of its filters in the address, those of the contract: the
 * state, and the bounds of the rate of a year (#545).
 *
 * Neither server nor client: a value exported from a module `"use client"` reaches a server
 * component as a reference to the client, never as the value — the key of the settings and the
 * columns sorted were read so, the preferences of the grid never found (défaut n° 12 de
 * `typescript.md`).
 */

/** The key of the settings of the grid in the account: stable. */
export const RATE_GRID_KEY = "hourly_rates";

/** The column of the contract the server sorts the rates by. */
export type RateSort = "code" | "label" | "is_active" | `rate.${string}`;

/** The bounds of a year, as the contract takes it (`Year`). */
export const FIRST_YEAR = 2000;
export const LAST_YEAR = 2100;

/** The column of the contract that sorts by the rate of a year. */
export function rateSort(year: number): RateSort {
  return `rate.${year.toString()}`;
}

/**
 * Every column the server sorts the rates by, whatever years the answer holds: a year the grid does
 * not hold leaves the order of the code.
 */
export const RATE_SORTS: readonly RateSort[] = [
  "code",
  "label",
  "is_active",
  ...Array.from({ length: LAST_YEAR - FIRST_YEAR + 1 }, (_, at) => rateSort(FIRST_YEAR + at)),
];

/** The parameter of the address that filters the grid on the state of its categories. */
export const RATE_STATE = "is_active";

/** The parameter of the address that names the year whose rate is bounded. */
export const RATE_YEAR = "rate_year";

/** The column of the rate a year, which `rate_min` and `rate_max` bound (`boundNames`). */
export const RATE_COLUMN = "rate";

/** A year of the address the contract takes; none otherwise. */
export function yearOf(value: string | null): number | undefined {
  const year = value !== null && /^\d{4}$/.test(value) ? Number(value) : Number.NaN;
  return year >= FIRST_YEAR && year <= LAST_YEAR ? year : undefined;
}
