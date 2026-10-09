// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the rate the server answers changes of a row of the grid of the hourly rates: the cell of its
 * year, never the row whole. A row carries no counter of its own, each rate its own (`lock_version`
 * of `HourlyRate`): the answer is the change of one cell, laid over the row shown — or over a row
 * read anew — while the cell there is older than the rate answered, so that a reading anew that
 * caught up with another cell of the row keeps the rate answered since (`RowPart.versioned`). The
 * cell is found by its year among those of the row laid over, never by a place fixed when the rate
 * was written: a reading anew that holds a year more before it moves every cell after it. Each row
 * so carries the year of each of its cells — those of its reading, then those the grid added past
 * them —, one array the rows of a reading share.
 *
 * Neither server nor client: the grid writes by it, and its tests read it.
 */
import type { components } from "@/api/generated/schema";
import type { RowsWritten } from "@/components/grid/columns";

/**
 * A category of labour and its rate for each year of the grid, with the year of each of its cells:
 * `years[index]` is the year of `cells[index]`.
 */
export type RateRow = components["schemas"]["HourlyRateRow"] & {
  readonly years: readonly (number | undefined)[];
};

/** A year of the grid, and the place of its rate among the cells of a row. */
export interface YearCell {
  readonly year: number;
  readonly index: number;
}

/** The rows of a reading, each with the year of each of its cells, as the years of the grid place them. */
export function withYears(
  rows: readonly components["schemas"]["HourlyRateRow"][],
  cells: readonly YearCell[],
): RateRow[] {
  const years: (number | undefined)[] = [];
  for (const { year, index } of cells) {
    years[index] = year;
  }
  return rows.map((row) => ({ ...row, years }));
}

/** The hourly rate of a category for a year. */
export type HourlyRate = components["schemas"]["HourlyRate"];

/**
 * The row with a rate in the cell of its year; the very row when the row has no cell for that year,
 * or holds a rate of it as new or newer.
 */
export function rated(row: RateRow, rate: HourlyRate): RateRow {
  const index = row.years.indexOf(rate.year);
  const read = row.cells[index];
  if (
    index < 0 ||
    (read !== null && read !== undefined && read.lock_version >= rate.lock_version)
  ) {
    return row;
  }
  // The column of a year the grid added stands past the cells of the answer: the row grows to it.
  const cells = Array.from({ length: Math.max(row.cells.length, index + 1) }, (_, at) =>
    at === index ? rate : (row.cells[at] ?? null),
  );
  return { ...row, cells };
}

/**
 * What the rate the server answered for the cell of a year of a row writes: the change of that
 * cell; nothing when the server answered the rate of another category or another year — a failure
 * of the service, told as such.
 */
export function rateWritten(
  row: RateRow,
  year: number,
  rate: HourlyRate,
  order: number,
): RowsWritten<RateRow, null> {
  const same = rate.cost_category_id === row.cost_category_id && rate.year === year;
  return {
    rows: [],
    changed: [],
    parts: same
      ? [{ key: row.cost_category_id, change: (shown) => rated(shown, rate), versioned: true }]
      : [],
    totals: undefined,
    order,
  };
}
