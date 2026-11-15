// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { vi } from "vitest";

/**
 * The browser knows itself offline (`navigator.onLine` false) as a write is sent: a rejection of
 * `fetch` is then the API out of reach, nothing having left (`rejectedWrite`, US-2240), not a write
 * that may have been done. Called by `beforeEach` of a test that wants it, which runs the
 * restoration it returns once the test is over.
 */
export function browserOffline(): () => void {
  const spy = vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(false);
  return () => {
    spy.mockRestore();
  };
}
