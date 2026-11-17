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
 *
 * Compared to a base (`ComparedTotals`, WF-IHM-0160), each total says three lines: the one of the
 * revision read, that of the base and their difference, all given by the server — the grid sums and
 * subtracts nothing (WF-ARC-0020) —, and the row is marked modified when they differ, not when they
 * are equal.
 */
"use client";

import { useTranslations } from "next-intl";
import type { Column, RowData } from "@tanstack/react-table";
import type { ReactNode } from "react";

import { TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import { useCurrency } from "@/currency/context";
import type { Locale } from "@/i18n/locale";

import { alignment, DIFF_MARK_KEY, formatCell, type GridConfig } from "./columns";
import { DiffMark, differenceTint } from "./diff-mark";
import { configColumn, type GridFeatures, type GridTable } from "./grid-table";
import { type Pinning, pinningOf } from "./pinning";
import { isZero, signed } from "./signed";

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
  readonly caption: ReactNode;
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

/** The totals of a comparison, as the server gives them, and what says them in words. */
export interface ComparedTotals<Totals> {
  /** The totals of the base, on the rows the reading retains. */
  readonly base: Totals;
  /** The difference of the totals of the revision read and of the base, signed. */
  readonly delta: Totals;
  /** What the totals row says of totals, before its figures. */
  readonly caption: (totals: Totals) => string;
}

/** A line of a total: the one of the base or of the difference, named for a screen reader if need be. */
function Line({ label, children }: { readonly label?: string; readonly children: ReactNode }) {
  return (
    <span className="block font-normal text-muted-foreground">
      {label === undefined ? null : <span className="sr-only">{label}</span>}
      {children}
    </span>
  );
}

/** The figure of a total of the answer, and under it, compared, those of the base and the gap. */
function Figure<Totals>({
  format,
  total,
  totals,
  compared,
  locale,
}: {
  readonly format: Parameters<typeof formatCell>[0];
  readonly total: ((totals: Totals) => Parameters<typeof formatCell>[1]) | undefined;
  readonly totals: Totals;
  readonly compared: ComparedTotals<Totals> | undefined;
  readonly locale: Locale;
}) {
  const t = useTranslations("grid.compared");
  const currency = useCurrency();
  const shown = (of: Totals) => formatCell(format, total?.(of), locale, currency);
  if (compared === undefined || total === undefined) {
    return shown(totals);
  }
  const gap = total(compared.delta);
  return (
    <>
      <span className="block">{shown(totals)}</span>
      <Line label={t("base")}>{shown(compared.base)}</Line>
      <Line label={t("delta")}>
        {gap === null || gap === undefined ? "" : signed(gap, shown(compared.delta))}
      </Line>
    </>
  );
}

/**
 * Whether the totals of a comparison differ: a figure of a column, or what the caption counts. Every
 * column of the configuration is judged, those hidden by the reader included.
 */
function differ<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  totals: Totals,
  compared: ComparedTotals<Totals>,
): boolean {
  return (
    compared.caption(totals) !== compared.caption(compared.base) ||
    config.columns.some((column) => {
      const gap = column.total?.(compared.delta);
      return gap !== null && gap !== undefined && !isZero(gap);
    })
  );
}

/** The totals of the answer, at the foot: what they count under the label, figures under theirs. */
export function TotalsRow<Row extends RowData, Sort extends string, Totals>({
  table,
  config,
  totals,
  caption,
  compared,
  index,
  locale,
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly totals: Totals;
  readonly caption: string;
  /** The totals of the base and their difference, when the grid reads a comparison. */
  readonly compared?: ComparedTotals<Totals> | undefined;
  readonly index: number;
  readonly locale: Locale;
}) {
  const t = useTranslations("grid.compared");
  const columns = table.getVisibleLeafColumns();
  const at = columns.findIndex((column) => column.id === config.columns[0]?.key);
  const spanned = at < 0 ? [] : columns.slice(at, at + captionSpan(columns, at, config));
  const modified = compared !== undefined && differ(config, totals, compared);
  const words =
    compared === undefined ? (
      caption
    ) : (
      <>
        <span className="block">{caption}</span>
        <Line>{t("totalsBase", { caption: compared.caption(compared.base) })}</Line>
        <Line>{t("totalsDelta", { caption: compared.caption(compared.delta) })}</Line>
      </>
    );
  return (
    <TableRow
      aria-rowindex={index}
      data-difference={modified ? "modified" : undefined}
      className={cn(
        "h-8",
        compared !== undefined && "align-top",
        modified && differenceTint("modified"),
      )}
    >
      {columns.map((column, position) => {
        if (position === at) {
          return <CaptionCell key={column.id} table={table} spanned={spanned} caption={words} />;
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
            {column.id === DIFF_MARK_KEY ? (
              <DiffMark difference={modified ? "modified" : undefined} />
            ) : (
              <Figure
                format={configured?.format ?? "text"}
                total={configured?.total}
                totals={totals}
                compared={compared}
                locale={locale}
              />
            )}
          </TableCell>
        );
      })}
    </TableRow>
  );
}
