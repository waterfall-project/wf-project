// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The point of metrics of the front, played against the front as it is built and started (`next
 * start`), which the unit tests — a `http.createServer` of their own — do not play: that Next runs
 * `register()` in the process that serves, on the servers of `node:http` it observes, and that the
 * module the hook loads is the one the startup shares, so that a request is counted once. A front
 * that observed nothing would answer 200 on its port with no series: the count is read here
 * (WF-OBS-0010-A, TFX-09). The front is one of this file's, started on the two ports the slot owns
 * for it (`E2E_METRICS_FRONT_PORT`, `E2E_METRICS_PORT`, offsets 80 and 81 of its block): no other
 * path asks it, and its count is its own.
 * The image's `standalone` output is not played here (`check-front-image`).
 */
import { type ChildProcess, spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

/** The ports of the harness, as `playwright.config.ts` reads them. */
function port(variable: string, own: number): number {
  const named = process.env[variable];
  return named === undefined ? own : Number(named);
}

// The two ports the slot gives this path, named by `make e2e`.
const FRONT_PORT = port("E2E_METRICS_FRONT_PORT", 3180);
const METRICS_PORT = port("E2E_METRICS_PORT", 3181);
const FRONT = `http://127.0.0.1:${String(FRONT_PORT)}`;
const METRICS = `http://127.0.0.1:${String(METRICS_PORT)}/metrics`;
// The fake back of the harness: the front built for production reaches an API, which is not the
// service here, and not the development server's build either.
const NOT_BUILT =
  process.env.E2E_DEV_SERVER === "1" || process.env.WATERFALL_API_ADDRESS !== undefined;

let front: ChildProcess | undefined;
let failure: string | undefined;

/** Whether nothing listens on the port: an orphan of another build would be judged in place of ours. */
async function isFree(candidate: number): Promise<boolean> {
  const probe = createServer();
  probe.unref();
  const outcome = Promise.race([
    once(probe, "listening").then(() => true),
    once(probe, "error").then(() => false),
  ]);
  probe.listen(candidate, "127.0.0.1");
  const free = await outcome;
  if (free) {
    probe.close();
    await once(probe, "close");
  }
  return free;
}

test.beforeAll(async ({ request }) => {
  test.setTimeout(90_000);
  if (NOT_BUILT) {
    return;
  }
  for (const taken of [FRONT_PORT, METRICS_PORT]) {
    expect(await isFree(taken), `port ${String(taken)} is already served: make e2e-down`).toBe(
      true,
    );
  }
  // `next` itself, in a group of processes of its own: `pnpm` would not pass the signal on.
  const child = spawn(
    join(import.meta.dirname, "../node_modules/.bin/next"),
    ["start", "--hostname", "127.0.0.1", "--port", String(FRONT_PORT)],
    {
      detached: true,
      stdio: "ignore",
      env: {
        ...process.env,
        WATERFALL_API_ADDRESS: `http://127.0.0.1:${String(port("E2E_API_PORT", 4110))}`,
        WATERFALL_API_CONNECTIONS: "closed",
        WATERFALL_AUTH: "mock",
        WATERFALL_E2E: "1",
        WATERFALL_METRICS_PORT: String(METRICS_PORT),
      },
    },
  );
  front = child;
  child.once("error", (error) => {
    failure = `the front did not start: ${error.message}`;
  });
  child.once("exit", (code, signal) => {
    failure ??= `the front exited before it answered (${String(code ?? signal)})`;
  });
  await expect
    .poll(
      async () => {
        if (failure !== undefined) {
          throw new Error(failure);
        }
        return (await request.get(METRICS).catch(() => undefined))?.status();
      },
      { timeout: 60_000 },
    )
    .toBe(200);
});

test.afterAll(async () => {
  const child = front;
  if (child?.pid === undefined || child.exitCode !== null || child.signalCode !== null) {
    return;
  }
  const exited = once(child, "exit");
  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    return;
  }
  await exited;
});

/** The requests the front counted under a kind. */
function counted(body: string, kind: string): number {
  let total = 0;
  for (const line of body.split("\n")) {
    const match = /^waterfall_front_requests_total\{(.*)\} (\d+)$/.exec(line);
    if (match?.[1]?.includes(`kind="${kind}"`) === true && match[2] !== undefined) {
      total += Number(match[2]);
    }
  }
  return total;
}

test("the built front counts the page it serves on the port of the metrics, once, and none of the metrics' own requests [WF-OBS-0010-A]", async ({
  request,
}) => {
  test.skip(NOT_BUILT, "the front of the metrics is the built front, against the fake back");
  const before = await (await request.get(METRICS)).text();
  const page = await request.get(`${FRONT}/`);
  expect(page.ok()).toBe(true);
  await expect
    .poll(async () => counted(await (await request.get(METRICS)).text(), "page"))
    .toBe(counted(before, "page") + 1);
  // Read again, the collections are not counted, and nothing else has been.
  const after = await (await request.get(METRICS)).text();
  expect(after).toContain('waterfall_front_requests_total{kind="page",status="200"}');
  expect(counted(after, "page")).toBe(counted(before, "page") + 1);
  expect(counted(after, "action")).toBe(counted(before, "action"));
  expect(counted(after, "asset")).toBe(counted(before, "asset"));
});

test("the built front answers 404 to the metrics on its public port, to any method [TFX-09]", async ({
  request,
}) => {
  test.skip(NOT_BUILT, "the front of the metrics is the built front, against the fake back");
  for (const path of ["/metrics", "/api/v1/metrics"]) {
    const address = `${FRONT}${path}`;
    const answers = {
      GET: await request.get(address),
      POST: await request.post(address),
      PUT: await request.put(address),
      DELETE: await request.delete(address),
    };
    for (const [method, response] of Object.entries(answers)) {
      expect(response.status(), `${method} ${path}`).toBe(404);
      expect(await response.json()).toEqual({ code: "NOT_FOUND", status: 404 });
    }
  }
});
