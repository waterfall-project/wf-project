// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The two legs around Prism (`contract-proxy.ts`), between a client and an API, around a Prism that
 * does what Prism does to a body that is not JSON: read it as text, and write each byte past 0x7f
 * as U+FFFD. Every one is a server of `node:http` on a free port of the loopback, the legs as the
 * container runs them; only the time the bytes are kept is shortened, where it is what is tried.
 */
import { randomBytes } from "node:crypto";
import {
  type IncomingHttpHeaders,
  type IncomingMessage,
  type OutgoingHttpHeaders,
  request,
  type RequestListener,
  type Server,
} from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { entrance, exit, isJson, Kept, RAW, serve } from "./contract-proxy";

const LOOPBACK = "127.0.0.1";
const MEBIBYTE = 1024 * 1024;
// The part of a deposit in parts, as the API cuts an archive (`cut`, `platform/uploads.py`).
const PART = 5 * MEBIBYTE;
const OCTETS = { "content-type": "application/octet-stream" };

interface Answer {
  status: number;
  headers: IncomingHttpHeaders;
  body: Buffer;
}

async function read(message: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of message) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

function call(
  address: string,
  method: string,
  headers: OutgoingHttpHeaders = {},
  body?: Buffer,
): Promise<Answer> {
  return new Promise((resolve, reject) => {
    const sent = request(address, { method, headers }, (answer) => {
      read(answer).then((received) => {
        resolve({ status: answer.statusCode ?? 0, headers: answer.headers, body: received });
      }, reject);
    });
    sent.on("error", reject);
    sent.end(body);
  });
}

const servers: Server[] = [];

afterEach(async () => {
  await Promise.all(
    servers.splice(0).map(
      (server) =>
        new Promise<void>((resolve) => {
          server.closeAllConnections();
          server.close(() => {
            resolve();
          });
        }),
    ),
  );
});

async function started(listener: RequestListener): Promise<URL> {
  const server = await serve(listener, 0, LOOPBACK);
  servers.push(server);
  return new URL(`http://${LOOPBACK}:${String((server.address() as AddressInfo).port)}`);
}

/** What Prism does to a body that is not JSON: read as text, written back as UTF-8. */
function spoiled(headers: IncomingHttpHeaders, body: Buffer): Buffer {
  return isJson(headers["content-type"]) ? body : Buffer.from(body.toString("utf8"), "utf8");
}

const OWN = new Set(["content-length", "transfer-encoding", "connection", "host"]);

function passedOn(headers: IncomingHttpHeaders, body: Buffer, bodiless: boolean) {
  const passed: OutgoingHttpHeaders = Object.fromEntries(
    Object.entries(headers).filter(([name]) => !OWN.has(name) || (bodiless && name !== "host")),
  );
  if (!bodiless) {
    passed["content-length"] = String(body.length);
  }
  return passed;
}

const PROBLEM = { "content-type": "application/problem+json" };
const violation = JSON.stringify({
  type: "https://stoplight.io/prism/errors#VIOLATIONS",
  title: "Request/Response not valid",
  status: 500,
});

interface Behaviour {
  /** Held before the request is passed on, and before the answer is. */
  holdRequest?: number;
  holdAnswer?: number;
  /** The name of the bytes of an answer dropped, as a Prism that would not pass the header. */
  dropName?: boolean;
}

/**
 * A Prism in proxy: each body that is not JSON spoiled both ways, the headers passed on, an answer
 * of a path under `/violation` refused by a problem of its own, as `--errors` refuses an answer the
 * contract does not declare, and an upstream out of reach answered by a 502.
 */
function fakePrism(upstream: URL, behaviour: Behaviour = {}): RequestListener {
  const hold = (ms = 0) =>
    new Promise((resolve) => {
      setTimeout(resolve, ms);
    });
  const handle = async (incoming: IncomingMessage, outgoing: Parameters<RequestListener>[1]) => {
    const body = spoiled(incoming.headers, await read(incoming));
    await hold(behaviour.holdRequest);
    let answer: Answer;
    try {
      answer = await call(
        `${upstream.origin}${incoming.url ?? "/"}`,
        incoming.method ?? "GET",
        passedOn(incoming.headers, body, false),
        body,
      );
    } catch {
      outgoing.writeHead(502, PROBLEM).end('{"title":"upstream","status":502}');
      return;
    }
    await hold(behaviour.holdAnswer);
    if (incoming.url?.startsWith("/violation") === true) {
      outgoing.writeHead(500, PROBLEM).end(violation);
      return;
    }
    const answered = spoiled(answer.headers, answer.body);
    const bodiless = incoming.method === "HEAD" || answer.status === 204;
    const headers = passedOn(answer.headers, answered, bodiless);
    if (behaviour.dropName === true) {
      Reflect.deleteProperty(headers, RAW);
    }
    outgoing.writeHead(answer.status, headers).end(answered);
  };
  return (incoming, outgoing) => {
    void handle(incoming, outgoing);
  };
}

interface Received {
  method: string;
  url: string;
  headers: IncomingHttpHeaders;
  body: Buffer;
}

/**
 * An API that keeps what it receives, echoes what is put or posted to `/echo` with its type, serves
 * the bytes given it under `/blob`, in JSON under `/json`, a HEAD of `/blob` with its length.
 */
function fakeApi(blob: Buffer, received: Received[]): RequestListener {
  const json = JSON.stringify({ label: "Révision « été » — 5 €", lines: [1, 2, 3] });
  return (incoming, outgoing) => {
    void read(incoming).then((body) => {
      const url = incoming.url ?? "";
      const method = incoming.method ?? "";
      received.push({ method, url, headers: incoming.headers, body });
      if (url.endsWith("/echo")) {
        const type = incoming.headers["content-type"] ?? "application/octet-stream";
        outgoing.writeHead(200, { "content-type": type }).end(body);
      } else if (url.endsWith("/json")) {
        outgoing.writeHead(200, { "content-type": "application/json" }).end(json);
      } else if (method === "HEAD") {
        outgoing.writeHead(200, { ...OCTETS, "content-length": String(blob.length) }).end();
      } else if (url.endsWith("/hop")) {
        outgoing
          .writeHead(204, { connection: "x-answer-hop", "x-answer-hop": "1", "x-kept": "1" })
          .end();
      } else if (url.includes("/parts/")) {
        outgoing.writeHead(204).end();
      } else {
        outgoing.writeHead(200, OCTETS).end(blob);
      }
    });
  };
}

/** The bench: client ▶ entrance ▶ fake Prism ▶ exit ▶ fake API, the address of the entrance. */
async function bench(
  blob: Buffer = Buffer.alloc(0),
  behaviour: Behaviour = {},
  lifetime = 120_000,
): Promise<{ front: string; received: Received[]; prism: URL }> {
  const received: Received[] = [];
  const kept = new Kept(lifetime);
  const api = await started(fakeApi(blob, received));
  const exitAt = await started(exit(api, kept));
  const prism = await started(fakePrism(exitAt, behaviour));
  const front = await started(entrance(prism, kept));
  return { front: front.origin, received, prism };
}

/** Every byte, then random ones: what Prism spoils and what it does not. */
function binary(length: number): Buffer {
  const every = Buffer.from(Array.from({ length: 256 }, (_, byte) => byte));
  return Buffer.concat([every, randomBytes(Math.max(0, length - every.length))]).subarray(
    0,
    length,
  );
}

describe("the legs around Prism", () => {
  it("leave a fake Prism that spoils the bytes as Prism does", async () => {
    const { prism, received } = await bench();
    const sent = binary(1024);
    await call(`${prism.origin}/echo`, "PUT", OCTETS, sent);
    expect(received[0]?.body.length).toBeGreaterThan(sent.length);
  });

  it("carry a body that is not JSON byte for byte, both ways", async () => {
    const blob = binary(64 * 1024);
    const { front, received } = await bench(blob);
    const sent = binary(32 * 1024);
    const echoed = await call(`${front}/api/v1/echo`, "PUT", OCTETS, sent);
    expect(received[0]?.body.equals(sent)).toBe(true);
    expect(received[0]?.headers["content-length"]).toBe(String(sent.length));
    expect(received[0]?.headers[RAW]).toBeUndefined();
    expect(echoed.status).toBe(200);
    expect(echoed.body.equals(sent)).toBe(true);
    expect(echoed.headers[RAW]).toBeUndefined();
    const downloaded = await call(`${front}/api/v1/blob`, "GET");
    expect(downloaded.body.equals(blob)).toBe(true);
    expect(downloaded.headers["content-length"]).toBe(String(blob.length));
  });

  it("pass a body in JSON as it is, both ways, never named", async () => {
    const { front, received } = await bench();
    const sent = Buffer.from(JSON.stringify({ label: "Coût « réel » — 12 €" }), "utf8");
    const json = { "content-type": "application/json; charset=utf-8" };
    const echoed = await call(`${front}/api/v1/echo`, "POST", json, sent);
    expect(received[0]?.body.equals(sent)).toBe(true);
    expect(received[0]?.headers[RAW]).toBeUndefined();
    expect(echoed.body.equals(sent)).toBe(true);
    const answered = await call(`${front}/api/v1/json`, "GET");
    expect(JSON.parse(answered.body.toString("utf8"))).toEqual({
      label: "Révision « été » — 5 €",
      lines: [1, 2, 3],
    });
  });

  it("give the refusal of Prism as it is, of an answer in JSON or not", async () => {
    const { front } = await bench(binary(4096));
    for (const path of ["/violation/json", "/violation/blob"]) {
      const refused = await call(`${front}${path}`, "GET");
      expect(refused.status).toBe(500);
      expect(refused.headers["content-type"]).toBe("application/problem+json");
      expect(refused.body.toString("utf8")).toBe(violation);
    }
  });

  it("carry a body past 5 MiB, cut on a byte inside a character, intact both ways", async () => {
    // An archive past 5 MiB, binary at its head, then characters of two and three bytes — U+FFFD
    // among them, as Prism spoiled an archive downloaded (EF BF BD) —, its part cut on the first
    // byte inside a character from 5 MiB on: each part is then no UTF-8 at its edge, and Prism,
    // reading it as text, changes its length, which the API refuses (#2695).
    const text = Buffer.from("€\uFFFDé".repeat(Math.ceil(PART / 8)), "utf8");
    const archive = Buffer.concat([binary(MEBIBYTE), text]);
    let cut = PART;
    while (((archive[cut] ?? 0) & 0xc0) !== 0x80) {
      cut += 1;
    }
    expect(cut - PART).toBeLessThan(3);
    const { front, received, prism } = await bench(archive);
    const downloaded = await call(`${front}/api/v1/backups/blob/content`, "GET");
    expect(downloaded.body.equals(archive)).toBe(true);
    const parts = [downloaded.body.subarray(0, cut), downloaded.body.subarray(cut)];
    for (const [index, part] of parts.entries()) {
      const put = await call(`${front}/api/v1/parts/${String(index + 1)}`, "PUT", OCTETS, part);
      expect(put.status).toBe(204);
    }
    const deposited = received.filter(({ url }) => url.includes("/parts/"));
    expect(deposited.map(({ body }) => body.length)).toEqual(parts.map(({ length }) => length));
    expect(Buffer.concat(deposited.map(({ body }) => body)).equals(archive)).toBe(true);
    // The same part straight to the fake Prism, past the legs, is not the one sent.
    await call(`${prism.origin}/api/v1/parts/2`, "PUT", OCTETS, parts[1]);
    expect(received.at(-1)?.body.length).not.toBe(parts[1]?.length);
  });

  it("carry twenty exchanges at once, each with its own bytes", async () => {
    const { front } = await bench();
    const bodies = Array.from({ length: 20 }, (_, index) => binary(1000 + index * 997));
    const echoed = await Promise.all(
      bodies.map((body) => call(`${front}/api/v1/echo`, "PUT", OCTETS, body)),
    );
    expect(echoed.map(({ body }, index) => body.equals(bodies[index] ?? Buffer.alloc(0)))).toEqual(
      bodies.map(() => true),
    );
  });

  it("fail a request whose bytes outlived their time, never sending those Prism spoiled", async () => {
    const { front, received } = await bench(Buffer.alloc(0), { holdRequest: 200 }, 50);
    const refused = await call(`${front}/api/v1/echo`, "PUT", OCTETS, binary(2048));
    expect(refused.status).toBe(502);
    expect(received).toEqual([]);
  });

  it("fail an answer whose bytes outlived their time, never giving those Prism spoiled", async () => {
    const { front } = await bench(binary(2048), { holdAnswer: 200 }, 50);
    const refused = await call(`${front}/api/v1/blob`, "GET");
    expect(refused.status).toBe(502);
    expect(refused.headers["content-type"]).toBe("application/problem+json");
    expect(refused.body.toString("utf8")).toContain("no longer kept");
  });

  it("fail an answer that is not JSON and whose name of bytes Prism did not pass", async () => {
    const { front } = await bench(binary(2048), { dropName: true });
    const refused = await call(`${front}/api/v1/blob`, "GET");
    expect(refused.status).toBe(502);
    expect(refused.body.toString("utf8")).toContain("without the name of its bytes");
  });

  it("pass on neither the headers of a connection nor those it lists, either way", async () => {
    const { front, received } = await bench();
    const answered = await call(`${front}/api/v1/hop`, "GET", {
      connection: "x-hop",
      "x-hop": "1",
      "keep-alive": "timeout=5",
      "proxy-authorization": "Basic x",
      "x-kept": "1",
    });
    const headers = received[0]?.headers ?? {};
    expect(Object.keys(headers)).not.toContain("x-hop");
    expect(Object.keys(headers)).not.toContain("keep-alive");
    expect(Object.keys(headers)).not.toContain("proxy-authorization");
    expect(headers["x-kept"]).toBe("1");
    expect(answered.status).toBe(204);
    expect(Object.keys(answered.headers)).not.toContain("x-answer-hop");
    expect(answered.headers["x-kept"]).toBe("1");
  });

  it("answer a HEAD with the length the API gives", async () => {
    const blob = binary(4096);
    const { front } = await bench(blob);
    const answered = await call(`${front}/api/v1/blob`, "HEAD");
    expect(answered.headers["content-length"]).toBe(String(blob.length));
    expect(answered.body.length).toBe(0);
  });

  it("send a path that starts with two slashes to the API, not to another host", async () => {
    const { front, received } = await bench();
    await call(`${front}//elsewhere.invalid/echo`, "PUT", OCTETS, binary(300));
    expect(received[0]?.url).toBe("//elsewhere.invalid/echo");
  });
});
