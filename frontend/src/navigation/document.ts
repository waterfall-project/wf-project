// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A load of a whole document, where a navigation within the application would keep what the
 * session before left in the page. Signing in or out changes whose page it is: the root layout
 * reads the new session — its permissions, its language, its mode —, and the tracker of the
 * shell starts again from the storage of the tab, following on the tasks a lost session
 * interrupted (`src/components/tasks/storage.ts`).
 */

/** Load the document at an address of the front, or of the sign-out of the realm. */
export function loadDocument(address: string): void {
  window.location.assign(address);
}
