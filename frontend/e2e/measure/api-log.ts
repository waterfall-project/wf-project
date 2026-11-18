// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The log of the API of the service platform, which the measure of the journey of the grids reads
 * for the part of the API in each step (`report.ts`): Docker gives it, from the container `make
 * measure` names (`E2E_SERVICE_API`), for a window of time — never whole, it grows as long as the
 * platform stays up.
 *
 * The API stamps its records with its own clock — the workstation's under Docker on Linux, but not
 * under a virtual machine, which lets it drift —: the measure asks the API for its health once,
 * under an identifier of correlation of its own, which the API binds to the record of the request,
 * and takes the gap between the moment the record says and the moment the answer came back as the
 * offset of the clock of the API, within the time of that one request; the report writes it.
 */
import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";

import { type APIRequestContext, expect } from "@playwright/test";

import { type ApiRequest, apiRequests, momentOf } from "./report";

/** The container of the API of the platform, which `make measure` names. */
function apiContainer(): string {
  const container = process.env.E2E_SERVICE_API;
  if (container === undefined || container === "") {
    throw new Error("E2E_SERVICE_API must name the container of the API: run make measure");
  }
  return container;
}

/** A moment of the workstation as Docker takes it: seconds since the epoch, to the millisecond. */
function dockerMoment(moment: number): string {
  return (moment / 1000).toFixed(3);
}

/** How far around a window the log is read: the clock of the API may be a little off. */
const MARGIN = 5_000;

/**
 * The log of the API between two moments of the workstation, a margin around them: both its
 * outputs, which Docker gives back apart — the API writes its records on its error output.
 */
function logBetween(from: number, to: number): string {
  const read = spawnSync(
    "docker",
    [
      "logs",
      "--since",
      dockerMoment(from - MARGIN),
      "--until",
      dockerMoment(to + MARGIN),
      apiContainer(),
    ],
    { encoding: "utf8", maxBuffer: 1 << 28 },
  );
  if (read.status !== 0) {
    throw new Error(`docker logs ${apiContainer()} failed: ${read.stderr}`);
  }
  return `${read.stdout}\n${read.stderr}`;
}

/** The requests the API answered between two moments, on the clock of the workstation. */
export function apiAnswered(from: number, to: number, offset: number): ApiRequest[] {
  return apiRequests(logBetween(from, to), offset);
}

/** The header the API reads the identifier of correlation of a request from. */
const CORRELATION = "X-Correlation-ID";

/** The moment of the record of the request of a correlation, if the log holds it yet. */
function recordMoment(correlation: string, from: number, to: number): number | undefined {
  for (const line of logBetween(from, to).split("\n")) {
    if (line.includes(correlation) && line.includes("request.completed")) {
      const stamp = /"timestamp":\s*"([^"]+)"/.exec(line)?.[1];
      if (stamp !== undefined) {
        return momentOf(stamp);
      }
    }
  }
  return undefined;
}

/**
 * How far the clock of the API is ahead of the workstation's, in milliseconds: the moment of the
 * record of a request of health, under an identifier of its own, less the moment its answer came
 * back — the record is written once the answer is sent.
 */
export async function clockOffset(request: APIRequestContext, api: string): Promise<number> {
  const correlation = `measure-${randomBytes(8).toString("hex")}`;
  const asked = Date.now();
  const answer = await request.get(`${api}/api/v1/health`, {
    headers: { [CORRELATION]: correlation },
  });
  const answered = Date.now();
  expect(answer.ok(), "GET /api/v1/health").toBe(true);
  let found: number | undefined;
  await expect
    .poll(
      () => {
        found = recordMoment(correlation, asked, answered);
        return found !== undefined;
      },
      { message: `the record of the request ${correlation} in the log of the API` },
    )
    .toBe(true);
  return (found ?? answered) - answered;
}
