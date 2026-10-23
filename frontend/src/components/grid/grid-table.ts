// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The model of a dense grid, held by TanStack Table: the columns of its configuration, which
 * the user shows, hides and widens, the identifying ones pinned at the start — and one at the end,
 * for a grid that pins one there, the Gantt (US-0530) —, and the sort
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

import {
  type GridColumn,
  type GridConfig,
  DIFF_MARK_KEY,
  MAX_WIDTH,
  MIN_WIDTH,
  ROW_NUMBER_KEY,
  sortedBy,
  WIDEST,
} from "./columns";
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

/** The width of the column of the marks of a difference. */
const DIFF_MARK_WIDTH = 32;

/**
 * The columns of the table, from those of the configuration: the marks of a difference first, if the
 * grid reads any, then the row numbers, if any.
 */
function tableColumns<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  endMax: number,
) {
  const helper = createColumnHelper<GridFeatures, Row>();
  const marks =
    config.difference === undefined
      ? []
      : [
          helper.display({
            id: DIFF_MARK_KEY,
            size: DIFF_MARK_WIDTH,
            enableHiding: false,
            enableSorting: false,
            enableResizing: false,
          }),
        ];
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
    ...marks,
    ...numbers,
    // An accessor, which a column needs to offer its sort: the value it reads, never sorted
    // here — no sorted row model is registered.
    ...config.columns.map((column) =>
      helper.accessor((row): unknown => column.value(row), {
        id: column.key,
        size: column.width,
        minSize: MIN_WIDTH,
        maxSize: column.pinned === "end" ? endMax : MAX_WIDTH,
        enableHiding: column.pinned !== true,
        enableSorting: sortedBy(config, column) !== undefined,
        sortDescFirst: column.descendingFirst === true,
      }),
    ),
  ];
}

/** The width of a column of the configuration, as the settings size it. */
function widthOf(column: { readonly key: string; readonly width: number }, settings: GridSettings) {
  return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, settings.sizing[column.key] ?? column.width));
}

/**
 * The widest the column pinned at the end gets: the room of the frame less the columns pinned at
 * the start, which it never covers — the marks of a difference and the row numbers, which never
 * widen, then the identifying columns —, and less the widest column shown between them, so that
 * the active cell, wherever it is, scrolls out from under it whole (WF-IHM-0100). Never narrower
 * than any column; the widest a window holds before the frame is measured.
 */
export function endMaxOf<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  settings: GridSettings,
  room: number | undefined,
): number {
  if (room === undefined) {
    return WIDEST;
  }
  const fixed =
    (config.difference === undefined ? 0 : DIFF_MARK_WIDTH) +
    (config.rowNumber === undefined ? 0 : ROW_NUMBER_WIDTH);
  const start = config.columns
    .filter((column) => column.pinned === true)
    .reduce((width, column) => width + widthOf(column, settings), fixed);
  const between = config.columns
    .filter((column) => column.pinned === undefined || column.pinned === false)
    .filter((column) => settings.visibility[column.key] !== false)
    .reduce((widest, column) => Math.max(widest, widthOf(column, settings)), 0);
  return Math.max(MIN_WIDTH, Math.floor(room - start - between));
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
  /**
   * The room the rows have at the widest the frame gets, which bounds the column pinned at the end
   * (`useFrameRoom`); none before it is measured.
   */
  readonly room?: number | undefined;
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
 * one — ascending, descending, then none, unless the grid never lifts its sort — and hands it to
 * `onSort`, never to the rows.
 */
export function useGridTable<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  sort,
  onSort,
  settings,
  room,
  onSettings,
}: GridTableOptions<Row, Sort, Totals>): GridTable<Row> {
  const endMax = endMaxOf(config, settings, room);
  const columns = useMemo(() => tableColumns(config, endMax), [config, endMax]);
  const ended = useMemo(
    () => config.columns.filter((column) => column.pinned === "end").map((column) => column.key),
    [config],
  );
  const pinned = useMemo(
    () => [
      ...(config.difference === undefined ? [] : [DIFF_MARK_KEY]),
      ...(config.rowNumber === undefined ? [] : [ROW_NUMBER_KEY]),
      ...config.columns.filter((column) => column.pinned === true).map((column) => column.key),
    ],
    [config],
  );
  const sortedKey = config.columns.find(
    (column) => sort !== undefined && sortedBy(config, column) === sort.column,
  )?.key;
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
    enableSortingRemoval: config.lifts !== false,
    columnResizeMode: "onChange",
    initialState: { columnPinning: { start: pinned, end: ended } },
    state: {
      sorting,
      columnVisibility: settings.visibility,
      columnSizing: settings.sizing,
    },
    onSortingChange: (updater) => {
      const [next] = resolve(updater, sorting);
      const column = next === undefined ? undefined : configColumn(config, next.id);
      const by = column === undefined ? undefined : sortedBy(config, column);
      onSort(by === undefined ? undefined : { column: by, order: next?.desc ? "desc" : "asc" });
    },
    onColumnVisibilityChange: (updater) => {
      onSettings({ ...settings, visibility: resolve(updater, { ...settings.visibility }) });
    },
    onColumnSizingChange: (updater) => {
      // Each width changed within the bounds of its column, as the table shows it: a column dragged
      // past them widens back from where it stops. One left as it was keeps what the account kept,
      // wider than a narrow window lets it show.
      const sizing = Object.entries(resolve(updater, { ...settings.sizing })).map(([key, width]) =>
        width === settings.sizing[key]
          ? ([key, width] as const)
          : ([
              key,
              Math.min(
                configColumn(config, key)?.pinned === "end" ? endMax : MAX_WIDTH,
                Math.max(MIN_WIDTH, width),
              ),
            ] as const),
      );
      onSettings({ ...settings, sizing: Object.fromEntries(sizing) });
    },
  });
}
