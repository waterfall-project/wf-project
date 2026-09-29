// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of a dense grid (EP-02, « Composants partagés »): one component, and for
 * each screen — planning, estimate, remaining to commit, risks, actual costs, rates — the
 * columns it shows and the key under which the account keeps its settings. A column says what
 * it reads of a row, how its value shows, where it aligns, how wide it starts, whether the
 * server computes it, and by which column of the contract the server sorts it; the totals row
 * reads the totals of the answer, never a sum of the rows (WF-ARC-0020).
 *
 * Neither server nor client: the page reads the sortable columns of a configuration to check
 * the address, the grid the rest. Its functions stay on the side of the browser, which is why
 * a screen hands its configuration to the grid in a client component of its own.
 */
import type { ReactNode } from "react";

import type { Catalogue } from "@/i18n/catalogues";
import { formatDecimal, formatMoney, formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

/**
 * How the value of a cell shows, from the exact string of the contract: as it is (`text`), an
 * amount (`money`), a decimal — hours, a quantity (`decimal`) —, a date of planning (`date`).
 */
export type CellFormat = "text" | "money" | "decimal" | "date";

/** Where the content of a cell aligns: the start for a text, the end for a figure. */
export type CellAlign = "start" | "end";

/** The key of the heading of a column in the catalogue, under `grid.columns`. */
export type ColumnLabel = keyof Catalogue["grid"]["columns"];

/** The key of the accessible name of a grid in the catalogue, under `grid.names`. */
export type GridName = keyof Catalogue["grid"]["names"];

/** The value of a cell as the contract gives it, or none. */
export type CellValue = string | null | undefined;

/** A column of a grid of rows `Row`, sorted by a column `Sort` of the contract. */
export interface GridColumn<Row, Sort extends string, Totals> {
  /** The key of the column: stable, for it names the column in the settings of the account. */
  readonly key: string;
  readonly label: ColumnLabel;
  readonly format: CellFormat;
  /** Where the column aligns; by default, as its format does. */
  readonly align?: CellAlign;
  /** Its width before the user sets one, in pixels. */
  readonly width: number;
  /** Whether the server computes it: a shaded column, marked Σ in its header. */
  readonly computed?: boolean;
  /**
   * The identifying column: it stays at the start when the grid scrolls sideways, and cannot
   * be hidden. The first of them carries the tree, when the grid has one.
   */
  readonly pinned?: boolean;
  /** The column of the contract the server sorts it by; none, and it does not sort. */
  readonly sortBy?: Sort;
  /** What it reads of a row. */
  readonly value: (row: Row) => CellValue;
  /** What it reads of the totals of the answer, for the totals row; none, and it is blank. */
  readonly total?: (totals: Totals) => CellValue;
}

/** The tree of a grid: the depth of a row, the icon of its nature, how its label stands out. */
export interface GridTree<Row> {
  /** The depth of a row, `1` at the root, as the API computes it. */
  readonly level: (row: Row) => number;
  /** The icon of the nature of the row, named for it. */
  readonly nature: (row: Row) => ReactNode;
  /** Whether its label is set in bold — a summary — or muted — what nobody enters. */
  readonly emphasis?: (row: Row) => "strong" | "muted" | undefined;
}

/** A grid: its columns, its rows and how to tell them apart, its tree if it has one. */
export interface GridConfig<Row, Sort extends string, Totals> {
  /** The key of its settings in the account (`DisplayPreferences.grids`): stable. */
  readonly key: string;
  readonly name: GridName;
  /** The identity of a row, stable from one answer to the next. */
  readonly rowKey: (row: Row) => string;
  /** The number of a row, shown first and pinned, as the API computes it; none, no column. */
  readonly rowNumber?: (row: Row) => number;
  readonly tree?: GridTree<Row>;
  readonly columns: readonly GridColumn<Row, Sort, Totals>[];
}

/** The key of the column of row numbers, which no configuration may take. */
export const ROW_NUMBER_KEY = "row_number";

/** The narrowest a column gets: the contract keeps no width under 20. */
export const MIN_WIDTH = 40;

/** The widest a column gets. */
export const MAX_WIDTH = 800;

/** Where a column aligns. */
export function alignment(column: { readonly format: CellFormat; readonly align?: CellAlign }) {
  return column.align ?? (column.format === "text" ? "start" : "end");
}

/**
 * Show the value of a cell in a language, from the exact string of the contract: nothing for
 * none, a text as it is, a figure by the formats of the interface — never through a float.
 */
export function formatCell(format: CellFormat, value: CellValue, locale: Locale): string {
  if (value === null || value === undefined) {
    return "";
  }
  switch (format) {
    case "money":
      return formatMoney(value, locale);
    case "decimal":
      return formatDecimal(value, locale);
    case "date":
      return formatPlanningDate(value, locale);
    case "text":
      return value;
  }
}

/** The columns of a configuration the server sorts, by the column of the contract. */
export function sortColumns<Sort extends string>(config: {
  readonly columns: readonly { readonly sortBy?: Sort }[];
}): readonly Sort[] {
  return config.columns.flatMap((column) => (column.sortBy === undefined ? [] : [column.sortBy]));
}
