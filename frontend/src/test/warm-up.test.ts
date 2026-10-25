// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The warm-up of the paths against a server on a real socket, which answers as told by the address
 * asked: a page, a redirect, a refusal, an error of the server, a connection dropped unanswered —
 * every time, or the first time only, then a page, an error of the server or an answer that is not
 * HTTP —, an answer that is not HTTP, or a page held until the test lets it go; and the rule that
 * tells a dropped connection from any other failure.
 */
import { createServer, type Server, type Socket } from "node:net";

import { afterEach, describe, expect, it, vi } from "vitest";

import { isDropped, warm } from "../../e2e/warm-up";

/** What the server answers, by the address asked; any other, a page. */
const STATUSES = new Map([
  ["/redirect", 307],
  ["/refused", 405],
  ["/broken", 500],
  ["/down", 503],
  ["/dropped-then-broken", 500],
]);

/** The addresses whose connection is dropped the first time they are asked, and only then. */
const DROPPED_ONCE = new Set(["/dropped-once", "/dropped-then-broken", "/dropped-then-garbled"]);

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
      const first = !asked.includes(url);
      asked.push(url);
      if (url === "/dropped" || (DROPPED_ONCE.has(url) && first)) {
        socket.destroy();
      } else if (url === "/garbled" || url === "/dropped-then-garbled") {
        socket.end("garbled\r\n\r\n");
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
    expect(message).toMatch(/\/dropped failed again: .*\nfirst dropped: .*socket hang up/s);
    // Every address asked all the same, the dropped one twice, and each error written once.
    expect(asked).toHaveLength(7);
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

  it("asks once more an address whose connection was dropped, and writes it (#1301)", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    await warm(address, ["/dropped-once", "/a"]);
    expect([...asked].sort()).toEqual(["/a", "/dropped-once", "/dropped-once"]);
    expect(errors).not.toHaveBeenCalled();
    expect(warnings).toHaveBeenCalledOnce();
    expect(warnings.mock.calls[0]?.[0]).toMatch(
      /^Warm-up: \/dropped-once dropped, asked again: .*(?:ECONNRESET|EPIPE|socket hang up)/,
    );
  });

  it("fails on a second drop, naming the address, after asking it twice", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    const warming = warm(address, ["/dropped", "/a"]);
    await expect(warming).rejects.toThrow(
      /^Warm-up: 1 of 2 routes in error:\n\/dropped failed again: .*socket hang up.*\nfirst dropped: .*socket hang up/s,
    );
    expect(asked.filter((url) => url === "/dropped")).toHaveLength(2);
    expect(warnings).toHaveBeenCalledOnce();
  });

  it("fails on an error of the server answered once dropped, after asking it twice", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    await expect(warm(address, ["/dropped-then-broken"])).rejects.toThrow(
      new Error("Warm-up: 1 of 1 routes in error:\n/dropped-then-broken answered 500"),
    );
    expect(asked).toEqual(["/dropped-then-broken", "/dropped-then-broken"]);
    expect(warnings).toHaveBeenCalledOnce();
  });

  it("fails on another failure once dropped, keeping the message of the drop", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    await expect(warm(address, ["/dropped-then-garbled"])).rejects.toThrow(
      /^Warm-up: 1 of 1 routes in error:\n\/dropped-then-garbled failed again: .*Parse Error.*\nfirst dropped: .*socket hang up/s,
    );
    expect(asked).toEqual(["/dropped-then-garbled", "/dropped-then-garbled"]);
    expect(warnings).toHaveBeenCalledOnce();
  });

  it("asks an error of the server, or an answer that is not HTTP, only once", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { address, asked } = await serve();
    const warming = warm(address, ["/broken", "/down", "/garbled"]);
    await expect(warming).rejects.toThrow(/^Warm-up: 3 of 3 routes in error:\n/);
    const message = await warming.catch((error: unknown) => String(error));
    expect(message).toMatch(/\/garbled failed: /);
    expect([...asked].sort()).toEqual(["/broken", "/down", "/garbled"]);
    expect(warnings).not.toHaveBeenCalled();
  });
});

describe("a connection the server dropped (#1301)", () => {
  it.each(["read ECONNRESET", "write EPIPE", "apiRequestContext.get: socket hang up"])(
    "is told by %j",
    (message) => {
      expect(isDropped(message)).toBe(true);
    },
  );

  it.each([
    "connect ECONNREFUSED 127.0.0.1:3000",
    "apiRequestContext.get: Timeout 180000ms exceeded.",
    "apiRequestContext.get: Parse Error: Expected HTTP/",
    "socket hang upside",
  ])("is not told by %j", (message) => {
    expect(isDropped(message)).toBe(false);
  });
});
