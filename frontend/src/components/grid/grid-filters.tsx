// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters above the grid of the estimate and the grid of the planning: a lot or a post of the
 * work breakdown, « Écarts seulement » on a differential, a risk occurred. A server component that
 * renders their row only when it offers one, so that a screen without filter does not spend the
 * space of an empty row.
 */
import type { BreakdownChoices } from "./breakdown-filter";
import { BreakdownFilterChoice } from "./breakdown-filter-choice";
import type { DifferenceValue } from "./difference-filter";
import { DifferencesOnly } from "./differences-only";
import type { OriginChoices } from "./origin-filter";
import { OriginFilterChoice } from "./origin-filter-choice";

/** What a grid offers to filter it by, each filter absent when the screen does not offer it. */
export interface GridFiltersProps {
  readonly breakdown: BreakdownChoices | undefined;
  /** The differences the address retains; the button is offered on a differential alone. */
  readonly difference: readonly DifferenceValue[] | undefined;
  readonly differential: boolean;
  readonly origin: OriginChoices | undefined;
}

/** Render the row of the filters of a grid; nothing when it offers none. */
export function GridFilters({ breakdown, difference, differential, origin }: GridFiltersProps) {
  if (breakdown === undefined && !differential && origin === undefined) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
      {breakdown === undefined ? null : <BreakdownFilterChoice choices={breakdown} />}
      <DifferencesOnly filter={difference} offered={differential} />
      {origin === undefined ? null : <OriginFilterChoice choices={origin} />}
    </div>
  );
}
