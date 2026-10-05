// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The examples of the contract, for the unit tests of the front: the same data the fake back
 * serves (`fixtures/api/`), so that a page is tested on what it will receive.
 *
 * `fakeClient` is the generated client itself, with a middleware that answers each call
 * from those examples before it reaches the network: the paths, parameters and bodies a
 * page sends go through openapi-fetch as they would in production, and the test reads them
 * back from `calls`. An answer is typed by the operation it answers: only a status the
 * contract declares for it, with a body only when that status has one, and of its kind — a
 * fixture only among the examples the contract gives that status of that operation
 * (`generated/examples.d.ts`, which `make generate-client` writes).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { API_PREFIX, type ApiClient, createApiClient } from "@/api/client";
import type { Examples } from "@/api/generated/examples";
import type { components, paths } from "@/api/generated/schema";

// From the directory of this file: under a document, `import.meta.url` is not a file URL.
const FIXTURES = join(import.meta.dirname, "../../../fixtures/api/");

// Never reached: the middleware answers every call, or fails it.
const ADDRESS = "http://fake.invalid";

/** Read the value of an example of the contract, by the name of its fixture. */
export function example(name: string): unknown {
  const text = readFileSync(`${FIXTURES}${name}.json`, "utf-8");
  return (JSON.parse(text) as { value: unknown }).value;
}

/** The methods of the generated client that call an operation of the contract. */
export type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** An operation of the contract, as its method and path template: `GET /projects/{project_id}`. */
export type Route = {
  [P in keyof paths]: {
    [M in Method]: undefined extends paths[P][Lowercase<M>] ? never : `${M} ${P}`;
  }[Method];
}[keyof paths];

/** The error envelope of the contract (WF-ARC-0110). */
export type Problem = components["schemas"]["Problem"];

/** The responses the contract declares for an operation, by status. */
type Responses<R extends Route> =
  R extends `${infer M extends Method} ${infer P extends keyof paths}`
    ? paths[P][Lowercase<M>] extends { responses: infer X }
      ? X
      : never
    : never;

/** The fixtures the contract cites as examples of one status of an operation; none, never. */
type Cited<R extends Route, S> = R extends keyof Examples
  ? S extends keyof Examples[R]
    ? Examples[R][S]
    : never
  : never;

/**
 * The answers to one declared status, by what its body is. A JSON body answers the name of a
 * fixture of `fixtures/api/` the contract cites for it (`E`) — alone for 200; a Problem body, a
 * `Problem` carrying that status; any other body — an image, an archive, text — a `Blob` or a
 * string, served with one of the media types the status declares; a status without a body
 * answers the status alone.
 */
type StatusAnswer<X, S extends keyof X & number, E> = X[S] extends { content: infer C }
  ? "application/json" extends keyof C
    ? | (S extends 200 ? E : never)
      | (Keys<"example" | "status"> & { readonly example: E; readonly status: S })
    : "application/problem+json" extends keyof C
      ? Keys<"problem"> & { readonly problem: Problem & { readonly status: S } }
      : Keys<"body" | "type" | "status"> & {
          readonly body: Blob | string;
          readonly type: keyof C & string;
          readonly status: S;
        }
  : Keys<"status"> & { readonly status: S };

/** The keys of an answer: it must have none of the others, or a type would take any extra key. */
type Keys<K extends AnswerKey> = Partial<Readonly<Record<Exclude<AnswerKey, K>, never>>>;
type AnswerKey = "example" | "problem" | "body" | "type" | "status";

/** What the fake client may answer to one call of an operation. */
export type FakeAnswer<R extends Route> = {
  [S in keyof Responses<R> & number]: StatusAnswer<Responses<R>, S, Cited<R, S>>;
}[keyof Responses<R> & number];

/**
 * The answers of a fake client, by route. A sequence answers the calls of its route in turn
 * — `running`, then `succeeded` — and its last answer repeats.
 */
export type FakeAnswers = {
  readonly [R in Route]?: FakeAnswer<R> | readonly FakeAnswer<R>[];
};

/** An answer, whatever its operation: what the middleware serves. */
type AnyAnswer =
  | string
  | { readonly example: string; readonly status: number }
  | { readonly problem: Problem }
  | { readonly body: Blob | string; readonly type: string; readonly status: number }
  | { readonly status: number };

/** A call the fake client received. */
export interface FakeCall {
  /** The operation the call named, as openapi-fetch received it. */
  readonly route: string;
  /** The path called, its parameters filled in, without the prefix of the contract. */
  readonly path: string;
  /** The query string the client serialized. */
  readonly query: URLSearchParams;
  /** The body: parsed when JSON, a `FormData` when multipart, a `Blob` otherwise. */
  readonly body: unknown;
}

/** A client of the API that answers from the examples of the contract, and records its calls. */
export type FakeClient = ApiClient & { readonly calls: readonly FakeCall[] };

/** Read the body of a request the way a test inspects it. */
async function bodyOf(request: Request): Promise<unknown> {
  if (request.body === null) {
    return undefined;
  }
  const type = request.headers.get("content-type") ?? "";
  if (type.includes("json")) {
    const value: unknown = JSON.parse(await request.text());
    return value;
  }
  return type.startsWith("multipart/form-data") ? request.formData() : request.blob();
}

/** Make the response of one answer. */
function respond(answer: AnyAnswer): Response {
  if (typeof answer === "string") {
    return Response.json(example(answer));
  }
  if ("example" in answer) {
    return Response.json(example(answer.example), { status: answer.status });
  }
  if ("problem" in answer) {
    const headers = { "content-type": "application/problem+json" };
    return Response.json(answer.problem, { status: answer.problem.status, headers });
  }
  if ("body" in answer) {
    const headers = { "content-type": answer.type };
    return new Response(answer.body, { status: answer.status, headers });
  }
  return new Response(null, { status: answer.status });
}

/** Whether an answer is a sequence of answers. */
function isSequence(answer: AnyAnswer | readonly AnyAnswer[]): answer is readonly AnyAnswer[] {
  return Array.isArray(answer);
}

/** Refuse the network: a call the middleware let through would be a defect of the fake. */
function refuse(request: Request): Promise<Response> {
  return Promise.reject(
    new Error(`fakeClient: ${request.method} ${request.url} reached the network`),
  );
}

/** How a fake client answers besides what: when. */
export interface FakeTiming {
  /**
   * Hold the answer to a call until the promise given settles — two calls in flight, the
   * second answered first —; nothing, and the call is answered at once. The call is recorded
   * before it is held; `index` counts the calls of its route, from 0.
   */
  readonly hold?: (route: string, index: number) => Promise<unknown> | undefined;
}

/**
 * Make a client that answers each route from the examples of the contract. A call to a route
 * it has no answer for fails the test: an unexpected call is a defect, not an empty page. A
 * table keyed by any string — a `Record<string, string>` — is refused: it would name no
 * operation, and its examples would escape the typing of each.
 */
export function fakeClient<const A extends FakeAnswers>(
  answers: string extends keyof A ? never : A,
  timing: FakeTiming = {},
): FakeClient {
  const table: Readonly<Record<string, AnyAnswer | readonly AnyAnswer[] | undefined>> = answers;
  const served = new Map<string, number>();
  const calls: { -readonly [K in keyof FakeCall]: FakeCall[K] }[] = [];
  const client = createApiClient({ address: ADDRESS, fetch: refuse });

  client.use({
    async onRequest({ request, schemaPath }) {
      const route = `${request.method} ${schemaPath}`;
      const given = table[route] ?? [];
      const sequence = isSequence(given) ? given : [given];
      const index = served.get(route) ?? 0;
      const answer = sequence[Math.min(index, sequence.length - 1)];
      if (answer === undefined) {
        throw new Error(`fakeClient: no answer for ${route}`);
      }
      served.set(route, index + 1);
      // The call takes its place before the first await: calls made together are recorded
      // in the order they were made, whatever their bodies take to read.
      const url = new URL(request.url);
      const call = {
        route,
        path: url.pathname.slice(API_PREFIX.length),
        query: url.searchParams,
        body: undefined as unknown,
      };
      calls.push(call);
      call.body = await bodyOf(request);
      await timing.hold?.(route, index);
      return respond(answer);
    },
  });

  return Object.assign(client, { calls });
}

/**
 * Make a client of the API whose every call finds the API out of reach: `fetch` rejects, as when
 * the service is down, and the client marks it `Unreachable` — what the decoder says as such.
 */
export function unreachable(): ApiClient {
  return createApiClient({
    address: ADDRESS,
    fetch: () => Promise.reject(new TypeError("fetch failed")),
  });
}
