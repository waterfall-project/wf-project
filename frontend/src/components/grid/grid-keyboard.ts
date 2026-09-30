// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The keyboard of a dense grid (WF-IHM-0040, the `grid` pattern of ARIA): one cell of the body is
 * in the order of tabulation, the active one, and the arrows move it — Page Up and Page Down by a
 * screenful, Home and End along the row, Ctrl with them to the first and the last row. The row it
 * lands on is brought into view, clear of the header and of the totals, and the cell takes the
 * focus once rendered: the rows are virtualized. The cell focused, by the keyboard or the
 * pointer, is the active one.
 *
 * A computed cell is traversed, never entered: Enter, F2 or a character typed on it — or a click —
 * opens its refusal, which names what its value depends on (WF-IHM-0030), and which the grid holds
 * and closes, the focus back on the cell.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import {
  type FocusEvent,
  type KeyboardEvent,
  type MouseEvent,
  type RefObject,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import type { GridConfig } from "./columns";
import { configColumn } from "./grid-table";

/** A cell of the body: its row, by its index among the rows of the answer, and its column. */
export interface CellPosition {
  readonly row: number;
  readonly column: string;
}

/** The refusal shown, if any, and how many times one has opened: a failure is asked again. */
export interface CellRefusal {
  readonly at: CellPosition | undefined;
  readonly opening: number;
}

/** Whether two positions are the same cell. */
export function samePosition(a: CellPosition | undefined, b: CellPosition): boolean {
  return a?.row === b.row && a.column === b.column;
}

/** The position a cell of the body carries, if the element is one. */
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
 * Where a key moves the cursor, among `rows` rows and the columns shown; `undefined` for a key
 * that moves nothing.
 */
export function moved(
  key: string,
  ctrl: boolean,
  at: CellPosition,
  bounds: { readonly rows: number; readonly columns: readonly string[]; readonly page: number },
): CellPosition | undefined {
  const last = bounds.columns.length - 1;
  const to = (row: number, column: number): CellPosition => ({
    row: clamp(row, 0, bounds.rows - 1),
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
}): boolean {
  if (event.key === "Enter" || event.key === "F2") {
    return true;
  }
  // A key that types a character is named by that character, one code point.
  return /^.$/u.test(event.key) && !event.ctrlKey && !event.metaKey && !event.altKey;
}

/** The body cell at a position, once rendered. */
function renderedCell(scroller: HTMLElement | null, at: CellPosition): HTMLElement | null {
  return (
    scroller?.querySelector<HTMLElement>(
      `td[data-row="${at.row.toString()}"][data-column="${at.column}"]`,
    ) ?? null
  );
}

/** The body cell a click landed in, if any — never one of a popover over it. */
function clickedCell(event: MouseEvent<HTMLElement>): CellPosition | undefined {
  const { target } = event;
  return positionOf(target instanceof Element ? target.closest("td[data-column]") : null);
}

/** What the keyboard of a grid works on. */
export interface GridKeyboardOptions<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  /** The rows of the answer, in its order. */
  readonly rows: readonly Row[];
  /** The keys of the columns shown, in their order. */
  readonly columns: readonly string[];
  readonly scroller: RefObject<HTMLElement | null>;
  readonly scrollToIndex: (index: number) => void;
  /** How many rows a screenful holds. */
  readonly page: () => number;
}

/** Move the active cell of a grid, and open the refusal of a computed cell tried. */
export function useGridKeyboard<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  columns,
  scroller,
  scrollToIndex,
  page,
}: GridKeyboardOptions<Row, Sort, Totals>) {
  const [cursor, setCursor] = useState<CellPosition>(() => ({
    row: 0,
    column: config.columns[0]?.key ?? "",
  }));
  const [refusal, setRefusal] = useState<CellRefusal>({ at: undefined, opening: 0 });
  // The cell to focus once it is rendered.
  const follow = useRef<CellPosition>(undefined);
  // The cursor stays within the answer and among the columns shown, whatever they became.
  const active: CellPosition = {
    row: clamp(cursor.row, 0, Math.max(rows.length - 1, 0)),
    column: columns.includes(cursor.column) ? cursor.column : (columns[0] ?? cursor.column),
  };

  useLayoutEffect(() => {
    const target = follow.current;
    const cell = target === undefined ? null : renderedCell(scroller.current, target);
    if (cell !== null) {
      follow.current = undefined;
      cell.focus();
    }
  });

  /** Focus a cell: now if it is rendered, once it is otherwise, brought into view. */
  const focusCell = (at: CellPosition) => {
    follow.current = at;
    scrollToIndex(at.row);
    const cell = renderedCell(scroller.current, at);
    if (cell !== null) {
      follow.current = undefined;
      cell.focus();
    }
  };
  /** Whether the server computes the cell at a position. */
  const computedAt = (at: CellPosition): boolean => {
    const row = rows[at.row];
    return row !== undefined && configColumn(config, at.column)?.computed?.in(row) === true;
  };
  /** Open the refusal of a computed cell tried: whether it opened. */
  const refuse = (at: CellPosition): boolean => {
    if (!computedAt(at)) {
      return false;
    }
    setRefusal((before) => ({ at, opening: before.opening + 1 }));
    return true;
  };
  const body = {
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      const at = positionOf(event.target);
      if (at === undefined) {
        return;
      }
      const bounds = { rows: rows.length, columns, page: page() };
      const target = moved(event.key, event.ctrlKey || event.metaKey, at, bounds);
      if (target !== undefined) {
        event.preventDefault();
        setCursor(target);
        focusCell(target);
      } else if (triesEntry(event) && refuse(at)) {
        event.preventDefault();
      }
    },
    onFocus: (event: FocusEvent<HTMLElement>) => {
      const at = positionOf(event.target);
      if (at !== undefined && !samePosition(at, active)) {
        setCursor(at);
      }
    },
    onClick: (event: MouseEvent<HTMLElement>) => {
      const at = clickedCell(event);
      if (at !== undefined) {
        refuse(at);
      }
    },
  };
  return {
    cursor: active,
    refusal,
    body,
    /** Close the refusal shown, the focus back on its cell. */
    closeRefusal: () => {
      const { at } = refusal;
      setRefusal((before) => ({ ...before, at: undefined }));
      if (at !== undefined) {
        focusCell(at);
      }
    },
    /** Take the focus given to the grid itself, the active row not rendered, to its cell. */
    focusActive: () => {
      focusCell(active);
    },
  };
}
