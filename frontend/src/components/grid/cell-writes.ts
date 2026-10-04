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
 * typing. What is answered belongs to the reading it was written in: a page read anew — a sort,
 * a search, a reload — shows the rows of its answer, and an answer that arrives after it, a
 * success or a refusal, is dropped (défauts n° 1 et 2 de `typescript.md`): the reading the state
 * belongs to is changed in the render that brings the new rows, before any answer can land. An
 * answer about another row than the one written is a failure of the service. A refusal stays told
 * until the notice clears it, whatever writes succeed after it. Rows a paste wrote together take
 * the place of those read the same way, the cells of each row written after them starting from
 * them (WF-IHM-0050). A cell written before a paste and answered after it is taken as any answer,
 * its place among the writes deciding which of the two a row shows (#202); only its refusal is
 * kept quiet when the paste wrote its row since — the row shows the paste, the refusal no longer
 * says anything of it.
 */
"use client";

import { useMemo, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";

import { type Answers, answersOf, retotalled, shownRow, shownRows, take } from "./answers";
import type { CellEntry, RowsWritten } from "./columns";

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<never> = { kind: "unreachable" };

/**
 * The server answered another row than the one written: an unexpected error of the service, told
 * as such, which nothing takes the place of the row for.
 */
const ANOTHER_ROW: Outcome<never> = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 500 },
  conflictingObjectId: null,
};

/**
 * What the cells written change of a reading: the rows and the totals answered, the cells
 * pending, the last outcome.
 */
interface Written<Row, Totals> {
  readonly reading: readonly Row[];
  /** The rows the server answered, by the key of the row. */
  readonly answered: ReadonlyMap<string, Row>;
  /** The totals the server last answered for the reading; none before any. */
  readonly totals: Totals | undefined;
  /** What each cell under way shows, by `cellKey`. */
  readonly pending: ReadonlyMap<string, string>;
  /** The outcome of the last write answered; none before any. */
  readonly outcome: Outcome<unknown> | undefined;
}

/** Nothing written yet in a reading. */
function fresh<Row, Totals>(reading: readonly Row[]): Written<Row, Totals> {
  return {
    reading,
    answered: new Map(),
    totals: undefined,
    pending: new Map(),
    outcome: undefined,
  };
}

/** What the answers of a reading show: the rows and the totals answered. */
function shown<Row, Totals>(
  answers: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
): Pick<Written<Row, Totals>, "answered" | "totals"> {
  return { answered: shownRows(answers, rowKey), totals: answers.totals?.value };
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
 * Write the cells of a grid, on the rows of a reading, keyed by `rowKey`; the totals of a reading
 * the writes do not answer them for read anew by `retotal`.
 */
export function useCellWrites<Row, Totals>(
  reading: readonly Row[],
  rowKey: (row: Row) => string,
  retotal?: () => Promise<Outcome<Totals>>,
): CellWrites<Row, Totals> {
  const [state, setState] = useState(() => fresh<Row, Totals>(reading));
  // A new reading starts afresh, in the very render that brings it.
  let written = state;
  if (state.reading !== reading) {
    written = fresh(reading);
    setState(written);
  }
  // What the server last answered, which the next write of a row starts from; and the write of
  // each row under way, which the next waits for.
  const last = useRef(answersOf<Row, Totals>(reading));
  const queues = useRef(new Map<string, Promise<void>>());
  // How many pastes wrote each row: a refusal of a write the paste of its row overtook says
  // nothing of the row shown.
  const pasted = useRef(new Map<string, number>());
  // The writes under way, whether one was done since the totals were last read anew, and the
  // reading of the totals an answer belongs to — moved on by each write that leaves.
  const underWay = useRef(0);
  const done = useRef(false);
  const retotals = useRef(0);
  const { answered, totals, pending, outcome } = written;
  const rows = useMemo(
    () => (answered.size === 0 ? reading : reading.map((row) => answered.get(rowKey(row)) ?? row)),
    [reading, answered, rowKey],
  );
  /** The answers of the reading shown, afresh for a new one. */
  const answers = () => {
    if (last.current.reading !== reading) {
      last.current = answersOf(reading);
    }
    return last.current;
  };
  /** An answer that does not hold the row written is a failure of the service. */
  const answering = (
    key: string,
    answer: Outcome<RowsWritten<Row, Totals>>,
  ): Outcome<RowsWritten<Row, Totals>> =>
    answer.kind === "done" && !answer.data.rows.some((row) => rowKey(row) === key)
      ? ANOTHER_ROW
      : answer;
  /** Change the state of the reading, unless a new one came meanwhile. */
  const current = (update: (before: Written<Row, Totals>) => Written<Row, Totals>) => {
    setState((before) => (before.reading === reading ? update(before) : before));
  };
  /**
   * Once every write answered, and one at least was done, read the totals anew — for a reading
   * whose totals the writes do not answer: an answer is taken only if no write left meanwhile,
   * whose own answer reads them again; a refusal is told unless another is.
   */
  const settle = (memory: Answers<Row, Totals>) => {
    if (retotal === undefined || underWay.current > 0 || !done.current) {
      return;
    }
    done.current = false;
    retotals.current += 1;
    const asked = retotals.current;
    void retotal()
      .catch(() => UNREACHABLE)
      .then((answer) => {
        if (asked !== retotals.current) {
          return;
        }
        if (answer.kind === "done") {
          retotalled(memory, answer.data);
        }
        current((before) => ({
          ...before,
          ...shown(memory, rowKey),
          // A refusal told before stays; a success told says nothing of this one.
          outcome:
            answer.kind === "done" ||
            (before.outcome !== undefined && before.outcome.kind !== "done")
              ? before.outcome
              : answer,
        }));
      });
  };
  const write = ({ row, column, entry, value, shown: showing }: CellWrite<Row, Totals>) => {
    const key = rowKey(row);
    const cell = cellKey(key, column);
    const born = pasted.current.get(key) ?? 0;
    const memory = answers();
    underWay.current += 1;
    retotals.current += 1;
    current((before) => ({ ...before, pending: changed(before.pending, cell, showing) }));
    const queued = (queues.current.get(key) ?? Promise.resolve()).then(async () => {
      const from = shownRow(memory, rowKey, key) ?? row;
      const answer = answering(key, await entry.write(from, value).catch(() => UNREACHABLE));
      const stale = answer.kind !== "done" && born !== (pasted.current.get(key) ?? 0);
      const data = answer.kind === "done" ? answer.data : undefined;
      if (data !== undefined) {
        take(memory, data, rowKey);
        done.current = true;
      }
      underWay.current -= 1;
      current((before) => ({
        ...before,
        ...(data === undefined ? {} : shown(memory, rowKey)),
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
      settle(memory);
    });
    queues.current.set(key, queued);
  };
  const applied = (together: RowsWritten<Row, Totals>) => {
    for (const row of together.rows) {
      const key = rowKey(row);
      pasted.current.set(key, (pasted.current.get(key) ?? 0) + 1);
    }
    const memory = answers();
    take(memory, together, rowKey);
    done.current = true;
    current((before) => ({ ...before, ...shown(memory, rowKey) }));
    settle(memory);
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
