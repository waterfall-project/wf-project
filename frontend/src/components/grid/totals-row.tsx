// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The totals row at the foot of a dense grid, and the alignment of a column's content, which the
 * cells and the totals share.
 */
"use client";

import type { RowData } from "@tanstack/react-table";

import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import { useCurrency } from "@/currency/context";
import type { Locale } from "@/i18n/locale";

import { alignment, formatCell, type GridConfig } from "./columns";
import { configColumn, type GridTable } from "./grid-table";
import { pinningOf } from "./pinning";

/**
 * The classes that align the content of a column: the row numbers and the figures at the end,
 * an icon alone at the centre.
 */
export function alignClass(column: Parameters<typeof alignment>[0] | undefined): string | null {
  const align = column === undefined ? "end" : alignment(column);
  return { start: null, end: "text-right", center: "text-center" }[align];
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
  return (
    <TableRow aria-rowindex={index} className="h-8">
      {table.getVisibleLeafColumns().map((column) => {
        const configured = configColumn(config, column.id);
        const pinning = pinningOf(table, column.id, "z-30");
        const first = configured !== undefined && configured === config.columns[0];
        return (
          <TableCell
            key={column.id}
            style={{ left: pinning.left, right: pinning.right }}
            className={cn(
              "sticky bottom-0 z-20 overflow-hidden border-t border-b-0 bg-muted font-semibold text-ellipsis",
              pinning.className,
              first ? null : alignClass(configured),
            )}
          >
            {first
              ? caption
              : formatCell(
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
