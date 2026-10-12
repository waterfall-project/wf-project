// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the paths against the service (`contract.ts`, WF-ARC-0060): it reads what the proxy
 * of the contract refused during a path, though nothing in the path looked at the answer — the one
 * refusal it reads here, which it takes, and which would otherwise fail the path.
 */
import { expect, test } from "@playwright/test";

import { healthChecksAlone, heldToTheContract, proxyFallenQuiet, takeErrors } from "./contract";

heldToTheContract();

test("an address outside the contract is read as refused by the proxy, the one refusal of the path [WF-ARC-0060-A]", async ({
  request,
}) => {
  const outside = await request.get(
    `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/outside-the-contract`,
  );
  expect(outside.status()).toBe(404);
  // Prism writes its line once it has answered: read once it has fallen quiet.
  expect(await proxyFallenQuiet()).toBe(true);
  const refused = takeErrors();
  expect(refused).toHaveLength(1);
  expect(refused[0]).toContain("get /api/v1/outside-the-contract");
  expect(refused[0]).toContain("NO_PATH_MATCHED_ERROR");
});

// Lines as Prism wrote them on 2026-10-11: a health check, then the answer of another
// request, whose last line is the same.
const HEALTH_CHECK = [
  "[1:13:54 PM] › [HTTP SERVER] get /api/v1/health ℹ  info      Request received",
  '[1:13:54 PM] ›     [PROXY] ℹ  info      > Forwarding "get" request to http://api:8000/api/v1/health...',
  "[1:13:54 PM] ›     [PROXY] ℹ  info      The upstream call to /api/v1/health has returned 200",
  "[1:13:54 PM] ›     [PROXY] ℹ  info      < Received forward response",
];
const ANOTHER = [
  "[1:13:55 PM] ›     [PROXY] ℹ  info      The upstream call to /api/v1/me has returned 200",
  "[1:13:55 PM] ›     [PROXY] ℹ  info      < Received forward response",
];

test("counts the last line of an answer as the health check's only after the answer of a health check", () => {
  expect(healthChecksAlone(HEALTH_CHECK)).toBe(true);
  expect(healthChecksAlone([...HEALTH_CHECK, ...ANOTHER])).toBe(false);
  expect(healthChecksAlone(ANOTHER.slice(1), HEALTH_CHECK[2])).toBe(true);
  expect(healthChecksAlone(ANOTHER.slice(1), ANOTHER[0])).toBe(false);
  expect(healthChecksAlone(ANOTHER.slice(1))).toBe(false);
});
