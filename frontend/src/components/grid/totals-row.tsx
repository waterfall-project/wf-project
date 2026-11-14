// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The totals row at the foot of a dense grid, and the alignment of a column's content, which the
 * cells and the totals share.
 *
 * What the totals count — « 150 catégories » — is said in the first column of the configuration,
 * often a narrow code: it spans the columns after it that have no figure, up to the first that has
 * one, rather than being cut (US-2080, #3072). Pinned at the start, it stays where it is as the grid
 * scrolls sideways, but over the pinned columns alone: its offset is less the columns it spans that
 * are not pinned, so that it never covers a figure scrolled under it, and its words stick to the
 * start of its first column. All of it is CSS, from the widths the table holds.
 */
"use client";

import type { Column, RowData } from "@tanstack/react-table";

import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import { useCurrency } from "@/currency/context";
import type { Locale } from "@/i18n/locale";

import { alignment, formatCell, type GridConfig } from "./columns";
import { configColumn, type GridFeatures, type GridTable } from "./grid-table";
import { type Pinning, pinningOf } from "./pinning";

/**
 * The classes that align the content of a column: the row numbers and the figures at the end,
 * an icon alone at the centre.
 */
export function alignClass(column: Parameters<typeof alignment>[0] | undefined): string | null {
  const align = column === undefined ? "end" : alignment(column);
  return { start: null, end: "text-right", center: "text-center" }[align];
}

/** A column of the table of a grid. */
type TableColumn<Row extends RowData> = Column<GridFeatures, Row>;

/** The classes of every cell of the totals, stuck to the foot of the grid. */
const TOTAL_CELL = "sticky bottom-0 z-20 border-t border-b-0 bg-muted font-semibold";

/**
 * How many columns the caption of the totals spans from the one at `at`: its own, then each one
 * shown after it with no total, up to the first with one or to the column pinned at the end.
 */
export function captionSpan<Row extends RowData, Sort extends string, Totals>(
  columns: readonly TableColumn<Row>[],
  at: number,
  config: GridConfig<Row, Sort, Totals>,
): number {
  let span = 1;
  for (const column of columns.slice(at + 1)) {
    if (column.getIsPinned() === "end" || configColumn(config, column.id)?.total !== undefined) {
      break;
    }
    span += 1;
  }
  return span;
}

/**
 * How the caption spanning `spanned` is pinned: as its first column is, its offset less the width
 * of the columns it spans that are not pinned at the start, so that, stuck, it ends where the
 * pinned columns end; the line beside the last pinned column drawn only where its edge is that
 * column's. And the offset of its words, which stick to the start of its first column — none when
 * it spans no column that scrolls, or is not pinned.
 */
export function captionPinning<Row extends RowData>(
  table: GridTable<Row>,
  spanned: readonly TableColumn<Row>[],
): { readonly pinning: Pinning; readonly words: number | undefined } {
  const [first] = spanned;
  const last = spanned.at(-1);
  if (first === undefined || last === undefined || first.getIsPinned() !== "start") {
    return { pinning: { className: "", left: undefined, right: undefined }, words: undefined };
  }
  const scrolled = spanned
    .filter((column) => column.getIsPinned() !== "start")
    .reduce((width, column) => width + column.getSize(), 0);
  const start = first.getStart("start");
  if (scrolled === 0) {
    const { className } = pinningOf(table, last.id, "z-30");
    return { pinning: { className, left: start, right: undefined }, words: undefined };
  }
  return {
    pinning: { className: "sticky z-30", left: start - scrolled, right: undefined },
    words: start,
  };
}

/** The cell of the caption of the totals, over the columns it spans. */
function CaptionCell<Row extends RowData>({
  table,
  spanned,
  caption,
}: {
  readonly table: GridTable<Row>;
  readonly spanned: readonly TableColumn<Row>[];
  readonly caption: string;
}) {
  const { pinning, words } = captionPinning(table, spanned);
  return (
    <TableCell
      colSpan={spanned.length}
      style={{ left: pinning.left }}
      className={cn(
        TOTAL_CELL,
        // A box that clips without scrolling, so that its words stick to the frame of the grid.
        words === undefined ? "overflow-hidden text-ellipsis" : "overflow-clip px-0",
        pinning.className,
      )}
    >
      {words === undefined ? (
        caption
      ) : (
        // A sticky box stays within its cell, which would push words wider than what is left of the
        // cell back to the left, out of the frame; a margin that takes the whole width of the window
        // off its end leaves it where it sticks, the cell cutting the words at its own edge.
        <span className="sticky -mr-[100vw] block w-fit px-2" style={{ left: words }}>
          {caption}
        </span>
      )}
    </TableCell>
  );
}

/** The totals of the answer, at the foot: what they count under the label, figures under theirs. */
export function TotalsRow<Row extends RowData, Sort extends string, Totals>({
  table,
  config,
  totals,
  caption,
  index,
  locale,
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly totals: Totals;
  readonly caption: string;
  readonly index: number;
  readonly locale: Locale;
}) {
  const currency = useCurrency();
  const columns = table.getVisibleLeafColumns();
  const at = columns.findIndex((column) => column.id === config.columns[0]?.key);
  const spanned = at < 0 ? [] : columns.slice(at, at + captionSpan(columns, at, config));
  return (
    <TableRow aria-rowindex={index} className="h-8">
      {columns.map((column, position) => {
        if (position === at) {
          return <CaptionCell key={column.id} table={table} spanned={spanned} caption={caption} />;
        }
        if (at >= 0 && position > at && position < at + spanned.length) {
          return null;
        }
        const configured = configColumn(config, column.id);
        const pinning = pinningOf(table, column.id, "z-30");
        return (
          <TableCell
            key={column.id}
            style={{ left: pinning.left, right: pinning.right }}
            className={cn(
              TOTAL_CELL,
              "overflow-hidden text-ellipsis",
              pinning.className,
              alignClass(configured),
            )}
          >
            {formatCell(
              configured?.format ?? "text",
              configured?.total?.(totals),
              locale,
              currency,
            )}
          </TableCell>
        );
      })}
    </TableRow>
  );
}
