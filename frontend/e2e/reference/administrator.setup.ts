// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The administrator of a restored reference set, signed in (US-2950/L3): the set was engendered on a
 * platform whose bootstrap link served once, and the password the account was then given is not the
 * one of the paths (`LOCAL_PASSWORD`). Every path acts through this administrator — it makes the
 * manager each worker signs in as (`e2e/mode.ts`) —, so the project `reference-administrator` gives
 * it the password of the paths first, by the administration of Keycloak, and signs it in once to
 * prove that the account the set holds is the one the paths act with. The project every other
 * path of `e2e/reference/` depends on.
 */
import { expect, test } from "@playwright/test";

import { compileAnswered } from "../compile";
import { heldToTheContract } from "../service/contract";
import { ADMINISTRATOR, givePassword, LOCAL_PASSWORD, signIn } from "../service/realm";

heldToTheContract();

const ACCOUNT = "/account";

test.beforeEach(async ({ request }) => {
  await compileAnswered(request, "/auth/callback", ACCOUNT);
});

test("the administrator of the restored set signs in with the password of the paths [US-2950]", async ({
  page,
  playwright,
}) => {
  expect(ADMINISTRATOR.email, "E2E_ADMIN_EMAIL, as make e2e-reference gives it").not.toBe("");
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    await givePassword(calls, ADMINISTRATOR.email, LOCAL_PASSWORD);
  } finally {
    await calls.dispose();
  }
  await signIn(page, ADMINISTRATOR, ACCOUNT);
});
