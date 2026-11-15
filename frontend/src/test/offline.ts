// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { vi } from "vitest";

/**
 * The browser knows itself offline (`navigator.onLine` false), as when a server action cannot be
 * reached: a rejection of `fetch` is then the API out of reach, nothing having left (`rejected`,
 * US-2240), not a write that may have been done. Called by `beforeEach`.
 */
export function browserOffline(): void {
  vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(false);
}
