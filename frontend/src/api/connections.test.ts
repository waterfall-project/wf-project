// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The client against a server on a real socket, through the platform's fetch: undici, as the server
 * of Next sends. The server answers the first request of a connection, kept alive, and drops the
 * connection when a second request arrives on it — what Prism does to a request sent on a
 * connection it has just closed, the loop of the client held up past its delay (#1145). A server of
 * `node:net`, bare: it answers as HTTP/1.1 does, and reads no more of it than it needs.
 */
import { createServer, type Server, type Socket } from "node:net";

import { afterEach, describe, expect, it, vi } from "vitest";

import { API_PREFIX, type Connections, createApiClient, Unreachable } from "./client";

/** How the server drops a connection a second request arrives on. */
type Drop = "closed" | "reset";

/** What the server saw: per connection, the request lines it received. */
interface Seen {
  readonly connections: string[][];
}

/** The answer of the first request of a connection, kept alive. */
const ANSWER = [
  "HTTP/1.1 200 OK",
  "Content-Type: application/json",
  "Content-Length: 2",
  "Connection: keep-alive",
  "Keep-Alive: timeout=5",
  "",
  "{}",
].join("\r\n");

let server: Server | undefined;
/** The sockets the server opened, destroyed with it: a connection kept alive would hold it. */
const sockets: Socket[] = [];

/**
 * Let undici give the connection back to its pool: it does once the body is read, a turn later —
 * the request sent at once would open another.
 */
function released(): Promise<void> {
  return new Promise((resolve) => setImmediate(resolve));
}

/** Start the server on a port of its own; the address of the API it stands for. */
async function serve(drop: Drop): Promise<{ address: string; seen: Seen }> {
  const seen: Seen = { connections: [] };
  const started = createServer((socket: Socket) => {
    sockets.push(socket);
    const lines: string[] = [];
    seen.connections.push(lines);
    let received = "";
    socket.on("data", (chunk: Buffer) => {
      received += chunk.toString("latin1");
      const requests = [...received.matchAll(/^([A-Z]+ \S+) HTTP\/1\.1\r$/gm)];
      for (const request of requests.slice(lines.length)) {
        lines.push(request[1] ?? "");
        if (lines.length === 1) {
          socket.write(ANSWER);
        } else if (drop === "closed") {
          socket.end();
        } else {
          socket.resetAndDestroy();
        }
      }
    });
    socket.on("error", () => undefined);
  });
  server = started;
  await new Promise<void>((resolve) => started.listen(0, "127.0.0.1", resolve));
  const at = started.address();
  if (at === null || typeof at === "string") {
    throw new Error("the server listens on no port");
  }
  return { address: `http://127.0.0.1:${String(at.port)}`, seen };
}

/** A client of the server, by the platform's fetch, its connections held as told. */
function clientOf(address: string, connections: Connections) {
  return createApiClient({ address, connections });
}

afterEach(async () => {
  vi.restoreAllMocks();
  for (const socket of sockets.splice(0)) {
    socket.destroy();
  }
  const running = server;
  server = undefined;
  await new Promise<void>((resolve) => {
    if (running === undefined) {
      resolve();
      return;
    }
    running.close(() => {
      resolve();
    });
  });
});

describe("the connections of the client, on a real socket (#1145)", () => {
  it.each<Drop>(["closed", "reset"])(
    "sends a read again on a new connection when the API drops (%s) the one kept alive",
    async (drop) => {
      const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
      const { address, seen } = await serve(drop);
      const client = clientOf(address, "kept");
      expect((await client.GET("/health")).response.status).toBe(200);
      await released();
      expect((await client.GET("/health")).response.status).toBe(200);
      const health = `GET ${API_PREFIX}/health`;
      // The second read went out on the connection kept alive, was dropped, and was answered on a
      // connection of its own.
      expect(seen.connections).toEqual([[health, health], [health]]);
      expect(warn).toHaveBeenCalledOnce();
    },
  );

  it("never sends a write again on a new connection: it is the API out of reach", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, seen } = await serve("closed");
    const client = clientOf(address, "kept");
    await client.GET("/health");
    await released();
    await expect(client.POST("/projects", { body: { label: "Poste" } })).rejects.toBeInstanceOf(
      Unreachable,
    );
    expect(seen.connections).toEqual([[`GET ${API_PREFIX}/health`, `POST ${API_PREFIX}/projects`]]);
    expect(warn).not.toHaveBeenCalled();
  });

  it("never reuses a connection when its connections are closed: nothing to drop", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, seen } = await serve("closed");
    const client = clientOf(address, "closed");
    expect((await client.GET("/health")).response.status).toBe(200);
    await released();
    expect((await client.POST("/projects", { body: { label: "Poste" } })).response.status).toBe(
      200,
    );
    await released();
    expect((await client.GET("/health")).response.status).toBe(200);
    expect(seen.connections).toEqual([
      [`GET ${API_PREFIX}/health`],
      [`POST ${API_PREFIX}/projects`],
      [`GET ${API_PREFIX}/health`],
    ]);
    expect(warn).not.toHaveBeenCalled();
  });
});
