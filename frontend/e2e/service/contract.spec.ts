// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the paths against the service (`contract.ts`, WF-ARC-0060): a path during which the
 * proxy of the contract refused a request fails, though nothing in it looked at the answer.
 */
import { test } from "@playwright/test";

import { heldToTheContract, proxyFallenQuiet } from "./contract";

heldToTheContract();

test("an address outside the contract fails the path [WF-ARC-0060-A]", async ({ request }) => {
  // Failing, as the guard makes it fail: Prism answers 404 (`NO_PATH_MATCHED_ERROR`) and writes it.
  test.fail();
  await request.get(`${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/outside-the-contract`);
  // Prism writes its line once it has answered: the path ends once it is written.
  await proxyFallenQuiet();
});
