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
 * - `unreachable`, the API did not answer at all — `fetch` rejected, or a gateway answered
 *   502, 503 or 504 without the envelope — a result of its own, never a `Problem` the API did
 *   not send, and never a blank screen.
 *
 * A code the catalogue does not know is decoded as `INTERNAL_ERROR`, the unexpected error of
 * the service: the screen never shows the bare key of a text.
 *
 * A client component imports only the types of this module; the decoding runs on the server.
 */
import { unstable_rethrow } from "next/navigation";

import { CATALOGUES } from "@/i18n/catalogues";
import { FALLBACK_LOCALE } from "@/i18n/locale";

import { Unreachable } from "./client";
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
 * Call the API, or `undefined` when it cannot be reached — `fetch` rejected, which the client
 * marks `Unreachable`. Any other error is a defect, and goes on, a `TypeError` thrown elsewhere
 * included: an error of Next first, which it must handle itself, then the rest — a fake
 * client's call without an answer among them.
 */
export async function reach<T>(call: () => Promise<T>): Promise<T | undefined> {
  try {
    return await call();
  } catch (error) {
    unstable_rethrow(error);
    if (error instanceof Unreachable) {
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

/**
 * The statuses a gateway in front of the API answers when the service behind it is down: said
 * without the envelope of the contract, they are the API out of reach, not a refusal of it.
 */
const GATEWAY_STATUSES: ReadonlySet<number> = new Set([502, 503, 504]);

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
 * The envelope of a refusal the catalogue can render. A body that is none — the page of a
 * proxy in front of the API — or whose code the catalogue does not know — a service newer than
 * the front — stands as the unexpected error of the service, at the status the answer carried:
 * never the bare key of a text nobody wrote.
 */
function envelope(body: unknown, status: number): Problem {
  return isProblem(body) && Object.hasOwn(CATALOGUES[FALLBACK_LOCALE].errors, body.code)
    ? body
    : { code: "INTERNAL_ERROR", status };
}

/** Decode an answer of the API into what the screen is to do with it. */
function decodeAnswer<T>(answer: Answer<T>): Outcome<T> {
  const { status, ok } = answer.response;
  if (ok) {
    return { kind: "done", data: answer.data as T };
  }
  if (GATEWAY_STATUSES.has(status) && !isProblem(answer.error)) {
    return { kind: "unreachable" };
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
