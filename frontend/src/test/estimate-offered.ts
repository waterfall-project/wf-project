// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The columns the grid of the estimate offers, for the tests of its settings: its own, and those of
 * the difference to a base, whatever it reads (US-2340). An account that set the grid before has not
 * seen the latter: they are hidden, as any column it did not know (US-0650). A module of the
 * browser, as the grid it names the columns of: tests of the project `dom` alone import it.
 */
"use client";

import { comparedGrid } from "@/components/grid/compared";
import { ESTIMATE_GRID } from "@/components/grid/estimate";

import type { FakeClient } from "./fixtures";
import { allShown, recordedAside } from "./grid-preferences";

/** The columns of the grid of the estimate, and those of the difference to a base. */
export const ESTIMATE_OFFERED = comparedGrid(ESTIMATE_GRID, false).columns;

/** The preferences of a grid of the estimate that knows each of them and hides none. */
export const ESTIMATE_SHOWN = allShown(ESTIMATE_OFFERED);

/** What such an account records hidden once the sub-project is: the columns it did not know. */
export const UNSEEN = [
  "delta_unit_disbursement",
  "subproject",
  "delta_base_amount",
  "delta_reestimated_amount",
];

/** The bodies the fake back received to record the preferences of the grid of the estimate. */
export function recordedEstimate(client: FakeClient): unknown[] {
  return recordedAside(client, ESTIMATE_OFFERED);
}
