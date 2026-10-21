// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The warm-up of the paths against a server on a real socket, which answers as told by the address
 * asked: a page, a redirect, a refusal, an error of the server, a connection dropped unanswered, or
 * a page held until the test lets it go.
 */
import { createServer, type Server, type Socket } from "node:net";

import { afterEach, describe, expect, it, vi } from "vitest";

import { warm } from "../../e2e/warm-up";

/** What the server answers, by the address asked; any other, a page. */
const STATUSES = new Map([
  ["/redirect", 307],
  ["/refused", 405],
  ["/broken", 500],
  ["/down", 503],
]);

let server: Server | undefined;
/** The sockets the server opened, destroyed with it. */
const sockets: Socket[] = [];
/** Let the held page answer. */
let release: () => void = () => undefined;

/** The answer of a status, empty, the connection closed once sent. */
function answer(status: number): string {
  const location = status === 307 ? ["Location: /elsewhere"] : [];
  return [`HTTP/1.1 ${String(status)} -`, "Content-Length: 0", "Connection: close", ...location]
    .concat("", "")
    .join("\r\n");
}

/**
 * Start the server on a port of its own, a bare one of `node:net` that answers as HTTP/1.1 does;
 * its address, and the addresses it was asked for.
 */
async function serve(): Promise<{ address: string; asked: string[] }> {
  const asked: string[] = [];
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const started = createServer((socket: Socket) => {
    sockets.push(socket);
    socket.on("error", () => undefined);
    socket.once("data", (chunk: Buffer) => {
      const url = /^[A-Z]+ (\S+) HTTP\/1\.1\r$/m.exec(chunk.toString("latin1"))?.[1] ?? "";
      asked.push(url);
      if (url === "/dropped") {
        socket.destroy();
      } else if (url === "/held") {
        void held.then(() => socket.end(answer(200)));
      } else {
        socket.end(answer(STATUSES.get(url) ?? 200));
      }
    });
  });
  server = started;
  await new Promise<void>((resolve) => started.listen(0, "127.0.0.1", resolve));
  const at = started.address();
  if (at === null || typeof at === "string") {
    throw new Error("the server listens on no port");
  }
  return { address: `http://127.0.0.1:${String(at.port)}`, asked };
}

afterEach(async () => {
  vi.restoreAllMocks();
  release();
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

describe("the warm-up of the paths (#1145)", () => {
  it("asks each address once, its redirect not followed, and passes any answer but an error", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    await warm(address, ["/", "/redirect", "/refused", "/a", "/b"]);
    expect([...asked].sort()).toEqual(["/", "/a", "/b", "/redirect", "/refused"]);
    expect(errors).not.toHaveBeenCalled();
  });

  it("writes each error as it comes, then fails naming every address in error", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    const warming = warm(address, ["/broken", "/", "/dropped", "/down", "/a", "/b"]);
    await expect(warming).rejects.toThrow(/^Warm-up: 3 of 6 routes in error:\n/);
    const message = await warming.catch((error: unknown) => String(error));
    expect(message).toContain("/broken answered 500");
    expect(message).toContain("/down answered 503");
    expect(message).toContain("/dropped failed: ");
    // Every address asked all the same, and each error written once, on its own.
    expect(asked).toHaveLength(6);
    expect(
      errors.mock.calls.map(([written]: unknown[]) => String(written).split(" ")[1]).sort(),
    ).toEqual(["/broken", "/down", "/dropped"]);
  });

  it("writes an error as it comes, before the routes still compiling answer", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { address } = await serve();
    const warming = warm(address, ["/held", "/broken"]);
    await vi.waitFor(() => {
      expect(errors).toHaveBeenCalledOnce();
    });
    expect(errors.mock.calls[0]?.[0]).toBe("Warm-up: /broken answered 500");
    release();
    await expect(warming).rejects.toThrow("Warm-up: 1 of 2 routes in error:\n/broken answered 500");
  });
});
