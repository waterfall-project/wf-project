// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one decoder of what an action of the server gets back from the API: every server action
 * of `src/api/actions/` hands its component an `Outcome`, never a raw answer, so that each
 * screen meets a refusal the same way (WF-ARC-0110):
 *
 * - `done`, the answer of the API;
 * - `refused`, a `Problem` whose code and parameters the catalogue renders;
 * - `stale` (412), the object changed since it was read: the screen offers to reload it;
 * - `conflict` (409), the state of an object forbids the operation: the screen explains it,
 *   naming the object in conflict when the envelope carries it and the screen knows it;
 * - `signed_out` (401), no session: the screen leads to the sign-in page, which comes back to
 *   the screen once signed in again (`loginHref`, `src/navigation/login.ts`);
 * - `unreachable`, the API did not answer at all — a result of its own, never a `Problem`
 *   the API did not send, and never a blank screen.
 *
 * A client component imports only the types of this module; the decoding runs on the server.
 */
import { unstable_rethrow } from "next/navigation";

import type { components } from "./generated/schema";

/** The error envelope of the contract (WF-ARC-0110). */
export type Problem = components["schemas"]["Problem"];

/** What a refusal of the API asks of the screen, by the status that carries it. */
export type ProblemKind = "refused" | "stale" | "conflict" | "signed_out";

/** What an action gives back: the answer of the API, its refusal, or the API out of reach. */
export type Outcome<T> =
  | { readonly kind: "done"; readonly data: T }
  | {
      readonly kind: ProblemKind;
      readonly problem: Problem;
      /** The object the refusal is about, `params.conflicting_object_id`, when it names one. */
      readonly conflictingObjectId: string | null;
    }
  | { readonly kind: "unreachable" };

/** An answer of openapi-fetch, whatever the operation. */
export interface Answer<T> {
  readonly data?: T;
  readonly error?: unknown;
  readonly response: Response;
}

/**
 * Call the API, or `undefined` when it cannot be reached — `fetch` failing, a `TypeError`:
 * openapi-fetch lets it through. Any other error is a defect, and goes on: an error of Next
 * first, which it must handle itself, then the rest — a fake client's call without an answer
 * among them.
 */
export async function reach<T>(call: () => Promise<T>): Promise<T | undefined> {
  try {
    return await call();
  } catch (error) {
    unstable_rethrow(error);
    if (error instanceof TypeError) {
      return undefined;
    }
    throw error;
  }
}

/** The reaction a status asks for; any other refusal is rendered as it is. */
const KIND_BY_STATUS: Readonly<Record<number, ProblemKind>> = {
  401: "signed_out",
  409: "conflict",
  412: "stale",
};

/** Whether the body of a refusal is the envelope of the contract. */
function isProblem(body: unknown): body is Problem {
  return (
    typeof body === "object" &&
    body !== null &&
    "code" in body &&
    typeof body.code === "string" &&
    "status" in body &&
    typeof body.status === "number"
  );
}

/**
 * The envelope of a refusal. A body that is none — the page of a proxy in front of the API —
 * says nothing the catalogue can render: it stands as the unexpected error of the service, at
 * the status the answer carried.
 */
function envelope(body: unknown, status: number): Problem {
  return isProblem(body) ? body : { code: "INTERNAL_ERROR", status };
}

/** Decode an answer of the API into what the screen is to do with it. */
function decodeAnswer<T>(answer: Answer<T>): Outcome<T> {
  const { status, ok } = answer.response;
  if (ok) {
    return { kind: "done", data: answer.data as T };
  }
  const problem = envelope(answer.error, status);
  const conflicting = problem.params?.conflicting_object_id;
  return {
    kind: KIND_BY_STATUS[status] ?? "refused",
    problem,
    conflictingObjectId: typeof conflicting === "string" ? conflicting : null,
  };
}

/** Call the API and decode its answer, `unreachable` when it does not answer at all. */
export async function decode<T>(call: () => Promise<Answer<T>>): Promise<Outcome<T>> {
  const answer = await reach(call);
  return answer === undefined ? { kind: "unreachable" } : decodeAnswer(answer);
}
