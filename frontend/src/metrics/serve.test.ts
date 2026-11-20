// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { type IncomingHttpHeaders, type Server, createServer, get } from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { REQUESTS, REQUEST_DURATION, requestKind } from "./front-metrics";
import { METRICS_PORT, metricsPort, serveMetrics, type MetricsServer } from "./serve";

const closers: (() => Promise<void>)[] = [];

afterEach(async () => {
  for (const close of closers.splice(0).reverse()) {
    await close();
  }
});

/** What a server answered: its status, its type, its body. */
interface Reply {
  status: number | undefined;
  type: string | undefined;
  body: string;
}

/** Ask a server of the machine for a path, with headers. */
function ask(port: number, path: string, headers: IncomingHttpHeaders = {}): Promise<Reply> {
  return new Promise((resolve, reject) => {
    get({ host: "127.0.0.1", port, path, headers }, (response) => {
      const chunks: Buffer[] = [];
      response.on("data", (chunk: Buffer) => chunks.push(chunk));
      response.on("end", () => {
        resolve({
          status: response.statusCode,
          type: response.headers["content-type"],
          body: Buffer.concat(chunks).toString(),
        });
      });
    }).on("error", reject);
  });
}

/** Start a server of the application, which answers each path as the table says. */
async function application(statuses: Record<string, number>): Promise<number> {
  const server: Server = createServer((request, response) => {
    response.statusCode = statuses[request.url ?? ""] ?? 200;
    response.end("body");
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  closers.push(
    () =>
      new Promise<void>((resolve) => {
        server.close(() => {
          resolve();
        });
      }),
  );
  return (server.address() as AddressInfo).port;
}

/** Start the point of metrics on a free port. */
async function metrics(): Promise<MetricsServer> {
  const served = await serveMetrics(0);
  closers.push(() => served.close());
  return served;
}

/** Let the answers of the requests end, which the metrics count as they finish. */
function settled(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 20));
}

describe("the point of metrics of the front", () => {
  it("counts the requests and their durations by kind and status, in the format of Prometheus [WF-OBS-0010-A]", async () => {
    const served = await metrics();
    const port = await application({ "/boom": 503 });
    await ask(port, "/portfolio");
    await ask(port, "/boom");
    await ask(port, "/_next/static/a.js");
    await ask(port, "/projects", { "next-action": "abc" });
    await settled();
    const answer = await ask(served.port, "/metrics");
    expect(answer.status).toBe(200);
    expect(answer.type).toContain("text/plain");
    expect(answer.body).toContain(`${REQUESTS}{kind="page",status="200"} 1`);
    expect(answer.body).toContain(`${REQUESTS}{kind="page",status="503"} 1`);
    expect(answer.body).toContain(`${REQUESTS}{kind="asset",status="200"} 1`);
    expect(answer.body).toContain(`${REQUESTS}{kind="action",status="200"} 1`);
    expect(answer.body).toContain(`${REQUEST_DURATION}_count{kind="page"} 2`);
  });

  it("carries no path, no identity: the labels are the kind and the status alone [TFX-09]", async () => {
    const served = await metrics();
    const port = await application({});
    await ask(port, "/projects/0b0d7ee0-1c1c?token=secret");
    await settled();
    const { body } = await ask(served.port, "/metrics");
    expect(body).toContain(REQUESTS);
    expect(body).not.toContain("0b0d7ee0");
    expect(body).not.toContain("secret");
    expect(body).not.toContain("/projects");
  });

  it("does not count the collection itself, and answers 404 elsewhere than at /metrics [TFX-09]", async () => {
    const served = await metrics();
    await ask(served.port, "/metrics");
    expect((await ask(served.port, "/api/v1/metrics")).status).toBe(404);
    await settled();
    const { body } = await ask(served.port, "/metrics");
    expect(body).not.toContain(`${REQUESTS}{`);
  });

  it("counts again in a point of metrics started after another was closed [WF-OBS-0010-A]", async () => {
    const served = await serveMetrics(0);
    await served.close();
    const other = await metrics();
    const port = await application({});
    await ask(port, "/portfolio");
    await settled();
    expect((await ask(other.port, "/metrics")).body).toContain(`${REQUESTS}{kind="page"`);
  });
});

describe("the port of the metrics", () => {
  it("is the variable of the worker, and none when it is not set [WF-OBS-0010-A]", () => {
    expect(METRICS_PORT).toBe("WATERFALL_METRICS_PORT");
    expect(metricsPort({})).toBeUndefined();
    expect(metricsPort({ WATERFALL_METRICS_PORT: " " })).toBeUndefined();
    expect(metricsPort({ WATERFALL_METRICS_PORT: "9100" })).toBe(9100);
  });

  it.each(["abc", "0", "70000", "91.5"])("refuses %j, naming the variable", (value) => {
    expect(() => metricsPort({ WATERFALL_METRICS_PORT: value })).toThrow(
      `WATERFALL_METRICS_PORT must be a port between 1 and 65535: ${value}`,
    );
  });
});

describe("the kind of a request", () => {
  it.each([
    ["/_next/static/chunk.js", false, "asset"],
    ["/projects/abc", false, "page"],
    ["/projects/abc", true, "action"],
  ] as const)("names %s (action: %s) %s", (path, isAction, kind) => {
    expect(requestKind(path, isAction)).toBe(kind);
  });
});
