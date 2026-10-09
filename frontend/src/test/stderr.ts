// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a component test writes on the error output: a warning of ECharts, an error of React, an
 * answer the fake back lacks, thrown aside. The test passes all the same, and its output fills
 * with noise in which the next warning goes unseen. The console of the test is watched here, and
 * each test that wrote on it fails (`src/test/setup-dom.ts`).
 *
 * A test that proves an error is told on the console silences it itself, by a spy on the console
 * (`vi.spyOn(console, "error").mockImplementation(…)`), and checks what it was told: what a spy
 * catches is not written, so it is not counted.
 */
import { format } from "node:util";

import { expect } from "vitest";

/** The methods of the console that write on the error output. */
const LEVELS = ["error", "warn", "trace"] as const;

/** What was written since it was last taken. */
let written: string[] = [];

/** A console, or what of it writes on the error output. */
type ErrorConsole = Pick<Console, (typeof LEVELS)[number]>;

/**
 * Watch the methods of a console that write on the error output — of the test, unless another is
 * given: each line still goes out, and is kept until taken, under the name of the test running
 * as it is written.
 */
export function watchStderr(target: ErrorConsole = console): void {
  for (const level of LEVELS) {
    const write = target[level].bind(target);
    target[level] = (...data: unknown[]) => {
      // The test running as the line is written, which may be a later one than the test that
      // scheduled it: a timer left to run past its test writes in the next. A line written
      // between two tests bears the name of the one before; before the first, none.
      const test = expect.getState().currentTestName ?? "(before any test)";
      written.push(`${test} › console.${level}: ${format(...data)}`);
      write(...data);
    };
  }
}

/** What was written on the error output since the last time it was taken, emptied. */
export function takeStderr(): readonly string[] {
  const taken = written;
  written = [];
  return taken;
}
