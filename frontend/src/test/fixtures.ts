// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The examples of the contract, for the unit tests of the front: the same data the fake back
 * serves (`fixtures/api/`), so that a page is tested on what it will receive.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { Client } from "openapi-fetch";

import type { paths } from "@/api/generated/schema";

const FIXTURES = fileURLToPath(new URL("../../../fixtures/api/", import.meta.url));

/** Read the value of an example of the contract, by the name of its fixture. */
export function example(name: string): unknown {
  const text = readFileSync(`${FIXTURES}${name}.json`, "utf-8");
  return (JSON.parse(text) as { value: unknown }).value;
}

/** Make a client that answers each path with the example of the fixture it names. */
export function fakeClient(answers: Readonly<Record<string, string | undefined>>): Client<paths> {
  const get = (path: string) => {
    const name = answers[path];
    return Promise.resolve({ data: name === undefined ? undefined : example(name) });
  };
  return { GET: get } as unknown as Client<paths>;
}
