// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The keyboard of a dense grid (WF-IHM-0040, the `grid` pattern of ARIA): one cell of the grid is
 * in the order of tabulation, the active one, and the arrows move it — Page Up and Page Down by a
 * screenful, Home and End along the row, Ctrl with them to the first and the last row. The header
 * is a row of the grid, which the up arrow reaches from the first row, and whose buttons and
 * handles are out of the order of tabulation (WF-IHM-0100): Enter or Space on a header sorts its
 * column, Shift and the arrows widen it (`HeaderCell`). The row it lands on is brought into view,
 * clear of the header and of the totals, and the cell takes the focus once rendered: the rows are
 * virtualized, and the row of the active cell stays rendered however far the grid scrolls
 * (`kept`, `useRowWindow`), so that the focus never falls to the page. The cell focused, by the
 * keyboard or the pointer, is the active one; Space scrolls nothing.
 *
 * Enter or F2 enters a cell that takes an entry, a character typed starts its entry with it, and
 * a double click enters it. Once validated, the cursor goes on (`CellEditor`): Tab along the row,
 * Enter to the row below, at the cell the row was started from. A value validated is read
 * (`cell-values.ts`) and leaves alone, by the action of its column (`useCellWrites`); a value
 * unchanged writes nothing.
 *
 * A computed cell is traversed, never entered: Enter, F2 or a character typed on it — or a click —
 * opens its refusal, which names what its value depends on (WF-IHM-0030). The grid holds it, by the
 * identity of its row: Escape closes it and gives the focus back to the cell; a click elsewhere
 * closes it only, the focus going where the click took it; a click on the cell itself closes it;
 * scrolled out of view, it closes, the focus kept on the active cell where it is.
 *
 * The cell entered and the refusal follow their row by its identity: a reading anew that moves it
 * takes the active cell with it, and one that no longer holds it closes them — a later reading
 * that brings the row back does not open them again by itself.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import {
  type Dispatch,
  type FocusEvent,
  type KeyboardEvent,
  type MouseEvent,
  type RefObject,
  type SetStateAction,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import type { Locale } from "@/i18n/locale";

import type { EntryMove } from "./cell-editor";
import { type EntryProblem, parsedEntry, shownEntry, startingText } from "./cell-values";
import type { CellWrites } from "./cell-writes";
import type { CellEntry, GridConfig } from "./columns";
import { configColumn } from "./grid-table";

/** The row of the header, before the first row of the answer. */
export const HEADER_ROW = -1;

/**
 * A cell of the grid: its row, by its index among the rows of the answer — `HEADER_ROW` for the
 * header —, and its column.
 */
export interface CellPosition {
  readonly row: number;
  readonly column: string;
}

/**
 * A cell being entered: its row, by its identity, and its column; the text its entry starts
 * from, and why what was validated was not, if it was not.
 */
export interface CellDraft {
  readonly key: string;
  readonly column: string;
  readonly text: string;
  /** The character typed that opened the entry, if one did: a list goes on searching from it. */
  readonly typed: string | undefined;
  readonly problem: EntryProblem | undefined;
}

/** The cell whose refusal shows: its row, by its identity, and its column. */
export interface RefusedCell {
  readonly key: string;
  readonly column: string;
}

/** The refusal shown, if any, and how many times one has opened: a failure is asked again. */
export interface CellRefusal {
  readonly at: RefusedCell | undefined;
  readonly opening: number;
}

/** Whether the refusal shows for the cell of a row, by its identity, in a column. */
export function refusedAt(refusal: CellRefusal, key: string, column: string): boolean {
  return refusal.at?.key === key && refusal.at.column === column;
}

/** Whether two positions are the same cell. */
export function samePosition(a: CellPosition | undefined, b: CellPosition): boolean {
  return a?.row === b.row && a.column === b.column;
}

/** The position a cell of the grid carries, if the element is one — a header or a cell of the body. */
export function positionOf(element: EventTarget | null): CellPosition | undefined {
  if (!(element instanceof HTMLElement) || element.dataset.column === undefined) {
    return undefined;
  }
  return { row: Number(element.dataset.row), column: element.dataset.column };
}

/** A number, within bounds. */
function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(value, high));
}

/** The keys that move the cursor by a step, and how far: rows, columns. */
function stepOf(key: string, page: number): { readonly rows: number; readonly columns: number } {
  const steps: Readonly<Record<string, { readonly rows: number; readonly columns: number }>> = {
    ArrowUp: { rows: -1, columns: 0 },
    ArrowDown: { rows: 1, columns: 0 },
    ArrowLeft: { rows: 0, columns: -1 },
    ArrowRight: { rows: 0, columns: 1 },
    PageUp: { rows: -page, columns: 0 },
    PageDown: { rows: page, columns: 0 },
  };
  return steps[key] ?? { rows: 0, columns: 0 };
}

/**
 * Where a key moves the cursor, among the header, `rows` rows and the columns shown; `undefined`
 * for a key that moves nothing. The header is reached by the up arrow from the first row, and kept
 * along by the keys that move within a row or up; Ctrl with Home or End, Page Down and the down
 * arrow go to the rows.
 */
export function moved(
  key: string,
  ctrl: boolean,
  at: CellPosition,
  bounds: { readonly rows: number; readonly columns: readonly string[]; readonly page: number },
): CellPosition | undefined {
  const last = bounds.columns.length - 1;
  const header =
    key === "ArrowUp" ||
    bounds.rows === 0 ||
    (at.row === HEADER_ROW && !ctrl && key !== "PageDown");
  const to = (row: number, column: number): CellPosition => ({
    row: clamp(row, header ? HEADER_ROW : 0, bounds.rows - 1),
    column: bounds.columns[clamp(column, 0, last)] ?? at.column,
  });
  if (key === "Home" || key === "End") {
    const end = key === "End";
    return to(ctrl ? (end ? bounds.rows : 0) : at.row, end ? last : 0);
  }
  const step = stepOf(key, bounds.page);
  return step.rows === 0 && step.columns === 0
    ? undefined
    : to(at.row + step.rows, bounds.columns.indexOf(at.column) + step.columns);
}

/**
 * Whether a key tries to enter a cell: Enter, F2, or a character typed — a shortcut aside.
 */
export function triesEntry(event: {
  readonly key: string;
  readonly ctrlKey: boolean;
  readonly metaKey: boolean;
  readonly altKey: boolean;
  readonly getModifierState: (key: "AltGraph") => boolean;
}): boolean {
  if (event.key === "Enter" || event.key === "F2") {
    return true;
  }
  // AltGr, which Windows reports as Ctrl and Alt together, types a character: « € », « @ ».
  const altGraph = event.getModifierState("AltGraph");
  const shortcut = event.metaKey || (!altGraph && (event.ctrlKey || event.altKey));
  // A key that types a character is named by that character, one code point.
  return /^.$/u.test(event.key) && !shortcut;
}

/** The cell at a position — a header or a cell of the body —, once rendered. */
function renderedCell(scroller: HTMLElement | null, at: CellPosition): HTMLElement | null {
  const attributes = `[data-row="${at.row.toString()}"][data-column="${at.column}"]`;
  return scroller?.querySelector<HTMLElement>(`td${attributes}, th${attributes}`) ?? null;
}

/** The body cell a click landed in, if any — never one of a popover over it. */
function clickedCell(event: MouseEvent<HTMLElement>): CellPosition | undefined {
  const { target } = event;
  return positionOf(target instanceof Element ? target.closest("td[data-column]") : null);
}

/** The active cell of a grid: as it was set, and as it stands among the rows and columns shown. */
export interface Cursor {
  readonly active: CellPosition;
  readonly set: Dispatch<SetStateAction<CellPosition>>;
}

/**
 * The active cell of a grid, first on the first row, at its first column; it stays within the
 * answer — in the header when the answer has no row — and among the columns shown, whatever they
 * became.
 */
export function useCursor<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  rows: number,
  columns: readonly { readonly id: string }[],
): Cursor {
  const [cursor, set] = useState<CellPosition>(() => ({
    row: 0,
    column: config.columns[0]?.key ?? "",
  }));
  const shown = columns.some((column) => column.id === cursor.column);
  return {
    active: {
      row: rows === 0 ? HEADER_ROW : clamp(cursor.row, HEADER_ROW, rows - 1),
      column: shown ? cursor.column : (columns[0]?.id ?? cursor.column),
    },
    set,
  };
}

/** What the keyboard of a grid works on. */
export interface GridKeyboardOptions<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly cursor: Cursor;
  /** The rows of the answer, in its order. */
  readonly rows: readonly Row[];
  /** The keys of the columns shown, in their order. */
  readonly columns: readonly string[];
  readonly scroller: RefObject<HTMLElement | null>;
  readonly scrollToIndex: (index: number) => void;
  /** How many rows a screenful holds. */
  readonly page: () => number;
  /** Whether the row at an index is in view, clear of the header and the totals. */
  readonly inView: (index: number) => boolean;
  readonly writes: CellWrites<Row, Totals>;
  readonly locale: Locale;
}

/** What a cell of the body is: its row, whether the server computes it, how it is entered. */
interface CellNature<Row, Totals> {
  readonly row: Row;
  readonly computed: boolean;
  readonly entry: CellEntry<Row, Totals> | undefined;
}

/** Move the active cell of a grid, enter and validate cells, and refuse a computed cell tried. */
export function useGridKeyboard<Row extends RowData, Sort extends string, Totals>({
  config,
  cursor,
  rows,
  columns,
  scroller,
  scrollToIndex,
  page,
  inView,
  writes,
  locale,
}: GridKeyboardOptions<Row, Sort, Totals>) {
  const [draft, setDraft] = useState<CellDraft>();
  const [refusal, setRefusal] = useState<CellRefusal>({ at: undefined, opening: 0 });
  // The cell to focus once rendered; and the cell a row was started from, which Tab went along
  // and Enter comes back to, on the row below.
  const follow = useRef<CellPosition>(undefined);
  const origin = useRef<CellPosition>(undefined);
  const { active } = cursor;
  // The rows the cell entered and the refusal were last found among, which a reading anew changes
  // in the very render that brings it: the cell entered goes with its row, the active cell with
  // it, and neither the entry nor the refusal outlives its row.
  const [seen, setSeen] = useState(rows);
  if (seen !== rows) {
    setSeen(rows);
    const indexOf = (key: string) => rows.findIndex((row) => config.rowKey(row) === key);
    const entered = draft === undefined ? -1 : indexOf(draft.key);
    if (draft !== undefined && entered < 0) {
      setDraft(undefined);
    } else if (draft !== undefined && entered !== active.row) {
      cursor.set({ row: entered, column: draft.column });
    }
    if (refusal.at !== undefined && indexOf(refusal.at.key) < 0) {
      setRefusal((before) => ({ ...before, at: undefined }));
    }
  }

  useLayoutEffect(() => {
    const target = follow.current;
    const cell = target === undefined ? null : renderedCell(scroller.current, target);
    if (cell !== null) {
      follow.current = undefined;
      focusRendered(cell, scroller.current);
    }
  });

  /** Focus a cell: now if it is rendered, once it is otherwise, brought into view. */
  const focusCell = (at: CellPosition) => {
    follow.current = at;
    if (at.row !== HEADER_ROW) {
      scrollToIndex(at.row);
    }
    const cell = renderedCell(scroller.current, at);
    if (cell !== null) {
      follow.current = undefined;
      focusRendered(cell, scroller.current);
    }
  };
  const moveTo = (at: CellPosition) => {
    cursor.set(at);
    focusCell(at);
  };
  /** The cell at a position, if the server computes it: the identity of its row, its column. */
  const computedAt = (at: CellPosition): RefusedCell | undefined => {
    const row = rows[at.row];
    return row !== undefined && configColumn(config, at.column)?.computed?.in(row) === true
      ? { key: config.rowKey(row), column: at.column }
      : undefined;
  };
  /** Open the refusal of a computed cell tried, the cell made the active one: whether it opened. */
  const refuse = (at: CellPosition): boolean => {
    const cell = computedAt(at);
    if (cell !== undefined) {
      cursor.set(at);
      setRefusal((before) => ({ at: cell, opening: before.opening + 1 }));
    }
    return cell !== undefined;
  };
  const cellAt = (at: CellPosition): CellNature<Row, Totals> | undefined => {
    const row = rows[at.row];
    const column = configColumn(config, at.column);
    if (row === undefined || column === undefined) {
      return undefined;
    }
    const entry = column.entry?.in(row) === true ? column.entry : undefined;
    return { row, computed: column.computed?.in(row) === true, entry };
  };
  /** The next cell along the row, forth or back, that takes an entry. */
  const along = (at: CellPosition, step: 1 | -1): CellPosition | undefined => {
    for (let index = columns.indexOf(at.column) + step; index >= 0; index += step) {
      const column = columns[index];
      if (column === undefined) {
        return undefined;
      }
      if (cellAt({ row: at.row, column })?.entry !== undefined) {
        return { row: at.row, column };
      }
    }
    return undefined;
  };
  const moveAfter = (at: CellPosition, move: EntryMove) => {
    if (move === "none") {
      return;
    }
    const next = move === "down" ? undefined : along(at, move === "next" ? 1 : -1);
    if (next !== undefined) {
      if (origin.current?.row !== at.row) {
        origin.current = at;
      }
      moveTo(next);
    } else if (move === "previous") {
      focusCell(at);
    } else {
      const from = origin.current?.row === at.row ? origin.current.column : at.column;
      origin.current = undefined;
      moveTo({ row: Math.min(at.row + 1, rows.length - 1), column: from });
    }
  };
  /** Enter a cell, or open its refusal if the server computes it: whether anything opened. */
  const start = (at: CellPosition, typed: string | undefined): boolean => {
    if (refuse(at)) {
      return true;
    }
    const cell = cellAt(at);
    if (cell?.entry === undefined) {
      return false;
    }
    const { kind, value } = cell.entry;
    const text = startingText(kind, value(cell.row), typed, locale);
    const key = config.rowKey(cell.row);
    setDraft({ key, column: at.column, text, typed, problem: undefined });
    return true;
  };
  /** Where the cell entered is among the rows, found by the identity of its row. */
  const draftAt = (entered: CellDraft): CellPosition | undefined => {
    const row = rows.findIndex((each) => config.rowKey(each) === entered.key);
    return row < 0 ? undefined : { row, column: entered.column };
  };
  const validate = (text: string, move: EntryMove): boolean => {
    const at = draft === undefined ? undefined : draftAt(draft);
    const cell = at === undefined ? undefined : cellAt(at);
    if (draft === undefined || at === undefined || cell?.entry === undefined) {
      setDraft(undefined);
      return true;
    }
    const { entry } = cell;
    const parsed = parsedEntry(entry.kind, text, locale);
    if ("problem" in parsed) {
      setDraft({ ...draft, text, problem: parsed.problem });
      return false;
    }
    setDraft(undefined);
    if (parsed.value !== (entry.value(cell.row) ?? null)) {
      const shown = shownEntry(entry.kind, parsed.value, locale);
      writes.write({ row: cell.row, column: at.column, entry, value: parsed.value, shown });
    }
    moveAfter(at, move);
    return true;
  };
  /** Close the refusal, the focus left where it is. */
  const dismiss = () => {
    setRefusal((before) => ({ ...before, at: undefined }));
  };
  // The keys of the header and of the body, but those a header took for itself — the sort, the
  // width of its column.
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const at = positionOf(event.target);
    if (at === undefined || event.defaultPrevented) {
      return;
    }
    const bounds = { rows: rows.length, columns, page: page() };
    const target = moved(event.key, event.ctrlKey || event.metaKey, at, bounds);
    const typed = /^(Enter|F2)$/.test(event.key) ? undefined : event.key;
    if (target !== undefined) {
      origin.current = undefined;
      moveTo(target);
    } else if (!(triesEntry(event) && start(at, typed)) && event.key !== " ") {
      return;
    }
    // A key the grid took: its default — the page scrolled by Space — is not done.
    event.preventDefault();
  };
  const onFocus = (event: FocusEvent<HTMLElement>) => {
    const at = positionOf(event.target);
    if (at !== undefined && !samePosition(at, active)) {
      cursor.set(at);
    }
  };
  const body = {
    onKeyDown,
    onFocus,
    // A click starts a row afresh, and tries a computed cell or closes the refusal it has open;
    // a double click enters a cell.
    onClick: (event: MouseEvent<HTMLElement>) => {
      const at = clickedCell(event);
      const cell = at === undefined ? undefined : computedAt(at);
      origin.current = undefined;
      if (at === undefined || cell === undefined) {
        return;
      }
      if (refusedAt(refusal, cell.key, cell.column)) {
        dismiss();
      } else {
        refuse(at);
      }
    },
    onDoubleClick: (event: MouseEvent<HTMLElement>) => {
      const at = clickedCell(event);
      if (at !== undefined) {
        start(at, undefined);
      }
    },
  };
  return {
    draft,
    refusal,
    body,
    /** The keyboard of the header: its cells moved along and left by the arrows. */
    header: { onKeyDown, onFocus },
    validate,
    /** Abandon the entry: from the keyboard, the focus back on its cell; on a blur, where it went. */
    abandon: (refocus: boolean) => {
      const at = draft === undefined ? undefined : draftAt(draft);
      setDraft(undefined);
      if (refocus && at !== undefined) {
        focusCell(at);
      }
    },
    /** Close the refusal from the keyboard, the focus back on its cell. */
    closeRefusal: () => {
      const { at } = refusal;
      dismiss();
      const row = at === undefined ? -1 : rows.findIndex((each) => config.rowKey(each) === at.key);
      if (at !== undefined && row >= 0) {
        moveTo({ row, column: at.column });
      }
    },
    /** Close the refusal, a click having taken the focus elsewhere. */
    dismissRefusal: dismiss,
    /**
     * Close the refusal once its row is scrolled out of view — it would stand beside nothing —, the
     * focus kept on the active cell, where it is.
     */
    followScroll: () => {
      const { at } = refusal;
      if (at === undefined) {
        return;
      }
      const index = rows.findIndex((row) => config.rowKey(row) === at.key);
      if (index < 0 || !inView(index)) {
        dismiss();
        renderedCell(scroller.current, active)?.focus({ preventScroll: true });
      }
    },
  };
}

/**
 * Focus a cell, and bring it into view as little as it takes. A cell of a column pinned at the
 * start is where it sticks, and no scroll brings it into view sideways: its row is brought into
 * the window, which the grid may overflow (#183). The others come out from under the pinned
 * columns, the header and the totals (`scroll-padding` of the element that scrolls), which the
 * scroll of a focus does not always heed. A header sticks to the top of the grid, within the
 * padding its rows come out of: it is brought into view sideways alone, the rows left where they
 * are.
 */
function focusRendered(cell: HTMLElement, scroller: HTMLElement | null): void {
  cell.focus({ preventScroll: true });
  const pinned = cell.style.left !== "";
  if (positionOf(cell)?.row === HEADER_ROW) {
    if (!pinned && scroller !== null) {
      revealSideways(cell, scroller);
    }
  } else if (pinned) {
    cell.closest("tr")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  } else {
    cell.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
}

/** Scroll the grid sideways as little as it takes for a cell to come out from under the pinned. */
function revealSideways(cell: HTMLElement, scroller: HTMLElement): void {
  const box = cell.getBoundingClientRect();
  const view = scroller.getBoundingClientRect();
  const padding = Number.parseFloat(scroller.style.scrollPaddingInlineStart);
  const start = view.left + scroller.clientLeft + (Number.isNaN(padding) ? 0 : padding);
  const end = view.left + scroller.clientLeft + scroller.clientWidth;
  if (box.left < start) {
    scroller.scrollLeft -= start - box.left;
  } else if (box.right > end) {
    scroller.scrollLeft += Math.min(box.right - end, box.left - start);
  }
}
