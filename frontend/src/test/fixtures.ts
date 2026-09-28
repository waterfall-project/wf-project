// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The examples of the contract, for the unit tests of the front: the same data the fake back
 * serves (`fixtures/api/`), so that a page is tested on what it will receive.
 *
 * `fakeClient` is the generated client itself, over a transport that answers from those
 * examples instead of the network: the paths, parameters and bodies a page sends go through
 * openapi-fetch as they would in production, and the test reads them back from `calls`.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { API_PREFIX, type ApiClient, createApiClient } from "@/api/client";
import type { components, paths } from "@/api/generated/schema";

// From the directory of this file: in jsdom, `import.meta.url` is not a file URL.
const FIXTURES = join(import.meta.dirname, "../../../fixtures/api/");

// Never resolved: the fake transport answers before anything could leave.
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

/**
 * What the fake client answers to one call: the name of a fixture of `fixtures/api/`, served
 * with 200; the same with another status (201, 202); a `Problem`, served with its own status,
 * which the client returns as `error` instead of `data`; or a status without a body (204).
 */
export type FakeAnswer =
  | string
  | { readonly example: string; readonly status: number }
  | { readonly problem: Problem }
  | { readonly status: number };

/**
 * The answers of a fake client, by route. A sequence answers the calls of its route in turn
 * — `running`, then `succeeded` — and its last answer repeats.
 */
export type FakeAnswers = Partial<Readonly<Record<Route, FakeAnswer | readonly FakeAnswer[]>>>;

/** A call the fake client received. */
export interface FakeCall {
  /** The operation the call matched. */
  readonly route: Route;
  /** The path called, its parameters filled in, without the prefix of the contract. */
  readonly path: string;
  /** The query string the client serialized. */
  readonly query: URLSearchParams;
  /** The body: parsed when JSON, a `FormData` when multipart, a `Blob` otherwise. */
  readonly body: unknown;
}

/** A client of the API that answers from the examples of the contract, and records its calls. */
export type FakeClient = ApiClient & { readonly calls: readonly FakeCall[] };

/** What answers one route: how a request is matched, and what it is answered. */
interface Matcher {
  readonly route: Route;
  readonly method: string;
  readonly pattern: RegExp;
  readonly parameters: number;
  readonly sequence: readonly FakeAnswer[];
  /** How many calls the route has answered: where it stands in its sequence. */
  served: number;
}

/** Whether a key of the answers names a route; the type of `FakeAnswers` sees to the rest. */
function isRoute(key: string): key is Route {
  return /^(GET|POST|PUT|PATCH|DELETE) \//.test(key);
}

/** Compile a route into what matches a request: a parameter is one path segment. */
function matcher(route: Route, answer: FakeAnswer | readonly FakeAnswer[]): Matcher {
  const [method = "", template = ""] = route.split(" ");
  const pattern = new RegExp(`^${template.replaceAll(/\{[^}]+\}/g, "[^/]+")}$`);
  const sequence = isSequence(answer) ? answer : [answer];
  const parameters = template.split("{").length - 1;
  return { route, method, pattern, parameters, sequence, served: 0 };
}

/** The answer to the next call of a route: its sequence in turn, the last answer repeating. */
function next(entry: Matcher): FakeAnswer | undefined {
  const answer = entry.sequence[Math.min(entry.served, entry.sequence.length - 1)];
  entry.served += 1;
  return answer;
}

/** Whether an answer is a sequence of answers. */
function isSequence(answer: FakeAnswer | readonly FakeAnswer[]): answer is readonly FakeAnswer[] {
  return Array.isArray(answer);
}

/** The route a request calls: of those that match, the one with the fewest parameters. */
function matching(matchers: readonly Matcher[], method: string, path: string): Matcher | undefined {
  const found = matchers.filter((m) => m.method === method && m.pattern.test(path));
  found.sort((a, b) => a.parameters - b.parameters);
  return found[0];
}

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
function respond(answer: FakeAnswer): Response {
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
  return new Response(null, { status: answer.status });
}

/**
 * Make a client that answers each route from the examples of the contract. A call to a route
 * it has no answer for fails the test: an unexpected call is a defect, not an empty page.
 */
export function fakeClient(answers: FakeAnswers): FakeClient {
  const matchers = Object.entries(answers).flatMap(([key, answer]) =>
    isRoute(key) ? [matcher(key, answer)] : [],
  );
  const calls: FakeCall[] = [];

  const transport = async (request: Request): Promise<Response> => {
    const url = new URL(request.url);
    const path = url.pathname.slice(API_PREFIX.length);
    const found = matching(matchers, request.method, path);
    const answer = found === undefined ? undefined : next(found);
    if (found === undefined || answer === undefined) {
      throw new Error(`fakeClient: no answer for ${request.method} ${path}`);
    }
    calls.push({ route: found.route, path, query: url.searchParams, body: await bodyOf(request) });
    return respond(answer);
  };

  return Object.assign(createApiClient({ address: ADDRESS, fetch: transport }), { calls });
}
