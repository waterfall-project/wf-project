// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The reset of the grid preferences against the service: a tool of the harness (#2282), not a
 * requirement. What a path set on a grid of the account that signs in — a number of lines per page,
 * a sort — is kept by the service in the preferences of that account, and `resetGridPreferences`
 * (`e2e/mode.ts` calls it before each path of `@shared`) gives the grid its defaults back, the
 * other preferences left as they are.
 */
import { expect, test } from "@playwright/test";

import type { components } from "../../src/api/generated/schema";
import { heldToTheContract } from "./contract";
import {
  accountAdministrator,
  frontToken,
  gridPreferences,
  localAccount,
  resetGridPreferences,
} from "./realm";

heldToTheContract();

test("gives the grids of an account their defaults back, whatever a path set, and keeps its language", async ({
  browser,
  playwright,
}) => {
  test.setTimeout(90_000);
  const calls = await playwright.request.newContext({ ignoreHTTPSErrors: true });
  try {
    const administrator = await accountAdministrator(browser, calls);
    const holder = await localAccount(browser, administrator);
    const before = await calls.get(`${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/me`, {
      headers: { Authorization: `Bearer ${await frontToken(browser, holder)}` },
    });
    const start = (await before.json()) as components["schemas"]["UserSelf"];
    expect(start.display_preferences?.language, "a new account is not yet in English").not.toBe(
      "en",
    );
    const written: components["schemas"]["DisplayPreferences"] = {
      language: "en",
      grids: {
        users: { page_size: 10, sort: { column: "last_name", order: "desc" } },
        projects: { page_size: 25 },
      },
    };
    const set = await calls.patch(
      `${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/me/preferences`,
      { headers: { Authorization: `Bearer ${await frontToken(browser, holder)}` }, data: written },
    );
    expect(set.status(), "PATCH /me/preferences").toBe(200);
    expect(gridPreferences(holder.email, "users")).toMatchObject({ page_size: 10 });
    expect(gridPreferences(holder.email, "projects")).toMatchObject({ page_size: 25 });

    await resetGridPreferences(browser, calls, holder);

    // Both grids found their defaults again; the language, which is not a grid, stays.
    expect(gridPreferences(holder.email, "users")).toBeNull();
    expect(gridPreferences(holder.email, "projects")).toBeNull();
    const me = await calls.get(`${process.env.WATERFALL_API_ADDRESS ?? ""}/api/v1/me`, {
      headers: { Authorization: `Bearer ${await frontToken(browser, holder)}` },
    });
    const kept = (await me.json()) as components["schemas"]["UserSelf"];
    expect(kept.display_preferences?.language).toBe("en");
  } finally {
    await calls.dispose();
  }
});
