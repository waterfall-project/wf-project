// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { availableParallelism } from "node:os";

import { afterEach, describe, expect, it, vi } from "vitest";

import config, { processors, workers } from "../../vitest.config";

describe("the workers of the unit tests of the front (#1474)", () => {
  it.each([
    [1, 1],
    [2, 1],
    [3, 2],
    [4, 3],
    [5, 4],
    [12, 4],
    [64, 4],
  ])("plays on %i processors with %i workers", (processors, expected) => {
    expect(workers(processors)).toBe(expected);
  });

  it("leaves a processor to the main process wherever there are two or more, and never takes more than four", () => {
    for (let processors = 1; processors <= 128; processors += 1) {
      const taken = workers(processors);
      expect(taken).toBeGreaterThanOrEqual(1);
      expect(taken).toBeLessThanOrEqual(4);
      if (processors >= 2) {
        expect(taken).toBeLessThan(processors);
      }
    }
  });

  it("is the number the configuration gives Vitest on this machine, or on its share of it", () => {
    expect(config.test?.maxWorkers).toBe(workers(processors()));
  });
});

describe("the processors of a run of the unit tests, as make shares them (US-1090)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it.each([undefined, ""])("are all of the machine's when the share is %j", (named) => {
    vi.stubEnv("WATERFALL_PROCESSORS", named);
    expect(processors()).toBe(availableParallelism());
  });

  it.each([
    ["12", 12],
    ["6", 6],
    ["1", 1],
  ])("are the share %j make gave the run", (named, expected) => {
    vi.stubEnv("WATERFALL_PROCESSORS", named);
    expect(processors()).toBe(expected);
    expect(workers(processors())).toBe(workers(expected));
  });

  it.each(["0", "-1", "2.5", "half"])("refuses %j as a share of the processors", (named) => {
    vi.stubEnv("WATERFALL_PROCESSORS", named);
    expect(() => processors()).toThrow("WATERFALL_PROCESSORS must be a whole number of processors");
  });
});
