// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the writes answered in a reading of a grid, as the latest of them left it (#218): the rows
 * the server answered whole — those written, the summaries above them recalculated —, the parts of
 * rows it answered alone — the schedule of a task rescheduled, the amounts of a line or a task
 * moved in time —, and the totals.
 *
 * Each answer has its place among the writes (`RowsWritten.order`): a row answered whole is never
 * taken back to one an earlier write answered; a part, kept aside with its place, is laid over the
 * row whole it is later than — the one shown then, or one an earlier write answers after it —, so
 * that a part never keeps out the label nor the version of a row an earlier write answered whole.
 * A part sets the values of its own fields alone: the parts of a row are laid one over the other in
 * the order of their answers, so that the schedule of one write and the amounts of another both
 * stand. A part that changes nothing of what the grid reads is not kept at all, and a part a later
 * row whole covers is let go (#355): a long run of writes keeps no more than it shows.
 *
 * Pure, and neither server nor client: the cells written keep one of these by reading.
 */
import type { RowPart, RowsWritten } from "./columns";

/** A value an answer gave, and the place of that answer among the writes. */
interface Answered<T> {
  readonly value: T;
  readonly order: number;
}

/** What the answers in a reading hold. */
export interface Answers<Row, Totals> {
  readonly reading: readonly Row[];
  /** The rows answered whole, by their key. */
  readonly rows: Map<string, Answered<Row>>;
  /** The parts of a row answered alone, by the key of the row, in the order of their answers. */
  readonly parts: Map<string, readonly Answered<RowPart<Row>["change"]>[]>;
  totals: Answered<Totals> | undefined;
  /** The place of the latest answer taken. */
  latest: number;
  /** The rows of the reading by their key, made at the first answer that needs it. */
  index: ReadonlyMap<string, Row> | undefined;
}

/** No answer yet in a reading. */
export function answersOf<Row, Totals>(reading: readonly Row[]): Answers<Row, Totals> {
  return {
    reading,
    rows: new Map(),
    parts: new Map(),
    totals: undefined,
    latest: Number.NEGATIVE_INFINITY,
    index: undefined,
  };
}

/** Whether an answer at a place comes after what was answered before, if anything was. */
function later(order: number, before: Answered<unknown> | undefined): boolean {
  return before === undefined || before.order <= order;
}

/** The row of the reading of a key, as read; none for a row the reading does not show. */
function read<Row, Totals>(
  answers: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
  key: string,
): Row | undefined {
  answers.index ??= new Map(answers.reading.map((row) => [rowKey(row), row]));
  return answers.index.get(key);
}

/** The row of a key whole, as the latest answer gave it whole, or as read. */
function whole<Row, Totals>(
  answers: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
  key: string,
): Answered<Row> | undefined {
  const answered = answers.rows.get(key);
  if (answered !== undefined) {
    return answered;
  }
  const row = read(answers, rowKey, key);
  return row === undefined ? undefined : { value: row, order: Number.NEGATIVE_INFINITY };
}

/**
 * The row of a key as the answers show it: whole as the latest answer gave it, each part answered
 * after it laid over it in turn; none for a row the reading does not show.
 */
export function shownRow<Row, Totals>(
  answers: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
  key: string,
): Row | undefined {
  const base = whole(answers, rowKey, key);
  if (base === undefined) {
    return undefined;
  }
  let row = base.value;
  for (const part of answers.parts.get(key) ?? []) {
    if (part.order > base.order) {
      row = part.value(row);
    }
  }
  return row;
}

/** Every row the answers changed, by its key, as they show it. */
export function shownRows<Row, Totals>(
  answers: Answers<Row, Totals>,
  rowKey: (row: Row) => string,
): Map<string, Row> {
  const shown = new Map<string, Row>();
  for (const key of new Set([...answers.rows.keys(), ...answers.parts.keys()])) {
    const row = shownRow(answers, rowKey, key);
    if (row !== undefined) {
      shown.set(key, row);
    }
  }
  return shown;
}

/**
 * Take what a write answered among the answers of its reading: each row written and each row it
 * gave whole, unless a later write answered it whole — the parts of that row it covers let go —;
 * each part of a row, kept aside among the others in the order of its answer, only when it is
 * later than the row whole taken and changes the row shown; the totals, unless later ones were.
 */
export function take<Row, Totals>(
  answers: Answers<Row, Totals>,
  written: RowsWritten<Row, Totals>,
  rowKey: (row: Row) => string,
): void {
  const { order } = written;
  answers.latest = Math.max(answers.latest, order);
  for (const row of [...written.rows, ...written.changed]) {
    const key = rowKey(row);
    if (later(order, answers.rows.get(key))) {
      answers.rows.set(key, { value: row, order });
      prune(answers, key, order);
    }
  }
  for (const { key, change } of written.parts) {
    // A part no later than the row whole already taken is covered: never shown, never kept.
    const base = answers.rows.get(key);
    if (base !== undefined && base.order >= order) {
      continue;
    }
    const shown = shownRow(answers, rowKey, key);
    if (shown !== undefined && change(shown) !== shown) {
      const parts = answers.parts.get(key) ?? [];
      const at = parts.findIndex((part) => part.order > order);
      const part = { value: change, order };
      answers.parts.set(
        key,
        at < 0 ? [...parts, part] : [...parts.slice(0, at), part, ...parts.slice(at)],
      );
    }
  }
  if (written.totals !== undefined && later(order, answers.totals)) {
    answers.totals = { value: written.totals, order };
  }
}

/** Let go of the parts of a row that a row answered whole at a place covers: those not later. */
function prune<Row, Totals>(answers: Answers<Row, Totals>, key: string, order: number): void {
  const parts = answers.parts.get(key);
  if (parts === undefined) {
    return;
  }
  const kept = parts.filter((part) => part.order > order);
  if (kept.length === 0) {
    answers.parts.delete(key);
  } else if (kept.length !== parts.length) {
    answers.parts.set(key, kept);
  }
}

/**
 * Take the totals of the reading read anew, once the writes answered: those of the latest answer
 * taken, unless a write answered later ones.
 */
export function retotalled<Row, Totals>(answers: Answers<Row, Totals>, totals: Totals): void {
  if (later(answers.latest, answers.totals)) {
    answers.totals = { value: totals, order: answers.latest };
  }
}
