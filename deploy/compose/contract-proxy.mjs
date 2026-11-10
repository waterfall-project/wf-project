// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The proxy of the contract of the paths against the service (`contract-proxy`,
 * `compose.service.yaml`): Prism between the front and the API (`prism proxy --errors`,
 * WF-ARC-0060), and around it two legs of this file that carry the bytes of a body that is not JSON
 * past it (US-1550/L7, #973, #1025, #2687, #2695). Node runs it, in the container of Prism, with
 * nothing but its own modules; it starts Prism, and stops with it.
 *
 * Prism reads every body that is not JSON as text (`micri.text` for a request, `response.text()` for
 * an answer) and writes it back as UTF-8: each byte past 0x7f becomes U+FFFD. A workbook, an archive
 * cut in parts, an image came out of it spoiled. Every exchange still goes through Prism, which
 * checks it against the contract and writes it to its log, where the guard of the paths reads it
 * (`frontend/e2e/service/contract.ts`); but the bytes of a body that is not JSON are kept here, on
 * the way in and on the way out, and put back once Prism has passed the message:
 *
 *   front ──▶ entrance (4010, published) ──▶ Prism (4011) ──▶ exit (4012) ──▶ API
 *
 * - a request whose body is not JSON: the entrance keeps its bytes under a name it gives in the
 *   header `RAW`, and passes Prism the same bytes stripped of their high bit (`ascii`); the exit
 *   sends the API the bytes kept, not those Prism passed on;
 * - an answer whose body is not JSON: the exit keeps its bytes under a name it gives in `RAW`, and
 *   passes the answer to Prism as it came; the entrance answers the front the bytes kept, not those
 *   Prism rewrote — unless Prism refused the answer, whose problem it answers then, as before.
 *
 * Whether a body is JSON is read from the Content-Type of each message, the request's and the
 * answer's apart: the download of a workbook is a GET without a body whose answer alone is binary.
 * A body that is JSON passes untouched both ways, checked by Prism as before.
 *
 * Kept: these two legs, in the container and the image of Prism, pinned already. Set aside: sending
 * the exchanges that are not JSON straight to the API, past Prism — a GET cannot be sorted so before
 * its answer comes, and the refusal in JSON of an upload, the route and the status of a download
 * would no longer be checked by the contract nor written to the log the guard reads —; and a patch of
 * Prism in the container, which would rewrite its compiled sources (`micri.text`,
 * `parseResponseBody`, `serialize`: three places that make a body a string) at each version
 * Dependabot brings, with no test of Prism to say that the patch still holds.
 *
 * Usage: `node contract-proxy.mjs <address of the API> <command of Prism…>`, Prism told to listen on
 * 127.0.0.1:4011 and to forward to http://127.0.0.1:4012.
 */
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { Agent, createServer, request } from "node:http";

/** The header that names the bytes of a body kept by one leg for the other. */
const RAW = "x-waterfall-raw-body";
/** How long bytes are kept for the other leg: past it, Prism refused or never passed the message. */
const KEPT = 120_000;

/** The ports in the container: the entrance (the one published), Prism, the exit. */
const ENTRANCE = 4010;
const PRISM = 4011;
const EXIT = 4012;

/**
 * Whether a Content-Type is JSON as Prism reads it (`type-is` on `application/json` and
 * `application/*+json`).
 */
function isJson(contentType) {
  return /^\s*application\/(?:[^\s;/]+\+)?json\s*(?:;|$)/i.test(
    contentType ?? "",
  );
}

/** Whether a message carries a body that Prism would rewrite: one that is not empty, nor JSON. */
function carriesRawBody(headers, body) {
  return body.length > 0 && !isJson(headers["content-type"]);
}

/** The bytes kept by one leg for the other, by the name `RAW` gives them. */
const kept = new Map();

function keep(body) {
  const name = randomUUID();
  kept.set(name, body);
  setTimeout(() => kept.delete(name), KEPT).unref();
  return name;
}

function take(name) {
  const body = kept.get(name);
  kept.delete(name);
  return body;
}

/**
 * The bytes Prism is given of a request body that is not JSON: each past 0x7f stripped of its high
 * bit. Prism reads them as text of the same length, so that the length the request declares stays
 * true on its way to the exit, which replaces them; the ASCII of the body — the boundaries and the
 * headers of the parts of a form — is left as it is, for Prism to check.
 */
function ascii(body) {
  return Buffer.from(body.map((byte) => byte & 0x7f));
}

/** The whole body of a message. */
async function read(message) {
  const chunks = [];
  for await (const chunk of message) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

/**
 * Headers to send a body with, read whole already: its length, without the framing it came in nor
 * a name of kept bytes. A message without a body and without a length is left without one.
 */
function sized(headers, body) {
  const { "transfer-encoding": framing, [RAW]: _kept, ...rest } = headers;
  if (
    body.length === 0 &&
    framing === undefined &&
    rest["content-length"] === undefined
  ) {
    return rest;
  }
  return { ...rest, "content-length": String(body.length) };
}

/** A new connection for each exchange: neither Prism nor the API is raced on one it closes. */
const agent = new Agent({ keepAlive: false });

/** Send a message, and read the whole answer: its status, its headers, its body. */
function send(address, method, headers, body) {
  return new Promise((resolve, reject) => {
    const sent = request(address, { method, headers, agent }, (answer) => {
      read(answer).then(
        (received) =>
          resolve({
            status: answer.statusCode,
            headers: answer.headers,
            body: received,
          }),
        reject,
      );
    });
    sent.on("error", reject);
    sent.end(body);
  });
}

/** Say what went wrong, on the error output: the standard output is Prism's log, read line by line. */
function complain(message) {
  process.stderr.write(`contract-proxy: ${message}\n`);
}

/**
 * The entrance: what the front sends, to Prism, the bytes of a request body that is not JSON kept;
 * what Prism answers, to the front, the bytes of an answer that is not JSON put back.
 */
async function entrance(incoming, outgoing) {
  const body = await read(incoming);
  const headers = sized(incoming.headers, body);
  const sent = carriesRawBody(headers, body)
    ? { headers: { ...headers, [RAW]: keep(body) }, body: ascii(body) }
    : { headers, body };
  const address = new URL(incoming.url, `http://127.0.0.1:${PRISM}`);
  const answered = await send(
    address,
    incoming.method,
    sent.headers,
    sent.body,
  );
  const name = answered.headers[RAW];
  const answeredBody = name === undefined ? answered.body : take(name);
  if (answeredBody === undefined) {
    complain(
      `the bytes of the answer to ${incoming.method} ${incoming.url} were no longer kept`,
    );
    outgoing.destroy();
    return;
  }
  outgoing.writeHead(answered.status, sized(answered.headers, answeredBody));
  outgoing.end(answeredBody);
}

/**
 * The exit, Prism's upstream: what Prism sends, to the API, the bytes the entrance kept in place of
 * those Prism passed on; what the API answers, to Prism, the bytes of an answer that is not JSON
 * kept. The API is asked for no compression: the bytes kept go to the front as they are, and Prism
 * drops the Content-Encoding of an answer.
 */
async function exit(incoming, outgoing, api) {
  const received = await read(incoming);
  const name = incoming.headers[RAW];
  const body = name === undefined ? received : take(name);
  if (body === undefined) {
    // Cut short: Prism writes the request terminated with an error, which fails the path.
    complain(
      `the bytes of ${incoming.method} ${incoming.url} were no longer kept`,
    );
    outgoing.destroy();
    return;
  }
  const headers = {
    ...sized(incoming.headers, body),
    host: api.host,
    "accept-encoding": "identity",
  };
  const answered = await send(
    new URL(incoming.url, api),
    incoming.method,
    headers,
    body,
  );
  const passed = sized(answered.headers, answered.body);
  if (carriesRawBody(answered.headers, answered.body)) {
    passed[RAW] = keep(answered.body);
  }
  outgoing.writeHead(answered.status, passed);
  outgoing.end(answered.body);
}

/**
 * Serve a leg on a port. A failure cuts the connection short: Prism then writes the request
 * terminated with an error, as it did of an API out of reach, and the path fails on it.
 */
function serve(port, host, leg) {
  createServer((incoming, outgoing) => {
    leg(incoming, outgoing).catch((error) => {
      complain(String(error));
      outgoing.destroy();
    });
  }).listen(port, host);
}

const [address, program, ...rest] = process.argv.slice(2);
if (address === undefined || program === undefined) {
  throw new Error(
    "usage: contract-proxy.mjs <address of the API> <command of Prism…>",
  );
}
const api = new URL(address);
serve(EXIT, "127.0.0.1", (incoming, outgoing) => exit(incoming, outgoing, api));
serve(ENTRANCE, "0.0.0.0", entrance);
const prism = spawn(program, rest, { stdio: ["ignore", "inherit", "inherit"] });
for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => prism.kill(signal));
}
// Stopped by a signal, Prism has no code: the stop was asked for.
prism.on("exit", (code, signal) =>
  process.exit(code ?? (signal === null ? 1 : 0)),
);
