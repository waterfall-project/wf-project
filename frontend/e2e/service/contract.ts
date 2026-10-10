// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The paths against the service, held to the contract (US-0340, WF-ARC-0060). The front reaches
 * the API through Prism as a proxy (`make e2e-service`), which turns an answer outside the schema
 * its operation declares into a 500 (`VIOLATIONS`), an address outside the contract into a 404
 * (`NO_PATH_MATCHED_ERROR`), a request outside it into a 422, and writes each in its log, under
 * the request it answered. The server of Next makes these requests, where the browser does not
 * see them, and a screen may outlive one — a read it can do without —: each path of a file that
 * holds itself to the contract fails on any error Prism wrote while it ran.
 *
 * A status the operation does not declare is not an error to Prism: it passes the answer on with a
 * warning (`sl-violations`, of severity `Warning`), which its log does not tie to its request.
 * Today the shell reads operations the service does not serve yet, and the service answers them
 * 404; the tests of the service hold its statuses to the contract (`ContractClient`,
 * `backend/tests/test_api_service.py`), the paths the bodies (#726).
 *
 * The log is read by Docker, from the container `make e2e-service` names (`E2E_CONTRACT_PROXY`):
 * the lines a path adds to it are its own, and those of a path that ran beside it.
 */
import { execFileSync } from "node:child_process";

import { expect, test } from "@playwright/test";

// What Prism writes of each request it refused to pass on as it is, under the type of its error.
const PRISM_ERROR = "Request terminated with error: https://stoplight.io/prism/errors#";

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

/**
 * Hold each path of the file to the contract: it fails on an error Prism wrote while it ran — an
 * answer outside its schema, an address or a request outside the contract.
 */
export function heldToTheContract(): void {
  let start = 0;
  test.beforeEach(() => {
    start = proxyLog().length;
  });
  test.afterEach(() => {
    const errors = proxyLog()
      .slice(start)
      .filter((line) => line.includes(PRISM_ERROR));
    expect(errors, "what the proxy of the contract refused during the path").toEqual([]);
  });
}
