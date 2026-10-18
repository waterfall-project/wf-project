// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The session of the front in a unit test: the Redis of the tests, and the cookies of a request.
 *
 * The sessions are tested against a real Redis, never a stand-in: `WATERFALL_TEST_REDIS_URL` names
 * it (guide, « Un test contre Redis »), and a test that needs it fails, saying so, without it. Each
 * key the store writes is drawn at random: files that run together never meet.
 */
import { afterAll, beforeAll } from "vitest";

import { closeStore } from "@/session/store";

/** Point the store of the sessions at the Redis of the tests, and close it after the file. */
export function withTestRedis(): void {
  beforeAll(() => {
    const address = process.env.WATERFALL_TEST_REDIS_URL;
    if (address === undefined || address === "") {
      throw new Error(
        "WATERFALL_TEST_REDIS_URL must name a Redis for the tests of the sessions of the front " +
          '(docs/dev/README.md, "Un test contre Redis")',
      );
    }
    process.env.WATERFALL_REDIS_URL = address;
  });
  afterAll(closeStore);
}

/** The cookies of a request, as `cookies()` of `next/headers` gives what the session reads. */
export interface CookieJar {
  get(name: string): { readonly name: string; readonly value: string } | undefined;
  delete(name: string): void;
  /** What the request holds, by name. */
  readonly held: Map<string, string>;
}

/** The cookies of a request that holds these. */
export function cookieJar(held: Record<string, string> = {}): CookieJar {
  const cookies = new Map(Object.entries(held));
  return {
    held: cookies,
    get: (name) => {
      const value = cookies.get(name);
      return value === undefined ? undefined : { name, value };
    },
    delete: (name) => {
      cookies.delete(name);
    },
  };
}
