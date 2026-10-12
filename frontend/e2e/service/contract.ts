// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The paths against the service, held to the contract (US-0340, WF-ARC-0060). The front reaches
 * the API through Prism as a proxy (`make e2e-service`), which turns an answer outside the schema
 * its operation declares into a 500 (`VIOLATIONS`), an address outside the contract into a 404
 * (`NO_PATH_MATCHED_ERROR`), a request outside it into a 422, and writes each in its log, under
 * the request it answered. The server of Next makes these requests, where the browser does not
 * see them, a screen may outlive one — a read it can do without —, and Prism writes its line once
 * it has answered: the paths read every line of the log once, from where the first file started,
 * and fail on any error Prism wrote there. Each path fails on those written before its end, an
 * error written later the next path — of its file or of the next one, the reading going on from
 * file to file —, and those written after the last path of a file the file, once its pages are
 * closed and the proxy fallen quiet.
 *
 * The reading is one for the worker, which is why the paths against the service run on one: a
 * second worker would read the errors of the first, the refusal `contract.spec.ts` asks for among
 * them (#735).
 *
 * A status the operation does not declare is not an error to Prism: it passes the answer on with a
 * warning (`sl-violations`, of severity `Warning`), which its log does not tie to its request.
 * Today the shell reads operations the service does not serve yet, and the service answers them
 * 404; the tests of the service hold its statuses to the contract (`ContractClient`,
 * `backend/tests/test_api_service.py`), the paths the bodies (#726).
 *
 * The log is read by Docker, from the container `make e2e-service` names (`E2E_CONTRACT_PROXY`),
 * from the moment last read on (`--since`), never whole: it grows as long as the platform stays up.
 */
import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

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

/** The container of the proxy of the contract, which `make e2e-service` names. */
function proxy(): string {
  const container = process.env.E2E_CONTRACT_PROXY;
  if (container === undefined || container === "") {
    throw new Error(
      "E2E_CONTRACT_PROXY must name the container of the proxy of the contract: run make e2e-service",
    );
  }
  return container;
}

/** A line of the log, and the moment Docker received it. */
interface Logged {
  /** The moment, `YYYY-MM-DDTHH:MM:SS.nnnnnnnnn`, its nanoseconds whole: in order as a text. */
  readonly at: string;
  readonly line: string;
}

/**
 * A line as Docker gives it with its moment (`--timestamps`): RFC 3339, its nanoseconds stripped
 * of their trailing zeros, which are put back so that two moments compare as texts.
 */
export function logged(text: string): Logged {
  const [stamp = "", ...rest] = text.split(" ");
  const [seconds = "", fraction = ""] = stamp.replace(/Z$/, "").split(".");
  return { at: `${seconds}.${fraction.padEnd(9, "0")}`, line: rest.join(" ") };
}

/** The lines the proxy wrote from a moment on — all of them, without one — in order. */
function proxyLog(since?: string): Logged[] {
  const window = since === undefined ? ["--tail", "1"] : ["--since", `${since}Z`];
  // Prism writes to the standard output; the error output is npm's, which starts Prism.
  return execFileSync("docker", ["logs", "--timestamps", ...window, proxy()], {
    encoding: "utf8",
    maxBuffer: 1 << 28,
    stdio: ["ignore", "pipe", "ignore"],
  })
    .split("\n")
    .filter((text) => text !== "")
    .map(logged);
}

/** The moment the reading of the worker has reached, from the start of its first file. */
let cursor: string | undefined;

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

/**
 * Wait until the proxy has written all it had to of the requests made so far: nothing but the
 * health checks for a while. Whether it fell quiet within its bound. The errors among what it
 * reads are kept for the guard.
 */
export async function proxyFallenQuiet(): Promise<boolean> {
  let previous: string | undefined;
  for (let waited = 0; waited < FALLING_QUIET; waited += QUIET) {
    await new Promise((resolve) => setTimeout(resolve, QUIET));
    const lines = unread();
    errors.push(...lines.filter((line) => line.includes(PRISM_ERROR)));
    const quiet = healthChecksAlone(lines, previous);
    previous = lines.at(-1) ?? previous;
    if (quiet) {
      return true;
    }
  }
  return false;
}

/** The errors read while waiting for the proxy to fall quiet, not yet laid at a path's door. */
const errors: string[] = [];

/** The errors Prism wrote since the last were taken: laid at the door of one path alone. */
export function takeErrors(): string[] {
  return [...errors.splice(0), ...unread().filter((line) => line.includes(PRISM_ERROR))];
}

/**
 * Hold each path of the file to the contract: it fails on an error Prism wrote since the previous
 * path ended — an answer outside its schema, an address or a request outside the contract —, and
 * the file on one Prism wrote after its last path.
 */
export function heldToTheContract(): void {
  test.beforeAll(() => {
    expect(
      test.info().config.workers,
      "the paths against the service read the log of the proxy on one worker",
    ).toBe(1);
    // From the last line written, or from now when there is none yet.
    cursor ??= proxyLog().at(-1)?.at ?? logged(`${new Date().toISOString()} `).at;
  });
  test.afterEach(() => {
    expect(
      takeErrors(),
      "what the proxy of the contract refused up to the end of the path",
    ).toEqual([]);
  });
  // After the pages of the file are closed: the server of Next may still have been reading for them.
  test.afterAll(async () => {
    expect.soft(await proxyFallenQuiet(), "the proxy of the contract fell quiet").toBe(true);
    expect(takeErrors(), "what the proxy of the contract refused after the last path").toEqual([]);
  });
}
