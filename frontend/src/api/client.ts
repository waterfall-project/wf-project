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
  /**
   * The bearer token a request carries (`Authorization: Bearer …`), asked for at each request —
   * the session may have been refreshed or closed in the meantime; none when it gives none, or
   * without it.
   */
  readonly bearer?: Bearer;
  /** How the requests hold their connections to the API: kept alive by default (`Connections`). */
  readonly connections?: Connections;
}

/**
 * How the requests hold their connections to the API. `kept`, the platform's: a connection is kept
 * alive once answered, and the next request reuses it. `closed`: each request opens a connection of
 * its own, closed once answered (`Connection: close`) — the end-to-end harness's (#1145). Its
 * servers are Prism, the fake back or the proxy of the contract, which closes a connection idle
 * for five seconds; the development server, loaded by four workers, has its loop held up for
 * longer than the margin undici keeps under that delay, and sends a request on a connection Prism
 * has just closed. No delay of its own would do: the loop held up delays its timer as well.
 */
export type Connections = "kept" | "closed";

/** What gives the token of a request: the session of the front, or the fixed token of the mock. */
export type Bearer = () => string | undefined | Promise<string | undefined>;

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

  /**
   * The rejection of `fetch`, kept as the cause; none when a gateway answered. A component the
   * request needs before it leaves — Redis, the realm — names itself in `message`, so that the log
   * of the server says which was out of reach.
   */
  constructor(cause?: unknown, message = "the API cannot be reached") {
    super(message, { cause });
    this.name = "Unreachable";
  }
}

/** The methods of a read: asked again, it changes nothing on the API. */
const READS = new Set(["GET", "HEAD"]);

/**
 * What the rejection of `fetch` carries when the API closed the connection before answering:
 * undici's socket closed by the other side (`UND_ERR_SOCKET`, « other side closed »), or reset.
 */
const DROPPED = new Set(["UND_ERR_SOCKET", "ECONNRESET", "EPIPE"]);

/** Whether `fetch` rejected because the API closed the connection before answering. */
function isDropped(error: unknown): boolean {
  if (!(error instanceof TypeError)) {
    return false;
  }
  const { cause } = error;
  return (
    typeof cause === "object" &&
    cause !== null &&
    "code" in cause &&
    typeof cause.code === "string" &&
    DROPPED.has(cause.code)
  );
}

/** The rejection of `fetch` — a `TypeError` — marked as `Unreachable`; any other error as it is. */
function marked(error: unknown): unknown {
  return error instanceof TypeError ? new Unreachable(error) : error;
}

/**
 * Send a request, the rejection of `fetch` marked as `Unreachable`. A read the API dropped the
 * connection of before answering is sent once more: a connection kept alive and closed by the API
 * at the very moment it is reused — the API closes an idle one after a delay of its own, which the
 * platform's cannot be sure to stay under, its timer held up by a loaded loop. Sent again, it opens
 * a new one. A write is never sent again: the API may have done it before closing. The read dropped
 * a second time is the API out of reach, and the first drop is written to the log of the server,
 * never passed over in silence.
 */
function transport(send: (request: Request) => Promise<Response>, connections: Connections) {
  return async (request: Request): Promise<Response> => {
    if (connections === "closed") {
      request.headers.set("Connection", "close");
    }
    const read = READS.has(request.method);
    try {
      // A read keeps its request whole, to be sent again.
      return await send(read ? request.clone() : request);
    } catch (error) {
      if (!read || !isDropped(error)) {
        throw marked(error);
      }
      console.warn(`The API dropped the connection of ${request.method} ${request.url}`, error);
    }
    try {
      return await send(request);
    } catch (error) {
      throw marked(error);
    }
  };
}

/**
 * How a query is written: every list the contract takes in a query is one parameter, its values
 * apart by commas (`explode: false`) — `kinds=task,estimate_line`, never the parameter repeated.
 */
const QUERY = { array: { style: "form", explode: false } } as const;

/** Make a client of the API served at an address. */
export function createApiClient(options: ApiClientOptions): ApiClient {
  const baseUrl = new URL(API_PREFIX, options.address).toString();
  // The platform's fetch is looked up at each call: Next may have replaced it in the meantime.
  const send = options.fetch ?? ((request: Request) => fetch(request));
  const fetching = transport(send, options.connections ?? "kept");
  const client = createClient<paths>({ baseUrl, fetch: fetching, querySerializer: QUERY });
  const { bearer } = options;
  if (bearer !== undefined) {
    // The first middleware: whatever comes after sees the request as it leaves.
    client.use({
      async onRequest({ request }) {
        const token = await bearer();
        if (token !== undefined) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
        return request;
      },
    });
  }
  return client;
}
