// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The floor of a dense grid: the height under which its frame does not shrink on a screen that
 * fills the window, and never above the height of its content, so that a grid of a few rows has
 * no empty band under its totals (#1041).
 */

/** The height of a row, in `rem` — `h-7`, a dense grid —. */
export const ROW_REM = 1.75;

/**
 * The height of the header and of the totals, in `rem` — `h-8` —: the rows brought into view come
 * out from under them.
 */
export const EDGE_REM = 2;

/** The floor of a frame whose content is tall, in `rem`: ten rem, 160 px. */
export const FLOOR_REM = 10;

/** The two borders of the frame, which the height of the frame counts. */
const BORDER_PX = 2;

/**
 * The height of the content of a grid of `rows` rows, in `rem`: the header, the totals, and the
 * rows — an empty grid has one, which says so.
 */
export function contentRem(rows: number): number {
  return 2 * EDGE_REM + Math.max(rows, 1) * ROW_REM;
}

/**
 * The minimum height of the frame of a grid of `rows` rows: the floor, or the content when it is
 * lower, borders included.
 */
export function floorOf(rows: number): string {
  return `min(${String(FLOOR_REM)}rem, calc(${String(contentRem(rows))}rem + ${String(BORDER_PX)}px))`;
}

/** The height of the bar above a grid and the gap under it, in `rem`: `h-7` and `gap-2`. */
const BAR_REM = ROW_REM + 0.5;

/**
 * The minimum height of what holds a grid and its bar: the floor of the frame and the bar, so that
 * the wrappers of a screen that fills the window, which shrink to what is left, never push the frame
 * below its floor over what follows it (#1033).
 */
export function withBar(rows: number): string {
  return `calc(${floorOf(rows)} + ${String(BAR_REM)}rem)`;
}

/**
 * The width of the bar above a grid: that of the frame of its table as the browser laid it out,
 * the scroll bars it takes included, when it is measured; its table and its two borders until then.
 */
export function barWidthOf(frame: number | undefined, table: number): string {
  return `${String(frame !== undefined && frame > 0 ? frame : table + BORDER_PX)}px`;
}
