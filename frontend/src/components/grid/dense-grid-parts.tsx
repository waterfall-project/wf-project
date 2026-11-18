// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The small parts of a dense grid (`dense-grid.tsx`): the spacer of the rows not rendered, what the cells of the body are doing, whether
 * the grid is busy, the name of a grid among several on its screen, and what holds the grid.
 */
import type { RowData } from "@tanstack/react-table";
import type { ReactNode } from "react";

import type { RowSelection } from "./row-selection";
import type { GridColumn, GridName } from "./columns";
import type { ComputedColumn } from "./computed-cell";
import type { CellDraft, CellPosition, CellRefusal } from "./grid-keyboard";
import type { UndoControl } from "./undo-commands";

/** A spacer for the rows not rendered, before or after those in view. */
export function Spacer({ height, span }: { readonly height: number; readonly span: number }) {
  return height > 0 ? (
    <tr aria-hidden="true">
      <td colSpan={span} style={{ height }} className="p-0" />
    </tr>
  ) : null;
}

/** Whether the grid is busy: reading a sort or a search anew, or a command of its screen waiting. */
export function gridBusy(
  reading: boolean,
  commands: { readonly busy: boolean },
  undo: UndoControl | undefined,
  lost = false,
): boolean {
  return reading || lost || commands.busy || undo?.busy === true;
}

/**
 * The name of a grid among several on its screen — one that writes the address under its own
 * names —, which names its search and its menu of the columns; none for a grid alone.
 */
export function sharedName(
  config: { readonly address?: unknown; readonly name: GridName },
  named: (name: GridName) => string,
): string | undefined {
  return config.address === undefined ? undefined : named(config.name);
}

/** The grid, held by what its screen puts around it, if anything. */
export function held<Row>(
  grid: ReactNode,
  rows: readonly Row[],
  around: ((rows: readonly Row[], grid: ReactNode) => ReactNode) | undefined,
): ReactNode {
  return around === undefined ? grid : around(rows, grid);
}

/** Whether the server computes the cell of a column in a row. */
export function computedIn<Row extends RowData, Sort extends string, Totals>(
  column: GridColumn<Row, Sort, Totals> | undefined,
  row: Row,
): column is ComputedColumn<Row, Sort, Totals> {
  return column?.computed?.in(row) === true;
}

/** What the cells of the body are doing: the active one, the one entered, the refusal shown. */
export interface CellStates<Row extends RowData, Sort extends string, Totals> {
  readonly cursor: CellPosition;
  readonly draft: CellDraft | undefined;
  readonly refusal: CellRefusal;
  /** What a cell under way shows, by the key of its row and its column, if it is. */
  readonly pending: (row: string, column: string) => string | undefined;
  /** The identifier of the refusal told of the write of a cell, by its row and column, if any. */
  readonly writeRefusal: (row: string, column: string) => string | undefined;
  /** The entry of the cell entered. */
  readonly editor: (draft: CellDraft, column: GridColumn<Row, Sort, Totals>) => ReactNode;
  /** Close the refusal from the keyboard, the focus back on its cell. */
  readonly closeRefusal: () => void;
  /** Close the refusal, the focus gone elsewhere. */
  readonly dismissRefusal: () => void;
  /** Whether the cells have a menu, which they announce. */
  readonly menu: boolean;
  /** The keys of the folding a row that folds tells, as far as they reach; none, none told. */
  readonly foldKeys: string | undefined;
  /** The selection of the rows, whose handles are the cells of the row numbers. */
  readonly selection: RowSelection<unknown>;
  /** The name of the handle of the row of a number, and the identifier of what describes it. */
  readonly handle: {
    readonly name: (number: number) => string;
    readonly hint: string;
  };
}
