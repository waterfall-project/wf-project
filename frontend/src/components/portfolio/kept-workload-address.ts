// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the aggregated workload keeps from one consultation to the next (WF-PTF-0060-A): its
 * horizon, its threshold of under-load and the node of organisation of its perimeter — display
 * preferences (WF-ADM-0040), kept as the settings of a grid are (WF-IHM-0060): under a key of its
 * own, in the `filters` of its `GridPreferences`, each parameter under the name of the address with
 * its value as text. The address stays the truth of the screen: a setting it names — even empty, "by
 * default" — stands, one it leaves out takes the value kept, which the page restores, on the server,
 * by redirecting to the address that names it (`restoredWorkload`). The node being a parameter of
 * the perimeter other views share, an address that names it alone still finds the horizon and the
 * threshold kept. The other parameters of the perimeter — the states, the period, the date of
 * calculation — are shared with the other views of the portfolio, and kept by none.
 *
 * Pure, and neither server nor client: the page restores, the screen records (`kept-workload.tsx`).
 */
import type { KeptReading } from "@/components/grid/kept-address";
import type { SearchParameters } from "@/navigation/context";

import { AS_OF, FROM, HORIZON, ORG_NODE, STATES, THRESHOLD, TO } from "./address";

/** The three settings, under the names of the address. */
const SETTINGS = [HORIZON, THRESHOLD, ORG_NODE];

/** The key the preferences of the aggregated workload are kept under, as `portfolio_projects` is. */
export const WORKLOAD_KEY = "portfolio_workload";

/** The route of the aggregated workload. */
export const WORKLOAD_PATH = "/portfolio/workload";

/**
 * What the screen reads of its address to keep: the three settings, each restored by itself, and
 * written empty — "by default" — when a change removes it. It has neither sort nor pages.
 */
export const WORKLOAD_KEPT: KeptReading = {
  search: HORIZON,
  filters: SETTINGS,
  sort: [],
  size: [],
  settings: SETTINGS,
};

/** The parameters of the perimeter the other views share, which a restoration keeps as they are. */
const SHARED = [STATES, FROM, TO, AS_OF] as const;

/**
 * The address of the settings kept, setting by setting: one the address does not name takes the value
 * kept for it, if any; one it names, even empty — "by default" —, stands as written. None when no
 * setting the address leaves out has a value kept, which ends the redirection: the address then names
 * every setting restored. The shared parameters of the address are carried over.
 */
export function restoredWorkload(
  search: SearchParameters,
  kept: Readonly<Record<string, unknown>> | null | undefined,
): string | undefined {
  const query = new URLSearchParams();
  let restored = false;
  for (const name of SETTINGS) {
    const asked = search.get(name);
    const value = kept?.[name];
    if (asked !== null) {
      query.set(name, asked);
    } else if (typeof value === "string" && value !== "") {
      query.set(name, value);
      restored = true;
    }
  }
  if (!restored) {
    return undefined;
  }
  for (const name of SHARED) {
    const value = search.get(name);
    if (value !== null) {
      query.set(name, value);
    }
  }
  return `${WORKLOAD_PATH}?${query.toString()}`;
}
