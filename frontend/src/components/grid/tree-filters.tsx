// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the grids of the structure — the estimate, the planning, the remaining to commit:
 * a lot or a post of the work breakdown, « Écarts seulement » on a differential, a risk occurred.
 * A server component that renders them as compact controls for the bar of the grid
 * (`GridToolbar.barFilters`, #2916/L6, WF-IHM-0130, WF-PLA-0080), and nothing when the screen offers
 * none: the bar keeps its one line.
 */
import type { BreakdownChoices } from "./breakdown-filter";
import { BreakdownFilterChoice } from "./breakdown-filter-choice";
import type { DifferenceValue } from "./difference-filter";
import { DifferencesOnly } from "./differences-only";
import type { OriginChoices } from "./origin-filter";
import { OriginFilterChoice } from "./origin-filter-choice";

/** What a grid offers to filter it by, each filter absent when the screen does not offer it. */
export interface TreeFiltersProps {
  readonly breakdown?: BreakdownChoices | undefined;
  /** The differences the address retains; the button is offered on a differential alone. */
  readonly difference?: readonly DifferenceValue[] | undefined;
  readonly differential?: boolean | undefined;
  readonly origin?: OriginChoices | undefined;
}

/** Render the filters of a grid for its bar; nothing when it offers none. */
export function TreeFilters({ breakdown, difference, differential, origin }: TreeFiltersProps) {
  if (breakdown === undefined && differential !== true && origin === undefined) {
    return null;
  }
  return (
    <>
      {breakdown === undefined ? null : <BreakdownFilterChoice choices={breakdown} />}
      <DifferencesOnly filter={difference} offered={differential === true} compact />
      {origin === undefined ? null : <OriginFilterChoice choices={origin} />}
    </>
  );
}
