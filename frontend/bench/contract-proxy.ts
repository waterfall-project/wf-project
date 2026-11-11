// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The proxy of the contract of the paths against the service (`contract-proxy`,
 * `deploy/compose/compose.service.yaml`): Prism between the front and the API (`prism proxy
 * --errors`, WF-ARC-0060), and around it two legs of this file that carry the bytes of a body that
 * is not JSON past it (US-1550/L7, #973, #1025, #2687, #2695). Node runs it, in the container of
 * Prism, with nothing but its own modules and its stripping of the types; it starts Prism, and
 * stops with it.
 *
 * Prism reads every body that is not JSON as text (`micri.text` for a request, `response.text()`
 * for an answer) and writes it back as UTF-8: each byte past 0x7f becomes U+FFFD. A workbook, an
 * archive cut in parts, an image came out of it spoiled. Every exchange still goes through Prism,
 * which checks it against the contract and writes it to its log, where the guard of the paths reads
 * it (`frontend/e2e/service/contract.ts`); but the bytes of a body that is not JSON are kept here,
 * on the way in and on the way out, and put back once Prism has passed the message:
 *
 *   front ──▶ entrance (4010, published) ──▶ Prism (4011) ──▶ exit (4012) ──▶ API
 *
 * - a request whose body is not JSON: the entrance keeps its bytes under a name it gives in the
 *   header `RAW`, and passes Prism the same bytes stripped of their high bit (`ascii`); the exit
 *   sends the API the bytes kept, not those Prism passed on;
 * - an answer whose body is not JSON: the exit keeps its bytes under a name it gives in `RAW`, and
 *   passes the answer to Prism as it came; the entrance answers the front the bytes kept, not those
 *   Prism rewrote. An answer of Prism in JSON is passed as it is, whatever it names: it is Prism's
 *   refusal, a problem of its own in place of the answer of the API.
 *
 * Whether a body is JSON is read from the Content-Type of each message, the request's and the
 * answer's apart: the download of a workbook is a GET without a body whose answer alone is binary.
 * A body that is JSON passes untouched both ways, checked by Prism as before.
 *
 * Kept: these two legs, in the container and the image of Prism, pinned already. Set aside: sending
 * the exchanges that are not JSON straight to the API, past Prism — a GET cannot be sorted so
 * before its answer comes, and the refusal in JSON of an upload, the route and the status of a
 * download would no longer be checked by the contract nor written to the log the guard reads —; and
 * a patch of Prism in the container, which would rewrite its compiled sources (`micri.text`,
 * `parseResponseBody`, `serialize`: three places that make a body a string) at each version
 * Dependabot brings, with no test of Prism to say that the patch still holds.
 *
 * The file lives in the front, beside its test (`contract-proxy.test.ts`), so that the lint, the
 * types and the tests of the front hold it; it is no code of the front, which the network guard of
 * `eslint.config.mjs` keeps to the generated client, and that guard lets this directory alone call
 * the network, as a proxy must.
 *
 * Usage: `node contract-proxy.ts <address of the API> <command of Prism…>`, Prism told to listen on
 * 127.0.0.1:4011 and to forward to http://127.0.0.1:4012.
 */
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  Agent,
  createServer,
  type IncomingHttpHeaders,
  type IncomingMessage,
  type OutgoingHttpHeaders,
  request,
  type RequestListener,
  type Server,
  type ServerResponse,
} from "node:http";

/** The header that names the bytes of a body kept by one leg for the other. */
export const RAW = "x-waterfall-raw-body";

/** How long bytes are kept for the other leg: past it, Prism refused or never passed them on. */
const KEPT_FOR = 120_000;

/** The ports in the container: the entrance (the one published), Prism, the exit. */
const ENTRANCE = 4010;
const PRISM = 4011;
const EXIT = 4012;

/**
 * The headers of one connection, not of the message (RFC 9110, § 7.6.1): never passed on, either
 * way, with those that the header `Connection` lists. `transfer-encoding` among them: a body is
 * read whole here, and sent on with its length.
 */
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

/**
 * Whether a Content-Type is JSON as Prism reads it (`type-is` on `application/json` and
 * `application/*+json`, a problem of Prism's among them).
 */
export function isJson(contentType: string | undefined): boolean {
  return /^\s*application\/(?:[^\s;/]+\+)?json\s*(?:;|$)/i.test(contentType ?? "");
}

/** Whether a message carries a body that Prism would rewrite: one that is not empty, nor JSON. */
function carriesRawBody(headers: IncomingHttpHeaders, body: Buffer): boolean {
  return body.length > 0 && !isJson(headers["content-type"]);
}

/**
 * The bytes kept by one leg for the other, by the name `RAW` gives them, each for so long. The
 * memory is bounded by what the paths have in flight over that time, never more than a few
 * archives: a body is taken as soon as the other leg sees its name, and one whose name never comes
 * back — the message refused by Prism — is dropped at the end of its time. The bench serves one
 * run, on a port of the workstation or of the runner: no ceiling is worth its refusal.
 */
export class Kept {
  readonly #bodies = new Map<string, Buffer>();
  readonly #lifetime: number;

  /** Keep each body for so many milliseconds. */
  constructor(lifetime: number) {
    this.#lifetime = lifetime;
  }

  /** Keep the bytes of a body, under the name returned. */
  keep(body: Buffer): string {
    const name = randomUUID();
    this.#bodies.set(name, body);
    setTimeout(() => this.#bodies.delete(name), this.#lifetime).unref();
    return name;
  }

  /** Take the bytes kept under a name, once: undefined once their time is past. */
  take(name: string): Buffer | undefined {
    const body = this.#bodies.get(name);
    this.#bodies.delete(name);
    return body;
  }
}

/**
 * The bytes Prism is given of a request body that is not JSON: each past 0x7f stripped of its high
 * bit. Prism reads them as text of the same length, so that the length the request declares stays
 * true on its way to the exit, which replaces them; the ASCII of the body — the boundaries and the
 * headers of the parts of a form — is left as it is, for Prism to check.
 */
function ascii(body: Buffer): Buffer {
  const stripped = Buffer.allocUnsafe(body.length);
  for (let at = 0; at < body.length; at += 1) {
    stripped[at] = (body[at] ?? 0) & 0x7f;
  }
  return stripped;
}

/** The whole body of a message. */
async function read(message: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of message) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

/** The headers of a message that pass on: neither those of its connection nor a name of bytes. */
function endToEnd(headers: IncomingHttpHeaders): OutgoingHttpHeaders {
  const listed = new Set(
    (headers.connection ?? "")
      .split(",")
      .map((token) => token.trim().toLowerCase())
      .filter((token) => token !== ""),
  );
  return Object.fromEntries(
    Object.entries(headers).filter(
      ([name, value]) =>
        value !== undefined &&
        name !== RAW &&
        !HOP_BY_HOP.has(name) &&
        !name.startsWith("proxy-") &&
        !listed.has(name),
    ),
  );
}

/**
 * Headers to send a body with, read whole already: its length, in place of the framing it came in.
 * A message without a body and without a length is left without one.
 */
function sized(headers: IncomingHttpHeaders, body: Buffer): OutgoingHttpHeaders {
  const passed = endToEnd(headers);
  const framed =
    headers["content-length"] !== undefined || headers["transfer-encoding"] !== undefined;
  if (body.length > 0 || framed) {
    passed["content-length"] = String(body.length);
  }
  return passed;
}

/**
 * Headers to answer with. The answer to a HEAD, a 204 and a 304 has no body, whatever length it
 * says: the length the API gave, that of the body a GET would have, is passed as it came.
 */
function answering(
  method: string | undefined,
  status: number,
  headers: IncomingHttpHeaders,
  body: Buffer,
): OutgoingHttpHeaders {
  return method === "HEAD" || status === 204 || status === 304
    ? endToEnd(headers)
    : sized(headers, body);
}

/** One header, as one value: a name of bytes is never given twice. */
function single(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/** A new connection for each exchange: neither Prism nor the API is raced on one it closes. */
const agent = new Agent({ keepAlive: false });

interface Answer {
  status: number;
  headers: IncomingHttpHeaders;
  body: Buffer;
}

/** Send a message, and read the whole answer: its status, its headers, its body. */
function send(
  address: string,
  method: string | undefined,
  headers: OutgoingHttpHeaders,
  body: Buffer,
): Promise<Answer> {
  return new Promise((resolve, reject) => {
    const sent = request(address, { method, headers, agent }, (answer) => {
      read(answer).then((received) => {
        resolve({ status: answer.statusCode ?? 502, headers: answer.headers, body: received });
      }, reject);
    });
    sent.on("error", reject);
    if (body.length > 0) {
      sent.end(body);
    } else {
      sent.end();
    }
  });
}

/**
 * The address a message is sent to: the path it asked for, on the origin of the next hop. Composed
 * as text, never resolved against it, so that a path `//host/x` stays a path of that origin.
 */
function onto(origin: URL, path: string | undefined): string {
  return `${origin.origin}${path ?? "/"}`;
}

/** Say what went wrong, on the error output: the standard output is Prism's log, read by line. */
function complain(message: string): void {
  process.stderr.write(`contract-proxy: ${message}\n`);
}

/**
 * Answer the front that the bytes of an answer are lost, rather than give it those Prism rewrote: a
 * problem of 502, which the path fails on, saying why.
 */
function lost(outgoing: ServerResponse, detail: string): void {
  complain(detail);
  outgoing.writeHead(502, { "content-type": "application/problem+json" });
  outgoing.end(JSON.stringify({ type: "about:blank", title: "Bad Gateway", status: 502, detail }));
}

/** A leg as a listener of a server: a failure cuts the connection short, and says why. */
function leg(
  handle: (incoming: IncomingMessage, outgoing: ServerResponse) => Promise<void>,
): RequestListener {
  return (incoming, outgoing) => {
    handle(incoming, outgoing).catch((error: unknown) => {
      complain(String(error));
      outgoing.destroy();
    });
  };
}

/**
 * The entrance, before Prism: what the front sends, to Prism, the bytes of a request body that is
 * not JSON kept; what Prism answers, to the front, the bytes of an answer that is not JSON put
 * back. An answer of Prism that is not JSON and names no bytes kept is one whose bytes Prism
 * rewrote and whose name it dropped: refused, never given as it is.
 */
export function entrance(prism: URL, kept: Kept): RequestListener {
  return leg(async (incoming, outgoing) => {
    const body = await read(incoming);
    const headers = sized(incoming.headers, body);
    const raw = carriesRawBody(incoming.headers, body);
    const answered = await send(
      onto(prism, incoming.url),
      incoming.method,
      raw ? { ...headers, [RAW]: kept.keep(body) } : headers,
      raw ? ascii(body) : body,
    );
    const exchange = `${incoming.method ?? ""} ${incoming.url ?? ""}`;
    const name = single(answered.headers[RAW]);
    const prismOwn = !carriesRawBody(answered.headers, answered.body);
    const keptBody = name === undefined ? undefined : kept.take(name);
    if (!prismOwn && name === undefined) {
      lost(outgoing, `Prism passed the answer to ${exchange} without the name of its bytes`);
      return;
    }
    if (!prismOwn && keptBody === undefined) {
      lost(outgoing, `the bytes of the answer to ${exchange} were no longer kept`);
      return;
    }
    const passed = prismOwn ? answered.body : (keptBody ?? answered.body);
    outgoing.writeHead(
      answered.status,
      answering(incoming.method, answered.status, answered.headers, passed),
    );
    outgoing.end(passed);
  });
}

/**
 * The exit, Prism's upstream: what Prism sends, to the API, the bytes the entrance kept in place of
 * those Prism passed on; what the API answers, to Prism, the bytes of an answer that is not JSON
 * kept. The API is asked for no compression: the bytes kept go to the front as they are, and Prism
 * drops the Content-Encoding of an answer.
 */
export function exit(api: URL, kept: Kept): RequestListener {
  return leg(async (incoming, outgoing) => {
    const received = await read(incoming);
    const name = single(incoming.headers[RAW]);
    const body = name === undefined ? received : kept.take(name);
    if (body === undefined) {
      // Cut short: Prism answers the request terminated with an error, which fails the path.
      complain(`the bytes of ${incoming.method ?? ""} ${incoming.url ?? ""} were no longer kept`);
      outgoing.destroy();
      return;
    }
    const headers = {
      ...sized(incoming.headers, body),
      host: api.host,
      "accept-encoding": "identity",
    };
    const answered = await send(onto(api, incoming.url), incoming.method, headers, body);
    const passed = answering(incoming.method, answered.status, answered.headers, answered.body);
    if (carriesRawBody(answered.headers, answered.body)) {
      passed[RAW] = kept.keep(answered.body);
    }
    outgoing.writeHead(answered.status, passed);
    outgoing.end(answered.body);
  });
}

/** Serve a listener on a port of an address, once it listens. */
export function serve(listener: RequestListener, port: number, host: string): Promise<Server> {
  const server = createServer(listener);
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => {
      resolve(server);
    });
  });
}

/** The two legs on their ports, then Prism, which the process stops with. */
async function main([address, program, ...rest]: string[]): Promise<void> {
  if (address === undefined || program === undefined) {
    throw new Error("usage: contract-proxy.ts <address of the API> <command of Prism…>");
  }
  const kept = new Kept(KEPT_FOR);
  await serve(exit(new URL(address), kept), EXIT, "127.0.0.1");
  await serve(entrance(new URL(`http://127.0.0.1:${String(PRISM)}`), kept), ENTRANCE, "0.0.0.0");
  const prism = spawn(program, rest, { stdio: ["ignore", "inherit", "inherit"] });
  for (const signal of ["SIGTERM", "SIGINT"] as const) {
    process.on(signal, () => prism.kill(signal));
  }
  // Stopped by a signal, Prism has no code: the stop was asked for.
  prism.on("exit", (code, signal) => process.exit(code ?? (signal === null ? 1 : 0)));
}

// Imported by its test, the file starts nothing: only run, it serves and starts Prism.
if (import.meta.main) {
  await main(process.argv.slice(2));
}
