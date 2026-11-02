// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The preferences of a grid, for the tests of its settings: those of a grid that knows every column
 * it offers and hides none, and what a grid records, its known columns checked to be the ones it
 * offers and set aside (US-0650). Each test file mocks the server of Next itself and serves its own
 * fake back: what is shared here is data and the reading of its calls.
 */
import { expect } from "vitest";

import { ESTIMATE_GRID } from "@/components/grid/estimate";
import { PLANNING_GRID } from "@/components/grid/planning";
import { REMAINING_GRID } from "@/components/grid/remaining";
import type { GridPreferences } from "@/components/grid/settings";

import type { FakeClient } from "./fixtures";

/** The operation that records the preferences of the account. */
export const PREFERENCES = "PATCH /me/preferences";

/** The keys of the columns a grid offers, in its order: those it records as known. */
export function keysOf(columns: readonly { readonly key: string }[]): string[] {
  return columns.map((column) => column.key);
}

/** The preferences of a grid that knows the columns given and hides none: each of them shows. */
export function allShown(columns: readonly { readonly key: string }[]): GridPreferences {
  return { hidden_columns: [], known_columns: keysOf(columns) };
}

/**
 * The preferences of a grid of a structure — the planning, the estimate, the remaining to commit —
 * that knows every column the three offer and hides none: the columns hidden by default show too.
 */
export const SHOWN: GridPreferences = allShown([
  ...PLANNING_GRID.columns,
  ...ESTIMATE_GRID.columns,
  ...REMAINING_GRID.columns,
]);

/**
 * The bodies the fake back received to record preferences, the known columns of each grid set
 * aside once checked to be the keys of the columns given — what the grid offers.
 */
export function recordedAside(
  client: FakeClient,
  columns: readonly { readonly key: string }[],
): unknown[] {
  return client.calls
    .filter((call) => call.route === PREFERENCES)
    .map((call) => {
      const { grids } = call.body as { readonly grids: Readonly<Record<string, GridPreferences>> };
      const aside = Object.entries(grids).map(([key, { known_columns: known, ...grid }]) => {
        expect(known).toEqual(keysOf(columns));
        return [key, grid] as const;
      });
      return { grids: Object.fromEntries(aside) };
    });
}
