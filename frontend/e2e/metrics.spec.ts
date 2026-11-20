// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The point of metrics of the front, played against the front as it is built and started (`next
 * start`), which the unit tests — a `http.createServer` of their own — do not play: that Next runs
 * `register()` in the process that serves, on the servers of `node:http` it observes, and that the
 * module the hook loads is the one the startup shares, so that a request is counted once. A front
 * that observed nothing would answer 200 on its port with no series: the count is read here
 * (WF-OBS-0010-A, TFX-09). The front is a dedicated one (`playwright.config.ts`, `metricsFront`),
 * on the ports of the slot, which no other path asks.
 */
import { expect, test } from "@playwright/test";

const FRONT = process.env.E2E_METRICS_FRONT;
const PORT = process.env.E2E_METRICS_PORT;

/** The requests the front counted under a kind and a status, all statuses when none is named. */
function counted(body: string, kind: string, status?: string): number {
  let total = 0;
  for (const line of body.split("\n")) {
    const match = /^waterfall_front_requests_total\{(.*)\} (\d+)$/.exec(line);
    if (match?.[1] === undefined || match[2] === undefined) {
      continue;
    }
    const labels = match[1];
    if (labels.includes(`kind="${kind}"`) && (status === undefined || labels.includes(`status="${status}"`))) {
      total += Number(match[2]);
    }
  }
  return total;
}

test("the built front counts the page it serves on the port of the metrics, once, and none of the metrics' own requests [WF-OBS-0010-A]", async ({
  request,
}) => {
  test.skip(FRONT === undefined || PORT === undefined, "the front of the metrics is not started");
  const metrics = `http://127.0.0.1:${String(PORT)}/metrics`;
  // The readiness probe of the harness asked for the metrics alone: the pages start at zero or
  // wherever the harness left them, and the difference is read.
  const before = await (await request.get(metrics)).text();
  const page = await request.get(`${String(FRONT)}/`);
  expect(page.ok()).toBe(true);
  await expect
    .poll(async () => counted(await (await request.get(metrics)).text(), "page"))
    .toBe(counted(before, "page") + 1);
  // Read again, the collection itself is not counted, and the page is not counted twice.
  const after = await (await request.get(metrics)).text();
  expect(after).toContain('waterfall_front_requests_total{kind="page",status="200"}');
  expect(counted(after, "page")).toBe(counted(before, "page") + 1);
  expect(counted(after, "action")).toBe(counted(before, "action"));
  expect(counted(after, "asset")).toBe(counted(before, "asset"));
});

test("the built front answers 404 to the metrics on its public port, to any method [TFX-09]", async ({
  request,
}) => {
  test.skip(FRONT === undefined, "the front of the metrics is not started");
  for (const path of ["/metrics", "/api/v1/metrics"]) {
    for (const method of ["GET", "POST", "PUT", "DELETE"]) {
      const response = await request.fetch(`${String(FRONT)}${path}`, { method });
      expect(response.status(), `${method} ${path}`).toBe(404);
      expect(await response.json()).toEqual({ code: "NOT_FOUND", status: 404 });
    }
  }
});
