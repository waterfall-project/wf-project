// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Set up the component tests, which run in a document (happy-dom): the matchers of jest-dom
 * (`toBeInTheDocument`, `toHaveAccessibleName`…), and a clean document after each test —
 * Testing Library only cleans up by itself when the test functions are global, and they
 * are imported here.
 *
 * A test that writes on the error output fails, once its document is cleaned: a warning or an
 * error on the console is a defect of the test or of the code, never noise to read past
 * (`src/test/stderr.ts`). Each line names the test running as it was written. The output is
 * checked once more as the file ends, for a line written after its last test — a check no test
 * of the setup proves: a test cannot watch the end of its own file.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach } from "vitest";

import { takeStderr, watchStderr } from "./stderr";

watchStderr();

/** Fail on what was written on the error output since it was last taken, each line by its test. */
function refuseStderr(): void {
  const written = takeStderr();
  if (written.length > 0) {
    throw new Error(`A test wrote on the error output:\n${written.join("\n")}`);
  }
}

// The hooks after a test run in the reverse of their order here: the document is cleaned first,
// and what its unmounting writes is counted.
afterEach(refuseStderr);
afterAll(refuseStderr);

afterEach(() => {
  cleanup();
});
