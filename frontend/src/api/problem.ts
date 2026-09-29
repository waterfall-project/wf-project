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
 * A read of a server component that its screen cannot do without goes through `readOrFail`
 * instead: what is not its data is thrown — not found, the API out of reach, an unexpected
 * answer —, and the pages of the shell say it (`not-found.tsx`, `error.tsx`).
 *
 * A client component imports only the types of this module; the decoding runs on the server.
 */
import { notFound, unstable_rethrow } from "next/navigation";

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
 * Whether an answer is a gateway's saying the service behind it is down — 502, 503 or 504
 * without the envelope of the contract: the API out of reach, for a read as for an action.
 */
export function isGatewayFailure(response: Response, body: unknown): boolean {
  return GATEWAY_STATUSES.has(response.status) && !isProblem(body);
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

/**
 * An answer of the API to a read of a screen that is neither a success, nor "not found", nor
 * the API out of reach: a refusal without a session — a screen means nothing without an
 * account — or a failure of the service. The page does not swallow it: it throws, and the
 * screen of failure shows it, with the correlation identifier of the request when the
 * envelope carries one (WF-OBS-0020) — its digest, the one thing of it Next forwards.
 */
export class UnexpectedAnswer extends Error {
  readonly digest: string | undefined;

  /** The answer of an operation, by its `operationId`, its status and its envelope. */
  constructor(
    readonly operation: string,
    readonly status: number,
    body?: unknown,
  ) {
    super(`${operation} answered ${String(status)}`);
    this.name = "UnexpectedAnswer";
    this.digest = isProblem(body) ? body.correlation_id : undefined;
  }
}

/**
 * Call the API for a read a screen cannot do without, and give its data. Anything else
 * throws, for Next to render: a 404 is the object not found — or not readable, which the API
 * answers alike (WF-ADM-0110) — and the page is not found; the API out of reach, `fetch`
 * rejected or a gateway saying the service is down, is `Unreachable`; any other answer,
 * `UnexpectedAnswer`.
 */
export async function readOrFail<T>(operation: string, call: () => Promise<Answer<T>>): Promise<T> {
  const answer = await call();
  const { ok, status } = answer.response;
  if (ok) {
    return answer.data as T;
  }
  if (status === 404) {
    notFound();
  }
  if (isGatewayFailure(answer.response, answer.error)) {
    throw new Unreachable();
  }
  throw new UnexpectedAnswer(operation, status, answer.error);
}

/** Decode an answer of the API into what the screen is to do with it. */
function decodeAnswer<T>(answer: Answer<T>): Outcome<T> {
  const { status, ok } = answer.response;
  if (ok) {
    return { kind: "done", data: answer.data as T };
  }
  if (isGatewayFailure(answer.response, answer.error)) {
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
