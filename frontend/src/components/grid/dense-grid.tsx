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
 * with it, the totals (`useCellWrites`), a refusal told above the grid, its cell marked (EP-14/L44d). A block pasted from a spreadsheet on the active cell is
 * shown as the server would write and refuse it, and its valid rows written once confirmed, in one
 * operation, what was not written told (WF-IHM-0050, `useGridPaste`). A grid that enters a
 * revision in progress places undo and redo, not wired yet (WF-IHM-0110, `UndoCommands`). A screen
 * may give its rows commands, in the bar on the row of the active cell and in the menu of a cell on
 * its row (`RowCommands`): the work breakdown edited in its grid (EP-14/L44c) — on the selection of
 * rows its handles make, which they drag, where the screen drags rows (`useRowSelection`, US-0460).
 *
 * A grid whose rows name their parents is a tree, which folds and unfolds (WF-PLA-0080,
 * `useGridFold`): a `treegrid`, each row telling its level, its place among its siblings and
 * whether it is unfolded; a row folded takes the rows under it out of the grid — out of those it
 * renders, numbers and moves through —, and the Gantt, a column of the grid, folds with it
 * (WF-PLA-0090). The button in a label folds its row; Alt and minus and Alt and plus fold and
 * unfold the row of the active cell — the row above it, from a row under which nothing folds —, Alt
 * and * unfolds the whole tree, Shift or not, as in Microsoft Project; the bar folds the tree down to a
 * level. The active cell stays on its row, or goes to the row folded over it.
 */
"use client";

import type { RowData, Row as TableRowModel } from "@tanstack/react-table";
import { usePathname, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Fragment,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useOptimistic,
  useRef,
  useState,
  useTransition,
} from "react";

import { OutcomeNotice, refusalDescription } from "@/components/commands/outcome-notice";
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
  DIFF_MARK_KEY,
  formatCell,
  type GridColumn,
  type GridConfig,
  type GridName,
  headingOf,
  ROW_NUMBER_KEY,
} from "./columns";
import { cellAttributes, cellKeys, cellStateOf, invalidRing } from "./cell-attributes";
import { CellEditor, EntryProblemNotice } from "./cell-editor";
import { useCellWrites } from "./cell-writes";
import { ComputedCell, type ComputedColumn } from "./computed-cell";
import { DiffMark, differenceTint } from "./diff-mark";
import {
  FOLD_KEYS,
  useFoldReach,
  FoldContext,
  FoldToggle,
  isNarrowed,
  useFoldCommands,
  useGridFold,
  useTreeRow,
} from "./fold";
import { useFrameWidth } from "./frame-width";
import { barWidthOf, EDGE_REM, floorOf, ROW_REM, withBar } from "./grid-floor";
import {
  type CellDraft,
  type CellPosition,
  type CellRefusal,
  HEADER_ROW,
  samePosition,
  useCursor,
  useGridKeyboard,
} from "./grid-keyboard";
import { configColumn, type GridFeatures, type GridTable, useGridTable } from "./grid-table";
import { GridToolbar, toggledColumns } from "./grid-toolbar";
import { HeaderCell } from "./header-cell";
import { type KeptFilters, useKeptFilters } from "./kept-filters";
import { useKeptPageSize } from "./kept-size";
import { useGridPaste } from "./paste";
import { PasteAppliedNotice, PasteDialog, UnshownNotice } from "./paste-dialog";
import { PendingAddress, usePendingAddress } from "./pending-address";
import { endPinnedWidth, pinnedWidth, pinningOf, useFrameRoom } from "./pinning";
import { useRootFontSize, useRowWindow } from "./row-window";
import { type GridQuery, type GridSort, searchHref, sortHref } from "./query";
import {
  HandleCell,
  type RowSelection,
  SelectionNotes,
  selectedRow,
  useRowSelection,
} from "./row-selection";
import {
  type GridPreferences,
  initialSettings,
  keptPageSize,
  recordedPreferences,
  useSettingsWriter,
} from "./settings";
import {
  busyOf,
  CellMenu,
  hasCellMenu,
  onRows,
  type RowCommands,
  UndoAnnouncer,
  useUndoShortcut,
  writingOf,
} from "./undo-commands";

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
   * on it (WF-IHM-0030); none, and the refusal names only what the row itself says it depends on
   * (`dependsOn`), if anything.
   */
  readonly dependencies?: DependencyReader<Row> | undefined;
  /**
   * Whether the grid enters a revision in progress: its bar offers undo and redo, and it takes
   * Ctrl+Z and Ctrl+Shift+Z (WF-IHM-0110) — placed, not wired yet.
   */
  readonly undoable?: boolean | undefined;
  /**
   * What holds the grid, given the rows it shows — those of the answer, as its writes left them —:
   * the Gantt of the planning lays them out once for all its cells (`GanttRows`). One element
   * around the grid, never a prop of each row (défaut n° 14).
   */
  readonly around?: ((rows: readonly Row[], grid: ReactNode) => ReactNode) | undefined;
  /**
   * What the folds of a tree are kept for in the session, besides the grid: the revision it reads.
   */
  readonly foldScope?: string | undefined;
  /**
   * What the reading asked of the server besides its fields and its sort — the search, the filters —,
   * as it was sent: a reading so narrowed unfolds the rows above those it retains. None, or nothing
   * in it, for a reading not narrowed.
   */
  readonly narrowing?: Readonly<Record<string, unknown>> | undefined;
  /** The commands the screen gives the rows of the grid; none for a grid it writes nothing from. */
  readonly commands?: RowCommands<Row> | undefined;
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
      <FoldToggle rowKey={config.rowKey(row)} placeholder />
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
  readonly handle: { readonly name: (number: number) => string; readonly hint: string };
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
  const column = configColumn(config, position.column);
  const computed = computedIn(column, row);
  const pinning = pinningOf(table, position.column, "z-10");
  const state = cellStateOf(cells, config.rowKey(row), position);
  const marks = position.column === DIFF_MARK_KEY;
  const content =
    state.pending ??
    (marks ? (
      <DiffMark difference={config.difference?.(row)} />
    ) : (
      cellContent(config, column, row, locale)
    ));
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
        computed ? "bg-muted" : "bg-background",
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
  // In a tree, where the row stands, and whether it is unfolded.
  const tree = useTreeRow(shared.config.rowKey(row.original));
  const { selection } = shared.cells;
  const { className, ...selected } = selectedRow(
    selection.selected(index),
    selection.dropAt(index),
  );
  return (
    <TableRow
      aria-rowindex={index + 2}
      aria-level={tree?.level}
      aria-posinset={tree?.position}
      aria-setsize={tree?.siblings}
      aria-expanded={tree?.expanded}
      {...selected}
      className={cn("h-7", className, differenceTint(shared.config.difference?.(row.original)))}
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
              number={shared.config.rowNumber?.(row.original)}
              selected={selection.selected(index) === true}
              name={shared.cells.handle.name}
              hint={shared.cells.handle.hint}
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
            style={{ left: pinning.left, right: pinning.right }}
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

/** Whether the grid is busy: reading a sort or a search anew, or a command of its screen waiting. */
function gridBusy(reading: boolean, commands: { readonly busy: boolean }): boolean {
  return reading || commands.busy;
}

/**
 * The name of a grid among several on its screen — one that writes the address under its own
 * names —, which names its search and its menu of the columns; none for a grid alone.
 */
function sharedName(
  config: { readonly address?: unknown; readonly name: GridName },
  named: (name: GridName) => string,
): string | undefined {
  return config.address === undefined ? undefined : named(config.name);
}

/** The grid, held by what its screen puts around it, if anything. */
function held<Row>(
  grid: ReactNode,
  rows: readonly Row[],
  around: ((rows: readonly Row[], grid: ReactNode) => ReactNode) | undefined,
): ReactNode {
  return around === undefined ? grid : around(rows, grid);
}

/**
 * Render a dense grid, which shares the address last asked with its bar — and with its screen,
 * when the screen shares one (`PendingAddress`): a search typed on while the one sent is on its
 * way survives its arrival (`useDatedState`).
 */
export function DenseGrid<Row extends RowData, Sort extends string, Totals>(
  props: DenseGridProps<Row, Sort, Totals>,
) {
  return (
    <PendingAddress>
      <SharedGrid {...props} />
    </PendingAddress>
  );
}

/** Render a dense grid, the address last asked shared. */
function SharedGrid<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  totals,
  totalsCaption,
  query,
  preferences,
  dependencies,
  undoable,
  around,
  foldScope,
  narrowing,
  commands,
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
  // The size of its pages the account keeps for the grid: the session's, then the last one chosen.
  const [keptSize, setKeptSize] = useState(keptPageSize(preferences));
  const [settings, setSettings] = useState(() => initialSettings(preferences, config.columns));
  // The settings as they are now, which a preference written later reads: kept at each change.
  const currentSettings = useRef(settings);
  const writer = useSettingsWriter(config.key);
  // The filters its screen keeps with its settings, as the page last showed them (`kept-filters.ts`).
  const { recordShown, shown } = writer;
  const recordFilters = useCallback(
    (filters: KeptFilters) => {
      recordShown(() =>
        recordedPreferences(
          preferences,
          currentSettings.current,
          keptSort.current,
          filters,
          keptSize,
        ),
      );
      shown();
    },
    [keptSize, preferences, recordShown, shown],
  );
  const kept = useKeptFilters(config, preferences, recordFilters);
  // The size of the pages the address asks, recorded as the filters are (`kept-size.ts`).
  const recordSize = useCallback(
    (size: number) => {
      setKeptSize(size);
      recordShown(() =>
        recordedPreferences(
          preferences,
          currentSettings.current,
          keptSort.current,
          kept.current,
          size,
        ),
      );
      shown();
    },
    [kept, preferences, recordShown, shown],
  );
  useKeptPageSize(config.address, keptSize, recordSize, config.paged === true);
  const scroller = useRef<HTMLDivElement>(null);
  const frameWidth = useFrameWidth(scroller);
  const room = useFrameRoom(scroller);
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
  useEffect(() => {
    shown();
  }, [query, shown]);
  // A sort or a search changes the address only: the server reads it, and answers anew. A sort
  // navigates at once, and its preference is written once it is shown: the address carries it —
  // a sort lifted included —, so the page never waits for the preference, nor reads it for it.
  const changeSort = (next: GridSort<Sort> | undefined) => {
    startTransition(() => {
      showSort(next);
      request((query) => sortHref(pathname, query, next, config.address));
    });
    keptSort.current = next === undefined ? null : { column: next.column, order: next.order };
    writer.recordShown(() =>
      recordedPreferences(
        preferences,
        currentSettings.current,
        keptSort.current,
        kept.current,
        keptSize,
      ),
    );
  };
  const search = (text: string) => {
    writer.flush();
    startTransition(() => {
      request((query) => searchHref(pathname, query, text, config.address));
    });
  };
  // The rows as the cells written left them: each row the server answered in place of the one read,
  // at the address they were written at — the page read anew there, or the same rows read at
  // another, drop none of them.
  const address = `${pathname}?${useSearchParams().toString()}`;
  // Each write a cell or a paste sends is one the commands of the screen wait for (#1224).
  const writing = writingOf(commands);
  const writes = useCellWrites<Row, Totals>({ address, rows, totals }, config, writing);
  // The totals the writes last answered, or those of the answer.
  const shownTotals = writes.totals ?? totals;
  // The rows the tree leaves unfolded, which the grid renders and moves through.
  const fold = useGridFold({
    tree: config.tree,
    rowKey: config.rowKey,
    rows: writes.rows,
    grid: config.key,
    scope: foldScope,
    narrowing,
  });
  const shownRows = fold.shown;
  const table = useGridTable({
    config,
    rows: shownRows,
    sort,
    onSort: changeSort,
    settings,
    room,
    onSettings: (next) => {
      setSettings(next);
      currentSettings.current = next;
      writer.record(
        recordedPreferences(preferences, next, keptSort.current, kept.current, keptSize),
      );
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
    rows: shownRows,
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
    rows: shownRows,
    columns: shownColumns,
    writes,
    scroller,
    answered: writes.rows,
    narrowed: isNarrowed(narrowing),
    writing,
    // The confirmation waits for any other write of the screen, as its gestures do (#1224).
    busy: busyOf(commands),
  });
  const undo = useUndoShortcut(undoable);
  const foldReach = useFoldReach();
  const folding = useFoldCommands({
    fold,
    rowKey: config.rowKey,
    cursor,
    scroller,
    focusAt: keyboard.focusAt,
    labelOf: (row) => {
      const label = config.columns[0];
      return label === undefined ? "" : formatCell(label.format, label.value(row), locale);
    },
  });
  const invalid = useId();
  const refusalId = useId();
  const hint = useId();
  const selection = useRowSelection({
    rows: shownRows,
    keyOf: config.rowKey,
    commands,
    cursor,
    focusAt: keyboard.focusAt,
    scroller,
  });
  const screenCommands = onRows(
    commands,
    (index) => model[index]?.original,
    selection.acted,
    (written) => {
      writes.applied({ ...written, totals: undefined });
    },
  );
  const cells: CellStates<Row, Sort, Totals> = {
    cursor: cursor.active,
    draft: keyboard.draft,
    refusal: keyboard.refusal,
    pending: writes.pending,
    writeRefusal: (row, column) => {
      if (writes.refused(row, column)) {
        return refusalDescription(writes.outcome, refusalId);
      }
      // A command refused at a row marks its label and has the refusal describe it.
      const refused = commands?.refused;
      return refused !== undefined &&
        column === config.columns[0]?.key &&
        row === config.rowKey(refused.row)
        ? refused.described
        : undefined;
    },
    closeRefusal: keyboard.closeRefusal,
    dismissRefusal: keyboard.dismissRefusal,
    menu: hasCellMenu(undoable, folding.menu, screenCommands.menu),
    foldKeys: FOLD_KEYS[foldReach],
    selection,
    handle: { name: (number) => t("selection.handle", { number }), hint },
    editor: (draft, column) =>
      column.entry === undefined ? null : (
        <CellEditor
          kind={column.entry.kind}
          label={headingOf(column, (key) => t(`columns.${key}`))}
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

  const grid = (
    <div
      className="flex min-h-0 flex-col gap-2"
      style={{ minHeight: withBar(bodyRows) }}
      onKeyDown={undo.onKeyDown}
    >
      <GridToolbar
        width={barWidthOf(frameWidth, table.getTotalSize())}
        search={query.search}
        onSearch={config.searched ? search : undefined}
        undoable={undoable}
        outline={folding.outline}
        commands={screenCommands.bar(cursor.active.row)}
        grid={sharedName(config, (name) => t(`names.${name}`))}
        columns={toggledColumns(table, config, (column) =>
          headingOf(column, (key) => t(`columns.${key}`)),
        )}
      />
      <UndoAnnouncer offered={undoable} told={undo.told} />
      <SelectionNotes hint={hint} count={selection.count} />
      <OutcomeNotice
        outcome={writer.outcome}
        onClear={writer.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      <OutcomeNotice
        id={refusalId}
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
      {commands?.around}
      <PasteAppliedNotice
        applied={paste.applied}
        onClear={paste.clear}
        onDismissed={keyboard.refocus}
      />
      <UnshownNotice
        unshown={paste.hidden}
        heading={(column) => headingOf(column, (key) => t(`columns.${key}`))}
      />
      {paste.pasting === undefined ? null : (
        <PasteDialog
          pasting={paste.pasting}
          waiting={paste.waiting}
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
        role={folding.role}
        aria-label={t(`names.${config.name}`)}
        aria-rowcount={bodyRows + 2}
        aria-colcount={columns.length}
        aria-multiselectable={selection.multiselectable}
        aria-busy={gridBusy(pending, screenCommands)}
        // The grid takes the height its screen leaves it (`Screen`, `fill`), shrinking from that
        // of its rows down to a floor; never taller than the window, so that the rows in view
        // stay a window's worth whatever holds it. The header and the totals stick to its edges,
        // the pinned columns to its start and to its end: a cell the focus brings into view comes out
        // from under them. A refusal whose row scrolls out of view closes.
        container={{
          ref: scroller,
          className: "w-fit max-w-full max-h-svh rounded-md border",
          style: {
            minHeight: floorOf(model.length),
            scrollPaddingBlock: edge,
            scrollPaddingInlineStart: pinnedWidth(table),
            scrollPaddingInlineEnd: endPinnedWidth(table),
          },
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
        <CellMenu
          offered={undoable}
          commands={screenCommands.menu}
          folding={
            folding.menu === undefined
              ? undefined
              : { menu: folding.menu, refocus: keyboard.refocus }
          }
          disabled={keyboard.draft !== undefined}
        >
          <TableBody
            {...keyboard.body}
            {...selection.body}
            onClick={(event) => {
              selection.body.onClick(event);
              keyboard.body.onClick(event);
            }}
            onKeyDown={(event) => {
              if (
                folding.onKeyDown(event) ||
                screenCommands.keys(cursor.active.row, event) ||
                selection.onKeyDown(event)
              ) {
                event.preventDefault();
              } else {
                keyboard.body.onKeyDown(event);
              }
            }}
          >
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
        </CellMenu>
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
  return held(<FoldContext value={folding.view}>{grid}</FoldContext>, shownRows, around);
}
