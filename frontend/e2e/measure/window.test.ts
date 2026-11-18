// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The window of the measures against the service (`window.ts`, #3801): every browser context that
 * `signedIn` opens takes it. A tool of the measure, which covers no requirement of its own and
 * cites none: the grids shown at 1366 points is a check of the acceptance, not of this test.
 */
import type { Browser, BrowserContext } from "@playwright/test";
import { describe, expect, it } from "vitest";

import type { Person } from "../service/realm";
import { signedIn } from "./steps";
import { MEASURE_WINDOW } from "./window";

describe("signedIn", () => {
  it("opens the context of each user in the window of the measures", async () => {
    const opened: unknown[] = [];
    const stop = new Error("stop after the context");
    const browser = {
      newContext: (options: unknown) => {
        opened.push(options);
        return Promise.resolve({
          newPage: () => Promise.reject(stop),
        } as unknown as BrowserContext);
      },
    } as unknown as Browser;
    const user = { login: "a", email: "a@example.org", password: "b", name: "A" } as Person;

    await expect(signedIn(browser, [user], "http://localhost")).rejects.toBe(stop);

    expect(opened).toEqual([{ viewport: MEASURE_WINDOW }]);
  });
});
