// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The log of the proxy of the contract (`make e2e-service`), as Docker gives it with the moment it
 * received each line (`--timestamps`): read by the guard of the contract (`contract.ts`), and by
 * `playwright.config.ts`, which takes the start of the run from it. Every moment the paths compare
 * is one of this log, on the clock of Docker — never the clock of the workstation, which a virtual
 * machine lets drift from it: a window started by the workstation would miss the first lines of the
 * run, or read lines of the run before.
 */
import { execFileSync } from "node:child_process";

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
export interface Logged {
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

/**
 * The lines the proxy wrote from a moment on — the last one alone, without one —, in order: the
 * log is never read whole, it grows as long as the platform stays up.
 */
export function proxyLog(since?: string): Logged[] {
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

/**
 * The moment of the last line the proxy wrote, as Docker stamped it: the start of a run. The proxy
 * answers a health check every two seconds from its start, which `make e2e-service` waits for: a
 * log without a line is a proxy that is not the one of the platform.
 */
export function lastLogged(): string {
  const last = proxyLog().at(-1);
  if (last === undefined) {
    throw new Error(
      `the proxy of the contract ${proxy()} has written nothing: run make e2e-service`,
    );
  }
  return last.at;
}
