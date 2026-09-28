// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The client of the API, generated from the contract (PBS-1.2, WF-ARC-0060).
 *
 * The types come from `generated/schema.d.ts`, which `make generate-client` writes from the
 * bundled contract and nobody edits; `openapi-fetch` turns them into typed calls. Every call
 * to the API goes through a client made here: ESLint refuses any network call anywhere else
 * (WF-ARC-0020), and `server-only` keeps this module out of the browser — only the server
 * of Next calls the API (§4.3.1).
 */
import "server-only";

import createClient, { type Client } from "openapi-fetch";

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

/** Make a client of the API served at an address. */
export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = new URL(API_PREFIX, options.address).toString();
  return createClient<paths>(
    options.fetch === undefined ? { baseUrl } : { baseUrl, fetch: options.fetch },
  );
}
