// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells a grid writes (WF-IHM-0040): each cell validated leaves alone, by the action of its
 * column, and the row the server answers takes the place of the row read — its computed values
 * recalculated, its version moved on —, never a reading of the whole grid anew, which would cost
 * the second of §4.6.2 and lose the place of the cursor (EP-02, « Qui appelle l'API »). So do the
 * other rows the write changed — the summaries above it recalculated, the tasks it rescheduled —,
 * and the totals, when the server's are those of the reading (`RowsWritten`, #218): the grid sums
 * nothing and dates nothing. Each answer has its place among the writes, and a row or totals a
 * later write answered are never taken back to an earlier one (`answers.ts`). A reading narrowed
 * by a search or a filter, whose totals the writes do not answer, reads them anew once its writes
 * all answered (`GridConfig.retotal`). Until the server answers, the cell
 * shows what was validated, as pending; a refusal leaves the row as it was, and is told as every
 * screen tells one (`OutcomeNotice`) — a session lost among them, which leads to the sign-in
 * page and back to the screen (WF-SEC-0020).
 *
 * The cells of a row leave one after the other: each is written from the row the server last
 * answered, so that the second carries the version the first gave it, whatever the pace of the
 * typing. What is answered belongs to the address it was written at: a page read at another address
 * — a sort, a search, a filter, a page — shows the rows of its answer, and an answer that arrives
 * after it, a success or a refusal, is dropped (défauts n° 1 et 2 de `typescript.md`): the address
 * the state belongs to is changed in the render that brings the new rows, before any answer can
 * land. A reading that holds the same rows in the same order is the same address all the same —
 * another list of the screen sorted, the address rewritten by `history.replaceState` before a
 * `refresh` —: only the parameters that change the rows of the grid count, as long as what a row
 * holds does not depend on the address. A page read anew at its address — `refresh` after a write
 * elsewhere on the screen, which Next may bring after the write of a cell left — drops nothing: the
 * cells under way stay pending, a refusal stays told, and an answer, arrived before it or after it,
 * is judged whole by the counter of the object it wrote (`GridConfig.fresher`,
 * `RowPart.versioned`): newer than the row read anew, it keeps all it gave, the summaries and the
 * totals included — or, where the grid cannot tell, while the reading anew reads the row as the one
 * before did (`reread` of `answers.ts`, défaut n° 22). An answer about another row than the one
 * written is a failure of the service. A refusal stays told until the notice clears it, whatever
 * writes succeed after it. Rows a paste wrote together take the place of those read the same way,
 * the cells of each row written after them starting from them (WF-IHM-0050). A cell written before
 * a paste and answered after it is taken as any answer, its place among the writes deciding which
 * of the two a row shows (#202); only its refusal is kept quiet when the paste wrote its row since
 * — the row shows the paste, the refusal no longer says anything of it.
 *
 * What the writes answered is kept in one place per address, changed by the callbacks alone and laid
 * over each reading committed (`useLayoutEffect`, as no callback runs between a commit and its
 * layout effects); the state holds copies of it, which a render lays over a reading anew without
 * changing anything it does not own.
 */
"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";
import { rejected } from "@/components/commands/rejection";

import {
  alike,
  type Answers,
  answersOf,
  copyAnswers,
  type Fresher,
  readRow,
  reread,
  retotalled,
  shownRow,
  shownRows,
  take,
} from "./answers";
import type { CellEntry, GridConfig, RowsWritten } from "./columns";

/**
 * The server answered another row than the one written: an unexpected error of the service, told
 * as such, which nothing takes the place of the row for.
 */
const ANOTHER_ROW: Outcome<never> = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 500 },
  conflictingObjectId: null,
};

/** A reading of a grid: the address it was read at, its rows and its totals. */
export interface CellReading<Row, Totals> {
  /** The address, path and query, the reading was read at. */
  readonly address: string;
  readonly rows: readonly Row[];
  readonly totals: Totals | undefined;
}

/** How a grid tells its rows apart, reads its totals anew and judges an answer against a row read. */
export type CellRules<Row, Totals> = Pick<
  GridConfig<Row, string, Totals>,
  "rowKey" | "retotal" | "fresher"
>;

/**
 * What the cells written change of the readings of an address: the answers laid over its last
 * reading, the rows and the totals they show, the cells pending, the last outcome.
 */
interface Written<Row, Totals> {
  readonly address: string;
  /** The readings of one address, a new one for another address. */
  readonly epoch: object;
  /** A copy of what the writes answered, laid over the last reading — never changed once here. */
  readonly view: Answers<Row, Totals>;
  /** The rows the server answered, by the key of the row. */
  readonly answered: ReadonlyMap<string, Row>;
  /** The totals the server last answered for the reading; none before any. */
  readonly totals: Totals | undefined;
  /** What each cell under way shows, by `cellKey`. */
  readonly pending: ReadonlyMap<string, string>;
  /** The outcome of the last write answered; none before any. */
  readonly outcome: Outcome<unknown> | undefined;
}

/** What the writes answered at an address, which the callbacks change: one per address. */
interface Book<Row, Totals> {
  readonly epoch: object;
  readonly answers: Answers<Row, Totals>;
}

/** Nothing written yet at the address of a reading. */
function fresh<Row, Totals>({
  address,
  rows,
  totals,
}: CellReading<Row, Totals>): Written<Row, Totals> {
  return {
    address,
    epoch: {},
    view: answersOf(rows, totals),
    answered: new Map(),
    totals: undefined,
    pending: new Map(),
    outcome: undefined,
  };
}

/** The state with the answers of a view: the rows and the totals they show. */
function laid<Row, Totals>(
  state: Written<Row, Totals>,
  view: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
): Written<Row, Totals> {
  return { ...state, view, answered: shownRows(view, rowKey), totals: view.totals?.value };
}

/** A copy of some answers laid over the reading of a view, the answers left alone. */
function over<Row, Totals>(
  answers: Answers<Row, Totals>,
  { reading, readTotals }: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
  fresher: Fresher<Row> | undefined,
): Answers<Row, Totals> {
  const copy = copyAnswers(answers);
  reread(copy, reading, readTotals, rowKey, fresher);
  return copy;
}

/** Whether two readings hold the same rows, in the same order. */
function sameRows<Row>(
  before: readonly Row[],
  after: readonly Row[],
  rowKey: (row: Row) => string,
): boolean {
  return (
    before.length === after.length &&
    before.every((row, at) => {
      const other = after[at];
      return other !== undefined && rowKey(row) === rowKey(other);
    })
  );
}

/** The key of a cell: the key of its row, and that of its column. */
export function cellKey(row: string, column: string): string {
  return `${row}\u0000${column}`;
}

/** A map with one key changed — set, or taken away when the value is `undefined`. */
function changed<V>(map: ReadonlyMap<string, V>, key: string, value: V | undefined) {
  const next = new Map(map);
  if (value === undefined) {
    next.delete(key);
  } else {
    next.set(key, value);
  }
  return next;
}

/** A write validated: the row, the column, how it writes, the value, and what the cell shows meanwhile. */
export interface CellWrite<Row, Totals> {
  readonly row: Row;
  readonly column: string;
  readonly entry: CellEntry<Row, Totals>;
  readonly value: string | null;
  readonly shown: string;
}

/** The rows of a reading as the cells written left them, its totals, and how to write another. */
export interface CellWrites<Row, Totals> {
  /** The rows of the reading, each answered row in place of the one read. */
  readonly rows: readonly Row[];
  /** The totals the writes last answered for the reading; none, and those of the reading stand. */
  readonly totals: Totals | undefined;
  /** What a cell under way shows, if it is. */
  readonly pending: (row: string, column: string) => string | undefined;
  readonly outcome: Outcome<unknown> | undefined;
  /** Forget the outcome told. */
  readonly clear: () => void;
  readonly write: (write: CellWrite<Row, Totals>) => void;
  /**
   * Take what the server wrote together — a paste applied — in place of what was read, in the
   * reading it was written in; a row the reading does not show is left out.
   */
  readonly applied: (written: RowsWritten<Row, Totals>) => void;
}

/**
 * Write the cells of a grid, on the rows of a reading, by the rules of the grid: its rows told
 * apart by `rowKey`, the totals of a reading the writes do not answer read anew by `retotal`, an
 * answer judged against a row read anew by `fresher`.
 */
export function useCellWrites<Row, Totals>(
  reading: CellReading<Row, Totals>,
  { rowKey, retotal, fresher }: CellRules<Row, Totals>,
): CellWrites<Row, Totals> {
  const [state, setState] = useState(() => fresh<Row, Totals>(reading));
  // A reading at another address starts afresh, in the very render that brings it; a reading anew
  // of the same address — or of the same rows — lays a copy of what was written over it.
  let written = state;
  if (state.view.reading !== reading.rows) {
    written =
      state.address === reading.address || sameRows(state.view.reading, reading.rows, rowKey)
        ? laid(
            { ...state, address: reading.address },
            over(state.view, answersOf(reading.rows, reading.totals), rowKey, fresher),
            rowKey,
          )
        : fresh(reading);
    setState(written);
  }
  const { epoch, view, answered, totals, pending, outcome } = written;
  // What the server answered at the address, which the next write of a row starts from: laid over
  // each reading as it is committed — afresh for another address.
  const book = useRef<Book<Row, Totals>>(undefined);
  useLayoutEffect(() => {
    if (book.current?.epoch === epoch) {
      reread(book.current.answers, view.reading, view.readTotals, rowKey, fresher);
    } else {
      book.current = { epoch, answers: copyAnswers(view) };
    }
  }, [epoch, view, rowKey, fresher]);
  // The write of each row under way, which the next waits for.
  const queues = useRef(new Map<string, Promise<void>>());
  // How many pastes wrote each row: a refusal of a write the paste of its row overtook says
  // nothing of the row shown.
  const pasted = useRef(new Map<string, number>());
  // The writes under way, whether one was done since the totals were last read anew, and the
  // reading of the totals an answer belongs to — moved on by each write that leaves.
  const underWay = useRef(0);
  const done = useRef(false);
  const retotals = useRef(0);
  const rows = useMemo(
    () =>
      answered.size === 0
        ? view.reading
        : view.reading.map((row) => answered.get(rowKey(row)) ?? row),
    [view.reading, answered, rowKey],
  );
  /** What was answered at the address shown; read in a callback alone. */
  const kept = (): Book<Row, Totals> => {
    book.current ??= { epoch, answers: copyAnswers(view) };
    return book.current;
  };
  /** An answer that does not hold the row written is a failure of the service. */
  const answering = (
    key: string,
    answer: Outcome<RowsWritten<Row, Totals>>,
  ): Outcome<RowsWritten<Row, Totals>> =>
    answer.kind === "done" &&
    !answer.data.rows.some((row) => rowKey(row) === key) &&
    !answer.data.parts.some((part) => part.key === key)
      ? ANOTHER_ROW
      : answer;
  /**
   * Whether an answer is to be taken over the row now read: unless the row read anew since the
   * write left is newer — by the counter of the row written, or, where it says nothing, by a
   * reading anew that reads it otherwise. A part that judges by its counter judges for itself.
   */
  const newer = (
    data: RowsWritten<Row, Totals>,
    key: string,
    first: Row | undefined,
    now: Row | undefined,
  ): boolean => {
    const own = data.rows.find((row) => rowKey(row) === key);
    return own === undefined || now === undefined || (fresher?.(own, now) ?? alike(first, now));
  };
  /** Change the state of an address, unless another address came meanwhile. */
  const current = (at: object, update: (before: Written<Row, Totals>) => Written<Row, Totals>) => {
    setState((before) => (before.epoch === at ? update(before) : before));
  };
  /**
   * The state with a copy of what was answered at an address, laid over the reading the state
   * holds — one rendered and not committed yet included.
   */
  const showing = ({ answers }: Book<Row, Totals>) => {
    const copy = copyAnswers(answers);
    return (before: Written<Row, Totals>) =>
      laid(
        before,
        before.view.reading === copy.reading ? copy : over(copy, before.view, rowKey, fresher),
        rowKey,
      );
  };
  /**
   * Once every write answered, and one at least was done, read the totals anew — for a reading
   * whose totals the writes do not answer: an answer is taken only if no write left meanwhile,
   * whose own answer reads them again; a refusal is told unless another is.
   */
  const settle = (at: Book<Row, Totals>) => {
    if (retotal === undefined || underWay.current > 0 || !done.current) {
      return;
    }
    done.current = false;
    retotals.current += 1;
    const asked = retotals.current;
    void retotal()
      .catch(rejected)
      .then((answer) => {
        if (asked !== retotals.current) {
          return;
        }
        if (answer.kind === "done") {
          retotalled(at.answers, answer.data);
        }
        const show = showing(at);
        current(at.epoch, (before) => ({
          ...show(before),
          // A refusal told before stays; a success told says nothing of this one.
          outcome:
            answer.kind === "done" ||
            (before.outcome !== undefined && before.outcome.kind !== "done")
              ? before.outcome
              : answer,
        }));
      });
  };
  const write = ({ row, column, entry, value, shown: meanwhile }: CellWrite<Row, Totals>) => {
    const key = rowKey(row);
    const cell = cellKey(key, column);
    const born = pasted.current.get(key) ?? 0;
    const at = kept();
    underWay.current += 1;
    retotals.current += 1;
    current(at.epoch, (before) => ({
      ...before,
      pending: changed(before.pending, cell, meanwhile),
    }));
    const queued = (queues.current.get(key) ?? Promise.resolve()).then(async () => {
      const memory = at.answers;
      const from = shownRow(memory, rowKey, key) ?? row;
      const first = readRow(memory, rowKey, key);
      const answer = answering(key, await entry.write(from, value).catch(rejected));
      const stale = answer.kind !== "done" && born !== (pasted.current.get(key) ?? 0);
      const data =
        answer.kind === "done" && newer(answer.data, key, first, readRow(memory, rowKey, key))
          ? answer.data
          : undefined;
      if (data !== undefined) {
        take(memory, data, rowKey);
        done.current = true;
      }
      underWay.current -= 1;
      const show = data === undefined ? undefined : showing(at);
      current(at.epoch, (before) => ({
        ...(show === undefined ? before : show(before)),
        pending: changed(before.pending, cell, undefined),
        // A refusal stays told until the notice clears it: a later write done says nothing of
        // it. A refusal a paste of its row overtook says nothing at all — any refusal, the API
        // out of reach and a session lost included: it belongs to the row before the paste,
        // which the paste wrote since, and the paste itself, answered, proved the API reachable
        // and the session open; a session lost meanwhile is told by the next write.
        outcome:
          stale || (answer.kind === "done" && before.outcome !== undefined)
            ? before.outcome
            : answer,
      }));
      settle(at);
    });
    queues.current.set(key, queued);
  };
  const applied = (together: RowsWritten<Row, Totals>) => {
    for (const row of together.rows) {
      const key = rowKey(row);
      pasted.current.set(key, (pasted.current.get(key) ?? 0) + 1);
    }
    const at = kept();
    take(at.answers, together, rowKey);
    done.current = true;
    current(at.epoch, showing(at));
    settle(at);
  };
  return {
    rows,
    totals,
    pending: (row, column) => pending.get(cellKey(row, column)),
    outcome,
    clear: () => {
      setState((before) => ({ ...before, outcome: undefined }));
    },
    write,
    applied,
  };
}
