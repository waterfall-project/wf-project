// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The window of the measures against the service (`window.ts`, #3801): never narrower than the
 * specification guarantees the grids usable in.
 */
import { describe, expect, it } from "vitest";

import { MEASURE_WINDOW, SPECIFIED_WIDTH } from "./window";

describe("MEASURE_WINDOW", () => {
  it("is as wide as the specification guarantees the grids usable in [WF-CMP-0010-A]", () => {
    expect(MEASURE_WINDOW.width).toBeGreaterThanOrEqual(SPECIFIED_WIDTH);
  });
});
