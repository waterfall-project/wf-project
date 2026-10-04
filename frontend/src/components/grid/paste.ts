// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A block of cells pasted from a spreadsheet into a grid, in two steps (WF-IHM-0050). The block
 * is read where the browser hands it, at the event `paste`, heard on the document — the browser
 * aims it at the node the caret was left in — never by `navigator.clipboard`, which asks a
 * permission —, as the tab-separated values a spreadsheet copies (`readBlock`). The cell pasted
 * on is the one that holds the focus in this grid; an entry under way holds it in its field,
 * which takes what is pasted as a field does.
 *
 * The block lands from that cell, named by its column of the contract, and the server fills the
 * columns of the facet of its node in the order of the contract (`NodeColumn`), without knowing
 * which ones the grid shows (#200). The front therefore measures the block on those columns
 * (`GridPaste.span`, #223), and refuses at once, asking nothing, a block wider than them from the
 * cell — as the server would refuse it (`PASTE_TOO_WIDE`) — and a block whose span, from the column
 * of the cell to the last one filled in that order, reaches a column the grid does not show —
 * hidden, or that the grid does not present at all —, which would write what the user cannot see
 * (`hidden`), named. Otherwise the server says what it would write and refuse, with the reason of
 * each refusal, and writes nothing (`GridPaste.preview`); the grid shows that plan, and applies it
 * once confirmed, in one operation (`GridPaste.apply`), what the server wrote taking the place of
 * what was read (`CellWrites.applied`). A paste abandoned asks nothing more, and an answer that
 * arrives after it is dropped; a plan that refuses a row cannot be applied: the grid stays as it
 * was. The grid judges nothing of what is pasted: the server reads the cells, and says why.
 *
 * A grid without `paste` in its configuration — read only — takes no paste: the browser does what
 * it does with one, and nothing is asked.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { type RefObject, useEffect, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";

import type { CellWrites } from "./cell-writes";
import type { ColumnLabel, GridColumn, GridConfig, PastedBlock, PastePlan } from "./columns";
import { type CellPosition, positionOf } from "./grid-keyboard";

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

/** The width of a block: the widest of its rows — never by a spread, which a tall block blows. */
export function widest(block: PastedBlock): number {
  return block.reduce((width, cells) => Math.max(width, cells.length), 0);
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
 * The column a block pasted from a cell lands on: that of the cell, or the first when the cell is
 * the number of its row.
 */
function landing<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  at: CellPosition,
): GridColumn<Row, Sort, Totals> | undefined {
  return config.columns.find((column) => column.key === at.column) ?? config.columns[0];
}

/**
 * Where a block landed: the cell, its row, the column it lands on — named as the server names it,
 * by the column it sorts by (#200).
 */
interface Landed<Row, Sort extends string, Totals> {
  readonly at: CellPosition;
  readonly row: Row;
  readonly column: GridColumn<Row, Sort, Totals>;
  readonly named: Sort;
}

/** The cell a paste landed on, among the rows shown; none when the focus holds no cell. */
function landedAt<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  rows: readonly Row[],
  focused: Element | null,
): Landed<Row, Sort, Totals> | undefined {
  const at = positionOf(focused);
  const row = at === undefined ? undefined : rows[at.row];
  const column = at === undefined ? undefined : landing(config, at);
  // Every column of a grid sorts (WF-IHM-0060): one the server has no name for takes no paste.
  const named = column?.sortBy;
  return at === undefined || row === undefined || column === undefined || named === undefined
    ? undefined
    : { at, row, column, named };
}

/**
 * A column a block would fill that the grid does not show: hidden, named by its heading; or one
 * the grid does not present, named by the contract (`GridPaste.name`).
 */
export type UnshownColumn =
  | { readonly shown: "hidden"; readonly label: ColumnLabel }
  | { readonly shown: "absent"; readonly name: string };

/** The refusal the front opposes itself, before asking anything (#200, #223). */
interface LocalRefusal {
  readonly outcome: Outcome<never> | undefined;
  readonly hidden: UnshownColumn | undefined;
}

/**
 * Whether a block is refused here, before the server is asked: wider than the columns of the
 * facet of its node from the cell, in the order of the contract, or reaching one among them the
 * grid does not show — absent from its configuration, or hidden (WF-IHM-0060). Nothing when the
 * contract does not range the column of the cell: the server alone judges.
 */
function localRefusal<Row extends RowData, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  paste: NonNullable<GridConfig<Row, Sort, Totals>["paste"]>,
  landed: Landed<Row, Sort, Totals>,
  block: PastedBlock,
  shown: readonly string[],
): LocalRefusal | undefined {
  const span = paste.span(landed.row, landed.named);
  if (span === undefined) {
    return undefined;
  }
  const width = widest(block);
  if (width > span.length) {
    return { outcome: tooWide(span.length), hidden: undefined };
  }
  const set = new Set(shown);
  for (const filled of span.slice(0, width)) {
    const column = config.columns.find((configured) => configured.sortBy === filled);
    if (column === undefined) {
      return { outcome: undefined, hidden: { shown: "absent", name: paste.name(filled) } };
    }
    if (!set.has(column.key)) {
      return { outcome: undefined, hidden: { shown: "hidden", label: column.label } };
    }
  }
  return undefined;
}

/** What a paste works on. */
export interface GridPasteOptions<Row extends RowData, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  /** The rows of the answer, as the cells written left them. */
  readonly rows: readonly Row[];
  /** The keys of the columns shown, in their order. */
  readonly columns: readonly string[];
  readonly writes: CellWrites<Row, Totals>;
  /** The element the grid scrolls in: a paste is taken only when the focus is within it. */
  readonly scroller: RefObject<HTMLElement | null>;
}

/** Paste a block into a grid: read it, show its plan, apply it once confirmed, or abandon it. */
export function useGridPaste<Row extends RowData, Sort extends string, Totals>({
  config,
  rows,
  columns,
  writes,
  scroller,
}: GridPasteOptions<Row, Sort, Totals>) {
  const [pasting, setPasting] = useState<Pasting>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // The column the grid does not show a refused block would reach, named to the user (#200).
  const [hidden, setHidden] = useState<UnshownColumn>();
  // The paste an answer belongs to: one abandoned, or another started, drops the answer.
  const current = useRef(0);
  // The cell the block was pasted on, which has the focus back once the report closes.
  const origin = useRef<HTMLElement>(undefined);
  const { paste } = config;

  /** Refuse a block here, asking nothing: too wide, or reaching a column the grid does not show. */
  const refuse = (told: Outcome<never> | undefined, masked: UnshownColumn | undefined) => {
    setOutcome(told);
    setHidden(masked);
  };
  /** Ask the server the plan of a block, from a row and the first column it fills. */
  const ask = (
    asking: NonNullable<typeof paste>,
    row: Row,
    at: CellPosition,
    column: GridColumn<Row, Sort, Totals>,
    named: Sort,
    block: PastedBlock,
  ) => {
    current.current += 1;
    const asked = current.current;
    const target = { row: config.rowNumber?.(row) ?? at.row + 1, column: column.label };
    refuse(undefined, undefined);
    setPasting({ block, width: widest(block), target, plan: undefined, applying: false });
    void asking
      .preview(row, named, block)
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
  // The cell pasted on is the one that holds the focus in this grid; an entry under way holds
  // it in its field, which has no position, and keeps what is pasted for itself.
  const onPaste = (event: ClipboardEvent) => {
    const focused = scroller.current?.ownerDocument.activeElement ?? null;
    const within = scroller.current?.contains(focused) === true;
    const landed = within ? landedAt(config, rows, focused) : undefined;
    if (paste === undefined || landed === undefined) {
      return;
    }
    event.preventDefault();
    const text = event.clipboardData?.getData("text/plain") ?? "";
    if (text === "") {
      return;
    }
    const block = readBlock(text);
    const refused = localRefusal(config, paste, landed, block, columns);
    if (refused !== undefined) {
      refuse(refused.outcome, refused.hidden);
      return;
    }
    origin.current = focused instanceof HTMLElement ? focused : undefined;
    ask(paste, landed.row, landed.at, landed.column, landed.named, block);
  };

  // The event is heard on the document, where the browser lets it bubble whatever node the
  // caret was left in; the handler of the render is the one that runs, through a ref.
  const handler = useRef<(event: ClipboardEvent) => void>(undefined);
  useEffect(() => {
    handler.current = onPaste;
  });
  useEffect(() => {
    if (paste === undefined) {
      return undefined;
    }
    const listen = (event: ClipboardEvent) => handler.current?.(event);
    document.addEventListener("paste", listen);
    return () => {
      document.removeEventListener("paste", listen);
    };
  }, [paste]);

  /**
   * Apply the plan shown, once: what the server wrote takes the place of what was read, and a
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
    /** The column the grid does not show a refused block would reach, if one was refused for it. */
    hidden,
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
      refuse(undefined, undefined);
    },
  };
}
