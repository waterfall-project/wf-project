// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The client of the API, generated from the contract (PBS-1.2, WF-ARC-0060).
 *
 * The types come from `generated/schema.d.ts`, which `make generate-client` writes from the
 * bundled contract and nobody edits; `openapi-fetch` turns them into typed calls. Every call
 * to the API goes through a client made here: ESLint refuses the known ways of reaching the
 * network in any other module (WF-ARC-0020), and a client component importing this one —
 * only the server of Next calls the API (§4.3.1); `server-only` is the net of the build.
 */
import "server-only";

import createClient, { type Client } from "openapi-fetch";

import { UNREACHABLE_DIGEST } from "@/components/system/failure";

import type { paths } from "./generated/schema";

/** The path every operation of the contract lives under: the `servers` of the contract. */
export const API_PREFIX = "/api/v1";

/** A client of the API: what the rest of the front knows of openapi-fetch. */
export type ApiClient = Client<paths>;

/** What a client needs to know: where the API is, and how to reach it. */
export interface ApiClientOptions {
  /** The address of the API, without its prefix: `http://localhost:4010`. */
  readonly address: string;
  /** The function that sends requests; the platform's by default. */
  readonly fetch?: (request: Request) => Promise<Response>;
}

/**
 * The API did not answer at all: `fetch` itself rejected, as it does when the network or the
 * service is down. Marked here, where `fetch` is called, so that the API out of reach is told
 * apart from a defect that happens to throw a `TypeError` too (`reach`, `src/api/problem.ts`).
 * A read a screen cannot do without throws it too when a gateway says the service is down.
 *
 * Its digest is what the screen of failure receives of it in production, where Next forwards
 * nothing else of an error thrown on the server: it announces the API out of reach, not a
 * defect (`src/components/system/failure.ts`).
 */
export class Unreachable extends Error {
  readonly digest = UNREACHABLE_DIGEST;

  /** The rejection of `fetch`, kept as the cause; none when a gateway answered. */
  constructor(cause?: unknown) {
    super("the API cannot be reached", { cause });
    this.name = "Unreachable";
  }
}

/** Send a request, the rejection of `fetch` — a `TypeError` — marked as `Unreachable`. */
function marking(send: (request: Request) => Promise<Response>) {
  return async (request: Request): Promise<Response> => {
    try {
      return await send(request);
    } catch (error) {
      throw error instanceof TypeError ? new Unreachable(error) : error;
    }
  };
}

/** Make a client of the API served at an address. */
export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = new URL(API_PREFIX, options.address).toString();
  // The platform's fetch is looked up at each call: Next may have replaced it in the meantime.
  const send = options.fetch ?? ((request: Request) => fetch(request));
  return createClient<paths>({ baseUrl, fetch: marking(send) });
}
