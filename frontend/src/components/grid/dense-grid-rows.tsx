// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rows of the body of a dense grid (`dense-grid.tsx`): each row of the answer the grid renders,
 * and its cells — the active one in the order of tabulation, the one entered, the one the server
 * computes, the mark of the difference of the row and of the base of a cell that differs.
 */
"use client";

import type { RowData, Row as TableRowModel } from "@tanstack/react-table";
import type { ReactNode } from "react";

import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import { useCurrency } from "@/currency/context";
import type { Locale } from "@/i18n/locale";

import { BaseMark } from "./base-mark";
import {
  BODY_ROW,
  cellAttributes,
  cellKeys,
  cellStateOf,
  invalidRing,
  ROW_HOVER,
} from "./cell-attributes";
import {
  type DependencyReader,
  DIFF_MARK_KEY,
  type GridColumn,
  type GridConfig,
  ROW_NUMBER_KEY,
} from "./columns";
import { ComputedCell } from "./computed-cell";
import { cellContent } from "./dense-grid-cell";
import { type CellStates, computedIn } from "./dense-grid-parts";
import { DiffMark, differenceTint } from "./diff-mark";
import { useTreeRow } from "./fold";
import type { CellPosition } from "./grid-keyboard";
import { configColumn, type GridFeatures, type GridTable } from "./grid-table";
import { pinningOf } from "./pinning";
import { HandleCell, selectedRow } from "./row-selection";
import { alignClass } from "./totals-row";

/**
 * What a cell shows: the text its write waits on, the mark of the difference of its row, or its
 * content — which bears the mark of the base where its value differs from it, and gives it.
 */
function shownContent<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  column: GridColumn<Row, Sort, Totals> | undefined,
  row: Row,
  { pending, marks }: { readonly pending: string | undefined; readonly marks: boolean },
  [locale, currency]: readonly [Locale, string | undefined],
): ReactNode {
  if (pending !== undefined) {
    return pending;
  }
  if (marks) {
    return <DiffMark difference={config.difference?.(row)} />;
  }
  const content = cellContent(config, column, row, locale, currency);
  const base = column?.base?.(row);
  return base === undefined ? content : <BaseMark base={base}>{content}</BaseMark>;
}

/**
 * A cell of a row: the active one in the order of tabulation, the others reached by the arrows;
 * its entry while entered; what was validated while the server has not answered. A cell the
 * server computes in this row is shaded and marked (WF-IHM-0030), and refuses an entry.
 */
function BodyCell<Row extends RowData, Sort extends string, Totals>({
  table,
  config,
  dependencies,
  cells,
  row,
  folds,
  position,
  locale,
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly dependencies: DependencyReader<Row> | undefined;
  readonly cells: CellStates<Row, Sort, Totals>;
  readonly row: Row;
  /** Whether the row folds: its label tells the keys that fold it. */
  readonly folds: boolean;
  readonly position: CellPosition;
  readonly locale: Locale;
}) {
  const currency = useCurrency();
  const column = configColumn(config, position.column);
  const computed = computedIn(column, row);
  const pinning = pinningOf(table, position.column, "z-10");
  const state = cellStateOf(cells, config.rowKey(row), position);
  const marks = position.column === DIFF_MARK_KEY;
  const content = shownContent(config, column, row, { pending: state.pending, marks }, [
    locale,
    currency,
  ]);
  let shown = content;
  if (state.draft !== undefined && column !== undefined) {
    shown = cells.editor(state.draft, column);
  } else if (computed) {
    shown = (
      <ComputedCell
        column={column}
        row={row}
        dependencies={dependencies}
        open={state.refused}
        opening={cells.refusal.opening}
        onClose={cells.closeRefusal}
        onDismiss={cells.dismissRefusal}
      >
        {content}
      </ComputedCell>
    );
  }
  return (
    <TableCell
      {...cellAttributes(
        position,
        state,
        column?.entry?.in(row) === true,
        computed,
        cellKeys(cells.menu, { folds, keys: cells.foldKeys }, position.column, config.columns[0]),
      )}
      style={{ left: pinning.left, right: pinning.right }}
      className={cn(
        "overflow-hidden text-ellipsis outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
        pinning.className,
        computed ? "bg-muted" : ROW_HOVER,
        column === undefined || state.pending !== undefined ? "text-muted-foreground" : null,
        state.draft === undefined ? null : "py-0",
        invalidRing(state.invalid),
        marks ? "text-center" : alignClass(column),
      )}
    >
      {shown}
    </TableCell>
  );
}

/**
 * A row of the answer, its visible cells, at its index among the rows shown — and at its place among
 * the rows the grid renders, which the runs of rows folded away are among too (`folded-runs.tsx`).
 */
export function BodyRow<Row extends RowData, Sort extends string, Totals>({
  row,
  index,
  place,
  ...shared
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  /** How a computed cell asks the server what its value depends on. */
  readonly dependencies: DependencyReader<Row> | undefined;
  readonly cells: CellStates<Row, Sort, Totals>;
  readonly row: TableRowModel<GridFeatures, Row>;
  readonly index: number;
  readonly place: number;
  readonly locale: Locale;
}) {
  // In a tree, where the row stands, and whether it is unfolded.
  const tree = useTreeRow(shared.config.rowKey(row.original));
  const { selection } = shared.cells;
  const { className, ...selected } = selectedRow(
    selection.selected(index),
    selection.dropAt(index),
  );
  return (
    <TableRow
      aria-rowindex={place + 2}
      aria-level={tree?.level}
      aria-posinset={tree?.position}
      aria-setsize={tree?.siblings}
      aria-expanded={tree?.expanded}
      {...selected}
      className={cn(
        BODY_ROW,
        "h-7",
        className,
        differenceTint(shared.config.difference?.(row.original)),
      )}
    >
      {row
        .getVisibleCells()
        .map((cell) =>
          cell.column.id === ROW_NUMBER_KEY && selection.offered ? (
            <HandleCell
              key={cell.id}
              position={{ row: index, column: cell.column.id }}
              state={cellStateOf(shared.cells, row.id, { row: index, column: cell.column.id })}
              menu={shared.cells.menu}
              pinning={pinningOf(shared.table, cell.column.id, "z-10")}
              number={shared.config.rowNumber?.(row.original) ?? index + 1}
              selected={selection.selected(index) === true}
              name={shared.cells.handle.name}
              hint={shared.cells.handle.hint}
              draggable={selection.dragging}
              pick={selection.pick}
            />
          ) : (
            <BodyCell
              key={cell.id}
              {...shared}
              row={row.original}
              folds={tree?.expanded !== undefined}
              position={{ row: index, column: cell.column.id }}
            />
          ),
        )}
    </TableRow>
  );
}
