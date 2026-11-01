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
import { isApplicationPath } from "./application-path";
import { HOME } from "./home";

/** The route that opens the session, and comes back to the screen aimed at. */
export const LOGIN_ROUTE = "/login";

/** The parameter of the sign-in route that names the screen to come back to. */
export const NEXT_PARAMETER = "next";

/**
 * The parameter of the sign-in route that makes it the sign-out of a session the front lost
 * (#689): a sign-in the realm answers silently, whose token closes the sessions of the account.
 * It carries the ticket the server action of the sign-out armed, which the route takes once: a
 * link of another site, which names none, is a sign-in like any other.
 */
export const SIGN_OUT_PARAMETER = "sign_out";

/**
 * The parameter of the sign-in route that has the realm ask for the identifiers again
 * (`prompt=login`), even though its session in the browser lives: the API refused a token of a
 * sign-in that precedes the closing of the sessions of the account (401 `SESSION_REVOKED`, #855),
 * which a sign-in of the same session would only bring again. Anyone may write it: it does no more
 * than ask for the identifiers.
 */
export const REAUTHENTICATE_PARAMETER = "reauthenticate";

/**
 * Whether the sign-in a refusal of the API leads to asks for the identifiers again: on
 * `SESSION_REVOKED` only. An expired token (`SESSION_EXPIRED`), or none, does not: the session of
 * the realm signs the user in again without them.
 */
export function asksIdentifiers(code: unknown): boolean {
  return code === "SESSION_REVOKED";
}

/** Where the sign-out of a session the front lost leads the browser: the ticket it armed. */
export function signOutHref(ticket: string): string {
  return `${LOGIN_ROUTE}?${new URLSearchParams({ [SIGN_OUT_PARAMETER]: ticket }).toString()}`;
}

/**
 * The route that ends the session of the realm of an account Waterfall does not admit, which the
 * API does not close (#664): the screen of failure offers it.
 */
export const REALM_SIGN_OUT_ROUTE = "/auth/sign-out";

/** The page that says a sign-in could not be made, the service out of reach (#687). */
export const SIGN_IN_UNAVAILABLE_ROUTE = `${LOGIN_ROUTE}/unavailable`;

// An origin nobody serves, to resolve `next` as a browser would: only the path is kept.
const FRONT = "http://front.invalid";

/**
 * The screen a `next` names, or the home page when it names none of this front or cannot be
 * read as an address at all — `//[`, `//a b`. `next` must first be a path of this front as written
 * (`isApplicationPath`); it is then resolved as a browser would, and followed only when it stays on
 * this front: its path, its query and its fragment, never its origin.
 */
export function returnTarget(next: string | null | undefined): string {
  if (typeof next !== "string" || !isApplicationPath(next) || !URL.canParse(next, FRONT)) {
    return HOME;
  }
  const target = new URL(next, FRONT);
  if (target.origin !== FRONT) {
    return HOME;
  }
  // The path is normalised only once resolved: `/.//host` or `/a/..//host` come out as
  // `//host`, which a browser reads as another site. The path given back is checked again.
  const path = `${target.pathname}${target.search}${target.hash}`;
  return !isApplicationPath(path) || !staysOnFront(path) ? HOME : path;
}

/** Whether a path, resolved as a browser would, stays on this front. */
function staysOnFront(path: string): boolean {
  return URL.canParse(path, FRONT) && new URL(path, FRONT).origin === FRONT;
}

/**
 * The page that says a sign-in could not be made, which offers it again for a screen; with
 * `reauthenticate`, a sign-in that asks for the identifiers again, as the one that failed did:
 * the session of the realm would still bring a token of the same sign-in (#855).
 */
export function signInUnavailableHref(screen: string, reauthenticate = false): string {
  const query = new URLSearchParams({ [NEXT_PARAMETER]: returnTarget(screen) });
  if (reauthenticate) {
    query.set(REAUTHENTICATE_PARAMETER, "1");
  }
  return `${SIGN_IN_UNAVAILABLE_ROUTE}?${query.toString()}`;
}

/**
 * The address of the sign-in route, which comes back to a screen: its path and its query; with
 * `reauthenticate`, a sign-in that asks for the identifiers again — on `SESSION_REVOKED` only.
 */
export function loginHref(screen: string, reauthenticate = false): string {
  const query = new URLSearchParams({ [NEXT_PARAMETER]: returnTarget(screen) });
  if (reauthenticate) {
    query.set(REAUTHENTICATE_PARAMETER, "1");
  }
  return `${LOGIN_ROUTE}?${query.toString()}`;
}
