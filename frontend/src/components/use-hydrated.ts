// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether React answers the page yet: `false` on the server and while the document it sent is
 * being hydrated, `true` from then on — and at once for a component mounted by a navigation in
 * the browser.
 *
 * A form whose sending is handled by React — a value sent to a server action — keeps its
 * button disabled until then: before the hydration, the browser would send the form itself, by
 * GET, the value in the address (#499).
 */
import { useSyncExternalStore } from "react";

// Being hydrated does not change once it is: nothing to subscribe to.
const unchanging = () => () => undefined;

/** Whether the component is rendered by React in the browser, its document hydrated. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    unchanging,
    () => true,
    () => false,
  );
}
