// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the aggregated workload keeps from one consultation to the next (WF-PTF-0060-A): its
 * horizon, its threshold of under-load and the node of organisation of its perimeter — display
 * preferences (WF-ADM-0040), kept as the settings of a grid are (WF-IHM-0060): under a key of its
 * own, in the `filters` of its `GridPreferences`, each parameter under the name of the address with
 * its value as text. The address stays the truth of the screen: what is kept serves only when it
 * names none of the three, which the page replaces, on the server, by the address with those kept
 * (`restoredWorkload`). The other parameters of the perimeter — the states, the period, the date of
 * calculation — are shared with the other views of the portfolio, and kept by none.
 *
 * Pure, and neither server nor client: the page restores, the screen records (`kept-workload.tsx`).
 */
import { keptReading, restoredAddress } from "@/components/grid/kept-address";
import { CONTRACT_ADDRESS } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";

import { AS_OF, FROM, HORIZON, ORG_NODE, STATES, THRESHOLD, TO } from "./address";

/** The key the preferences of the aggregated workload are kept under, as `portfolio_projects` is. */
export const WORKLOAD_KEY = "portfolio_workload";

/** The route of the aggregated workload. */
export const WORKLOAD_PATH = "/portfolio/workload";

/**
 * What the screen reads of its address to keep: the three settings, and, as the search that says a
 * reading lifted, the horizon — written empty when a change would leave the address naming none.
 */
export const WORKLOAD_KEPT = {
  ...keptReading(CONTRACT_ADDRESS, []),
  search: HORIZON,
  filters: [HORIZON, THRESHOLD, ORG_NODE],
  sort: [],
  size: [],
};

/** The parameters of the perimeter the other views share, which a restoration keeps as they are. */
const SHARED = [STATES, FROM, TO, AS_OF] as const;

/**
 * The address of the settings kept, for a consultation that names none of them — the shared
 * parameters of its address carried over; none when it names one, or when nothing is kept.
 */
export function restoredWorkload(
  search: SearchParameters,
  kept: Readonly<Record<string, unknown>> | null | undefined,
): string | undefined {
  const restored = restoredAddress(WORKLOAD_PATH, search, WORKLOAD_KEPT, kept);
  if (restored === undefined) {
    return undefined;
  }
  const query = new URLSearchParams(restored.split("?")[1] ?? "");
  for (const name of SHARED) {
    const value = search.get(name);
    if (value !== null) {
      query.set(name, value);
    }
  }
  return `${WORKLOAD_PATH}?${query.toString()}`;
}
