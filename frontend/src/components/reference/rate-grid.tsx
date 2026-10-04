// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the hourly rates (WF-REF-0050, US-0250): one row for each category of labour, one
 * column for each year the server gives — a hundred and fifty categories over fifteen years
 * (§4.6.2) —, on the dense grid, given its configuration here, on the side of the browser. The
 * page hands it data only: the grid as the server answers it, the currency of the installation,
 * whether the session may modify the cost settings, what the address asked and the settings the
 * session read.
 *
 * Each cell entered is written alone (`setHourlyRate`): the first rate of a year without a
 * version, a correction with the version of the rate read; the rate the server answers takes the
 * place of the cell, and a refusal is told as every grid tells one. A year without a rate is an
 * empty cell; no column appears of itself (WF-REF-0060). The server orders the rows and searches
 * them (`search`); the grid sorts nothing, and its totals row says the currency, never a sum.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { setHourlyRate } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import type { GridColumn, GridConfig, RowsWritten } from "@/components/grid/columns";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

/** The grid of the hourly rates, as the server answers it. */
export type HourlyRateGrid = components["schemas"]["HourlyRateGrid"];

/** A category of labour and its rate for each year of the grid. */
type RateRow = components["schemas"]["HourlyRateRow"];

/** The hourly rate of a category for a year. */
type HourlyRate = components["schemas"]["HourlyRate"];

/** The grid of the rates sorts by no column: the server gives its rows in its order. */
type RateSort = never;

/** The key of the settings of the grid in the account: stable. */
export const RATE_GRID_KEY = "hourly_rates";

/** A column of the grid of the rates: no totals but the caption. */
type RateColumn = GridColumn<RateRow, RateSort, null>;

/**
 * The row with the rate the server answered in the cell written; none when the server answered
 * the rate of another category or another year — a failure of the service, told as such.
 */
function written(
  row: RateRow,
  year: number,
  index: number,
  rate: HourlyRate,
  order: number,
): RowsWritten<RateRow, null> {
  const same = rate.cost_category_id === row.cost_category_id && rate.year === year;
  return {
    rows: same
      ? [{ ...row, cells: row.cells.map((cell, at) => (at === index ? rate : cell)) }]
      : [],
    changed: [],
    parts: [],
    totals: undefined,
    order,
  };
}

/**
 * The column of a year: its heading the year itself, each cell the rate of its category as an
 * amount; entered where the session may modify the cost settings, from the version read.
 */
function yearColumn(
  year: number,
  index: number,
  editable: boolean,
  answered: () => number,
): RateColumn {
  const rate = (row: RateRow) => row.cells[index]?.amount;
  return {
    key: `year_${year.toString()}`,
    label: "hourlyRate",
    heading: year.toString(),
    format: "money",
    width: 76,
    value: rate,
    entry: editable
      ? {
          kind: { type: "money", nullable: false },
          in: () => true,
          value: rate,
          write: async (row, value): Promise<Outcome<RowsWritten<RateRow, null>>> => {
            const read = row.cells[index];
            const outcome = await setHourlyRate(row.cost_category_id, year, {
              amount: value ?? "",
              ...(read === null || read === undefined ? {} : { lock_version: read.lock_version }),
            });
            return outcome.kind === "done"
              ? { kind: "done", data: written(row, year, index, outcome.data, answered()) }
              : outcome;
          },
        }
      : undefined,
  };
}

/**
 * The place of each answer among the writes of a reading: the cells of a row leave one after the
 * other, and each answer counts one more than the one before it.
 */
function counter(): () => number {
  let answered = 0;
  return () => {
    answered += 1;
    return answered;
  };
}

/** The grid of the rates, a column for each year of the answer. */
function rateGrid(
  years: readonly number[],
  editable: boolean,
  answered: () => number,
): GridConfig<RateRow, RateSort, null> {
  return {
    key: RATE_GRID_KEY,
    name: "hourlyRates",
    rowKey: (row) => row.cost_category_id,
    columns: [
      {
        key: "code",
        label: "code",
        format: "text",
        width: 80,
        pinned: true,
        value: (row) => row.code,
      },
      {
        key: "label",
        label: "label",
        format: "text",
        width: 240,
        pinned: true,
        value: (row) => row.label,
      },
      ...years.map((year, index) => yearColumn(year, index, editable, answered)),
    ],
  };
}

/** What the grid of the rates shows. */
export interface RateGridProps {
  readonly grid: HourlyRateGrid;
  /** The currency of the installation, in which every rate is expressed (WF-REF-0140). */
  readonly currency: string;
  /** Whether the session may modify the cost settings (`platformOffer`). */
  readonly editable: boolean;
  readonly query: GridQuery<RateSort>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the hourly rates, its totals row the currency they are expressed in. */
export function RateGrid({ grid, currency, editable, query, preferences }: RateGridProps) {
  const t = useTranslations("reference.rates");
  // A new count of the answers for each configuration, which a new reading brings.
  const config = useMemo(() => rateGrid(grid.years, editable, counter()), [grid.years, editable]);
  return (
    <DenseGrid
      config={config}
      rows={grid.rows}
      totals={null}
      totalsCaption={() => t("caption", { currency })}
      query={query}
      preferences={preferences}
    />
  );
}
