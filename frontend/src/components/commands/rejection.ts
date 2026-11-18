// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen makes of a server action whose promise rejected: the action gave no outcome back
 * (#330). One rule for every screen that calls one — the cells of a grid, a paste, the import of a
 * file, the follow-up of a task —, the rule of the screen of failure itself (`failureOf`):
 *
 * - a `TypeError` is what the `fetch` of the browser throws when it loses its link with the server
 *   of Next. For a write (`rejectedWrite`), the browser does not say whether the request left: the
 *   write may have been done, and the outcome says so (`sent`), as for the link of Next to the API
 *   (US-2240), the screen reading its state anew before it offers to do it again. Only a browser
 *   that knew itself offline (`navigator.onLine` false) BEFORE it sent tells nothing left: the API
 *   out of reach, to try again in a moment. A read (`rejectedRead`) writes nothing: it is that
 *   out of reach, online or not, never "may have been done".
 *   The browser does not tell it from a `TypeError` thrown elsewhere, which passes for lost too —
 *   the one limit of the rule;
 * - any other rejection is classed by its `digest`, the one thing of an error thrown on the server
 *   Next forwards: the API out of reach (`UNREACHABLE_DIGEST`), a session lost
 *   (`SESSION_LOST_DIGEST`, `SESSION_REQUIRED_DIGEST`) or closed (`SESSION_REVOKED_DIGEST`), which
 *   the notice says before it leads to the sign-in page — never at once: the write is told as not
 *   applied; the sign-in asks for the identifiers again for a session closed —, an account
 *   deactivated or not admitted (`ACCOUNT_DEACTIVATED_DIGEST`, `ACCOUNT_NOT_ADMITTED_DIGEST`),
 *   which it does not — signing in again would loop —, a component of the platform unavailable
 *   (`componentDigest`), which the notice names as the refusal of the API does, or the unexpected
 *   error (`INTERNAL_ERROR`, WF-ARC-0110) with its reference — the correlation identifier of the
 *   API, or the digest Next computed —, kept only when it has the form the contract gives a
 *   `correlation_id`: the notice shows it as the screen of failure does (WF-OBS-0020).
 *
 * Never "unreachable" for a defect: a user told to try again in a moment would try for ever.
 * Pure, and free of the client of the API: a client component calls it.
 */
import type { Outcome } from "@/api/problem";
import {
  type BoundaryError,
  type Failure,
  failureOf,
  isCorrelation,
} from "@/components/system/failure";

/** The rejection as the screen of failure reads it: its digest, if it carries one. */
function asBoundaryError(error: unknown): BoundaryError {
  const digest =
    typeof error === "object" && error !== null && "digest" in error ? error.digest : undefined;
  return Object.assign(new Error("server action rejected"), {
    digest: typeof digest === "string" ? digest : undefined,
  });
}

/** A refusal of the account that says so, not a session lost: no link to the sign-in page. */
function accountRefused(code: "ACCOUNT_DEACTIVATED" | "ACCOUNT_NOT_ADMITTED"): Outcome<never> {
  return { kind: "refused", problem: { code, status: 401 }, conflictingObjectId: null };
}

/**
 * The outcome of a loss the screen of failure tells apart: out of reach, signed out, the session
 * closed, the account deactivated or not admitted, a component of the platform unavailable.
 */
function outcomeOfLoss(failure: Exclude<Failure, { kind: "unexpected" }>): Outcome<never> {
  switch (failure.kind) {
    case "unreachable":
      return { kind: "unreachable" };
    case "session_lost":
    case "signed_out":
    case "revoked":
      return {
        kind: "signed_out",
        problem: {
          code: failure.kind === "revoked" ? "SESSION_REVOKED" : "SESSION_REQUIRED",
          status: 401,
        },
        conflictingObjectId: null,
      };
    case "deactivated":
      return accountRefused("ACCOUNT_DEACTIVATED");
    case "not_admitted":
      return accountRefused("ACCOUNT_NOT_ADMITTED");
    case "component_unavailable":
      return {
        kind: "refused",
        problem: {
          code: "COMPONENT_UNAVAILABLE",
          status: 503,
          params: { component: failure.component },
        },
        conflictingObjectId: null,
      };
  }
}

/**
 * The outcome a rejected server action stands for, `online` being what the browser knew of its
 * link before the request left: a write rejected by a `TypeError` may have been done unless the
 * browser knew itself offline (`navigator.onLine` false) when it sent it, a link lost after the
 * sending changing nothing to that.
 */
export function rejectedAfter(online: boolean): (error: unknown) => Outcome<never> {
  return (error) => {
    if (error instanceof TypeError) {
      return online ? { kind: "unreachable", sent: true } : { kind: "unreachable" };
    }
    return classed(error);
  };
}

/** Whether `onLine` says offline: an absent value, as a browser may give, does not. */
function offline(onLine: boolean | undefined): boolean {
  return onLine === false;
}

/** Whether the browser does not know itself offline: no `navigator`, or no `onLine`, is not offline. */
function notKnownOffline(): boolean {
  if (typeof navigator === "undefined") {
    return true;
  }
  return !offline(navigator.onLine);
}

/**
 * The reading of the rejection of a server action that writes, called as the action is: the state
 * of the link is read here, before any rejection can come — `action(x).catch(rejectedWrite())`
 * evaluates it in the very turn that sends the request, no event of the browser coming between.
 */
export function rejectedWrite(): (error: unknown) => Outcome<never> {
  return rejectedAfter(notKnownOffline());
}

/**
 * The outcome a rejected server action that only reads stands for: nothing was written, so a
 * `TypeError` is the API out of reach, online or not — never "may have been done".
 */
export function rejectedRead(error: unknown): Outcome<never> {
  return error instanceof TypeError ? { kind: "unreachable" } : classed(error);
}

/** The outcome of a rejection that is not a `TypeError`: classed by its digest. */
function classed(error: unknown): Outcome<never> {
  const failure = failureOf(asBoundaryError(error));
  if (failure.kind !== "unexpected") {
    return outcomeOfLoss(failure);
  }
  const { reference } = failure;
  return {
    kind: "refused",
    problem: {
      code: "INTERNAL_ERROR",
      status: 500,
      ...(isCorrelation(reference) ? { correlation_id: reference } : {}),
    },
    conflictingObjectId: null,
  };
}
