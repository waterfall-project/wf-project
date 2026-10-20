// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a cell of the body of a dense grid says of itself: what it is doing — active, entered,
 * written, its refusal shown —, its place in the grid, and the keys it tells (WF-IHM-0100). Shared
 * by the cells of the grid (`dense-grid.tsx`) and the handles of its rows (`row-selection.tsx`).
 */
"use client";

import {
  type CellDraft,
  type CellPosition,
  type CellRefusal,
  refusedAt,
  samePosition,
} from "./grid-keyboard";

/** What a cell of the body is doing: active, entered, written, its refusal shown. */
export interface CellState {
  readonly active: boolean;
  readonly draft: CellDraft | undefined;
  /** What it shows while the server has not answered its write. */
  readonly pending: string | undefined;
  readonly refused: boolean;
  /** The identifier of the sentence of the refusal of its write, when the server refused it. */
  readonly invalid: string | undefined;
}

/** What the cells of a body are doing, as far as a cell reads it of itself. */
interface CellReading {
  readonly cursor: CellPosition;
  readonly draft: CellDraft | undefined;
  readonly refusal: CellRefusal;
  readonly pending: (row: string, column: string) => string | undefined;
  readonly writeRefusal: (row: string, column: string) => string | undefined;
}

/** What a cell of the body is doing, by the identity of its row and its place. */
export function cellStateOf(cells: CellReading, key: string, position: CellPosition): CellState {
  return {
    active: samePosition(cells.cursor, position),
    draft:
      cells.draft?.key === key && cells.draft.column === position.column ? cells.draft : undefined,
    pending: cells.pending(key, position.column),
    refused: refusedAt(cells.refusal, key, position.column),
    invalid: cells.writeRefusal(key, position.column),
  };
}

/** The ring of a cell whose write the server refused: none for another. */
export function invalidRing(invalid: string | undefined): string | null {
  return invalid === undefined ? null : "ring-2 ring-destructive ring-inset";
}

/** The key that opens the menu of a cell, as `aria-keyshortcuts` names it (`CellMenu`). */
const MENU_KEY = "Shift+F10";

/**
 * The attributes of a cell of the body: its place in the grid, and what it says of itself — the
 * key of its menu among them, where the grid offers one, so that a reader of the screen learns of
 * it (WF-IHM-0100, #339).
 */
export function cellAttributes(
  position: CellPosition,
  state: CellState,
  enterable: boolean,
  computed: boolean,
  shortcuts: readonly string[],
) {
  return {
    "data-row": position.row,
    "data-column": position.column,
    tabIndex: state.active ? 0 : -1,
    "aria-keyshortcuts": shortcuts.length === 0 ? undefined : shortcuts.join(" "),
    "aria-readonly": enterable ? undefined : true,
    "aria-busy": state.pending === undefined ? undefined : true,
    "aria-haspopup": computed ? ("dialog" as const) : undefined,
    "aria-expanded": computed ? state.refused : undefined,
    "aria-invalid": state.invalid === undefined ? undefined : true,
    "aria-describedby": state.invalid,
  };
}

/**
 * The keys a cell tells, as `aria-keyshortcuts` names them: those of the menu of the cells, where
 * the grid offers it, and in the column of the labels of a row that folds, those of the folding.
 */
export function cellKeys(
  menu: boolean,
  folding: { readonly folds: boolean; readonly keys: string | undefined },
  column: string,
  label: { readonly key: string } | undefined,
): string[] {
  const told = folding.folds && column === label?.key ? folding.keys : undefined;
  return [...(menu ? [MENU_KEY] : []), ...(told === undefined ? [] : [told])];
}
