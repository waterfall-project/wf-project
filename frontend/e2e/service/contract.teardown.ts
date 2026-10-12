// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The guard of the run against the service (`contract.ts`, WF-ARC-0060), once every path is done:
 * the project `contract`, the teardown of the installation (`playwright.config.ts`).
 */
import { test } from "@playwright/test";

import { heldTheRunToTheContract } from "./contract";

test("the proxy of the contract refused nothing the paths asked, up to the last answer it wrote [WF-ARC-0060-A]", async () => {
  await heldTheRunToTheContract();
});
