// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rows without difference of a comparison, folded away (WF-IHM-0170, US-2360): « Écarts
 * seulement », while a grid reads a comparison to a base, takes out of the rows it renders each node
 * the server marks unchanged under which no node is marked otherwise, and sets in the place of each
 * run of rows so folded a row that says how many they are, and unfolds them (`folded-runs.tsx`). It
 * is no filter (WF-IHM-0130): the rows are all in the answer, the totals are the answer's, and
 * nothing is asked of the server — the grid folds on the marks of the server alone, comparing no
 * value (`Node.difference`). A row the server marks nothing of is never folded away.
 *
 * A run unfolded stays so while the folding is on: its rows, and those under them, are kept among
 * those opened, by their identities, so that a reading anew — after a write — keeps them in view;
 * and a row a write made differ, the reading anew marking it, comes back into view by itself.
 *
 * Pure, and neither server nor client: the fold of a grid reads it (`useGridFold`).
 */
import type { RowDifference } from "./columns";
import type { TreeIndex } from "./fold";

/** Whether the rows without difference are folded away, and the rows of the runs unfolded since. */
export interface DifferenceFold {
  readonly on: boolean;
  readonly opened: ReadonlySet<string>;
}

/** Nothing folded away: every row of the comparison shown. */
export const NOT_FOLDED: DifferenceFold = { on: false, opened: new Set() };

/** A run of rows folded away, which one row of the grid stands for: the identities of its rows. */
export interface FoldedRun {
  /** The identity of its first row, which names the run. */
  readonly key: string;
  readonly keys: readonly string[];
}

/** The rows a grid renders once the rows without difference are folded away, and the runs folded. */
export interface DifferencesFolded<Row> {
  readonly shown: readonly Row[];
  /**
   * The run just before each row shown, by its index among them, the last one after them all — of
   * one more than the rows shown —; empty when nothing is folded away.
   */
  readonly runs: readonly (FoldedRun | undefined)[];
}

/** The rows of an answer, and the marks of the server on them. */
export interface MarkedRows<Row> {
  /** Every row of the answer, folded or not by the tree, under which a difference is sought. */
  readonly rows: readonly Row[];
  readonly rowKey: (row: Row) => string;
  readonly index: TreeIndex;
  /** The difference the server marks on a row; none while no comparison is read. */
  readonly difference: ((row: Row) => RowDifference | null | undefined) | undefined;
}

/**
 * The rows that bear a difference, or have one under them: each row the server marks otherwise than
 * unchanged — or does not mark —, and the rows above it.
 */
function bearing<Row>({ rows, rowKey, index, difference }: MarkedRows<Row>): ReadonlySet<string> {
  const kept = new Set<string>();
  for (const row of rows) {
    if (difference?.(row) === "unchanged") {
      continue;
    }
    for (let key: string | undefined = rowKey(row); key !== undefined;) {
      if (kept.has(key)) {
        break;
      }
      kept.add(key);
      key = index.parentOf.get(key);
    }
  }
  return kept;
}

/**
 * The rows of `visible` — those the tree leaves unfolded — that stay once the rows without
 * difference are folded away, and the runs folded between them; all of them, no run, when the
 * folding is off or no comparison is read.
 */
export function foldedDifferences<Row>(
  visible: readonly Row[],
  marked: MarkedRows<Row>,
  fold: DifferenceFold | undefined,
): DifferencesFolded<Row> {
  if (fold?.on !== true || marked.difference === undefined) {
    return { shown: visible, runs: [] };
  }
  const kept = bearing(marked);
  const shown: Row[] = [];
  const runs: (FoldedRun | undefined)[] = [];
  let run: string[] = [];
  const close = () => {
    runs[shown.length] = run.length === 0 ? undefined : { key: run[0] ?? "", keys: run };
    run = [];
  };
  for (const row of visible) {
    const key = marked.rowKey(row);
    if (kept.has(key) || fold.opened.has(key)) {
      close();
      shown.push(row);
    } else {
      run.push(key);
    }
  }
  close();
  return { shown, runs };
}

/**
 * The rows opened once a run is unfolded: those opened before, the rows of the run, and every row
 * under one of them — folded by the tree, they come back unfolded with it.
 */
export function openedWith<Row>(
  opened: ReadonlySet<string>,
  run: FoldedRun,
  { rows, rowKey, index }: Pick<MarkedRows<Row>, "rows" | "rowKey" | "index">,
): ReadonlySet<string> {
  const next = new Set([...opened, ...run.keys]);
  const runKeys = new Set(run.keys);
  for (const row of rows) {
    const key = rowKey(row);
    for (let above = index.parentOf.get(key); above !== undefined;) {
      if (runKeys.has(above)) {
        next.add(key);
        break;
      }
      above = index.parentOf.get(above);
    }
  }
  return next;
}

/** A place among the rows a grid renders: a row shown, by its index, or a run folded before one. */
export type GridSlot =
  | { readonly row: number; readonly run?: undefined }
  | {
      readonly run: FoldedRun;
      /** The index of the row shown just after the run; the number of rows after the last one. */
      readonly before: number;
    };

/** The places a grid renders, its rows and its runs in their order, and the place of each row. */
export interface GridSlots {
  readonly slots: readonly GridSlot[];
  /** The place of each row shown, by its index among them. */
  readonly slotOf: readonly number[];
}

/** The places of `count` rows shown and of the runs folded before each and after the last. */
export function gridSlots(count: number, runs: readonly (FoldedRun | undefined)[]): GridSlots {
  const slots: GridSlot[] = [];
  const slotOf: number[] = [];
  for (let row = 0; row <= count; row += 1) {
    const run = runs[row];
    if (run !== undefined) {
      slots.push({ run, before: row });
    }
    if (row < count) {
      slotOf.push(slots.length);
      slots.push({ row });
    }
  }
  return { slots, slotOf };
}
