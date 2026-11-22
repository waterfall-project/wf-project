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

import {
  componentDigest,
  type PlatformComponent,
  UNREACHABLE_DIGEST,
} from "@/components/system/failure";

import type { components, operations, paths } from "./generated/schema";

/** The path every operation of the contract lives under: the `servers` of the contract. */
export const API_PREFIX = "/api/v1";

/** The path of `listNodes`. */
type NodesPath = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";

type ListNodes = operations["listNodes"];
type ListNodesOk = ListNodes["responses"][200];
type ListNodesBody = ListNodesOk["content"]["application/json"];

/** The path of `compareRevisions`. */
type ComparisonPath = "/projects/{project_id}/revisions/comparison";

type CompareRevisions = operations["compareRevisions"];
type CompareRevisionsOk = CompareRevisions["responses"][200];
type CompareRevisionsBody = CompareRevisionsOk["content"]["application/json"];

/** A node of a comparison, read whole as a node is (`ClientPaths`), with its mark and its base. */
export type ComparedNode = components["schemas"]["Node"] &
  Pick<components["schemas"]["ComparedNodeRead"], "difference" | "changes" | "base" | "deltas">;

/**
 * The contract of the API as the client types it: that of `generated/schema.d.ts`, but for the
 * `items` of the `200` of `listNodes` and of `compareRevisions`, read as whole nodes (`Node`), a
 * node of a comparison with its mark and its base besides (`ComparedNode`). The contract types them
 * as projections (`NodeProjection`, #2485; `ComparedNodeRead`), a read with `fields` rendering only
 * the fields it named; a read only ever reads what it asked for by `fields` (`nodeFieldNames`,
 * `projectNodes`), so the front reads them whole — a grid reads a comparison as it reads its
 * structure (US-2330). This is the one place that says so. What the type does not say: a
 * property that a read did not ask for by `fields` is typed present but would be absent at run
 * time, which is why a read only reads what it asked for.
 */
type ClientPaths = Omit<paths, NodesPath | ComparisonPath> & {
  [P in NodesPath]: Omit<paths[P], "get"> & {
    get: Omit<ListNodes, "responses"> & {
      responses: Omit<ListNodes["responses"], 200> & {
        200: Omit<ListNodesOk, "content"> & {
          content: {
            "application/json": Omit<ListNodesBody, "items"> & {
              items: components["schemas"]["Node"][];
            };
          };
        };
      };
    };
  };
} & {
  [P in ComparisonPath]: Omit<paths[P], "get"> & {
    get: Omit<CompareRevisions, "responses"> & {
      responses: Omit<CompareRevisions["responses"], 200> & {
        200: Omit<CompareRevisionsOk, "content"> & {
          content: {
            "application/json": Omit<CompareRevisionsBody, "items"> & {
              items: ComparedNode[];
            };
          };
        };
      };
    };
  };
};

/** The `200` of `listNodes` as the client types it: the nodes whole (`ClientPaths`). */
export type ListNodesAnswer =
  ClientPaths[NodesPath]["get"]["responses"][200]["content"]["application/json"];

/** A client of the API: what the rest of the front knows of openapi-fetch. */
export type ApiClient = Client<ClientPaths>;

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
  readonly digest: string = UNREACHABLE_DIGEST;

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

/**
 * A component of the platform the front needs before a request leaves — Redis, which holds the
 * session — out of reach: still `Unreachable` to whoever tells the service out of reach, but its
 * digest names the component, so that the screen of failure says which one is down
 * (WF-EXP-0040-A, tableau 12). The message tells the log of the server the same.
 */
export class ComponentUnreachable extends Unreachable {
  override readonly digest: string;

  /** The component out of reach, the rejection that said so kept as the cause. */
  constructor(component: PlatformComponent, cause: unknown, message: string) {
    super(cause, message);
    this.name = "ComponentUnreachable";
    this.digest = componentDigest(component);
  }
}

/**
 * A write whose connection the API may have lost once it had left: no answer came, and `fetch` did
 * not say the request never left — the socket closed by the other side, reset, or silent past the
 * delay undici gives an answer, or a rejection it names no better. The API may have done it before
 * the connection was lost, or be doing it still: the screen says so, and reads anew what it shows
 * before offering to do it again (US-2240). A request known not to have left — the connection
 * refused, the name of the API unknown, the connection not opened in time (`NOT_SENT`) — is the API
 * out of reach (`Unreachable`), and nothing was done.
 *
 * Its digest is that of the API out of reach: a write thrown to the screen of failure, rather than
 * decoded into an outcome (`decode`, `src/api/problem.ts`), is told as before.
 */
export class Dropped extends Unreachable {
  /** The rejection of `fetch`, kept as the cause: what undici said of the connection lost. */
  constructor(cause: unknown) {
    super(cause, "the API lost the connection of a write once sent");
    this.name = "Dropped";
  }
}

/** The methods of a read: asked again, it changes nothing on the API. */
const READS = new Set(["GET", "HEAD"]);

/**
 * What the rejection of `fetch` carries when the API closed the connection before answering:
 * undici's socket closed by the other side (`UND_ERR_SOCKET`, « other side closed »), or reset.
 */
const DROPPED: ReadonlySet<string> = new Set(["UND_ERR_SOCKET", "ECONNRESET", "EPIPE"]);

/**
 * What the rejection of `fetch` carries when a request did not leave: the connection refused
 * (`ECONNREFUSED`), the name of the API unknown or not resolved in time (`ENOTFOUND`, `EAI_AGAIN`),
 * no route to its network or its host (`ENETUNREACH`, `EHOSTUNREACH`), its network or its host down
 * (`ENETDOWN`, `EHOSTDOWN`), or the connection not opened within undici's delay
 * (`UND_ERR_CONNECT_TIMEOUT`). Nothing was sent, and nothing was done. `ETIMEDOUT` is not of them:
 * the system gives it as well to a connection lost once opened, a write that left. Any
 * other rejection of a write — the connection dropped, reset, closed, destroyed or aborted, an
 * answer awaited past undici's delay, a code this list does not name, or none — is a write that may
 * have left (`Dropped`): telling it to be done again, when it may have been done, is the error this
 * list is short to avoid.
 */
const NOT_SENT: ReadonlySet<string> = new Set([
  "ECONNREFUSED",
  "ENOTFOUND",
  "EAI_AGAIN",
  "ENETUNREACH",
  "EHOSTUNREACH",
  "ENETDOWN",
  "EHOSTDOWN",
  "UND_ERR_CONNECT_TIMEOUT",
]);

/** Whether `fetch` rejected, the cause of its rejection naming one of the codes given. */
function failedWith(error: unknown, codes: ReadonlySet<string>): boolean {
  if (!(error instanceof TypeError)) {
    return false;
  }
  const { cause } = error;
  return (
    typeof cause === "object" &&
    cause !== null &&
    "code" in cause &&
    typeof cause.code === "string" &&
    codes.has(cause.code)
  );
}

/**
 * The rejection of `fetch` — a `TypeError` that carries a `cause`, or says "fetch failed", as
 * undici's does — marked as `Unreachable`, or as `Dropped` for a write that may have left
 * (`NOT_SENT`); any other error as it is, a `TypeError` thrown before the request leaves included.
 */
function marked(error: unknown, read: boolean): unknown {
  if (
    !(error instanceof TypeError) ||
    (error.cause === undefined && error.message !== "fetch failed")
  ) {
    return error;
  }
  return read || failedWith(error, NOT_SENT) ? new Unreachable(error) : new Dropped(error);
}

/**
 * Send a request, the rejection of `fetch` marked as `Unreachable`. A read the API dropped the
 * connection of before answering is sent once more: a connection kept alive and closed by the API
 * at the very moment it is reused — the API closes an idle one after a delay of its own, which the
 * platform's cannot be sure to stay under, its timer held up by a loaded loop. Sent again, it opens
 * a new one. A write is never sent again: the API may have done it before closing, and its loss is
 * marked `Dropped`, told apart from a write that did not leave. The read dropped a second time is
 * the API out of reach, and the first drop is written to the log of the server — its method and
 * path, never its query —, never passed over in silence.
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
      if (!read || !failedWith(error, DROPPED)) {
        throw marked(error, read);
      }
      // The path alone: the query may carry what the log of the server has no need of.
      const { pathname } = new URL(request.url);
      console.warn(`The API dropped the connection of ${request.method} ${pathname}`, error);
    }
    try {
      return await send(request);
    } catch (error) {
      throw marked(error, read);
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
  const client = createClient<ClientPaths>({ baseUrl, fetch: fetching, querySerializer: QUERY });
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
