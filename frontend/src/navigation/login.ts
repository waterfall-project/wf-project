// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way back from the sign-in: a refusal for want of a session (401) leads to
 * `/login?next=<the screen aimed at>`, and the route `/login`, once the session is open, goes
 * to the screen `next` names (US-0320). `next` is the path of the screen with its query — the
 * reading context of a project lives in the address, so the screen comes back as it was.
 *
 * The address is anyone's to write: `/login` follows only a path of this front, never another
 * site (`returnTarget`), or a link could send a user who just signed in elsewhere.
 *
 * `/login` is a route handler (`src/app/login/route.ts`), not a page: the identity provider
 * shows the screens of the sign-in, and Waterfall asks for no password (WF-ADM-0140).
 */
import { HOME } from "./home";

/** The route that opens the session, and comes back to the screen aimed at. */
export const LOGIN_ROUTE = "/login";

/** The parameter of the sign-in route that names the screen to come back to. */
export const NEXT_PARAMETER = "next";

// An origin nobody serves, to resolve `next` as a browser would: only the path is kept.
const FRONT = "http://front.invalid";

/**
 * The screen a `next` names, or the home page when it names none of this front or cannot be
 * read as an address at all — `//[`, `//a b`. `next` is resolved as a browser would resolve
 * it — which drops tabs and line breaks, and reads `//host` or `/\host` as another site —, and
 * followed only when it stays on this front: its path, its query and its fragment, never its
 * origin.
 */
export function returnTarget(next: string | null | undefined): string {
  if (next?.startsWith("/") !== true || !URL.canParse(next, FRONT)) {
    return HOME;
  }
  const target = new URL(next, FRONT);
  if (target.origin !== FRONT) {
    return HOME;
  }
  // The path is normalised only once resolved: `/.//host` or `/a/..//host` come out as
  // `//host`, which a browser reads as another site. The path given back is checked again.
  const path = `${target.pathname}${target.search}${target.hash}`;
  return path.startsWith("//") || path.startsWith("/\\") || !staysOnFront(path) ? HOME : path;
}

/** Whether a path, resolved as a browser would, stays on this front. */
function staysOnFront(path: string): boolean {
  return URL.canParse(path, FRONT) && new URL(path, FRONT).origin === FRONT;
}

/** The address of the sign-in route, which comes back to a screen: its path and its query. */
export function loginHref(screen: string): string {
  const query = new URLSearchParams({ [NEXT_PARAMETER]: returnTarget(screen) });
  return `${LOGIN_ROUTE}?${query.toString()}`;
}
