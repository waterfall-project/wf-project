// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Set up the component tests, which run in jsdom: the matchers of jest-dom
 * (`toBeInTheDocument`, `toHaveAccessibleName`…), and a clean document after each test —
 * Testing Library only cleans up by itself when the test functions are global, and they
 * are imported here.
 */
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
