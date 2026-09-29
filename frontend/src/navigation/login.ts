// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way back from the sign-in page: a refusal for want of a session (401) leads to
 * `/login?next=<the screen aimed at>`, and the sign-in page, once signed in again, goes to
 * the screen `next` names (US-0320). `next` is the path of the screen with its query — the
 * reading context of a project lives in the address, so the screen comes back as it was.
 *
 * The address is anyone's to write: the sign-in page follows only a path of this front, never
 * another site (`returnTarget`), or a link could send a user who just signed in elsewhere.
 */

/** The route of the sign-in page. */
export const LOGIN_ROUTE = "/login";

/** The parameter of the sign-in page that names the screen to come back to. */
export const NEXT_PARAMETER = "next";

/** Where the sign-in page leads when `next` names no screen of this front: the home page. */
const HOME = "/";

/**
 * The screen a `next` names, or the home page when it names none of this front: a path that
 * starts with a single `/` — neither `//host` nor `/\host`, which a browser reads as another
 * site.
 */
export function returnTarget(next: string | null | undefined): string {
  if (next?.startsWith("/") !== true || next.startsWith("//") || next.startsWith("/\\")) {
    return HOME;
  }
  return next;
}

/** The address of the sign-in page, which comes back to a screen: its path and its query. */
export function loginHref(screen: string): string {
  const query = new URLSearchParams({ [NEXT_PARAMETER]: returnTarget(screen) });
  return `${LOGIN_ROUTE}?${query.toString()}`;
}
