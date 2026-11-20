// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The point of metrics of the front (WF-OBS-0010, TFX-09): a server of HTTP of its own, on the
 * port `WATERFALL_METRICS_PORT` — the variable of the worker, 9100 in the image — that neither the
 * ingress nor Caddy routes: the public door answers 404 to `/metrics` and `/api/v1/metrics`
 * (`src/app/metrics`), and Prometheus reaches the port inside the network of the platform. Out of
 * the image, without the variable, nothing listens: the development server, the tests and the
 * end-to-end harness, which run several fronts on a machine, would share the one port.
 *
 * The requests are counted as the server of Next receives them: no hook of Next gives the status
 * of an answer, so the `request` event of the servers of Node is observed — the metrics' own
 * excepted — and the answer is counted when it ends.
 */
import "server-only";

import { IncomingMessage, Server, ServerResponse, createServer } from "node:http";

import { CONTENT_TYPE, FrontMetrics, requestKind } from "@/metrics/front-metrics";

/** The variable that holds the port of the metrics, the worker's. */
export const METRICS_PORT = "WATERFALL_METRICS_PORT";

/** The header Next reads to tell a server action from a page. */
const ACTION_HEADER = "next-action";

/** The port the metrics are served on; `undefined` when the environment says none. */
export function metricsPort(
  environment: Readonly<Record<string, string | undefined>> = process.env,
): number | undefined {
  const value = environment[METRICS_PORT]?.trim();
  if (value === undefined || value === "") {
    return undefined;
  }
  const port = Number(value);
  if (!/^\d+$/.test(value) || port < 1 || port > 65_535) {
    throw new Error(`${METRICS_PORT} must be a port between 1 and 65535: ${value}`);
  }
  return port;
}

/** The path of a request, without its query. */
function pathOf(request: IncomingMessage): string {
  return (request.url ?? "/").split("?", 1)[0] ?? "/";
}

/** Count the answer of a request when it ends, its duration from now. */
function track(metrics: FrontMetrics, request: IncomingMessage, response: ServerResponse): void {
  const started = performance.now();
  const kind = requestKind(pathOf(request), request.headers[ACTION_HEADER] !== undefined);
  response.once("finish", () => {
    metrics.requestEnded(kind, response.statusCode, (performance.now() - started) / 1000);
  });
}

/** Whether a value is the response of a server of HTTP. */
function isResponse(value: unknown): value is ServerResponse {
  return value instanceof ServerResponse;
}

/**
 * Observe every request the servers of HTTP of the process receive, but the ones in `ignored`.
 * Give what restores the servers as they were: `emit` is the `EventEmitter`'s, so it is shadowed
 * on the prototype of the servers, and the shadow removed.
 */
export function observeRequests(metrics: FrontMetrics, ignored: ReadonlySet<Server>): () => void {
  const original: unknown = Reflect.get(Server.prototype, "emit");
  if (typeof original !== "function") {
    throw new TypeError("the servers of HTTP have no emit");
  }
  const observed = function (this: Server, event: string | symbol, ...args: unknown[]): boolean {
    const [request, response] = args;
    if (
      event === "request" &&
      !ignored.has(this) &&
      request instanceof IncomingMessage &&
      isResponse(response)
    ) {
      track(metrics, request, response);
    }
    const emitted: unknown = Reflect.apply(original, this, [event, ...args]);
    return emitted === true;
  };
  Object.defineProperty(Server.prototype, "emit", {
    value: observed,
    configurable: true,
    writable: true,
  });
  return () => {
    Reflect.deleteProperty(Server.prototype, "emit");
  };
}

/** Answer the collection of Prometheus: the metrics at `/metrics`, nothing elsewhere. */
async function answer(
  metrics: FrontMetrics,
  request: IncomingMessage,
  response: ServerResponse,
): Promise<void> {
  if (request.method === "GET" && pathOf(request) === "/metrics") {
    response.writeHead(200, { "Content-Type": CONTENT_TYPE });
    response.end(await metrics.expose());
  } else {
    response.writeHead(404).end();
  }
}

/** The running point of metrics: where it listens, and what stops it. */
export interface MetricsServer {
  readonly port: number;
  close(): Promise<void>;
}

/** Serve the metrics on `port` — 0 for a free one —, counting the requests of the process. */
export async function serveMetrics(port: number): Promise<MetricsServer> {
  const metrics = new FrontMetrics();
  const server = createServer((request, response) => {
    answer(metrics, request, response).catch(() => {
      response.destroy();
    });
  });
  const restore = observeRequests(metrics, new Set([server]));
  try {
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(port, "0.0.0.0", resolve);
    });
  } catch (error) {
    restore();
    throw error;
  }
  const address = server.address();
  return {
    port: typeof address === "object" && address !== null ? address.port : port,
    close: () =>
      new Promise<void>((resolve) => {
        restore();
        server.close(() => {
          resolve();
        });
      }),
  };
}

/** The server started by this process, if any: a hook that runs twice starts one. */
let started: Promise<MetricsServer> | undefined;

/**
 * Start the point of metrics as the server of Next starts, if the environment names a port. A
 * port that cannot be taken is written, and the front goes on serving: the metrics are missing, the
 * screens are not.
 */
export async function startMetrics(): Promise<void> {
  let port: number | undefined;
  try {
    port = metricsPort();
  } catch {
    // A port that is none stopped the server at its check (`checkStart`): nothing to serve.
    return;
  }
  if (port === undefined || started !== undefined) {
    return;
  }
  started = serveMetrics(port);
  try {
    await started;
  } catch (error) {
    console.error(`${METRICS_PORT}: cannot listen on ${String(port)}: ${String(error)}`);
    started = undefined;
  }
}
