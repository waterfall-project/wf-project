// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells a grid writes (WF-IHM-0040): each cell validated leaves alone, by the action of its
 * column, and the row the server answers takes the place of the row read — its computed values
 * recalculated, its version moved on —, never a reading of the whole grid anew, which would cost
 * the second of §4.6.2 and lose the place of the cursor (EP-02, « Qui appelle l'API »). Until the
 * server answers, the cell shows what was validated, as pending; a refusal leaves the row as it
 * was, and is told as every screen tells one (`OutcomeNotice`).
 *
 * The cells of a row leave one after the other: each is written from the row the server last
 * answered, so that the second carries the version the first gave it, whatever the pace of the
 * typing. What is answered belongs to the reading it was written in: a page read anew — a sort,
 * a search, a reload — shows the rows of its answer, and an answer that arrives after it, a
 * success or a refusal, is dropped (défauts n° 1 et 2 de `typescript.md`): the reading the state
 * belongs to is changed in the render that brings the new rows, before any answer can land.
 */
"use client";

import { useMemo, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";

import type { CellEntry } from "./columns";

/** The API out of reach: the server action itself did not answer — the network is down. */
const UNREACHABLE: Outcome<never> = { kind: "unreachable" };

/** What the cells written change of a reading: the rows answered, the cells pending, the last outcome. */
interface Written<Row> {
  readonly reading: readonly Row[];
  /** The rows the server answered, by the key of the row. */
  readonly answered: ReadonlyMap<string, Row>;
  /** What each cell under way shows, by `cellKey`. */
  readonly pending: ReadonlyMap<string, string>;
  /** The outcome of the last write answered; none before any. */
  readonly outcome: Outcome<unknown> | undefined;
}

/** Nothing written yet in a reading. */
function fresh<Row>(reading: readonly Row[]): Written<Row> {
  return { reading, answered: new Map(), pending: new Map(), outcome: undefined };
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
export interface CellWrite<Row> {
  readonly row: Row;
  readonly column: string;
  readonly entry: CellEntry<Row>;
  readonly value: string | null;
  readonly shown: string;
}

/** The rows of a reading as the cells written left them, and how to write another. */
export interface CellWrites<Row> {
  /** The rows of the reading, each answered row in place of the one read. */
  readonly rows: readonly Row[];
  /** What a cell under way shows, if it is. */
  readonly pending: (row: string, column: string) => string | undefined;
  readonly outcome: Outcome<unknown> | undefined;
  /** Forget the outcome told. */
  readonly clear: () => void;
  readonly write: (write: CellWrite<Row>) => void;
}

/** Write the cells of a grid, on the rows of a reading, keyed by `rowKey`. */
export function useCellWrites<Row>(
  reading: readonly Row[],
  rowKey: (row: Row) => string,
): CellWrites<Row> {
  const [state, setState] = useState(() => fresh(reading));
  // A new reading starts afresh, in the very render that brings it.
  let written = state;
  if (state.reading !== reading) {
    written = fresh(reading);
    setState(written);
  }
  // The rows the server last answered, which the next write of the row starts from; and the
  // write of each row under way, which the next waits for.
  const last = useRef({ reading, answered: new Map<string, Row>() });
  const queues = useRef(new Map<string, Promise<void>>());
  const { answered, pending, outcome } = written;
  const rows = useMemo(
    () => (answered.size === 0 ? reading : reading.map((row) => answered.get(rowKey(row)) ?? row)),
    [reading, answered, rowKey],
  );
  const write = ({ row, column, entry, value, shown }: CellWrite<Row>) => {
    const key = rowKey(row);
    const cell = cellKey(key, column);
    if (last.current.reading !== reading) {
      last.current = { reading, answered: new Map() };
    }
    const memory = last.current;
    const current = (update: (before: Written<Row>) => Written<Row>) => {
      setState((before) => (before.reading === reading ? update(before) : before));
    };
    current((before) => ({ ...before, pending: changed(before.pending, cell, shown) }));
    const queued = (queues.current.get(key) ?? Promise.resolve()).then(async () => {
      const from = memory.answered.get(key) ?? row;
      const answer = await entry.write(from, value).catch(() => UNREACHABLE);
      const data = answer.kind === "done" ? answer.data : undefined;
      if (data !== undefined) {
        memory.answered.set(key, data);
      }
      current((before) => ({
        ...before,
        answered: data === undefined ? before.answered : changed(before.answered, key, data),
        pending: changed(before.pending, cell, undefined),
        outcome: answer,
      }));
    });
    queues.current.set(key, queued);
  };
  return {
    rows,
    pending: (row, column) => pending.get(cellKey(row, column)),
    outcome,
    clear: () => {
      setState((before) => ({ ...before, outcome: undefined }));
    },
    write,
  };
}
