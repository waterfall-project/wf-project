// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading of the cost of the cache by the measure of a version (`cache-read.ts`, US-2420): a
 * tool of the measure, which covers no requirement of its own and cites none.
 */
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterAll, describe, expect, it } from "vitest";

import { cacheRead } from "./cache-read";

const directory = mkdtempSync(join(tmpdir(), "cache-read-"));
afterAll(() => {
  rmSync(directory, { recursive: true, force: true });
});

describe("cacheRead", () => {
  it("refuses a path that is empty, naming the variable that gives it", () => {
    expect(() => cacheRead("")).toThrow(/E2E_MEASURE_CACHE.*run it first/);
  });

  it("refuses a file that is absent, naming it", () => {
    const absent = join(directory, "absent.json");
    expect(() => cacheRead(absent)).toThrow(new RegExp(`${absent}.*run it first`));
  });

  it("refuses a JSON that is invalid, naming the file", () => {
    const broken = join(directory, "broken.json");
    writeFileSync(broken, "{ not json");
    expect(() => cacheRead(broken)).toThrow(new RegExp(`${broken}: not a JSON`));
  });

  it("refuses a file without the measure of the cache", () => {
    const valid = join(directory, "other.json");
    writeFileSync(valid, JSON.stringify({ measures: [] }));
    expect(() => cacheRead(valid)).toThrow(/indicators cache/);
  });
});
