// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether the side bar is unfolded or folded into a rail, kept from one visit to the next in a
 * cookie of the front, as shadcn/ui keeps it: the root layout reads it, so the page is rendered
 * on the server with the bar as the user left it, without a jump once in the browser. Apart from
 * the component, which is a client one: a server module reads a constant of a client module as
 * a reference, not as its value.
 */

/** The cookie of the state of the side bar. */
export const SIDEBAR_COOKIE = "wf_sidebar_state";

/** A year: the bar stays as the user left it. */
const COOKIE_AGE = 60 * 60 * 24 * 365;

/** Whether the bar is unfolded, from the value of its cookie: unfolded unless folded. */
export function sidebarOpen(value: string | undefined): boolean {
  return value !== "false";
}

/** The cookie that keeps the state of the bar, as `document.cookie` takes it. */
export function sidebarCookie(open: boolean): string {
  return `${SIDEBAR_COOKIE}=${String(open)}; path=/; max-age=${String(COOKIE_AGE)}; samesite=lax`;
}
