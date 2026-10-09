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
 * The answers belong to the address they were written at (`reread`): a page read anew there —
 * `refresh` after a write elsewhere on the screen — keeps what was answered of a row while it is
 * newer than the row read anew, by the counter of the object written where the grid can tell
 * (`GridConfig.fresher`, `RowPart.versioned`); where it cannot, while the reading anew reads the row
 * as the one before did, the server having said nothing newer of it.
 *
 * Pure, and neither server nor client: the cells written keep one of these by address, and change
 * it in their callbacks alone — a render lays a copy over a reading anew (`copyAnswers`).
 */
import type { RowPart, RowsWritten } from "./columns";

/** A value an answer gave, and the place of that answer among the writes. */
interface Answered<T> {
  readonly value: T;
  readonly order: number;
}

/** A part of a row an answer gave, its place, and whether it judges by a counter. */
interface AnsweredPart<Row> extends Answered<RowPart<Row>["change"]> {
  readonly versioned: boolean;
}

/** Whether a row answered is newer than the same row read; `undefined` says nothing. */
export type Fresher<Row> = (answered: Row, read: Row) => boolean | undefined;

/** What the answers in a reading hold. */
export interface Answers<Row, Totals> {
  /** The reading the answers lie over: the last one read at their address. */
  reading: readonly Row[];
  /** The totals of that reading. */
  readTotals: Totals | undefined;
  /** The rows answered whole, by their key. */
  readonly rows: Map<string, Answered<Row>>;
  /** The rows each answer wrote, by its place among the writes, which judge it whole on a reading anew. */
  readonly writtenBy: Map<number, readonly Row[]>;
  /** The parts of a row answered alone, by the key of the row, in the order of their answers. */
  readonly parts: Map<string, readonly AnsweredPart<Row>[]>;
  totals: Answered<Totals> | undefined;
  /** The place of the latest answer taken. */
  latest: number;
  /** The rows of the reading by their key, made at the first answer that needs it. */
  index: ReadonlyMap<string, Row> | undefined;
}

/** No answer yet in a reading, and its totals. */
export function answersOf<Row, Totals>(
  reading: readonly Row[],
  readTotals?: Totals,
): Answers<Row, Totals> {
  return {
    reading,
    readTotals,
    rows: new Map(),
    writtenBy: new Map(),
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
export function readRow<Row, Totals>(
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
  const row = readRow(answers, rowKey, key);
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
  if (written.rows.length > 0) {
    answers.writtenBy.set(order, written.rows);
  }
  for (const row of [...written.rows, ...written.changed]) {
    const key = rowKey(row);
    if (later(order, answers.rows.get(key))) {
      answers.rows.set(key, { value: row, order });
      prune(answers, key, order);
    }
  }
  for (const { key, change, versioned = false } of written.parts) {
    // A part no later than the row whole already taken is covered: never shown, never kept.
    const base = answers.rows.get(key);
    if (base !== undefined && base.order >= order) {
      continue;
    }
    const shown = shownRow(answers, rowKey, key);
    if (shown !== undefined && change(shown) !== shown) {
      const parts = answers.parts.get(key) ?? [];
      const at = parts.findIndex((part) => part.order > order);
      const part = { value: change, order, versioned };
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

/**
 * Whether two values the API gave are alike: the same JSON, whatever objects hold it — a row read
 * anew is another object than the one read before, however alike.
 */
export function alike(a: unknown, b: unknown): boolean {
  if (a === b) {
    return true;
  }
  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) {
    return false;
  }
  if (Array.isArray(a) !== Array.isArray(b)) {
    return false;
  }
  const before = a as Readonly<Record<string, unknown>>;
  const after = b as Readonly<Record<string, unknown>>;
  const keys = Object.keys(before);
  return (
    keys.length === Object.keys(after).length &&
    keys.every((key) => Object.hasOwn(after, key) && alike(before[key], after[key]))
  );
}

/** A copy of some answers, which a change of the copy leaves alone. */
export function copyAnswers<Row, Totals>(answers: Answers<Row, Totals>): Answers<Row, Totals> {
  return {
    ...answers,
    rows: new Map(answers.rows),
    writtenBy: new Map(answers.writtenBy),
    parts: new Map(answers.parts),
  };
}

/**
 * What a reading anew says of each answer, by its place among the writes, judged by the rows it
 * wrote: `false` once one of them reads anew at least as new — the reading caught up with it —,
 * `true` while one is newer by its counter, `undefined` when the counters say nothing.
 */
type Verdicts = ReadonlyMap<number, boolean | undefined>;

/** Judge each answer by the rows it wrote against those read anew. */
function verdictsOf<Row, Totals>(
  answers: Answers<Row, Totals>,
  now: ReadonlyMap<string, Row>,
  rowKey: (row: Row) => string,
  fresher: Fresher<Row> | undefined,
): Verdicts {
  const verdicts = new Map<number, boolean | undefined>();
  for (const [order, rows] of answers.writtenBy) {
    const said = rows.map((row) => {
      const read = now.get(rowKey(row));
      return read === undefined ? undefined : fresher?.(row, read);
    });
    verdicts.set(order, said.includes(false) ? false : said.includes(true) ? true : undefined);
  }
  return verdicts;
}

/**
 * Lay what was answered of the row of a key over that row read anew — none, and let it go: each
 * value as the answer that gave it is judged, by the counter of what it wrote, and by the row
 * itself where that says nothing.
 */
function rereadRow<Row, Totals>(
  answers: Answers<Row, Totals>,
  key: string,
  read: Row | undefined,
  { rowKey, fresher, verdicts }: Judge<Row>,
): void {
  const whole = answers.rows.get(key);
  const parts = answers.parts.get(key) ?? [];
  if (read === undefined) {
    answers.rows.delete(key);
    answers.parts.delete(key);
    return;
  }
  const unchanged = alike(readRow(answers, rowKey, key), read);
  const keepWhole =
    whole !== undefined && (verdicts.get(whole.order) ?? fresher?.(whole.value, read) ?? unchanged);
  if (whole !== undefined && !keepWhole) {
    answers.rows.delete(key);
  }
  const kept = parts.filter((part) =>
    part.versioned
      ? part.value(read) !== read
      : (verdicts.get(part.order) ?? (whole === undefined ? unchanged : keepWhole)),
  );
  if (kept.length === 0) {
    answers.parts.delete(key);
  } else if (kept.length !== parts.length) {
    answers.parts.set(key, kept);
  }
}

/** How the values answered are judged against a reading anew. */
interface Judge<Row> {
  readonly rowKey: (row: Row) => string;
  readonly fresher: Fresher<Row> | undefined;
  readonly verdicts: Verdicts;
}

/** Let go of the rows written by answers no value of which is kept any longer. */
function forget<Row, Totals>(answers: Answers<Row, Totals>): void {
  const kept = new Set<number>([
    ...[...answers.rows.values()].map(({ order }) => order),
    ...[...answers.parts.values()].flatMap((parts) => parts.map(({ order }) => order)),
    ...(answers.totals === undefined ? [] : [answers.totals.order]),
  ]);
  for (const order of answers.writtenBy.keys()) {
    if (!kept.has(order)) {
      answers.writtenBy.delete(order);
    }
  }
}

/**
 * Lay the answers over a reading anew of their address, each answer judged whole: the rows it wrote
 * against those read anew, by their counter (`fresher`) — an answer newer than the reading keeps
 * all it gave, the rows it changed besides those it wrote, the summaries above them, and its totals,
 * whatever they read anew; one the reading caught up with gives way to it all. Where the counters say
 * nothing, each value stays while the reading anew reads its row — or its totals — as the reading
 * before did, the server having said nothing newer of it: a write answered before the reading
 * caught up, or the fake back, which keeps nothing. A part that judges by its own counter stays while
 * it changes the row read anew. A row the reading anew no longer holds is let go. A later answer
 * still prevails over an earlier one for the same row, as when they were taken.
 */
export function reread<Row, Totals>(
  answers: Answers<Row, Totals>,
  reading: readonly Row[],
  readTotals: Totals | undefined,
  rowKey: (row: Row) => string,
  fresher?: Fresher<Row>,
): void {
  if (answers.reading === reading) {
    return;
  }
  const now = new Map(reading.map((row) => [rowKey(row), row]));
  const judge = { rowKey, fresher, verdicts: verdictsOf(answers, now, rowKey, fresher) };
  for (const key of new Set([...answers.rows.keys(), ...answers.parts.keys()])) {
    rereadRow(answers, key, now.get(key), judge);
  }
  const { totals } = answers;
  if (
    totals !== undefined &&
    !(judge.verdicts.get(totals.order) ?? alike(answers.readTotals, readTotals))
  ) {
    answers.totals = undefined;
  }
  forget(answers);
  answers.reading = reading;
  answers.readTotals = readTotals;
  answers.index = now;
}
