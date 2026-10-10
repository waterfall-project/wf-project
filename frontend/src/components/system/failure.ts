// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of failure makes of an error a page threw: the API out of reach, no
 * session, or an unexpected defect, with the identifier that finds it again in the logs.
 *
 * In production, Next forwards to an error boundary no more of an error thrown on the server
 * than its `digest` — its message and its class stay on the server. An error that sets its
 * own `digest` keeps it: the API out of reach carries `UNREACHABLE_DIGEST`, a request the front
 * held no session for `SESSION_LOST_DIGEST`, a refusal of the API for want of a session
 * `SESSION_REQUIRED_DIGEST`, one for a deactivated account
 * `ACCOUNT_DEACTIVATED_DIGEST`, which the boundary tells apart; an unexpected
 * answer of the API carries the correlation identifier of the request (WF-OBS-0020), which
 * the API wrote in its logs, behind `CORRELATION_PREFIX`; any other error — an answer without
 * the envelope or without its identifier among them — the digest Next computes, which Next
 * writes in its own logs.
 *
 * The prefix keeps a value the API sends from standing as a digest Next or this module gives
 * a meaning to: a `NEXT_REDIRECT;…` would be followed by Next, a bare `WATERFALL_…` would be
 * taken for another failure.
 *
 * Pure, and free of the client of the API: the boundary, a client component, reads it.
 */

/** The digest of an error that says the API did not answer at all. */
export const UNREACHABLE_DIGEST = "WATERFALL_API_UNREACHABLE";

/**
 * The digest of an error that says the front holds no session that lives for the request, which
 * did not leave (`SessionLost`, `src/session/tokens.ts`): the screen of failure leads to the
 * sign-in page at once, which cannot loop.
 */
export const SESSION_LOST_DIGEST = "WATERFALL_SESSION_LOST";

/**
 * The digest of an error that says the API refused the read for want of a session (401), the
 * front having presented a token: the screen of failure offers the sign-in page, and goes nowhere
 * by itself — the token it would bring back could be refused again.
 */
export const SESSION_REQUIRED_DIGEST = "WATERFALL_SESSION_REQUIRED";

/** The digest of an error that says the API refused the read, the account being deactivated. */
export const ACCOUNT_DEACTIVATED_DIGEST = "WATERFALL_ACCOUNT_DEACTIVATED";

/** What comes before the correlation identifier of the API in a digest. */
export const CORRELATION_PREFIX = "WATERFALL_CORRELATION;";

/** The digest that carries a correlation identifier of the API. */
export function correlationDigest(correlationId: string): string {
  return `${CORRELATION_PREFIX}${correlationId}`;
}

/** An error as an error boundary receives it. */
export type BoundaryError = Error & { readonly digest?: string | undefined };

/**
 * What the screen of failure says: the API out of reach, no session — the front held none, and
 * the screen leads to the sign-in page at once, or the API refused the one it held, and the screen
 * offers the way to sign in —, the account deactivated, or a defect, with its reference when the
 * error carries one.
 */
export type Failure =
  | { readonly kind: "unreachable" | "session_lost" | "signed_out" | "deactivated" }
  | { readonly kind: "unexpected"; readonly reference: string | undefined };

/**
 * The reference a digest shows: the correlation identifier it carries, or itself; none when
 * it is empty — an empty identifier would show a reference followed by nothing.
 */
function referenceOf(digest: string | undefined): string | undefined {
  const reference = digest?.startsWith(CORRELATION_PREFIX)
    ? digest.slice(CORRELATION_PREFIX.length)
    : digest;
  return reference === "" ? undefined : reference;
}

/** Class the error a boundary caught. */
export function failureOf(error: BoundaryError): Failure {
  if (error.digest === UNREACHABLE_DIGEST) {
    return { kind: "unreachable" };
  }
  if (error.digest === SESSION_LOST_DIGEST) {
    return { kind: "session_lost" };
  }
  if (error.digest === SESSION_REQUIRED_DIGEST) {
    return { kind: "signed_out" };
  }
  if (error.digest === ACCOUNT_DEACTIVATED_DIGEST) {
    return { kind: "deactivated" };
  }
  return { kind: "unexpected", reference: referenceOf(error.digest) };
}
