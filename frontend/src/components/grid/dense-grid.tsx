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
 *
 * It is entered from the keyboard alone (WF-IHM-0040, `useGridKeyboard`): one cell is active, the
 * one stop of the grid in the order of tabulation, which the arrows move — the header among the
 * rows —, and a computed cell tried opens its refusal; a cell validated is written alone,
 * and what the server answers takes the place of what was read — the row, the rows the write changed
 * with it, the totals (`useCellWrites`). A block pasted
 * from a spreadsheet on the active cell is shown as the server would write and refuse it, and
 * written once confirmed, in one operation (WF-IHM-0050, `useGridPaste`).
 */
"use client";

import type { RowData, Row as TableRowModel } from "@tanstack/react-table";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Fragment,
  type ReactNode,
  useEffect,
  useId,
  useOptimistic,
  useRef,
  useState,
  useTransition,
} from "react";

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

import {
  alignment,
  type DependencyReader,
  type EntryKind,
  formatCell,
  type GridColumn,
  type GridConfig,
} from "./columns";
import { CellEditor } from "./cell-editor";
import type { EntryProblem } from "./cell-values";
import { useCellWrites } from "./cell-writes";
import { ComputedCell, type ComputedColumn } from "./computed-cell";
import {
  type CellDraft,
  type CellPosition,
  type CellRefusal,
  HEADER_ROW,
  refusedAt,
  samePosition,
  useCursor,
  useGridKeyboard,
} from "./grid-keyboard";
import { configColumn, type GridFeatures, type GridTable, useGridTable } from "./grid-table";
import { GridToolbar, type ToggledColumn } from "./grid-toolbar";
import { HeaderCell } from "./header-cell";
import { useGridPaste } from "./paste";
import { PasteDialog } from "./paste-dialog";
import { usePendingAddress } from "./pending-address";
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

/**
 * The height of the header and of the totals, in `rem` — `h-8` —: the rows brought into view come
 * out from under them.
 */
const EDGE_REM = 2;

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
  /** What the totals row says before its figures: what the totals shown count. */
  readonly totalsCaption: (totals: Totals) => string;
  /** What the address asked of the server. */
  readonly query: GridQuery<Sort>;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
  /**
   * How to ask the server what the value of a computed cell depends on, once an entry is tried
   * on it (WF-IHM-0030); none, and the refusal says only that the value is computed.
   */
  readonly dependencies?: DependencyReader<Row> | undefined;
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

/** What the cells of the body are doing: the active one, the one entered, the refusal shown. */
interface CellStates<Row extends RowData, Sort extends string, Totals> {
  readonly cursor: CellPosition;
  readonly draft: CellDraft | undefined;
  readonly refusal: CellRefusal;
  /** What a cell under way shows, by the key of its row and its column, if it is. */
  readonly pending: (row: string, column: string) => string | undefined;
  /** The entry of the cell entered. */
  readonly editor: (draft: CellDraft, column: GridColumn<Row, Sort, Totals>) => ReactNode;
  /** Close the refusal from the keyboard, the focus back on its cell. */
  readonly closeRefusal: () => void;
  /** Close the refusal, the focus gone elsewhere. */
  readonly dismissRefusal: () => void;
}

/** What a cell of the body is doing: active, entered, written, its refusal shown. */
interface CellState {
  readonly active: boolean;
  readonly draft: CellDraft | undefined;
  /** What it shows while the server has not answered its write. */
  readonly pending: string | undefined;
  readonly refused: boolean;
}

/** The attributes of a cell of the body: its place in the grid, and what it says of itself. */
function cellAttributes(
  position: CellPosition,
  state: CellState,
  enterable: boolean,
  computed: boolean,
) {
  return {
    "data-row": position.row,
    "data-column": position.column,
    tabIndex: state.active ? 0 : -1,
    "aria-readonly": enterable ? undefined : true,
    "aria-busy": state.pending === undefined ? undefined : true,
    "aria-haspopup": computed ? ("dialog" as const) : undefined,
    "aria-expanded": computed ? state.refused : undefined,
  };
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
  position,
  locale,
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly dependencies: DependencyReader<Row> | undefined;
  readonly cells: CellStates<Row, Sort, Totals>;
  readonly row: Row;
  readonly position: CellPosition;
  readonly locale: Locale;
}) {
  const column = configColumn(config, position.column);
  const computed = computedIn(column, row);
  const pinning = pinningOf(table, position.column, "z-10");
  const key = config.rowKey(row);
  const state: CellState = {
    active: samePosition(cells.cursor, position),
    draft:
      cells.draft?.key === key && cells.draft.column === position.column ? cells.draft : undefined,
    pending: cells.pending(key, position.column),
    refused: refusedAt(cells.refusal, key, position.column),
  };
  const content = state.pending ?? cellContent(config, column, row, locale);
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
      {...cellAttributes(position, state, column?.entry?.in(row) === true, computed)}
      style={{ left: pinning.left }}
      className={cn(
        "overflow-hidden text-ellipsis outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
        pinning.className,
        computed ? "bg-muted" : "bg-background",
        column === undefined || state.pending !== undefined ? "text-muted-foreground" : null,
        state.draft === undefined ? null : "py-0",
        alignClass(column),
      )}
    >
      {shown}
    </TableCell>
  );
}

/** A row of the answer, its visible cells, at its index among all the rows of the answer. */
function BodyRow<Row extends RowData, Sort extends string, Totals>({
  row,
  index,
  ...shared
}: {
  readonly table: GridTable<Row>;
  readonly config: GridConfig<Row, Sort, Totals>;
  /** How a computed cell asks the server what its value depends on. */
  readonly dependencies: DependencyReader<Row> | undefined;
  readonly cells: CellStates<Row, Sort, Totals>;
  readonly row: TableRowModel<GridFeatures, Row>;
  readonly index: number;
  readonly locale: Locale;
}) {
  return (
    <TableRow aria-rowindex={index + 2} className="h-7">
      {row.getVisibleCells().map((cell) => (
        <BodyCell
          key={cell.id}
          {...shared}
          row={row.original}
          position={{ row: index, column: cell.column.id }}
        />
      ))}
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

/** The width of the columns pinned at the start, which the other columns slide under. */
function pinnedWidth<Row extends RowData>(table: GridTable<Row>): number {
  return table.getStartVisibleLeafColumns().reduce((width, column) => width + column.getSize(), 0);
}

/**
 * Why the entry of a cell was not validated, which its field names as its description: a cell
 * left blank that may not be, a text too long, no number of the language — with an example of
 * one —, an amount with more than two decimals.
 */
function EntryProblemNotice({
  id,
  draft,
  kind,
}: {
  readonly id: string;
  readonly draft: CellDraft | undefined;
  readonly kind: EntryKind | undefined;
}) {
  const t = useTranslations("grid.entry");
  const locale = useLocale();
  const problem = draft?.problem;
  if (problem === undefined || kind === undefined) {
    return null;
  }
  const amount = formatCell("money", "1234.56", locale);
  const texts: Readonly<Record<EntryProblem, () => string>> = {
    required: () => t("required"),
    tooLong: () => t("tooLong", { max: kind.type === "text" ? kind.maxLength : 0 }),
    notANumber: () =>
      t("notANumber", {
        example: kind.type === "money" ? amount : formatCell("decimal", "1234.5", locale),
      }),
    twoDecimals: () => t("twoDecimals", { example: amount }),
  };
  return (
    <p id={id} role="alert" className="text-sm text-destructive">
      {texts[problem]()}
    </p>
  );
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
  dependencies,
}: DenseGridProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  const locale = useLocale();
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();
  // The sort asked, shown until the server answers: a second click on the header, before the
  // answer to the first, goes on from it — ascending, then descending.
  const [sort, showSort] = useOptimistic(query.sort);
  // The sort the account keeps for the grid: the session's, then the last one a header asked.
  // Only a header writes it; a column shown or widened sends it back as it is.
  const keptSort = useRef(preferences?.sort);
  const [settings, setSettings] = useState(() => initialSettings(preferences, config.columns));
  // The settings as they are now, which a preference written later reads: kept at each change.
  const currentSettings = useRef(settings);
  const writer = useSettingsWriter(config.key);
  const scroller = useRef<HTMLDivElement>(null);
  const rowHeight = ROW_REM * useRootFontSize();

  // The address the last navigation of the grid — or of its screen — asked for: a search entered
  // right after a sort, before the server answered, must carry the sort too (`pending-address.tsx`).
  const { request } = usePendingAddress();
  // The preference of the last sort asked is written once the page shows what the address asked,
  // with the settings of then — a width changed meanwhile included: Next carries a server action
  // in the state of its router, so that a navigation is not shown before the actions dispatched
  // after it have answered — writing the preference at the click would hold the sort back by a
  // round trip to the API, and by every action queued before it. Left, hidden or gone before,
  // the page writes it as it writes what waits.
  const { shown } = writer;
  useEffect(() => {
    shown();
  }, [query, shown]);
  // A sort or a search changes the address only: the server reads it, and answers anew. A sort
  // navigates at once, and its preference is written once it is shown: the address carries it —
  // a sort lifted included —, so the page never waits for the preference, nor reads it for it.
  const changeSort = (next: GridSort<Sort> | undefined) => {
    startTransition(() => {
      showSort(next);
      request((query) => sortHref(pathname, query, next));
    });
    keptSort.current = next === undefined ? null : { column: next.column, order: next.order };
    writer.recordShown(() =>
      recordedPreferences(preferences, currentSettings.current, keptSort.current),
    );
  };
  const search = (text: string) => {
    writer.flush();
    startTransition(() => {
      request((query) => searchHref(pathname, query, text));
    });
  };
  // The rows as the cells written left them: each row the server answered in place of the one read.
  const writes = useCellWrites<Row, Totals>(rows, config.rowKey, config.retotal);
  // The totals the writes last answered, or those of the answer.
  const shownTotals = writes.totals ?? totals;
  const table = useGridTable({
    config,
    rows: writes.rows,
    sort,
    onSort: changeSort,
    settings,
    onSettings: (next) => {
      setSettings(next);
      currentSettings.current = next;
      writer.record(recordedPreferences(preferences, next, keptSort.current));
    },
  });

  const model = table.getRowModel().rows;
  const edge = EDGE_REM * useRootFontSize();
  const columns = table.getVisibleLeafColumns();
  const cursor = useCursor(config, model.length, columns);
  // The row of the active cell stays rendered however far the grid scrolls: it holds the focus.
  const { items, gaps, after, scrollToIndex } = useRowWindow({
    rows: model,
    scroller,
    rowHeight,
    edges: { start: edge, end: edge },
    overscan: OVERSCAN,
    initialRect: FIRST_SCREEN,
    keyOf: (index) => model[index]?.id ?? index,
    kept: cursor.active.row === HEADER_ROW ? undefined : cursor.active.row,
  });
  const shownColumns = columns.map((column) => column.id);
  const keyboard = useGridKeyboard({
    config,
    cursor,
    rows: writes.rows,
    columns: shownColumns,
    scroller,
    scrollToIndex,
    page: () =>
      Math.max(1, Math.floor(((scroller.current?.offsetHeight ?? 0) - 2 * edge) / rowHeight)),
    inView: (index) => {
      const element = scroller.current;
      const top = edge + index * rowHeight - (element?.scrollTop ?? 0);
      return top + rowHeight > edge && top < (element?.offsetHeight ?? 0) - edge;
    },
    writes,
    locale,
  });
  const paste = useGridPaste({
    config,
    rows: writes.rows,
    columns: shownColumns,
    writes,
    scroller,
  });
  const invalid = useId();
  const cells: CellStates<Row, Sort, Totals> = {
    cursor: cursor.active,
    draft: keyboard.draft,
    refusal: keyboard.refusal,
    pending: writes.pending,
    closeRefusal: keyboard.closeRefusal,
    dismissRefusal: keyboard.dismissRefusal,
    editor: (draft, column) =>
      column.entry === undefined ? null : (
        <CellEditor
          kind={column.entry.kind}
          label={t(`columns.${column.label}`)}
          text={draft.text}
          typed={draft.typed}
          invalid={draft.problem === undefined ? undefined : invalid}
          onValidate={keyboard.validate}
          onAbandon={keyboard.abandon}
        />
      ),
  };
  // An empty answer still has a row, which says so, between the header and the totals.
  const bodyRows = Math.max(model.length, 1);

  return (
    <div className="flex min-h-0 flex-col gap-2">
      <GridToolbar
        search={query.search}
        onSearch={config.searched === false ? undefined : search}
        columns={toggledColumns(table, config, (column) => t(`columns.${column.label}`))}
      />
      <OutcomeNotice
        outcome={writer.outcome}
        onClear={writer.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      <OutcomeNotice
        outcome={writes.outcome}
        onClear={writes.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      <OutcomeNotice
        outcome={paste.outcome}
        onClear={paste.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      {paste.hidden === undefined ? null : (
        <p role="alert" className="text-sm text-destructive">
          {paste.hidden.shown === "hidden"
            ? t("paste.hiddenColumn", { column: t(`columns.${paste.hidden.label}`) })
            : t("paste.absentColumn", { column: paste.hidden.name })}
        </p>
      )}
      {paste.pasting === undefined ? null : (
        <PasteDialog
          pasting={paste.pasting}
          onApply={paste.apply}
          onAbandon={paste.abandon}
          onClosed={paste.refocus}
        />
      )}
      <EntryProblemNotice
        id={invalid}
        draft={keyboard.draft}
        kind={configColumn(config, keyboard.draft?.column ?? "")?.entry?.kind}
      />
      <Table
        role="grid"
        aria-label={t(`names.${config.name}`)}
        aria-rowcount={bodyRows + 2}
        aria-colcount={columns.length}
        aria-busy={pending}
        // The grid takes the height its screen leaves it (`Screen`, `fill`), shrinking from that
        // of its rows down to a floor; never taller than the window, so that the rows in view
        // stay a window's worth whatever holds it. The header and the totals stick to its edges,
        // the pinned columns to its start: a cell the focus brings into view comes out from under
        // them. A refusal whose row scrolls out of view closes.
        container={{
          ref: scroller,
          className: "w-fit max-w-full max-h-svh min-h-40 rounded-md border",
          style: { scrollPaddingBlock: edge, scrollPaddingInlineStart: pinnedWidth(table) },
          onScroll: keyboard.followScroll,
        }}
        className="table-fixed text-xs tabular-nums"
        style={{ width: table.getTotalSize() }}
      >
        <colgroup>
          {columns.map((column) => (
            <col key={column.id} style={{ width: column.getSize() }} />
          ))}
        </colgroup>
        <TableHeader {...keyboard.header}>
          <TableRow aria-rowindex={1}>
            {table.getHeaderGroups()[0]?.headers.map((header) => {
              const pinning = pinningOf(table, header.column.id, "z-30");
              const position = { row: HEADER_ROW, column: header.column.id };
              return (
                <HeaderCell
                  key={header.id}
                  table={table}
                  header={header}
                  column={configColumn(config, header.column.id)}
                  pinning={{ ...pinning, className: cn("sticky top-0 z-20", pinning.className) }}
                  position={position}
                  active={samePosition(cursor.active, position)}
                />
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody {...keyboard.body}>
          {items.map((item, position) => {
            const row = model[item.index];
            return row === undefined ? null : (
              <Fragment key={row.id}>
                <Spacer height={gaps[position] ?? 0} span={columns.length} />
                <BodyRow
                  table={table}
                  config={config}
                  dependencies={dependencies}
                  cells={cells}
                  row={row}
                  index={item.index}
                  locale={locale}
                />
              </Fragment>
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
            totals={shownTotals}
            caption={totalsCaption(shownTotals)}
            index={bodyRows + 2}
            locale={locale}
          />
        </TableFooter>
      </Table>
    </div>
  );
}
