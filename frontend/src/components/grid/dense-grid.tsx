// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grid (PBS-1.3, EP-02 « Grille dense »): one component, which each screen
 * configures — its columns, its tree, the key of its settings. It shows the rows of an answer
 * of the API in the order the server gave, and the totals the server computed for the same
 * request: a header clicked asks the server for the sort, both ways, by the parameters of the
 * contract, and a search asks it for the rows it retains — nothing is ordered, filtered nor
 * summed here (WF-ARC-0020).
 *
 * Only the rows in view are rendered (TanStack Virtual), and a thousand read as one: the header
 * and the totals stay at the top and at the foot of the grid as it scrolls, the row numbers and
 * the labels at its start as it scrolls sideways (WF-IHM-0060). It is a `grid` whose row count
 * is the whole answer's, each rendered row carrying its index among them, so that a reader
 * knows where it is whatever is rendered.
 *
 * The columns shown and their widths are a display preference of the account (WF-ADM-0040):
 * the grid starts from those the session read, and records each change after a pause.
 */
"use client";

import type { RowData, Row as TableRowModel } from "@tanstack/react-table";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { type ReactNode, useOptimistic, useRef, useState, useTransition } from "react";

import { OutcomeNotice } from "@/components/commands/outcome-notice";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import type { Locale } from "@/i18n/locale";

import { alignment, formatCell, type GridColumn, type GridConfig } from "./columns";
import { ComputedCell, type ComputedColumn } from "./computed-cell";
import { configColumn, type GridFeatures, type GridTable, useGridTable } from "./grid-table";
import { GridToolbar, type ToggledColumn } from "./grid-toolbar";
import { HeaderCell } from "./header-cell";
import { useRootFontSize, useRowWindow } from "./row-window";
import { type GridQuery, type GridSort, searchHref, sortHref } from "./query";
import {
  type GridPreferences,
  initialSettings,
  recordedPreferences,
  useSettingsWriter,
} from "./settings";

/**
 * The height of a row, in `rem` — `h-7`, a dense grid —: in pixels, as many times the size of
 * the root font, so that a font the user enlarges does not shift the rows the grid computes.
 */
export const ROW_REM = 1.75;

/** The rows rendered beyond those in view, at each end. */
const OVERSCAN = 12;

/**
 * The size the grid assumes before it is measured — on the server, and until the browser has
 * laid it out —: the rows of a first screen are in the page as it arrives.
 */
const FIRST_SCREEN = { width: 1280, height: 720 };

/** How far a level of the tree indents its label, in pixels. */
const INDENT = 16;

/** What a grid shows: an answer of the API, what was asked for it, and the settings kept. */
export interface DenseGridProps<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  /** The rows of the answer, in its order. */
  readonly rows: readonly Row[];
  /** The totals of the answer. */
  readonly totals: Totals;
  /** What the totals row says before its figures: what the totals count. */
  readonly totalsCaption: string;
  /** What the address asked of the server. */
  readonly query: GridQuery<Sort>;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** How a cell of a column is pinned: its classes, and its offset from the start. */
interface Pinning {
  readonly className: string;
  readonly left: number | undefined;
}

/** How a column of the table is pinned, at a layer above the cells it slides over. */
function pinningOf<Row extends RowData>(table: GridTable<Row>, id: string, layer: string): Pinning {
  const column = table.getColumn(id);
  if (column?.getIsPinned() !== "start") {
    return { className: "", left: undefined };
  }
  const last = table.getStartVisibleLeafColumns().at(-1)?.id === id;
  return {
    className: cn("sticky", layer, last ? "border-r" : null),
    left: column.getStart("start"),
  };
}

/**
 * The classes that align the content of a column: the row numbers and the figures at the end,
 * an icon alone at the centre.
 */
function alignClass(column: Parameters<typeof alignment>[0] | undefined): string | null {
  const align = column === undefined ? "end" : alignment(column);
  return { start: null, end: "text-right", center: "text-center" }[align];
}

/** The label of a row and its tree: indented by its level, the icon of its nature before it. */
function TreeLabel<Row extends RowData, Sort extends string, Totals>({
  config,
  row,
  text,
}: {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly row: Row;
  readonly text: string;
}) {
  const tree = config.tree;
  if (tree === undefined) {
    return text;
  }
  const emphasis = tree.emphasis?.(row);
  return (
    <span
      className={cn(
        "flex min-w-0 items-center gap-1.5",
        emphasis === "strong" ? "font-semibold" : null,
        emphasis === "muted" ? "text-muted-foreground" : null,
      )}
      style={{ paddingLeft: (tree.level(row) - 1) * INDENT }}
    >
      {tree.nature(row)}
      <span className="truncate">{text}</span>
    </span>
  );
}

/**
 * The content of a cell: the number of the row, the label and its tree, what its column renders,
 * or its value.
 */
function cellContent<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  column: GridColumn<Row, Sort, Totals> | undefined,
  row: Row,
  locale: Locale,
): ReactNode {
  if (column === undefined) {
    return config.rowNumber?.(row);
  }
  if (column.render !== undefined) {
    return column.render(row);
  }
  const text = formatCell(column.format, column.value(row), locale);
  return column === config.columns[0] ? <TreeLabel config={config} row={row} text={text} /> : text;
}

/** Whether the server computes the cell of a column in a row. */
function computedIn<Row extends RowData, Sort extends string, Totals>(
  column: GridColumn<Row, Sort, Totals> | undefined,
  row: Row,
): column is ComputedColumn<Row, Sort, Totals> {
  return column?.computed?.in(row) === true;
}

/**
 * A row of the answer, its visible cells, at its index among all the rows of the answer. A cell
 * the server computes in this row is shaded and marked (WF-IHM-0030), and refuses an entry.
 */
function BodyRow<Row extends RowData, Sort extends string, Totals>({
  table,
  config,
  rows,
  row,
  index,
  locale,
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly rows: readonly Row[];
  readonly row: TableRowModel<GridFeatures, Row>;
  readonly index: number;
  readonly locale: Locale;
}) {
  return (
    <TableRow aria-rowindex={index + 2} className="h-7">
      {row.getVisibleCells().map((cell) => {
        const column = configColumn(config, cell.column.id);
        const computed = computedIn(column, row.original);
        const pinning = pinningOf(table, cell.column.id, "z-10");
        const content = cellContent(config, column, row.original, locale);
        return (
          <TableCell
            key={cell.id}
            style={{ left: pinning.left }}
            className={cn(
              "overflow-hidden text-ellipsis",
              pinning.className,
              computed ? "bg-muted" : "bg-background",
              column === undefined ? "text-muted-foreground" : null,
              alignClass(column),
            )}
          >
            {computed ? (
              <ComputedCell config={config} column={column} rows={rows} index={index}>
                {content}
              </ComputedCell>
            ) : (
              content
            )}
          </TableCell>
        );
      })}
    </TableRow>
  );
}

/** The totals of the answer, at the foot: what they count under the label, figures under theirs. */
function TotalsRow<Row extends RowData, Sort extends string, Totals>({
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
  return (
    <TableRow aria-rowindex={index} className="h-8">
      {table.getVisibleLeafColumns().map((column) => {
        const configured = configColumn(config, column.id);
        const pinning = pinningOf(table, column.id, "z-30");
        const first = configured !== undefined && configured === config.columns[0];
        return (
          <TableCell
            key={column.id}
            style={{ left: pinning.left }}
            className={cn(
              "sticky bottom-0 z-20 overflow-hidden border-t border-b-0 bg-muted font-semibold text-ellipsis",
              pinning.className,
              first ? null : alignClass(configured),
            )}
          >
            {first
              ? caption
              : formatCell(configured?.format ?? "text", configured?.total?.(totals), locale)}
          </TableCell>
        );
      })}
    </TableRow>
  );
}

/** A spacer for the rows not rendered, before or after those in view. */
function Spacer({ height, span }: { readonly height: number; readonly span: number }) {
  return height > 0 ? (
    <tr aria-hidden="true">
      <td colSpan={span} style={{ height }} className="p-0" />
    </tr>
  ) : null;
}

/** The columns the user may show or hide, for the bar of the grid. */
function toggledColumns<Row extends RowData, Sort extends string, Totals>(
  table: GridTable<Row>,
  config: GridConfig<Row, Sort, Totals>,
  label: (column: GridColumn<Row, Sort, Totals>) => string,
): ToggledColumn[] {
  return table.getAllLeafColumns().flatMap((column) => {
    const configured = configColumn(config, column.id);
    return configured === undefined || !column.getCanHide()
      ? []
      : [
          {
            key: column.id,
            label: label(configured),
            visible: column.getIsVisible(),
            toggle: (visible: boolean) => {
              column.toggleVisibility(visible);
            },
          },
        ];
  });
}

/** Render a dense grid. */
export function DenseGrid<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  totals,
  totalsCaption,
  query,
  preferences,
}: DenseGridProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const address = useSearchParams();
  const [pending, startTransition] = useTransition();
  // The sort asked, shown until the server answers: a second click on the header, before the
  // answer to the first, goes on from it — ascending, then descending.
  const [sort, showSort] = useOptimistic(query.sort);
  // The sort the account keeps for the grid: the session's, then the last one a header asked.
  // Only a header writes it; a column shown or widened sends it back as it is.
  const keptSort = useRef(preferences?.sort);
  const [settings, setSettings] = useState(() => initialSettings(preferences, config.columns));
  const writer = useSettingsWriter(config.key);
  const scroller = useRef<HTMLDivElement>(null);
  const rowHeight = ROW_REM * useRootFontSize();

  // The address the last navigation of the grid asked for, and the address it was asked from.
  // Until it arrives, the address of the screen is still the one before, and Next drops a
  // navigation under way for the next one: a search entered right after a sort, before the
  // server answered, must carry the sort too. Forgotten once the address of the screen changes.
  const asked = useRef<{ readonly from: string; readonly query: string }>(undefined);
  /** Navigate to an address built from the last one asked, or from that of the screen. */
  const request = (build: (query: URLSearchParams) => string) => {
    const from = address.toString();
    const base = asked.current?.from === from ? asked.current.query : from;
    const href = build(new URLSearchParams(base));
    asked.current = { from, query: href.split("?")[1] ?? "" };
    router.push(href, { scroll: false });
  };
  // A sort or a search changes the address only: the server reads it, and answers anew. A sort
  // navigates at once, and its preference is written alongside: the address carries it — a
  // sort lifted included —, so the page never waits for the preference, nor reads it for it.
  const changeSort = (next: GridSort<Sort> | undefined) => {
    startTransition(() => {
      showSort(next);
      request((query) => sortHref(pathname, query, next));
    });
    keptSort.current = next === undefined ? null : { column: next.column, order: next.order };
    writer.recordNow(recordedPreferences(preferences, settings, keptSort.current));
  };
  const search = (text: string) => {
    writer.flush();
    startTransition(() => {
      request((query) => searchHref(pathname, query, text));
    });
  };
  const table = useGridTable({
    config,
    rows,
    sort,
    onSort: changeSort,
    settings,
    onSettings: (next) => {
      setSettings(next);
      writer.record(recordedPreferences(preferences, next, keptSort.current));
    },
  });

  const model = table.getRowModel().rows;
  const { items, before, after } = useRowWindow({
    rows: model,
    scroller,
    rowHeight,
    overscan: OVERSCAN,
    initialRect: FIRST_SCREEN,
    keyOf: (index) => model[index]?.id ?? index,
  });
  const columns = table.getVisibleLeafColumns();
  // An empty answer still has a row, which says so, between the header and the totals.
  const bodyRows = Math.max(model.length, 1);

  return (
    <div className="flex min-h-0 flex-col gap-2">
      <GridToolbar
        search={query.search}
        onSearch={search}
        columns={toggledColumns(table, config, (column) => t(`columns.${column.label}`))}
      />
      <OutcomeNotice outcome={writer.outcome} onClear={writer.clear} />
      <Table
        role="grid"
        aria-label={t(`names.${config.name}`)}
        aria-rowcount={bodyRows + 2}
        aria-colcount={columns.length}
        aria-busy={pending}
        // The grid takes the height its screen leaves it (`Screen`, `fill`), shrinking from that
        // of its rows down to a floor; never taller than the window, so that the rows in view
        // stay a window's worth whatever holds it.
        container={{
          ref: scroller,
          className: "w-fit max-w-full max-h-svh min-h-40 rounded-md border",
        }}
        className="table-fixed text-xs tabular-nums"
        style={{ width: table.getTotalSize() }}
      >
        <colgroup>
          {columns.map((column) => (
            <col key={column.id} style={{ width: column.getSize() }} />
          ))}
        </colgroup>
        <TableHeader>
          <TableRow aria-rowindex={1}>
            {table.getHeaderGroups()[0]?.headers.map((header) => {
              const pinning = pinningOf(table, header.column.id, "z-30");
              return (
                <HeaderCell
                  key={header.id}
                  table={table}
                  header={header}
                  column={configColumn(config, header.column.id)}
                  pinning={{ ...pinning, className: cn("sticky top-0 z-20", pinning.className) }}
                />
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          <Spacer height={before} span={columns.length} />
          {items.map((item) => {
            const row = model[item.index];
            return row === undefined ? null : (
              <BodyRow
                key={row.id}
                table={table}
                config={config}
                rows={rows}
                row={row}
                index={item.index}
                locale={locale}
              />
            );
          })}
          <Spacer height={after} span={columns.length} />
          {model.length === 0 ? (
            <TableRow aria-rowindex={2} className="h-7">
              <TableCell colSpan={columns.length} className="text-muted-foreground">
                {t("empty")}
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
        <TableFooter>
          <TotalsRow
            table={table}
            config={config}
            totals={totals}
            caption={totalsCaption}
            index={bodyRows + 2}
            locale={locale}
          />
        </TableFooter>
      </Table>
    </div>
  );
}
