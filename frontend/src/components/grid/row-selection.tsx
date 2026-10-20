// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The selection of rows of a dense grid (US-0460, WF-IHM-0040, WF-IHM-0100): rows contiguous among
 * those the grid shows, from an anchor to an end, found by their identity, so that a reading anew
 * that moves them keeps them selected. The cell of the row number is the handle of its row: a click
 * selects the row alone, Shift and a click extend the selection from the anchor to it; from the
 * keyboard, on the column of the handles, Space selects the row of the active cell, Shift and the up
 * or down arrow extend the selection as the active cell moves, and Escape lifts it. Each row tells
 * whether it is selected (`aria-selected`), the grid that it takes several (`aria-multiselectable`),
 * and a status how many are. The commands of the screen act on the selection the row they start
 * from stands in (Alt+Shift and an arrow, for the structure).
 *
 * A grid whose screen selects nothing (`RowCommands.selects`) shows no handle. The active cell, in
 * a row selected, follows its row through a reading anew that moves it, so that the next move starts
 * from the same rows.
 */
"use client";

import { Check, GripVertical } from "lucide-react";
import { useTranslations } from "next-intl";
import { type KeyboardEvent, type MouseEvent, useState } from "react";

import { TableCell } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";

import { cellAttributes, type CellState, cellKeys } from "./cell-attributes";
import { ROW_NUMBER_KEY } from "./columns";
import { type CellPosition, type Cursor, HEADER_ROW, positionOf } from "./grid-keyboard";

/** The selection, by the identity of its rows: the one it started from, and the one it ends on. */
interface Range {
  readonly anchor: string;
  readonly end: string;
}

/** The first and the last index of a selection among rows, if both of its ends are among them. */
function boundsOf(
  range: Range | undefined,
  keys: (index: number) => string | undefined,
  count: number,
): readonly [number, number] | undefined {
  if (range === undefined) {
    return undefined;
  }
  let anchor = -1;
  let end = -1;
  for (let index = 0; index < count && (anchor < 0 || end < 0); index += 1) {
    const key = keys(index);
    anchor = key === range.anchor ? index : anchor;
    end = key === range.end ? index : end;
  }
  return anchor < 0 || end < 0 ? undefined : [Math.min(anchor, end), Math.max(anchor, end)];
}

/** The index of the row a handle stands in, if an event happened in a handle. */
function handleOf(target: EventTarget): number | undefined {
  const cell = target instanceof Element ? target.closest("td[data-column]") : null;
  const at = positionOf(cell);
  return at?.column === ROW_NUMBER_KEY ? at.row : undefined;
}

/** What a key asks of the selection, on a handle: Space, Shift and Space, Escape, Shift and an arrow. */
function selectionKey(
  event: KeyboardEvent<HTMLElement>,
): "select" | "extend" | "lift" | "up" | "down" | undefined {
  if (event.altKey || event.ctrlKey || event.metaKey) {
    return undefined;
  }
  const keys: Readonly<Partial<Record<string, "select" | "lift" | "up" | "down">>> = {
    " ": "select",
    Escape: "lift",
    ArrowUp: "up",
    ArrowDown: "down",
  };
  const key = keys[event.key];
  if (key === "select") {
    return event.shiftKey ? "extend" : key;
  }
  return key === "lift" || event.shiftKey ? key : undefined;
}

/** What the grid of rows `Row` selects. */
export interface RowSelectionOptions<Row> {
  /** The rows the grid shows, in their order. */
  readonly rows: readonly Row[];
  readonly keyOf: (row: Row) => string;
  /** The commands of the screen, and whether they act on a selection; none, the grid selects nothing. */
  readonly commands: { readonly selects?: boolean | undefined } | undefined;
  readonly cursor: Cursor;
}

/** Select rows of a grid. */
export function useRowSelection<Row>({ rows, keyOf, commands, cursor }: RowSelectionOptions<Row>) {
  const [range, setRange] = useState<Range>();
  const keyAt = (index: number) => {
    const row = rows[index];
    return row === undefined ? undefined : keyOf(row);
  };
  const offered = commands?.selects === true;
  const bounds = offered ? boundsOf(range, keyAt, rows.length) : undefined;
  // The rows the active cell was among: a reading anew that moves the row of the active cell,
  // selected, takes the active cell with it.
  const [seen, setSeen] = useState(rows);
  if (seen !== rows) {
    setSeen(rows);
    const was = seen[cursor.active.row];
    const before = boundsOf(
      range,
      (index) => {
        const row = seen[index];
        return row === undefined ? undefined : keyOf(row);
      },
      seen.length,
    );
    const selected =
      before !== undefined && cursor.active.row >= before[0] && cursor.active.row <= before[1];
    const now = was === undefined ? -1 : rows.findIndex((row) => keyOf(row) === keyOf(was));
    if (selected && now >= 0 && now !== cursor.active.row) {
      cursor.set({ row: now, column: cursor.active.column });
    }
  }
  const isSelected = (index: number) =>
    bounds !== undefined && index >= bounds[0] && index <= bounds[1];
  /** The rows acted on from a row: the selection it stands in, or the row alone. */
  const acted = (index: number): readonly Row[] => {
    if (bounds !== undefined && isSelected(index)) {
      return rows.slice(bounds[0], bounds[1] + 1);
    }
    const row = rows[index];
    return row === undefined ? [] : [row];
  };
  /** Select the row at an index alone, or extend the selection to it. */
  const select = (index: number, extend: boolean) => {
    const key = keyAt(index);
    if (key === undefined) {
      return;
    }
    setRange((before) =>
      extend && before !== undefined && bounds !== undefined
        ? { anchor: before.anchor, end: key }
        : { anchor: key, end: key },
    );
  };
  /** Extend the selection from the row at an index to the next one up or down, if there is one. */
  const extend = (from: number, step: number) => {
    const anchor = isSelected(from) ? range?.anchor : keyAt(from);
    const end = keyAt(from + step);
    if (anchor !== undefined && end !== undefined) {
      setRange({ anchor, end });
    }
  };
  /**
   * The keys of the selection, on the column of the handles: whether the grid takes the key —
   * Shift and an arrow extend the selection and leave the grid to move the active cell, but past
   * the first row, to the header.
   */
  const onKeyDown = (event: KeyboardEvent<HTMLElement>): boolean => {
    const at = positionOf(event.target);
    const key = offered && at?.column === ROW_NUMBER_KEY ? selectionKey(event) : undefined;
    if (at === undefined || key === undefined || at.row === HEADER_ROW) {
      return false;
    }
    if (key === "select" || key === "extend") {
      select(at.row, key === "extend");
      return true;
    }
    if (key === "lift") {
      setRange(undefined);
      return range !== undefined;
    }
    extend(at.row, key === "up" ? -1 : 1);
    return key === "up" && at.row === 0;
  };
  const body = {
    onClick: (event: MouseEvent<HTMLElement>) => {
      const index = offered ? handleOf(event.target) : undefined;
      if (index !== undefined) {
        select(index, event.shiftKey);
      }
    },
  };
  return {
    offered,
    /** Whether the row at an index is selected; none where the grid selects nothing. */
    selected: (index: number): boolean | undefined => (offered ? isSelected(index) : undefined),
    acted,
    /** How many rows are selected; none where the grid selects nothing. */
    count: offered ? (bounds === undefined ? 0 : bounds[1] - bounds[0] + 1) : undefined,
    /** Whether the grid says it takes several rows: where it selects. */
    multiselectable: offered ? true : undefined,
    onKeyDown,
    body,
  };
}

/** The selection of a grid, as `useRowSelection` gives it. */
export type RowSelection<Row> = ReturnType<typeof useRowSelection<Row>>;

/** The keys of a handle, as `aria-keyshortcuts` names them. */
const HANDLE_KEYS = "Space Shift+ArrowUp Shift+ArrowDown Escape";

/** The attributes and the classes of a row of a grid that selects. */
export function selectedRow(selected: boolean | undefined) {
  return {
    "aria-selected": selected,
    className: selected === true ? "[&>td]:bg-accent" : undefined,
  };
}

/** The classes of the handle of a row, narrower in its padding for its mark and its number. */
const HANDLE_CELL =
  "overflow-hidden bg-background px-1 text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset";

/** A cell that tells no key of the folding. */
const NO_FOLD = { folds: false, keys: undefined };

/**
 * The handle of a row, in the cell of its number: a cell of the grid like the others, reached by the
 * arrows, which selects its row, is named by the number of its row and described by how it selects
 * and moves (`SelectionNotes`); a mark grips it, another where its row is selected.
 */
export function HandleCell({
  position,
  state,
  menu,
  pinning,
  number,
  selected,
  name,
  hint,
}: {
  readonly position: CellPosition;
  readonly state: CellState;
  /** Whether the cells have a menu, which they announce. */
  readonly menu: boolean;
  readonly pinning: { readonly className: string; readonly left: number | undefined };
  readonly number: number | undefined;
  readonly selected: boolean;
  readonly name: (number: number) => string;
  readonly hint: string;
}) {
  const Mark = selected ? Check : GripVertical;
  const keys = [...cellKeys(menu, NO_FOLD, "", undefined), HANDLE_KEYS];
  return (
    <TableCell
      {...cellAttributes(position, state, false, false, keys)}
      aria-label={name(number ?? 0)}
      aria-describedby={hint}
      style={{ left: pinning.left }}
      className={cn(HANDLE_CELL, pinning.className)}
    >
      <span className="flex cursor-pointer items-center justify-end gap-0.5 select-none">
        <Mark aria-hidden="true" className="size-2.5 shrink-0" />
        {number}
      </span>
    </TableCell>
  );
}

/**
 * What a grid that selects says once: how to select and move with its handles, which each handle
 * names as its description, and how many rows are selected, in a status.
 */
export function SelectionNotes({
  hint,
  count,
}: {
  readonly hint: string;
  readonly count: number | undefined;
}) {
  const t = useTranslations("grid.selection");
  if (count === undefined) {
    return null;
  }
  return (
    <>
      <p id={hint} hidden>
        {t("hint")}
      </p>
      <p role="status" aria-live="polite" className="sr-only">
        {count === 0 ? null : t("count", { count })}
      </p>
    </>
  );
}
