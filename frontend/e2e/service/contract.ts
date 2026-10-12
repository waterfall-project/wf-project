// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The paths against the service, held to the contract (US-0340, WF-ARC-0060). The front reaches
 * the API through Prism as a proxy (`make e2e-service`), which turns an answer outside the schema
 * its operation declares into a 500 (`VIOLATIONS`), an address outside the contract into a 404
 * (`NO_PATH_MATCHED_ERROR`), a request outside it into a 422, and writes each in its log, under
 * the request it answered. The server of Next makes these requests, where the browser does not
 * see them, a screen may outlive one — a read it can do without —, and Prism writes its line once
 * it has answered: each worker reads every line of the log once, from where its first file
 * started, and fails a path on any error Prism wrote before its end, an error written later the
 * next path of the worker. The paths run on several workers (#730), and the log does not say which
 * asked what: an error fails the path of each worker that reads it — the one that caused it among
 * them. The project of the guard (`contract.teardown.ts`) reads the whole log of the run once every
 * path is done, and the proxy fallen quiet: an error written after the last path of a worker fails
 * it. The one refusal a path asks for, an address outside the contract (`OUTSIDE`), is left by
 * every reader to the path that reads it (`contract.spec.ts`).
 *
 * A status the operation does not declare is not an error to Prism: it passes the answer on with a
 * warning (`sl-violations`, of severity `Warning`), which its log does not tie to its request.
 * Today the shell reads operations the service does not serve yet, and the service answers them
 * 404; the tests of the service hold its statuses to the contract (`ContractClient`,
 * `backend/tests/test_api_service.py`), the paths the bodies (#726).
 *
 * The log is read by Docker (`proxy-log.ts`), from the moment last read on (`--since`), never
 * whole, and every moment is one Docker stamped: the run starts at the last line the proxy wrote
 * before it (`E2E_SERVICE_STARTED`, `playwright.config.ts`), and the guard of the run proves its
 * window — a line read at least, and the refusal of `OUTSIDE` when its path played.
 */
import { createHash } from "node:crypto";
import { existsSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { logged, proxyLog } from "./proxy-log";

// What Prism writes of each request it refused to pass on as it is, whatever the error: one of its
// own, under the address of its type (`https://stoplight.io/prism/errors#…`), or one of the proxy —
// a body that is not what its type says, cut short, an API out of reach (`FetchError: …`,
// `Error: …`).
const PRISM_ERROR = "Request terminated with error:";
// The address of the health check, which reaches the API through Prism every two seconds.
const HEALTH = "/api/v1/health";
// The line Prism writes once the answer of the API has come back, the one it does not name the
// request in: written as soon as the headers are received, before the body is read and checked.
const RECEIVED = "< Received forward response";
// The proxy has fallen quiet once it has written nothing for so long but the health checks.
const QUIET = 2_000;
// How long the proxy is given to fall quiet, within the bound of a hook.
const FALLING_QUIET = 20_000;

/** The address outside the contract the guard's own path asks for, which only it reads. */
export const OUTSIDE = "/api/v1/outside-the-contract";

/**
 * The moment the run started, the last line of the proxy before it, which `playwright.config.ts`
 * gives every worker: the guard of the run reads the log from it.
 */
function startOfTheRun(): string {
  const started = process.env.E2E_SERVICE_STARTED;
  if (started === undefined || started === "") {
    throw new Error("E2E_SERVICE_STARTED is the moment the run started: playwright.config.ts");
  }
  return logged(`${started} `).at;
}

/** The moment the reading of the worker has reached, from the start of its first file. */
let cursor: string | undefined;
/** How many lines the reading of the worker has read. */
let linesRead = 0;

/**
 * The lines the proxy wrote since the reading last stopped, read: `--since` gives back the lines
 * of the moment it is given, which the reading already holds.
 */
function unread(): string[] {
  const from = cursor;
  if (from === undefined) {
    throw new Error(
      "the log of the proxy is read from the start of the first file, heldToTheContract",
    );
  }
  const lines = proxyLog(from).filter(({ at }) => at > from);
  cursor = lines.at(-1)?.at ?? from;
  linesRead += lines.length;
  return lines.map(({ line }) => line);
}

/**
 * Whether lines are the health checks alone. Prism names the request in each line it writes of
 * it, but the last, `RECEIVED`: that one is of a health check only when it follows the line of
 * the answer of one — `previous`, the line before them, may be it.
 */
export function healthChecksAlone(lines: readonly string[], previous?: string): boolean {
  return lines.every((line, at) => {
    if (line.endsWith(RECEIVED)) {
      return (at === 0 ? previous : lines[at - 1])?.includes(`The upstream call to ${HEALTH}`);
    }
    return line.includes(HEALTH);
  });
}

/** The errors read and not yet laid at a path's door; those of `OUTSIDE`, apart. */
const errors: string[] = [];
const outside: string[] = [];

/** Keep the errors among lines read, those of `OUTSIDE` apart. */
function keepErrors(lines: readonly string[]): void {
  for (const line of lines.filter((read) => read.includes(PRISM_ERROR))) {
    (line.includes(` ${OUTSIDE} `) ? outside : errors).push(line);
  }
}

/**
 * Wait until the proxy has written all it had to of the requests made so far: nothing but the
 * health checks for a while. Whether it fell quiet within its bound. The errors among what it
 * reads are kept for the guard.
 */
async function proxyFallenQuiet(): Promise<boolean> {
  let previous: string | undefined;
  for (let waited = 0; waited < FALLING_QUIET; waited += QUIET) {
    await new Promise((resolve) => setTimeout(resolve, QUIET));
    const lines = unread();
    keepErrors(lines);
    const quiet = healthChecksAlone(lines, previous);
    previous = lines.at(-1) ?? previous;
    if (quiet) {
      return true;
    }
  }
  return false;
}

/** The errors Prism wrote since the last were taken, but those of `OUTSIDE`. */
export function takeErrors(): string[] {
  keepErrors(unread());
  return errors.splice(0);
}

/** The errors Prism wrote of `OUTSIDE` since the last were taken. */
export function takeOutside(): string[] {
  keepErrors(unread());
  return outside.splice(0);
}

/**
 * Hold each path of the file to the contract: it fails on an error Prism wrote since the previous
 * path of the worker ended — an answer outside its schema, an address or a request outside the
 * contract.
 */
export function heldToTheContract(): void {
  test.beforeAll(() => {
    // From the last line written, or from the start of the run when there is none yet.
    cursor ??= proxyLog().at(-1)?.at ?? startOfTheRun();
  });
  test.afterEach(() => {
    expect(
      takeErrors(),
      "what the proxy of the contract refused up to the end of the path",
    ).toEqual([]);
  });
}

/**
 * The mark the path of `OUTSIDE` leaves once its refusal is read, for the guard of the run, in
 * another worker, to know it played: a file of the system's temporary directory, named after the
 * run.
 */
function outsideAsked(): string {
  const name = createHash("sha256").update(`${startOfTheRun()} ${OUTSIDE}`).digest("hex");
  return join(tmpdir(), `waterfall-e2e-${name.slice(0, 32)}`);
}

/** Mark that the path of `OUTSIDE` played, its refusal read. */
export function markOutsideAsked(): void {
  writeFileSync(outsideAsked(), "");
}

/**
 * Hold the run to the contract once every path is done: the errors Prism wrote since it started,
 * the proxy fallen quiet — those written after the last path of a worker among them, and those the
 * paths failed on already, which fail it again. The window is proved: at least a line read — the
 * health checks write one every two seconds —, and the refusal of `OUTSIDE` among them when its
 * path played, which a window started after it would miss.
 */
export async function heldTheRunToTheContract(): Promise<void> {
  cursor = startOfTheRun();
  linesRead = 0;
  expect.soft(await proxyFallenQuiet(), "the proxy of the contract fell quiet").toBe(true);
  expect(takeErrors(), "what the proxy of the contract refused during the run").toEqual([]);
  expect(linesRead, "the lines of the proxy read since the start of the run").toBeGreaterThan(0);
  const mark = outsideAsked();
  if (existsSync(mark)) {
    rmSync(mark, { force: true });
    expect(
      outside.splice(0).length,
      `the refusals of ${OUTSIDE}, which its path read during the run`,
    ).toBeGreaterThan(0);
  }
}
