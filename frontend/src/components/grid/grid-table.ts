// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The model of a dense grid, held by TanStack Table: the columns of its configuration, which
 * the user shows, hides and widens, the identifying ones pinned at the start, and the sort
 * the header offers. Sorting is manual: no sorted row model is registered, so the table keeps
 * the rows in the order of the answer, and a sort asked for only changes the address, which the
 * server reads (EP-02, « Grille dense »). Nothing is filtered, grouped or summed here either:
 * none of those features is registered.
 */
"use client";

import {
  columnPinningFeature,
  columnResizingFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  createColumnHelper,
  type Header,
  type ReactTable,
  type RowData,
  rowSortingFeature,
  type SortingState,
  tableFeatures,
  type Updater,
  useTable,
} from "@tanstack/react-table";
import { useMemo } from "react";

import { type GridColumn, type GridConfig, MAX_WIDTH, MIN_WIDTH, ROW_NUMBER_KEY } from "./columns";
import type { GridSort } from "./query";
import type { GridSettings } from "./settings";

/** The features of the table of a grid, and nothing more. */
export const GRID_FEATURES = tableFeatures({
  columnVisibilityFeature,
  columnSizingFeature,
  columnResizingFeature,
  columnPinningFeature,
  rowSortingFeature,
});

/** The features of the table of a grid. */
export type GridFeatures = typeof GRID_FEATURES;

/** The table of a grid of rows `Row`. */
export type GridTable<Row extends RowData> = ReactTable<GridFeatures, Row>;

/** A header of the table of a grid. */
export type GridHeader<Row extends RowData> = Header<GridFeatures, Row>;

/** The width of the column of row numbers. */
const ROW_NUMBER_WIDTH = 48;

/** The columns of the table, from those of the configuration: the row numbers first, if any. */
function tableColumns<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
) {
  const helper = createColumnHelper<GridFeatures, Row>();
  const numbers =
    config.rowNumber === undefined
      ? []
      : [
          helper.display({
            id: ROW_NUMBER_KEY,
            size: ROW_NUMBER_WIDTH,
            enableHiding: false,
            enableSorting: false,
            enableResizing: false,
          }),
        ];
  return [
    ...numbers,
    // An accessor, which a column needs to offer its sort: the value it reads, never sorted
    // here — no sorted row model is registered.
    ...config.columns.map((column) =>
      helper.accessor((row): unknown => column.value(row), {
        id: column.key,
        size: column.width,
        minSize: MIN_WIDTH,
        maxSize: MAX_WIDTH,
        enableHiding: column.pinned !== true,
        enableSorting: column.sortBy !== undefined,
        sortDescFirst: false,
      }),
    ),
  ];
}

/** Resolve a change of TanStack Table: a value, or what makes it from the one before. */
function resolve<T>(updater: Updater<T>, before: T): T {
  return typeof updater === "function" ? (updater as (old: T) => T)(before) : updater;
}

/** What the table of a grid is made of. */
export interface GridTableOptions<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly rows: readonly Row[];
  /** The sort the address asks for. */
  readonly sort: GridSort<Sort> | undefined;
  /** Ask for another sort, or none — the order of the plan. */
  readonly onSort: (sort: GridSort<Sort> | undefined) => void;
  readonly settings: GridSettings;
  readonly onSettings: (settings: GridSettings) => void;
}

/** The column of the configuration a column of the table shows, by its key. */
export function configColumn<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  key: string,
): GridColumn<Row, Sort, Totals> | undefined {
  return config.columns.find((column) => column.key === key);
}

/**
 * Make the table of a grid. Its sort is the address's: a click on a header computes the next
 * one — ascending, descending, then none — and hands it to `onSort`, never to the rows.
 */
export function useGridTable<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  sort,
  onSort,
  settings,
  onSettings,
}: GridTableOptions<Row, Sort, Totals>): GridTable<Row> {
  const columns = useMemo(() => tableColumns(config), [config]);
  const pinned = useMemo(
    () => [
      ...(config.rowNumber === undefined ? [] : [ROW_NUMBER_KEY]),
      ...config.columns.filter((column) => column.pinned === true).map((column) => column.key),
    ],
    [config],
  );
  const sortedKey = config.columns.find((column) => column.sortBy === sort?.column)?.key;
  const sorting: SortingState =
    sort === undefined || sortedKey === undefined
      ? []
      : [{ id: sortedKey, desc: sort.order === "desc" }];
  return useTable({
    features: GRID_FEATURES,
    columns,
    // The rows of the answer, as they came: the table never copies nor reorders them.
    data: rows,
    getRowId: (row) => config.rowKey(row),
    manualSorting: true,
    enableMultiSort: false,
    columnResizeMode: "onChange",
    initialState: { columnPinning: { start: pinned, end: [] } },
    state: {
      sorting,
      columnVisibility: settings.visibility,
      columnSizing: settings.sizing,
    },
    onSortingChange: (updater) => {
      const [next] = resolve(updater, sorting);
      const by = next === undefined ? undefined : configColumn(config, next.id)?.sortBy;
      onSort(by === undefined ? undefined : { column: by, order: next?.desc ? "desc" : "asc" });
    },
    onColumnVisibilityChange: (updater) => {
      onSettings({ ...settings, visibility: resolve(updater, { ...settings.visibility }) });
    },
    onColumnSizingChange: (updater) => {
      onSettings({ ...settings, sizing: resolve(updater, { ...settings.sizing }) });
    },
  });
}
