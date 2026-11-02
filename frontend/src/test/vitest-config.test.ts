// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { availableParallelism } from "node:os";

import { describe, expect, it } from "vitest";

import config, { workers } from "../../vitest.config";

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

  it("is the number the configuration gives Vitest on this machine", () => {
    expect(config.test?.maxWorkers).toBe(workers(availableParallelism()));
  });
});
