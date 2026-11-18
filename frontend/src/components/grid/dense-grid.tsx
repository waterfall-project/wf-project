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
 * rows —, and a computed cell tried opens its refusal; a cell validated is written alone, and what
 * the server answers takes the place of what was read — the row, the rows the write changed with
 * it, the totals (`useCellWrites`), a refusal told above the grid, its cell marked. A
 * block pasted from a spreadsheet on the active cell is shown as the server would write and refuse
 * it, and its valid rows written once confirmed, in one operation, what was not written told
 * (WF-IHM-0050, `useGridPaste`). A grid that enters a revision in progress places undo and redo,
 * not wired yet (WF-IHM-0110, `UndoCommands`). A screen may give its rows commands, in the bar on
 * the row of the active cell and in the menu of a cell on its row (`RowCommands`): the work
 * breakdown edited in its grid (EP-14/L44c), its selected rows dragged (`useRowSelection`, US-0460).
 *
 * A grid whose rows name their parents is a tree, which folds and unfolds (WF-PLA-0080,
 * `useGridFold`): a `treegrid`, each row telling its level, its place among its siblings and
 * whether it is unfolded; a row folded takes the rows under it out of the grid — out of those it
 * renders, numbers and moves through —, and the Gantt, a column of the grid, folds with it
 * (WF-PLA-0090). The button in a label folds its row; Alt and minus and Alt and plus fold and
 * unfold the row of the active cell — the row above it, from a row under which nothing folds —, Alt
 * and * unfolds the whole tree, Shift or not, as in Microsoft Project; the bar folds the tree down to a
 * level. The active cell stays on its row, or goes to the row folded over it.
 *
 * A grid that reads a comparison folds away, at « Écarts seulement », its rows without difference
 * (WF-IHM-0170, `folded-runs.tsx`): each run so folded is a row of its own among those it renders,
 * which the arrows stop on and which unfolds it — no row of the answer, the totals the answer's.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  Fragment,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useOptimistic,
  useRef,
  useState,
  useTransition,
} from "react";

import {
  OutcomeNotice,
  refusalDescription,
  useReadAnew,
} from "@/components/commands/outcome-notice";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/components/ui/utils";
import { useCurrency } from "@/currency/context";

import {
  type DependencyReader,
  formatCell,
  type GridConfig,
  headingOf,
  offeredColumns,
} from "./columns";
import { CellEditor, EntryProblemNotice } from "./cell-editor";
import { useCellWrites } from "./cell-writes";
import { BodyRow } from "./dense-grid-rows";
import {
  FOLD_KEYS,
  useFoldReach,
  FoldContext,
  isNarrowed,
  useFoldCommands,
  useGridFold,
} from "./fold";
import {
  comparedDifference,
  FoldedRunRow,
  useRunCommands,
  useRunSlots,
  withFoldToggle,
} from "./folded-runs";
import { useRoomBelow } from "./frame-width";
import { EDGE_REM, floorOf, ROW_REM, withBar } from "./grid-floor";
import { HEADER_ROW, samePosition, useCursor, useGridKeyboard } from "./grid-keyboard";
import { configColumn, useGridTable } from "./grid-table";
import { type Filtering, keptOpenOf, panelLayout } from "./filter-bar";
import { GridToolbar, toggledColumns } from "./grid-toolbar";
import { HeaderCell } from "./header-cell";
import { type KeptFilters, useKeptFilters } from "./kept-filters";
import { useKeptPageSize } from "./kept-size";
import { type CellStates, gridBusy, held, sharedName, Spacer } from "./dense-grid-parts";
import { useGridPaste } from "./paste";
import { PasteAppliedNotice, PasteDialog, UnshownNotice } from "./paste-dialog";
import { type ComparedTotals, TotalsRow } from "./totals-row";
import { PendingAddress, usePendingAddress } from "./pending-address";
import { endPinnedWidth, pinnedWidth, pinningOf, useFrameRoom } from "./pinning";
import { useRootFontSize, useRowWindow } from "./row-window";
import { restOf, stretchedColumn, tableWidth } from "./table-width";
import { type GridQuery, type GridSort, searchHref, sortHref } from "./query";
import { SelectionNotes, useRowSelection } from "./row-selection";
import {
  isBarOpen,
  useBarFocus,
  SelectionBar,
  type SelectionBarOptions,
  useSelectedConfig,
} from "./selection-bar";
import {
  type GridPreferences,
  gridShape,
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
  type UndoControl,
  useUndoShortcut,
  writingOf,
} from "./undo-commands";

/**
 * The width of the bars above the grid: that of what holds them, which the frame of the table takes
 * too (`table-width.ts`), its scroll bars within it.
 */
const FULL = "100%";

/** The control of undo and redo, keeping shown the rows `keys` says before it asks the server. */
function keepingUndo(
  control: UndoControl | undefined,
  keys: () => readonly string[],
  keepShown: (keys: readonly string[]) => void,
): UndoControl | undefined {
  return control === undefined
    ? undefined
    : {
        ...control,
        press: (command) => {
          keepShown(keys());
          control.press(command);
        },
      };
}

/** The rows rendered beyond those in view, at each end. */
const OVERSCAN = 12;

/**
 * The size the grid assumes before it is measured — on the server, and until the browser has
 * laid it out —: the rows of a first screen are in the page as it arrives.
 */
const FIRST_SCREEN = { width: 1280, height: 720 };

/** What a grid shows: an answer of the API, what was asked for it, and the settings kept. */
export interface DenseGridProps<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  /** The rows of the answer, in its order. */
  readonly rows: readonly Row[];
  /** The totals of the answer. */
  readonly totals: Totals;
  /** What the totals row says before its figures: what the totals shown count. */
  readonly totalsCaption: (totals: Totals) => string;
  /**
   * The totals of the base and their difference to those of the answer, when the grid reads a
   * comparison (WF-IHM-0160): the totals row says the three, as the server gives them.
   */
  readonly comparison?: { readonly base: Totals; readonly delta: Totals } | undefined;
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
   * What wires undo and redo of the grid on the server's history (WF-IHM-0110, `useUndoRedo`): the
   * buttons, the menu and the keys then ask it, and its refusal is told above the grid. None, and
   * they are placed, unavailable.
   */
  readonly undo?: UndoControl | undefined;
  /**
   * What holds the grid, given the rows it shows — those of the answer, as its writes left them —:
   * the Gantt of the planning lays them out once for all its cells (`GanttRows`). One element
   * around the grid, never a prop of each row (défaut n° 14).
   */
  readonly around?: ((rows: readonly Row[], grid: ReactNode) => ReactNode) | undefined;
  /** The filters of the screen, as menus in the bar of the grid (#2916/L6); none, the bar as it is. */
  readonly treeFilters?: ReactNode;
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
  /** The row the address targets, unfolded down to and aimed at once hydrated (`useFoldCommands`). */
  readonly target?: string | undefined;
  /** The commands the screen gives the rows of the grid; none for a grid it writes nothing from. */
  readonly commands?: RowCommands<Row> | undefined;
  /**
   * Whether the screen may lay the grid low on the page, below what it stacks above it: the frame
   * is then bounded to the window less where it starts, so that its totals stay in view
   * (US-0710, #1209). The bound is kept at every width, though the stacking exists below the
   * large breakpoint alone: above it the grid starts high and the bound is the window less a
   * little, which `max-h-svh` already gives, so nothing visible changes for the cost of one
   * observer of the page.
   */
  readonly stacked?: boolean | undefined;
  /**
   * Whether the rows of a flat table are selected, picked one by one (Ctrl or Cmd and a click, Ctrl and
   * Space), all at once by the box of the header of the handles, and acted on from a bar above the
   * grid (`SelectionBar`), with what the screen gives it (#2916/L4). Off by default; a tree keeps
   * its contiguous selection, and shows the bar alone.
   */
  readonly selecting?: SelectionBarOptions<Row> | undefined;
  /**
   * For a flat table whose screen folds its filters into the bar of the grid (#2916): the filters
   * of the screen, which the panel under the bar holds, and the chips of those on, built from its
   * address. The panel is closed unless the account keeps it open (`filters_open`). None, the bar
   * as before and the filters where the screen puts them.
   */
  readonly filtering?: Filtering | undefined;
  /** What the screen puts at the end of the bar, at its right edge (`GridToolbar`, #3071). */
  readonly ending?: ReactNode;
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

/**
 * How a grid reads its screen anew once its writes answered (`CellRules.reread`): compared to a
 * base, whose marks no write answers (US-2340), by `router.refresh`; out of a comparison, never —
 * the answers alone, as EP-02 has it.
 */
function useComparedReread(comparing: boolean | undefined): (() => void) | undefined {
  const router = useRouter();
  return comparing === true
    ? () => {
        router.refresh();
      }
    : undefined;
}

/**
 * The totals of the base and their difference, as the totals row says them: none out of a
 * comparison, and none once a write answered the totals — those the base and the difference were
 * read with are no longer the totals shown, and the page read anew, which takes the place of the
 * totals written (`askedAnew`, `reread`), brings the three together; until it does, the row says
 * the figures of the answer alone.
 */
function comparedTotals<Totals>(
  comparison: { readonly base: Totals; readonly delta: Totals } | undefined,
  written: Totals | undefined,
  caption: (totals: Totals) => string,
): ComparedTotals<Totals> | undefined {
  return comparison === undefined || written !== undefined ? undefined : { ...comparison, caption };
}

/** Render a dense grid, the address last asked shared. */
function SharedGrid<Row extends RowData, Sort extends string, Totals>({
  config: given,
  rows,
  totals,
  totalsCaption,
  comparison,
  query,
  preferences,
  dependencies,
  undoable,
  undo: undoControl,
  around,
  treeFilters,
  foldScope,
  narrowing,
  target,
  commands,
  stacked,
  selecting,
  filtering,
  ending,
}: DenseGridProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  const { config: selected, pick } = useSelectedConfig(given, selecting);
  // Its columns of difference are offered, and shown once chosen, while it reads a comparison; its
  // settings are those of the columns it has, whatever it reads.
  const config = useMemo(() => offeredColumns(selected), [selected]);
  const locale = useLocale();
  const currency = useCurrency();
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
  const [settings, setSettings] = useState(() => initialSettings(preferences, selected.columns));
  const shape = useMemo(() => gridShape(selected.columns), [selected.columns]);
  // The settings as they are now, which a preference written later reads: kept at each change.
  const currentSettings = useRef(settings);
  const writer = useSettingsWriter(config.key);
  // Whether the panel of the filters is open: as the account keeps it, then as the user sets it. A
  // grid that never set it records none, what the account keeps going back as it came.
  const [filtersOpen, setFiltersOpen] = useState(keptOpenOf(preferences));
  const keptOpen = useRef(filtersOpen);
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
          shape,
          { filtersOpen: keptOpen.current },
        ),
      );
      shown();
    },
    [shape, keptSize, preferences, recordShown, shown],
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
          shape,
          { filtersOpen: keptOpen.current },
        ),
      );
      shown();
    },
    [shape, kept, preferences, recordShown, shown],
  );
  useKeptPageSize(config.address, keptSize, recordSize, config.paged === true);
  const scroller = useRef<HTMLDivElement>(null);
  const room = useFrameRoom(scroller);
  const roomBelow = useRoomBelow(scroller, stacked, panelLayout(filtering, filtersOpen));
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
        shape,
        { filtersOpen: keptOpen.current },
      ),
    );
  };
  // The panel opened or closed is recorded at once: a discrete choice, found again on the next visit.
  const openFilters = (open: boolean) => {
    setFiltersOpen(open);
    keptOpen.current = open;
    // Written as a column is: after a pause, and not before the page shows a sort asked — what
    // waits for it is built from `keptOpen` when it goes (défaut n° 15).
    writer.recordLater(() =>
      recordedPreferences(
        preferences,
        currentSettings.current,
        keptSort.current,
        kept.current,
        keptSize,
        shape,
        { filtersOpen: keptOpen.current },
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
  const reread = useComparedReread(config.comparing);
  const writes = useCellWrites<Row, Totals>(
    { address, rows, totals },
    { rowKey: config.rowKey, retotal: config.retotal, fresher: config.fresher, reread },
    writing,
  );
  // A write of a cell lost once sent: the grid is read anew, and takes no entry until it is back
  // (US-2240). The settings written are read anew too, which no entry waits for.
  const readingCells = useReadAnew(writes.outcome);
  const readingSettings = useReadAnew(writer.outcome);
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
    difference: comparedDifference(config),
  });
  const shownRows = fold.shown;
  // A row the grid writes — typed, pasted — stays shown while the rows without difference are folded
  // away, even once read back unchanged (WF-IHM-0170): the focus and the active cell stay on it. An
  // undo is no write of the grid: it keeps the row of the active cell (`keptUndo`).
  const keptWrites: typeof writes = {
    ...writes,
    write: (write) => {
      fold.keepShown([config.rowKey(write.row)]);
      writes.write(write);
    },
    applied: (written) => {
      fold.keepShown(written.rows.map(config.rowKey));
      writes.applied(written);
    },
  };
  // The rows shown and the runs of rows without difference folded away between them (US-2360).
  const runSlots = useRunSlots(fold);
  const { slots, slotOf } = runSlots;
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
        recordedPreferences(preferences, next, keptSort.current, kept.current, keptSize, shape, {
          filtersOpen: keptOpen.current,
        }),
      );
    },
  });

  const model = table.getRowModel().rows;
  const edge = EDGE_REM * useRootFontSize();
  const columns = table.getVisibleLeafColumns();
  const stretched = stretchedColumn(table, config);
  // What the other columns leave the one that takes the rest, which its handle goes no narrower than.
  const rest = restOf(table, stretched, room);
  const cursor = useCursor(config, model.length, columns);
  // The row of the active cell stays rendered however far the grid scrolls: it holds the focus.
  // So does the run whose row holds it.
  const { items, gaps, after, scrollToIndex } = useRowWindow({
    rows: slots,
    scroller,
    rowHeight,
    edges: { start: edge, end: edge },
    overscan: OVERSCAN,
    initialRect: FIRST_SCREEN,
    keyOf: (index) => {
      const slot = slots[index];
      return slot?.run === undefined
        ? (model[slot?.row ?? -1]?.id ?? index)
        : `run:${slot.run.key}`;
    },
    kept: runSlots.focused ?? slotOf[cursor.active.row],
  });
  const placeOf = (row: number) => slotOf[row] ?? row;
  const shownColumns = columns.map((column) => column.id);
  const keyboard = useGridKeyboard({
    config,
    cursor,
    rows: shownRows,
    columns: shownColumns,
    scroller,
    scrollToIndex: (index) => {
      scrollToIndex(placeOf(index));
    },
    page: () =>
      Math.max(1, Math.floor(((scroller.current?.offsetHeight ?? 0) - 2 * edge) / rowHeight)),
    inView: (index) => {
      const element = scroller.current;
      const top = edge + placeOf(index) * rowHeight - (element?.scrollTop ?? 0);
      return top + rowHeight > edge && top < (element?.offsetHeight ?? 0) - edge;
    },
    writes: keptWrites,
    reading: readingCells,
    locale,
    currency,
  });
  const paste = useGridPaste({
    config,
    rows: shownRows,
    columns: shownColumns,
    writes: keptWrites,
    scroller,
    answered: writes.rows,
    narrowed: isNarrowed(narrowing),
    writing,
    // The confirmation waits for any other write of the screen, as its gestures do (#1224).
    busy: busyOf(commands, readingCells),
  });
  const runs = useRunCommands({
    fold,
    slots: runSlots,
    rows: writes.rows,
    rowKey: config.rowKey,
    cursor,
    columns: shownColumns,
    page: () =>
      Math.max(1, Math.floor(((scroller.current?.offsetHeight ?? 0) - 2 * edge) / rowHeight)),
    scroller,
    scrollToSlot: scrollToIndex,
    focusAt: keyboard.focusAt,
  });
  // An undo reads the page anew, and answers no row key: the row of the active cell, which it may
  // return to its state read unchanged, is kept shown before it is asked (WF-IHM-0170).
  const keptUndo = keepingUndo(
    undoControl,
    () => {
      const active = model[cursor.active.row]?.original;
      return active === undefined ? [] : [config.rowKey(active)];
    },
    fold.keepShown,
  );
  const undo = useUndoShortcut(undoable, keptUndo);
  const foldReach = useFoldReach();
  const folding = useFoldCommands({
    fold,
    rowKey: config.rowKey,
    cursor,
    scroller,
    focusAt: keyboard.focusAt,
    target,
    labelOf: (row) => {
      const label = config.columns[0];
      return label === undefined
        ? ""
        : formatCell(label.format, label.value(row), locale, currency);
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
    pick,
  });
  // The bar of the selection lies over the bar of the grid, in its place: nothing moves under it.
  const barOpen = isBarOpen(selecting, selection.rows);
  const barFocus = useBarFocus(barOpen, keyboard.refocus);
  const screenCommands = onRows(
    commands,
    (index) => model[index]?.original,
    selection.acted,
    (written) => {
      keptWrites.applied({ ...written, totals: undefined });
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
    handle: {
      name: (number) => t("selection.handle", { number }),
      hint,
    },
    editor: (draft, column) =>
      column.entry === undefined ? null : (
        <CellEditor
          kind={column.entry.kind}
          label={headingOf(column, (key) => t(`columns.${key}`))}
          text={draft.text}
          typed={draft.typed}
          invalid={draft.problem === undefined ? undefined : invalid}
          asking={draft.asking === true}
          onValidate={keyboard.validate}
          onAbandon={keyboard.abandon}
        />
      ),
  };
  // An empty answer still has a row, which says so, between the header and the totals.
  const bodyRows = Math.max(slots.length, 1);

  const grid = (
    <div
      className="relative flex min-h-0 flex-col gap-2"
      style={{ minHeight: withBar(bodyRows) }}
      onKeyDown={undo.onKeyDown}
      onFocusCapture={barFocus}
    >
      <GridToolbar
        covered={barOpen}
        width={FULL}
        search={query.search}
        onSearch={config.searched ? search : undefined}
        undoable={undoable}
        undo={keptUndo}
        outline={folding.outline}
        commands={screenCommands.bar(cursor.active.row)}
        treeFilters={withFoldToggle(treeFilters, runs.toggle)}
        filters={filtering}
        open={filtersOpen}
        onOpen={openFilters}
        address={config.address}
        filterNames={config.filters}
        ending={ending}
        grid={sharedName(config, (name) => t(`names.${name}`))}
        columns={toggledColumns(table, config, (column) =>
          headingOf(column, (key) => t(`columns.${key}`)),
        )}
      />
      <SelectionBar
        rows={selection.rows}
        options={selecting}
        width={FULL}
        onClear={() => {
          selection.lift();
          keyboard.refocus();
        }}
      />
      <UndoAnnouncer
        offered={undoable}
        control={keptUndo}
        told={undo.told}
        onDismissed={keyboard.refocus}
      />
      <SelectionNotes
        hint={hint}
        count={selection.count}
        total={shownRows.length}
        pick={selection.pick}
      />
      <OutcomeNotice
        outcome={writer.outcome}
        reading={readingSettings}
        onClear={writer.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      <OutcomeNotice
        id={refusalId}
        outcome={writes.outcome}
        reading={readingCells}
        onClear={writes.clear}
        onDismissed={keyboard.refocus}
        dismissible
      />
      <OutcomeNotice
        outcome={paste.outcome}
        reading={paste.reading}
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
          lines={config.creates === "lines"}
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
        aria-busy={gridBusy(pending, screenCommands, keptUndo, readingCells)}
        // The grid takes the height its screen leaves it (`Screen`, `fill`), shrinking from that
        // of its rows down to a floor; never taller than the window, so that the rows in view
        // stay a window's worth whatever holds it. The header and the totals stick to its edges,
        // the pinned columns to its start and to its end: a cell the focus brings into view comes out
        // from under them. A refusal whose row scrolls out of view closes.
        // The frame takes the width of its card, and the table the wider of the frame and of its
        // columns, one of which takes what the others leave (`table-width.ts`, #3075).
        container={{
          ref: scroller,
          className: "w-full max-h-svh rounded-md border",
          style: {
            minHeight: floorOf(slots.length),
            maxHeight: roomBelow,
            scrollPaddingBlock: edge,
            scrollPaddingInlineStart: pinnedWidth(table),
            scrollPaddingInlineEnd: endPinnedWidth(table),
          },
          onScroll: keyboard.followScroll,
        }}
        className="table-fixed text-xs tabular-nums"
        style={{ width: tableWidth(table) }}
      >
        <colgroup>
          {columns.map((column) => (
            <col
              key={column.id}
              style={column.id === stretched ? undefined : { width: column.getSize() }}
            />
          ))}
        </colgroup>
        <TableHeader
          {...keyboard.header}
          onKeyDown={(event) => {
            if (!runs.onKeyDown(event)) {
              keyboard.header.onKeyDown(event);
            }
          }}
        >
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
                  selectAll={selection.boxOf(header.column.id)}
                  rest={header.column.id === stretched ? rest : undefined}
                />
              );
            })}
          </TableRow>
        </TableHeader>
        <CellMenu
          offered={undoable}
          control={keptUndo}
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
              if (runs.onKeyDown(event)) {
                return;
              }
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
              const slot = slots[item.index];
              const row = slot?.run === undefined ? model[slot?.row ?? -1] : undefined;
              return (
                <Fragment key={item.key}>
                  <Spacer height={gaps[position] ?? 0} span={columns.length} />
                  {slot?.run !== undefined ? (
                    <FoldedRunRow
                      run={slot.run}
                      before={slot.before}
                      index={item.index}
                      span={columns.length}
                      commands={runs}
                    />
                  ) : null}
                  {row === undefined ? null : (
                    <BodyRow
                      table={table}
                      config={config}
                      dependencies={dependencies}
                      cells={cells}
                      row={row}
                      index={row.index}
                      place={item.index}
                      locale={locale}
                    />
                  )}
                </Fragment>
              );
            })}
            <Spacer height={after} span={columns.length} />
            {slots.length === 0 ? (
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
            compared={comparedTotals(comparison, writes.totals, totalsCaption)}
            index={bodyRows + 2}
            locale={locale}
          />
        </TableFooter>
      </Table>
    </div>
  );
  return held(<FoldContext value={folding.view}>{grid}</FoldContext>, shownRows, around);
}
