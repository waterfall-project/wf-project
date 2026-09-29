// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of failure makes of an error a page threw: the API out of reach, or an
 * unexpected defect, with the identifier that finds it again in the logs.
 *
 * In production, Next forwards to an error boundary no more of an error thrown on the server
 * than its `digest` — its message and its class stay on the server. An error that sets its
 * own `digest` keeps it: the API out of reach carries `UNREACHABLE_DIGEST`, which the
 * boundary tells apart; an unexpected answer of the API carries the correlation identifier
 * of the request (WF-OBS-0020), which the API wrote in its logs; any other error, the digest
 * Next gives it, which Next writes in its own.
 *
 * Pure, and free of the client of the API: the boundary, a client component, reads it.
 */

/** The digest of an error that says the API did not answer at all. */
export const UNREACHABLE_DIGEST = "WATERFALL_API_UNREACHABLE";

/** An error as an error boundary receives it. */
export type BoundaryError = Error & { readonly digest?: string };

/**
 * What the screen of failure says: the API out of reach, or a defect, with its reference
 * when the error carries one.
 */
export type Failure =
  | { readonly kind: "unreachable" }
  | { readonly kind: "unexpected"; readonly reference: string | undefined };

/** Class the error a boundary caught. */
export function failureOf(error: BoundaryError): Failure {
  if (error.digest === UNREACHABLE_DIGEST) {
    return { kind: "unreachable" };
  }
  return { kind: "unexpected", reference: error.digest === "" ? undefined : error.digest };
}
