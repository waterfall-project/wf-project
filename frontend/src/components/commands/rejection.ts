// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen makes of a server action whose promise rejected: the action gave no outcome back
 * (#330). One rule for every screen that calls one — the cells of a grid, a paste, the import of a
 * file, the follow-up of a task —, the rule of the screen of failure itself (`failureOf`):
 *
 * - a `TypeError` is the API out of reach: what the `fetch` of the browser throws when it cannot
 *   reach the server of Next. The browser does not tell it from a `TypeError` thrown elsewhere,
 *   which passes for out of reach too — the one limit of the rule;
 * - any other rejection is classed by its `digest`, the one thing of an error thrown on the server
 *   Next forwards: the API out of reach (`UNREACHABLE_DIGEST`), a session lost
 *   (`SESSION_LOST_DIGEST`, `SESSION_REQUIRED_DIGEST`), which the notice says before it leads to
 *   the sign-in page — never at once: the write is told as not applied —, an account deactivated
 *   (`ACCOUNT_DEACTIVATED_DIGEST`), which it does not — signing in again would loop —, or the unexpected error
 *   (`INTERNAL_ERROR`, WF-ARC-0110) with its reference — the correlation identifier of the API, or
 *   the digest Next computed —, kept only when it has the form the contract gives a
 *   `correlation_id`: the notice shows it as the screen of failure does (WF-OBS-0020).
 *
 * Never "unreachable" for a defect: a user told to try again in a moment would try for ever.
 * Pure, and free of the client of the API: a client component calls it.
 */
import type { Outcome } from "@/api/problem";
import { type BoundaryError, failureOf } from "@/components/system/failure";

/** The form the contract gives a correlation identifier (`Problem.correlation_id`). */
const CORRELATION = /^[A-Za-z0-9._-]{1,64}$/;

/** The rejection as the screen of failure reads it: its digest, if it carries one. */
function asBoundaryError(error: unknown): BoundaryError {
  const digest =
    typeof error === "object" && error !== null && "digest" in error ? error.digest : undefined;
  return Object.assign(new Error("server action rejected"), {
    digest: typeof digest === "string" ? digest : undefined,
  });
}

/** The outcome of a loss the screen of failure tells apart: out of reach, signed out, deactivated. */
function outcomeOfLoss(
  kind: "unreachable" | "session_lost" | "signed_out" | "deactivated",
): Outcome<never> {
  switch (kind) {
    case "unreachable":
      return { kind: "unreachable" };
    case "session_lost":
    case "signed_out":
      return {
        kind: "signed_out",
        problem: { code: "SESSION_REQUIRED", status: 401 },
        conflictingObjectId: null,
      };
    case "deactivated":
      // A refusal that says so, not a session lost: no link to the sign-in page.
      return {
        kind: "refused",
        problem: { code: "ACCOUNT_DEACTIVATED", status: 401 },
        conflictingObjectId: null,
      };
  }
}

/** The outcome a rejected server action stands for. */
export function rejected(error: unknown): Outcome<never> {
  if (error instanceof TypeError) {
    return { kind: "unreachable" };
  }
  const failure = failureOf(asBoundaryError(error));
  if (failure.kind !== "unexpected") {
    return outcomeOfLoss(failure.kind);
  }
  const { reference } = failure;
  return {
    kind: "refused",
    problem: {
      code: "INTERNAL_ERROR",
      status: 500,
      ...(reference !== undefined && CORRELATION.test(reference)
        ? { correlation_id: reference }
        : {}),
    },
    conflictingObjectId: null,
  };
}
