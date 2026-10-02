// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A block of cells pasted from a spreadsheet into a grid, in two steps (WF-IHM-0050). The block
 * is read where the browser hands it, at the event `paste` on the active cell — never by
 * `navigator.clipboard`, which asks a permission —, as the tab-separated values a spreadsheet
 * copies (`readBlock`). It lands from the active cell: a block wider than the columns the grid
 * shows from there is refused at once, as the server would refuse it (`PASTE_TOO_WIDE`), and
 * nothing is asked. Otherwise the server says what it would write and refuse, with the reason of
 * each refusal, and writes nothing (`GridPaste.preview`); the grid shows that plan, and applies it
 * once confirmed, in one operation (`GridPaste.apply`), the rows the server wrote taking the place
 * of those read (`CellWrites.applied`). A paste abandoned asks nothing more, and an answer that
 * arrives after it is dropped; a plan that refuses a row cannot be applied: the grid stays as it
 * was. The grid judges nothing of what is pasted: the server reads the cells, and says why.
 *
 * A grid without `paste` in its configuration — read only — takes no paste: the browser does what
 * it does with one, and nothing is asked.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { type ClipboardEvent, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";

import type { CellWrites } from "./cell-writes";
import type { ColumnLabel, GridColumn, GridConfig, PastedBlock, PastePlan } from "./columns";
import { type CellPosition, positionOf } from "./grid-keyboard";
import { configColumn } from "./grid-table";

/** The API out of reach: the server action itself did not answer. */
const UNREACHABLE: Outcome<never> = { kind: "unreachable" };

/** A cell of a spreadsheet's copy: quoted, its quotes doubled within, or as it is. */
const CELL = /"((?:[^"]|"")*)"(?=[\t\r\n]|$)|[^\t\r\n]*/y;

/**
 * The rows and cells of a spreadsheet's copy: its cells separated by tabs, its rows by line ends,
 * the last one closing the block; a cell that holds a tab, a line end or a quote comes quoted, its
 * quotes doubled. Each cell is kept as copied: the server reads it.
 */
export function readBlock(text: string): PastedBlock {
  const cell = new RegExp(CELL);
  const rows: string[][] = [];
  let row: string[] = [];
  let at = 0;
  for (;;) {
    cell.lastIndex = at;
    const found = cell.exec(text);
    row.push(found?.[1]?.replaceAll('""', '"') ?? found?.[0] ?? "");
    at = found === null ? text.length : cell.lastIndex;
    if (at >= text.length) {
      break;
    }
    const separator = text[at];
    at += text.startsWith("\r\n", at) ? 2 : 1;
    if (separator !== "\t") {
      rows.push(row);
      row = [];
      if (at >= text.length) {
        return rows;
      }
    }
  }
  rows.push(row);
  return rows;
}

/** Where a block is pasted from, as the dialog names it: the number of its row, its column. */
export interface PasteTarget {
  readonly row: number;
  readonly column: ColumnLabel;
}

/**
 * A paste under way: the block, its width, where it is pasted from; the plan the server answered,
 * none until it does; whether it is being applied.
 */
export interface Pasting {
  readonly block: PastedBlock;
  readonly width: number;
  readonly target: PasteTarget;
  readonly plan: PastePlan | undefined;
  readonly applying: boolean;
}

/** The refusal of a block wider than the grid from its cell, as the server says it. */
function tooWide(room: number): Outcome<never> {
  return {
    kind: "refused",
    problem: { code: "PASTE_TOO_WIDE", status: 422, params: { max_columns: room } },
    conflictingObjectId: null,
  };
}

/**
 * Where a block pasted from a cell lands: the column it starts at — the first of the grid when
 * the cell is the number of its row —, and how many columns the grid shows from there.
 */
function landing<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  columns: readonly string[],
  at: CellPosition,
): { readonly column: GridColumn<Row, Sort, Totals>; readonly room: number } | undefined {
  const offered = columns.filter((key) => configColumn(config, key) !== undefined);
  const from = Math.max(offered.indexOf(at.column), 0);
  const column = configColumn(config, offered[from] ?? "");
  return column === undefined ? undefined : { column, room: offered.length - from };
}

/** What a paste works on. */
export interface GridPasteOptions<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  /** The rows of the answer, as the cells written left them. */
  readonly rows: readonly Row[];
  /** The keys of the columns shown, in their order. */
  readonly columns: readonly string[];
  readonly writes: CellWrites<Row>;
}

/** Paste a block into a grid: read it, show its plan, apply it once confirmed, or abandon it. */
export function useGridPaste<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  columns,
  writes,
}: GridPasteOptions<Row, Sort, Totals>) {
  const [pasting, setPasting] = useState<Pasting>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // The paste an answer belongs to: one abandoned, or another started, drops the answer.
  const current = useRef(0);
  // The cell the block was pasted on, which has the focus back once the report closes.
  const origin = useRef<HTMLElement>(undefined);
  const { paste } = config;

  // The browser aims the event at the node of the caret a click left — the text of the cell —, so
  // the cell is the one that has the focus; an entry under way has it in its field, which takes
  // what is pasted as a field does.
  const onPaste = (event: ClipboardEvent<HTMLElement>) => {
    const focused = event.currentTarget.ownerDocument.activeElement;
    const at = positionOf(focused);
    const row = at === undefined ? undefined : rows[at.row];
    const text = event.clipboardData.getData("text/plain");
    const lands = at === undefined ? undefined : landing(config, columns, at);
    if (paste === undefined || at === undefined || row === undefined || lands === undefined) {
      return;
    }
    event.preventDefault();
    if (text === "") {
      return;
    }
    const block = readBlock(text);
    const width = Math.max(...block.map((cells) => cells.length));
    if (width > lands.room) {
      setOutcome(tooWide(lands.room));
      return;
    }
    current.current += 1;
    const asked = current.current;
    origin.current = focused instanceof HTMLElement ? focused : undefined;
    const target = { row: config.rowNumber?.(row) ?? at.row + 1, column: lands.column.label };
    setOutcome(undefined);
    setPasting({ block, width, target, plan: undefined, applying: false });
    void paste
      .preview(row, lands.column.key, block)
      .catch(() => UNREACHABLE)
      .then((answer) => {
        if (current.current !== asked) {
          return;
        }
        if (answer.kind === "done") {
          setPasting((before) => before && { ...before, plan: answer.data });
        } else {
          setPasting(undefined);
          setOutcome(answer);
        }
      });
  };

  /**
   * Apply the plan shown, once: the rows the server wrote take the place of those read, and a
   * refusal is told. The dialog stays until the server answers, and cannot be abandoned meanwhile:
   * what is under way is written whatever happens to it.
   */
  const apply = () => {
    const plan = pasting?.plan;
    if (paste === undefined || pasting === undefined || plan === undefined || pasting.applying) {
      return;
    }
    setPasting({ ...pasting, applying: true });
    void paste
      .apply(plan)
      .catch(() => UNREACHABLE)
      .then((answer) => {
        if (answer.kind === "done") {
          writes.applied(answer.data);
        }
        current.current += 1;
        setPasting(undefined);
        setOutcome(answer);
      });
  };

  return {
    pasting,
    outcome,
    onPaste,
    apply,
    /** Abandon the paste shown, before it is applied: nothing more is asked, nothing written. */
    abandon: () => {
      if (pasting?.applying !== true) {
        current.current += 1;
        setPasting(undefined);
      }
    },
    /** Give the focus back to the cell the block was pasted on, once the report closed. */
    refocus: () => {
      origin.current?.focus({ preventScroll: true });
    },
    /** Forget the outcome told. */
    clear: () => {
      setOutcome(undefined);
    },
  };
}
