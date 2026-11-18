// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Écarts seulement » in the bar of a grid that reads a comparison (WF-IHM-0170, US-2360), and the
 * row that stands in the place of each run of rows it folds away (`difference-fold.ts`): it says how
 * many rows it folds, and unfolds them, by the keyboard as by the pointer.
 *
 * The row of a run is a row of the grid, among those it renders and counts (`aria-rowindex`,
 * `aria-rowcount`), but no row of the answer: no command, no entry, no paste, no selection reaches
 * it, nor through it a row folded away. Its one cell spans the grid, the text at the start of the
 * frame however far the grid scrolls sideways. The arrows of the keyboard stop on it, between the
 * rows it lies between — the up arrow from the row after it, the down arrow from the row before it
 * or from the header —, and leave it to them; Enter, Space, or the keys that unfold a row (Alt and
 * plus, Alt and *), unfold it. The active cell stays the one stop of the grid in the order of
 * tabulation: the cell of a run takes the focus from the arrows alone, as the button in it, out of
 * that order, takes the click. Once unfolded, the first row of the run is the active cell, the focus
 * on it. A reader of the screen hears the cell as it takes the focus: the number of rows folded, and
 * a button that unfolds them, said collapsed.
 */
"use client";

import { ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type Dispatch,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
  type SetStateAction,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { TableCell, TableRow } from "@/components/ui/table";

import { BODY_ROW, CELL_BACKGROUND } from "./cell-attributes";
import type { RowDifference } from "./columns";
import { DifferencesButton } from "./difference-filter-toggle";
import {
  type FoldedRun,
  type GridSlots,
  gridSlots,
  NOT_FOLDED,
  openedWith,
} from "./difference-fold";
import { foldShortcutHere, type GridFold, rowAfterFold, unfoldKeys, useFoldReach } from "./fold";
import { type CellPosition, type Cursor, HEADER_ROW, moved, positionOf } from "./grid-keyboard";

/** The attribute that names the run of the cell that stands for it. */
const RUN_ATTRIBUTE = "data-run";

/** The places of a grid, and the run whose cell holds the focus, kept rendered wherever it scrolls. */
export interface RunSlots extends GridSlots {
  /** The place of the run whose cell holds the focus, if one does. */
  readonly focused: number | undefined;
  readonly setFocused: Dispatch<SetStateAction<string | undefined>>;
}

/** The places a grid renders — its rows shown and its runs folded —, and the run focused. */
export function useRunSlots<Row>(fold: GridFold<Row>): RunSlots {
  const [focused, setFocused] = useState<string>();
  const count = fold.shown.length;
  const slots = useMemo(() => gridSlots(count, fold.runs), [count, fold.runs]);
  const at = focused === undefined ? -1 : slots.slots.findIndex((s) => s.run?.key === focused);
  return { ...slots, focused: at < 0 ? undefined : at, setFocused };
}

/** What the runs of a grid are moved through and unfolded from. */
export interface RunCommandsOptions<Row> {
  readonly fold: GridFold<Row>;
  readonly slots: RunSlots;
  /** Every row of the answer, as its writes left them. */
  readonly rows: readonly Row[];
  readonly rowKey: (row: Row) => string;
  readonly cursor: Cursor;
  /** The columns shown, and the rows a screenful holds: Home, End and the pages go by them. */
  readonly columns: readonly string[];
  readonly page: () => number;
  readonly scroller: RefObject<HTMLElement | null>;
  /** Bring a place into view. */
  readonly scrollToSlot: (slot: number) => void;
  /** Focus a cell, once rendered, brought into view. */
  readonly focusAt: (at: CellPosition) => void;
}

/** How the runs of a grid are reached, unfolded, and folded away. */
export interface RunCommands {
  /** « Écarts seulement », pressed or not, while a comparison is read; none otherwise. */
  readonly toggle: { readonly pressed: boolean; readonly press: () => void } | undefined;
  /**
   * The keys of a cell of the grid, the header's or the body's: an arrow that reaches a run focuses
   * it; a key on the cell of a run is its alone. Whether the key is taken.
   */
  readonly onKeyDown: (event: KeyboardEvent<HTMLElement>) => boolean;
  /** The keys of the cell of a run. */
  readonly onRunKey: (event: KeyboardEvent<HTMLElement>, run: FoldedRun, before: number) => void;
  /** Unfold a run, its first row then the active cell, focused. */
  readonly open: (run: FoldedRun) => void;
  readonly setFocused: Dispatch<SetStateAction<string | undefined>>;
}

/** Whether a key has a modifier, which the arrows of a run do not take. */
function modified(event: KeyboardEvent<HTMLElement>): boolean {
  return event.altKey || event.ctrlKey || event.metaKey || event.shiftKey;
}

/** Whether an element is in the cell of a run. */
function inRun(target: EventTarget): boolean {
  return target instanceof Element && target.closest(`td[${RUN_ATTRIBUTE}]`) !== null;
}

/** Where Home, End or a page moves from a cell; none for any other key, the arrows included. */
function reached(
  event: KeyboardEvent<HTMLElement>,
  from: CellPosition,
  bounds: { readonly rows: number; readonly columns: readonly string[]; readonly page: number },
): CellPosition | undefined {
  if (event.altKey || event.key.startsWith("Arrow")) {
    return undefined;
  }
  return moved(event.key, event.ctrlKey || event.metaKey, from, bounds);
}

/**
 * Reach the runs of a grid from its cells, unfold them, and fold the rows without difference away or
 * back: the active cell stays on its row — or goes to the row above it that stays —, by its index
 * among the rows that stay.
 */
export function useRunCommands<Row>({
  fold,
  slots,
  rows,
  rowKey,
  cursor,
  columns,
  page,
  scroller,
  scrollToSlot,
  focusAt,
}: RunCommandsOptions<Row>): RunCommands {
  // What takes the focus once rendered: the cell of a run, or a cell of a row.
  const pending = useRef<{ readonly run: string } | { readonly cell: CellPosition }>(undefined);
  useLayoutEffect(() => {
    const next = pending.current;
    if (next === undefined) {
      return;
    }
    if ("cell" in next) {
      pending.current = undefined;
      focusAt(next.cell);
      return;
    }
    const cell = scroller.current?.querySelector<HTMLElement>(
      `td[${RUN_ATTRIBUTE}="${CSS.escape(next.run)}"]`,
    );
    if (cell !== null && cell !== undefined) {
      pending.current = undefined;
      cell.focus({ preventScroll: true });
    }
  });
  const { differences, index, runs } = fold;
  const { setFocused } = slots;
  const count = fold.shown.length;
  const focusRun = (run: FoldedRun) => {
    setFocused(run.key);
    pending.current = { run: run.key };
    scrollToSlot(slots.slots.findIndex((slot) => slot.run?.key === run.key));
  };
  const moveTo = (at: CellPosition) => {
    setFocused(undefined);
    cursor.set(at);
    focusAt(at);
  };
  const open = (run: FoldedRun) => {
    const now = differences ?? NOT_FOLDED;
    const next = { on: now.on, opened: openedWith(now.opened, run, { rows, rowKey, index }) };
    const row = fold.shownWith(fold.collapsed, next).findIndex((each) => rowKey(each) === run.key);
    fold.set(fold.collapsed, next);
    setFocused(undefined);
    if (row >= 0) {
      const at = { row, column: cursor.active.column };
      cursor.set(at);
      pending.current = { cell: at };
    }
  };
  const press = () => {
    const next = { on: differences?.on !== true, opened: new Set<string>() };
    const active = cursor.active.row === HEADER_ROW ? undefined : fold.shown[cursor.active.row];
    const key = active === undefined ? undefined : rowKey(active);
    const row = rowAfterFold(fold.shownWith(fold.collapsed, next), rowKey, index, key);
    fold.set(fold.collapsed, next);
    if (row !== undefined) {
      cursor.set({ row, column: cursor.active.column });
    }
  };
  return {
    toggle: differences === undefined ? undefined : { pressed: differences.on, press },
    onKeyDown: (event) => {
      if (inRun(event.target)) {
        return true;
      }
      const at = positionOf(event.target);
      if (at === undefined || runs.length === 0 || modified(event)) {
        return false;
      }
      let before: number | undefined;
      if (event.key === "ArrowDown") {
        before = at.row + 1;
      } else if (event.key === "ArrowUp" && at.row !== HEADER_ROW) {
        before = at.row;
      }
      const run = before === undefined ? undefined : runs[before];
      if (run === undefined) {
        return false;
      }
      event.preventDefault();
      focusRun(run);
      return true;
    },
    onRunKey: (event, run, before) => {
      const command = foldShortcutHere(event);
      const column = cursor.active.column;
      if (
        event.key === "Enter" ||
        event.key === " " ||
        (command !== undefined && command !== "collapse")
      ) {
        open(run);
      } else if (event.key === "ArrowDown" && !modified(event)) {
        // Past the last run the arrow moves nothing, and the page does not scroll.
        if (before < count) {
          moveTo({ row: before, column });
        }
      } else if (event.key === "ArrowUp" && !modified(event)) {
        moveTo({ row: before > 0 ? before - 1 : HEADER_ROW, column });
      } else {
        // Home, End and the pages, from the row before the run — the first, for a run before it —:
        // the keys a run takes for none of its own stay inert, and so do the typed characters.
        const from = { row: Math.max(0, Math.min(before - 1, count - 1)), column };
        const target = reached(event, from, { rows: count, columns, page: page() });
        if (target === undefined) {
          return;
        }
        moveTo(target);
      }
      event.preventDefault();
    },
    open,
    setFocused,
  };
}

/**
 * The row of a run folded away: one cell across the grid, the focus of the arrows, which says how
 * many rows it folds and unfolds them — its button at the start of the frame, out of the order of
 * tabulation, the click leaving the focus to the row it unfolds.
 */
export function FoldedRunRow({
  run,
  before,
  index,
  span,
  commands,
}: {
  readonly run: FoldedRun;
  /** The index of the row shown just after it. */
  readonly before: number;
  /** Its place among the rows the grid renders. */
  readonly index: number;
  readonly span: number;
  readonly commands: RunCommands;
}) {
  const t = useTranslations("grid.differenceFold");
  const keys = ["Enter", "Space", ...unfoldKeys(useFoldReach())].join(" ");
  return (
    <TableRow aria-rowindex={index + 2} className={`${BODY_ROW} h-7`}>
      <TableCell
        colSpan={span}
        tabIndex={-1}
        data-run={run.key}
        aria-keyshortcuts={keys}
        onKeyDown={(event) => {
          commands.onRunKey(event, run, before);
        }}
        onFocus={() => {
          commands.setFocused(run.key);
        }}
        onBlur={() => {
          commands.setFocused(undefined);
        }}
        className={`${CELL_BACKGROUND} p-0 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset`}
      >
        <button
          type="button"
          tabIndex={-1}
          aria-expanded={false}
          onMouseDown={(event) => {
            // The focus goes to the first row unfolded, not to the button.
            event.preventDefault();
          }}
          onClick={(event) => {
            event.stopPropagation();
            commands.open(run);
          }}
          className="sticky left-0 inline-flex h-7 items-center gap-1 px-2 text-muted-foreground italic hover:text-foreground"
        >
          <ChevronRight aria-hidden="true" className="size-3.5 shrink-0" />
          {t("run", { count: run.keys.length })}
        </button>
      </TableCell>
    </TableRow>
  );
}

/**
 * The difference the server marks on a row, which the rows without difference are folded away by,
 * while the grid reads a comparison; none otherwise — on a differential, « Écarts seulement » is the
 * filter of the server (US-0700).
 */
export function comparedDifference<Row>(config: {
  readonly comparing?: boolean;
  readonly difference?: ((row: Row) => RowDifference | null | undefined) | undefined;
}): ((row: Row) => RowDifference | null | undefined) | undefined {
  return config.comparing === true ? config.difference : undefined;
}

/** The filters of the bar of a grid, and « Écarts seulement » after them while it reads a comparison. */
export function withFoldToggle(filters: ReactNode, toggle: RunCommands["toggle"]): ReactNode {
  return toggle === undefined ? (
    filters
  ) : (
    <>
      {filters}
      <DifferencesFoldToggle toggle={toggle} />
    </>
  );
}

/** « Écarts seulement » in the bar of a grid that reads a comparison: it folds, it filters nothing. */
function DifferencesFoldToggle({
  toggle,
}: {
  readonly toggle: { readonly pressed: boolean; readonly press: () => void };
}) {
  const t = useTranslations("grid");
  return (
    <DifferencesButton
      label={t("differenceFilter.label")}
      help={t("differenceFold.help")}
      pressed={toggle.pressed}
      onPress={toggle.press}
    />
  );
}
