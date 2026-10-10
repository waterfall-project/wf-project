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
 *   naming the object in conflict when the envelope carries it — or one of its refusals by field,
 *   the object that holds a value already taken — and the screen knows it;
 * - `signed_out` (401), no session — or none the front holds, and the request did not leave —,
 *   not the deactivated account, a `refused` whose code the screen says (`ACCOUNT_DEACTIVATED`),
 *   since signing in again would loop —: the screen leads to the sign-in page, which comes back
 *   to the screen once signed in again (`loginHref`, `src/navigation/login.ts`);
 * - `unreachable`, the API did not answer at all — `fetch` rejected, or a gateway answered
 *   502, 503 or 504 without the envelope — a result of its own, never a `Problem` the API did
 *   not send, and never a blank screen.
 *
 * A code the catalogue does not know is decoded as `INTERNAL_ERROR`, the unexpected error of
 * the service: the screen never shows the bare key of a text.
 *
 * A read of a server component that its screen cannot do without goes through `readOrFail`
 * instead: what is not its data is thrown — not found, the API out of reach, no session, an
 * unexpected answer, the deactivated account —, and the pages of the shell say it (`not-found.tsx`, `error.tsx`). A read it
 * can do without goes through `readUnlessRefused`, which gives nothing on the refusals it expects.
 *
 * A client component imports only the types of this module; the decoding runs on the server.
 */
import { notFound, unstable_rethrow } from "next/navigation";

import {
  ACCOUNT_DEACTIVATED_DIGEST,
  correlationDigest,
  SESSION_LOST_DIGEST,
  SESSION_REQUIRED_DIGEST,
} from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { FALLBACK_LOCALE } from "@/i18n/locale";

import { Unreachable } from "./client";
import { isDeactivation, kindOf, type ProblemKind } from "./problem-kind";
import type { components } from "./generated/schema";

export { kindOf, type ProblemKind } from "./problem-kind";

/** The error envelope of the contract (WF-ARC-0110). */
export type Problem = components["schemas"]["Problem"];

/** What an action gives back: the answer of the API, its refusal, or the API out of reach. */
export type Outcome<T> =
  | { readonly kind: "done"; readonly data: T }
  | {
      readonly kind: ProblemKind;
      readonly problem: Problem;
      /**
       * The object the refusal is about, `params.conflicting_object_id` — or that of its first refusal
       * by field that names one —, when it names one.
       */
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
 * the API out of reach, nor a refusal for want of a session: a failure of the service. The
 * page does not swallow it: it throws, and the screen of failure shows it, with the
 * correlation identifier of the request when the envelope carries one (WF-OBS-0020) — in its
 * digest, the one thing of it Next forwards, behind a prefix that keeps a value of the API
 * from standing as a digest Next gives a meaning to (`correlationDigest`).
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
    const correlation = isProblem(body) ? body.correlation_id : undefined;
    this.digest = correlation === undefined ? undefined : correlationDigest(correlation);
  }
}

/**
 * The API refused a read of a screen for want of a session (401): the screen of failure
 * leads to the sign-in page, which comes back to the screen once signed in again — its
 * digest, the one thing of it Next forwards, says so.
 */
export class SignedOut extends Error {
  readonly digest = SESSION_REQUIRED_DIGEST;

  /** The refusal of an operation, by its `operationId`. */
  constructor(readonly operation: string) {
    super(`${operation} answered 401`);
    this.name = "SignedOut";
  }
}

/**
 * The API refused a read of a screen because the account is deactivated (401
 * `ACCOUNT_DEACTIVATED`): the screen of failure says so, and does not lead to the sign-in page,
 * which would loop.
 */
export class AccountDeactivated extends Error {
  readonly digest = ACCOUNT_DEACTIVATED_DIGEST;

  /** The refusal of an operation, by its `operationId`. */
  constructor(readonly operation: string) {
    super(`${operation} answered 401, the account being deactivated`);
    this.name = "AccountDeactivated";
  }
}

/**
 * What a read throws on an answer that is neither a success, nor "not found", nor the API
 * out of reach: `SignedOut` on 401, `AccountDeactivated` on the 401 that names the deactivated
 * account, `UnexpectedAnswer` otherwise.
 */
export function refusalOf(operation: string, status: number, body: unknown): Error {
  if (isDeactivation(status, isProblem(body) ? body.code : undefined)) {
    return new AccountDeactivated(operation);
  }
  return status === 401 ? new SignedOut(operation) : new UnexpectedAnswer(operation, status, body);
}

/**
 * Call the API for a read a screen cannot do without, and give its data. Anything else
 * throws, for Next to render: a 404 is the object not found — or not readable, which the API
 * answers alike (WF-ADM-0110) — and the page is not found; the API out of reach, `fetch`
 * rejected or a gateway saying the service is down, is `Unreachable`; a 401, `SignedOut`;
 * any other answer, `UnexpectedAnswer`.
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
  throw refusalOf(operation, status, answer.error);
}

/** A code of the catalogue of errors (WF-ARC-0110). */
export type ErrorCode = components["schemas"]["ErrorCode"];

/**
 * A refusal a screen expects and does without: its status, and the code its envelope carries when
 * the status alone does not say which refusal it is — a 409 says a state forbids, not which.
 */
export interface ExpectedRefusal {
  readonly status: number;
  readonly code?: ErrorCode;
}

/** Whether an answer is a refusal the screen expects. */
function isExpected(answer: Answer<unknown>, expected: ExpectedRefusal): boolean {
  if (answer.response.status !== expected.status) {
    return false;
  }
  const body = answer.error;
  return (
    expected.code === undefined ||
    (typeof body === "object" && body !== null && "code" in body && body.code === expected.code)
  );
}

/**
 * What a read its screen can do without gives: its data, or the expected refusal it met and its
 * envelope — whose `fields` may say which parameter it refused.
 */
export type ReadOrRefused<T, R extends ExpectedRefusal> =
  | { readonly kind: "read"; readonly data: T }
  | { readonly kind: "refused"; readonly refusal: R; readonly problem: Problem };

/**
 * Call the API for a read its screen can do without, and says why when it is refused: its data;
 * on a refusal the screen expects, which of them — the first that the answer matches —, for the
 * screen to say the data unavailable and why, and show the rest. Any other answer follows the
 * rule of `readOrFail`: not found, the API out of reach, no session, an unexpected answer.
 */
export async function readOrRefused<T, R extends ExpectedRefusal>(
  operation: string,
  expected: readonly R[],
  call: () => Promise<Answer<T>>,
): Promise<ReadOrRefused<T, R>> {
  const answer = await call();
  const refusal = answer.response.ok
    ? undefined
    : expected.find((each) => isExpected(answer, each));
  if (refusal !== undefined) {
    return { kind: "refused", refusal, problem: envelope(answer.error, answer.response.status) };
  }
  return { kind: "read", data: await readOrFail(operation, () => Promise.resolve(answer)) };
}

/**
 * Call the API for a read its screen can do without: its data; `undefined` on a refusal the
 * screen expects, which says the data unavailable and shows the rest. Any other answer follows
 * the rule of `readOrFail`: not found, the API out of reach, no session, an unexpected answer.
 */
export async function readUnlessRefused<T>(
  operation: string,
  expected: readonly ExpectedRefusal[],
  call: () => Promise<Answer<T>>,
): Promise<T | undefined> {
  const read = await readOrRefused(operation, expected, call);
  return read.kind === "read" ? read.data : undefined;
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
  return {
    kind: kindOf(status, problem.code),
    problem,
    conflictingObjectId: conflictingOf(problem),
  };
}

/**
 * The object a refusal is about: the one its envelope names (`params.conflicting_object_id`), or else
 * the first one its refusals by field name — a value already held, which a 409 `ALREADY_EXISTS` says
 * at each field it points at, by the object that holds it (WF-REF-0030, WF-REF-0040).
 */
function conflictingOf({ params, fields }: Problem): string | null {
  const named = [params, ...(fields ?? []).map((field) => field.params)]
    .map((each) => each?.conflicting_object_id)
    .find((id) => typeof id === "string");
  return typeof named === "string" ? named : null;
}

/** Whether an error is the session of the request lost: the request did not leave. */
function isSessionLost(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    error.digest === SESSION_LOST_DIGEST
  );
}

/**
 * Call the API and decode its answer, `unreachable` when it does not answer at all. Without a
 * session that lives, the request does not leave, and the outcome is `signed_out`, as if the API
 * had refused it: the action is not applied, and its screen says so before it leads to the
 * sign-in page — never the screen of failure, which would lead there at once.
 */
export async function decode<T>(call: () => Promise<Answer<T>>): Promise<Outcome<T>> {
  let answer: Answer<T> | undefined;
  try {
    answer = await reach(call);
  } catch (error) {
    if (isSessionLost(error)) {
      const problem: Problem = { code: "SESSION_REQUIRED", status: 401 };
      return { kind: "signed_out", problem, conflictingObjectId: null };
    }
    throw error;
  }
  return answer === undefined ? { kind: "unreachable" } : decodeAnswer(answer);
}

/** The outcome of an action whose success is all the screen needs to know. */
export type Settled = Outcome<null>;

/**
 * An outcome, its data left on the server: what an action gives back when the screen only needs
 * to know it succeeded — a session opened, a password changed —, and nothing of the answer.
 */
export function settled<T>(outcome: Outcome<T>): Settled {
  return outcome.kind === "done" ? { kind: "done", data: null } : outcome;
}

/** The reference of a background task (WF-ARC-0090). */
export type BackgroundTask = components["schemas"]["BackgroundTaskRef"];

/**
 * Call an operation that answers with a background task — one that starts it, or the read of
 * its progress — and decode its answer. The motive of a failed task is an envelope within a
 * success, which the decoding of a refusal does not see: it is held to the same rule — a code
 * the catalogue does not know is the unexpected error —, and a failure without a motive is the
 * unexpected error too, so that the screen always has a motive to render.
 */
export async function decodeTask(
  call: () => Promise<Answer<BackgroundTask>>,
): Promise<Outcome<BackgroundTask>> {
  const outcome = await decode(call);
  return outcome.kind === "done" ? { kind: "done", data: withMotive(outcome.data) } : outcome;
}

/**
 * A task as the screen may render it: the motive of a failure held to the rule of the catalogue,
 * the unexpected error when the API gave none or one the catalogue does not know.
 */
function withMotive(task: BackgroundTask): BackgroundTask {
  if (task.status !== "failed") {
    return task;
  }
  const motive = task.problem ?? undefined;
  return { ...task, problem: envelope(motive, motive?.status ?? 500) };
}

/** A page of the background tasks of the caller (`listBackgroundTasks`). */
export interface BackgroundTaskPage {
  readonly items: readonly BackgroundTask[];
}

/**
 * Call an operation that answers with a list of background tasks and decode its answer, the
 * motive of each failed task held to the rule of `decodeTask`.
 */
export async function decodeTasks(
  call: () => Promise<Answer<BackgroundTaskPage>>,
): Promise<Outcome<readonly BackgroundTask[]>> {
  const outcome = await decode(call);
  return outcome.kind === "done"
    ? { kind: "done", data: outcome.data.items.map(withMotive) }
    : outcome;
}
