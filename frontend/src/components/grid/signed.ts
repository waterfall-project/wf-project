// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a difference to a base is written (WF-IHM-0150, WF-IHM-0160): its sign written in front of a
 * positive one, nothing in front of zero or of a negative. The columns of difference of a grid
 * (`compared.tsx`) and the totals of a comparison (`totals-row.tsx`) say it the same way.
 */

/** An exact decimal that reads as zero: `0`, `-0`, `0.00`. */
const ZERO = /^-?0+(\.0+)?$/;

/** Whether a difference, as the server gives it, is zero. */
export function isZero(raw: string): boolean {
  return ZERO.test(raw);
}

/** A difference, its sign written in front of a positive one: the number of days, the amount. */
export function signed(raw: string, text: string): string {
  return raw.startsWith("-") || isZero(raw) ? text : `+${text}`;
}
