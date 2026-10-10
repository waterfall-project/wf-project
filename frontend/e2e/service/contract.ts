// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The paths against the service, held to the contract (US-0340, WF-ARC-0060). The front reaches
 * the API through Prism as a proxy (`make e2e-service`), which turns an answer outside the schema
 * its operation declares into a 500 (`VIOLATIONS`), an address outside the contract into a 404
 * (`NO_PATH_MATCHED_ERROR`), a request outside it into a 422, and writes each in its log, under
 * the request it answered. The server of Next makes these requests, where the browser does not
 * see them, a screen may outlive one — a read it can do without —, and Prism writes its line once
 * it has answered: a file that holds itself to the contract reads every line of the log once, from
 * where it started, and fails on any error Prism wrote there. Each path fails on those written
 * before its end, an error written later the next path, and those written after the last path the
 * file, once its pages are closed and the proxy fallen quiet.
 *
 * A status the operation does not declare is not an error to Prism: it passes the answer on with a
 * warning (`sl-violations`, of severity `Warning`), which its log does not tie to its request.
 * Today the shell reads operations the service does not serve yet, and the service answers them
 * 404; the tests of the service hold its statuses to the contract (`ContractClient`,
 * `backend/tests/test_api_service.py`), the paths the bodies (#726).
 *
 * The log is read by Docker, from the container `make e2e-service` names (`E2E_CONTRACT_PROXY`).
 */
import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

// What Prism writes of each request it refused to pass on as it is, whatever the error: one of its
// own, under the address of its type (`https://stoplight.io/prism/errors#…`), or one of the proxy —
// a body that is not what its type says, cut short, an API out of reach (`FetchError: …`,
// `Error: …`).
const PRISM_ERROR = "Request terminated with error:";
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

/** The lines the proxy of the contract has written so far, in order. */
function proxyLog(): string[] {
  // Prism writes to the standard output; the error output is npm's, which starts Prism.
  return execFileSync("docker", ["logs", proxy()], {
    encoding: "utf8",
    maxBuffer: 1 << 28,
    stdio: ["ignore", "pipe", "ignore"],
  })
    .split("\n")
    .filter((line) => line !== "");
}

/** A line of the health check, which reaches the API through Prism every two seconds. */
function ofHealthCheck(line: string): boolean {
  // Prism names the request in each line it writes of it, but the last.
  return line.includes("/api/v1/health") || line.endsWith("< Received forward response");
}

/**
 * Wait until the proxy has written all it had to of the requests made so far: nothing but the
 * health checks for a while. Whether it fell quiet within its bound.
 */
export async function proxyFallenQuiet(): Promise<boolean> {
  let read = proxyLog().length;
  for (let waited = 0; waited < FALLING_QUIET; waited += QUIET) {
    await new Promise((resolve) => setTimeout(resolve, QUIET));
    const log = proxyLog();
    const quiet = log.slice(read).every(ofHealthCheck);
    read = log.length;
    if (quiet) {
      return true;
    }
  }
  return false;
}

/**
 * Hold each path of the file to the contract: it fails on an error Prism wrote since the previous
 * path ended — an answer outside its schema, an address or a request outside the contract —, and
 * the file on one Prism wrote after its last path.
 */
export function heldToTheContract(): void {
  let read = 0;
  // The lines not read yet, read: an error is laid at the door of one path alone.
  const unreadErrors = (): string[] => {
    const log = proxyLog();
    const unread = log.slice(read);
    read = log.length;
    return unread.filter((line) => line.includes(PRISM_ERROR));
  };
  test.beforeAll(() => {
    read = proxyLog().length;
  });
  test.afterEach(() => {
    expect(
      unreadErrors(),
      "what the proxy of the contract refused up to the end of the path",
    ).toEqual([]);
  });
  // After the pages of the file are closed: the server of Next may still have been reading for them.
  test.afterAll(async () => {
    expect.soft(await proxyFallenQuiet(), "the proxy of the contract fell quiet").toBe(true);
    expect(unreadErrors(), "what the proxy of the contract refused after the last path").toEqual(
      [],
    );
  });
}
