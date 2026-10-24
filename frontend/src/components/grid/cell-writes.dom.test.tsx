// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, renderHook } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { Outcome, Problem } from "@/api/problem";
import type { components } from "@/api/generated/schema";
import {
  type HourlyRate,
  rateWritten,
  type RateRow,
  withYears,
} from "@/components/reference/rate-cells";
import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type CellReading, type CellRules, type CellWrites, useCellWrites } from "./cell-writes";
import type { CellEntry, RowsWritten } from "./columns";
import { ESTIMATE_FIELDS, type EstimateNode } from "./estimate";
import { type NodeList, nodeFresher, nodeKey, type NodeTotals, projectNodes } from "./nodes";

// The grid of the rates of the volumes, and the rates the server answers for the mechanical
// engineering (MO-003): the first of 2015, which it has none of yet — the cell of the path of
// L43a —, and a correction of 2016, read at 86,98.
const volume = example("volume/hourly_rate_grid") as {
  years: number[];
  rows: components["schemas"]["HourlyRateRow"][];
};
const grid = {
  years: volume.years,
  rows: withYears(
    volume.rows,
    volume.years.map((year, index) => ({ year, index })),
  ),
};
const entered = example("hourly_rate_entered") as HourlyRate;
const corrected = example("hourly_rate_corrected") as HourlyRate;
const Y2015 = grid.years.indexOf(entered.year);
const Y2016 = grid.years.indexOf(corrected.year);
const MECHANICAL = grid.rows.findIndex((row) => row.cost_category_id === entered.cost_category_id);
const ADDRESS = "/reference/costs?";
const NATURES_SORTED = "/reference/costs?type_sort_by=label&type_sort_order=asc";
const SORTED = "/reference/costs?sort_by=code&sort_order=desc";
const RATES: CellRules<RateRow, null> = { rowKey: (row) => row.cost_category_id };

// The estimate of the witness, its line of labour « Raccordement des borniers » and its totals.
const estimate = example("nodes_estimate") as NodeList;
const nodes = projectNodes(estimate, ESTIMATE_FIELDS);
const LABOUR = nodes.items.findIndex(
  (node) => node.estimate_line?.label === "Raccordement des borniers",
);
const NODES: CellRules<EstimateNode, NodeTotals> = { rowKey: nodeKey, fresher: nodeFresher };
const TASK = nodes.items.findIndex((node) => node.task?.label === "Câblage des armoires");

/** In French. */
function French({ children }: { readonly children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {children}
    </NextIntlClientProvider>
  );
}

/** Every promise under way settled. */
function settled(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/** A write whose answers wait until each is let go, from the row each write left from. */
function held<Row, Totals>() {
  const asked: { from: Row; answer: (outcome: Outcome<RowsWritten<Row, Totals>>) => void }[] = [];
  const entry: CellEntry<Row, Totals> = {
    kind: { type: "decimal", nullable: false },
    in: () => true,
    value: () => undefined,
    write: (from) =>
      new Promise((resolve) => {
        asked.push({ from, answer: resolve });
      }),
  };
  /** Let the server answer the write of a rank, as the grid reads its answer to the row written. */
  const answer = async (rank: number, written: (from: Row) => RowsWritten<Row, Totals>) => {
    const call = asked[rank];
    if (call === undefined) {
      throw new Error(`no write ${rank.toString()} left`);
    }
    await act(async () => {
      call.answer({ kind: "done", data: written(call.from) });
      await settled();
    });
  };
  /** Let the server refuse the write of a rank. */
  const refuse = async (rank: number, refusal: Outcome<never>) => {
    await act(async () => {
      asked[rank]?.answer(refusal);
      await settled();
    });
  };
  /** The row the write of a rank left from. */
  const from = (rank: number): Row | undefined => asked[rank]?.from;
  return { entry, answer, refuse, from };
}

/** The cells written of a grid, on a first reading of its address, each write told `writing`. */
function writes<Row, Totals>(
  rules: CellRules<Row, Totals>,
  first: CellReading<Row, Totals>,
  writing?: (write: Promise<unknown>) => void,
) {
  // In French, as the grid tells the refusals it keeps quiet to the history of the messages.
  return renderHook(
    (reading: CellReading<Row, Totals>) => useCellWrites<Row, Totals>(reading, rules, writing),
    { initialProps: first, wrapper: French },
  );
}

/** Write a cell of a row, as the grid writes a cell validated, and let the write leave. */
async function enter<Row, Totals>(
  writer: CellWrites<Row, Totals>,
  at: number,
  column: string,
  entry: CellEntry<Row, Totals>,
  value = "1",
) {
  const row = writer.rows[at];
  if (row === undefined) {
    throw new Error(`no row ${at.toString()}`);
  }
  await act(async () => {
    writer.write({ row, column, entry, value, shown: value });
    await settled();
  });
}

/** The rates of 2015 and 2016 of the mechanical engineering, as the rows given show them. */
function mechanical(rows: readonly RateRow[]): (string | undefined)[] {
  const row = rows[MECHANICAL];
  return [row?.cells[Y2015]?.amount, row?.cells[Y2016]?.amount];
}

/** The rows of the grid read anew: other objects, the same values but the rates given. */
function ratesAnew(...rates: readonly HourlyRate[]): RateRow[] {
  const rows = structuredClone(grid.rows);
  const row = rows[MECHANICAL];
  if (row !== undefined) {
    rows[MECHANICAL] = {
      ...row,
      cells: row.cells.map(
        (cell, at) => rates.find((rate) => grid.years[at] === rate.year) ?? cell,
      ),
    };
  }
  return rows;
}

/** The place of each answer among the writes, as the grid of the rates counts them. */
let answers = 0;

/** The rate answered for a cell of the mechanical engineering, as the grid of the rates takes it. */
function rate(answered: HourlyRate) {
  return (from: RateRow) => {
    answers += 1;
    return rateWritten(from, answered.year, answered, answers);
  };
}

describe("the rates written while the page is read anew", () => {
  const first = { address: ADDRESS, rows: grid.rows, totals: null };

  it("keeps the answer of a write when the page is read anew at its address before the server answers", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    // `refresh` after a creation elsewhere on the screen: the same address, its rows read anew.
    rerender({ address: ADDRESS, rows: ratesAnew(), totals: null });
    expect(result.current.pending(entered.cost_category_id, "year_2015")).toBe("1");
    await answer(0, rate(entered));
    expect(mechanical(result.current.rows)).toEqual(["85.48", "86.98"]);
    expect(result.current.pending(entered.cost_category_id, "year_2015")).toBeUndefined();
    expect(result.current.outcome?.kind).toBe("done");
    // Read anew once more, alike: the answer stays, the rate being newer than the cell read.
    rerender({ address: ADDRESS, rows: ratesAnew(), totals: null });
    expect(mechanical(result.current.rows)).toEqual(["85.48", "86.98"]);
  });

  it("keeps a refusal told when the page is read anew at its address", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, refuse } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await refuse(0, {
      kind: "refused",
      problem: { code: "STALE_LOCK_VERSION", status: 412 },
      conflictingObjectId: null,
    });
    rerender({ address: ADDRESS, rows: ratesAnew(), totals: null });
    expect(result.current.outcome).toMatchObject({ problem: { code: "STALE_LOCK_VERSION" } });
  });

  it("marks the cell refused until it is written, another cell written leaving it marked, the notice told", async () => {
    const { result } = writes(RATES, first);
    const { entry, answer, refuse } = held<RateRow, null>();
    const key = entered.cost_category_id;
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await refuse(0, {
      kind: "refused",
      problem: { code: "VALUE_OUT_OF_RANGE", status: 422 },
      conflictingObjectId: null,
    });
    expect(result.current.refused(key, "year_2015")).toBe(true);
    await enter(result.current, MECHANICAL, "year_2016", entry);
    await answer(1, rate(corrected));
    expect(result.current.refused(key, "year_2015")).toBe(true);
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await answer(2, rate(entered));
    expect(result.current.refused(key, "year_2015")).toBe(false);
    expect(result.current.outcome).toMatchObject({ problem: { code: "VALUE_OUT_OF_RANGE" } });
  });

  it("keeps the rate of 2015 and takes that of 2016 when a reading anew between the two carries the first alone", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await answer(0, rate(entered));
    await enter(result.current, MECHANICAL, "year_2016", entry);
    // A reading anew between the two answers — a deactivation pressed meanwhile —: it carries the
    // rate of 2015, written, and 2016 as it was.
    rerender({ address: ADDRESS, rows: ratesAnew(entered), totals: null });
    expect(mechanical(result.current.rows)).toEqual(["85.48", "86.98"]);
    await answer(1, rate(corrected));
    expect(mechanical(result.current.rows)).toEqual(["85.48", "87.20"]);
    // The next correction of 2016 leaves from the version the server answered.
    await enter(result.current, MECHANICAL, "year_2016", entry);
    expect(result.current.rows[MECHANICAL]?.cells[Y2016]?.lock_version).toBe(
      corrected.lock_version,
    );
  });

  it("shows the rate of a reading anew that caught up since, newer than the answer", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    const since = { ...entered, amount: "90.00", lock_version: entered.lock_version + 1 };
    rerender({ address: ADDRESS, rows: ratesAnew(since), totals: null });
    await answer(0, rate(entered));
    expect(mechanical(result.current.rows)).toEqual(["90.00", "86.98"]);
  });

  it("lets an answer kept give way to a reading anew newer than it", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await answer(0, rate(entered));
    const since = { ...entered, amount: "86.00", lock_version: entered.lock_version + 1 };
    rerender({ address: ADDRESS, rows: ratesAnew(since), totals: null });
    expect(mechanical(result.current.rows)).toEqual(["86.00", "86.98"]);
  });

  it("keeps the rates of 2015 and 2016, both answered, when a reading anew carries the first alone", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    await answer(0, rate(entered));
    await enter(result.current, MECHANICAL, "year_2016", entry);
    await answer(1, rate(corrected));
    rerender({ address: ADDRESS, rows: ratesAnew(entered), totals: null });
    expect(mechanical(result.current.rows)).toEqual(["85.48", "87.20"]);
  });

  it("writes the next rate of a cell from the version a reading anew brought, a third party's", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, from } = held<RateRow, null>();
    const theirs = { ...corrected, amount: "88.88", lock_version: 4 };
    rerender({ address: ADDRESS, rows: ratesAnew(theirs), totals: null });
    await enter(result.current, MECHANICAL, "year_2016", entry);
    expect(from(0)?.cells[Y2016]?.lock_version).toBe(4);
  });

  it("finds the cell of a rate pending by its year when a reading anew holds a year more before it", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    // A rate of 2011 written meanwhile: a column more at the head, every cell one place further.
    const years = [2011, ...grid.years];
    const shifted = withYears(
      structuredClone(volume.rows).map((row) => ({ ...row, cells: [null, ...row.cells] })),
      years.map((year, index) => ({ year, index })),
    );
    rerender({ address: ADDRESS, rows: shifted, totals: null });
    await answer(0, rate(entered));
    const row = result.current.rows[MECHANICAL];
    expect(row?.cells[Y2015 + 1]?.amount).toBe("85.48");
    expect(row?.cells[Y2015]).toBeNull();
  });

  it("keeps the cell pending, then answered, when another list of the screen is sorted meanwhile", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    // The natures sorted: another address, the same rows of the grid of the rates.
    rerender({ address: NATURES_SORTED, rows: ratesAnew(), totals: null });
    expect(result.current.pending(entered.cost_category_id, "year_2015")).toBe("1");
    await answer(0, rate(entered));
    expect(mechanical(result.current.rows)).toEqual(["85.48", "86.98"]);
  });

  it("drops the answer of a write when the grid is read at another address before the server answers", async () => {
    const { result, rerender } = writes(RATES, first);
    const { entry, answer } = held<RateRow, null>();
    await enter(result.current, MECHANICAL, "year_2015", entry);
    // The grid sorted otherwise: another address, its rows in another order.
    const sorted = ratesAnew().toReversed();
    rerender({ address: SORTED, rows: sorted, totals: null });
    expect(result.current.pending(entered.cost_category_id, "year_2015")).toBeUndefined();
    await answer(0, rate(entered));
    const row = result.current.rows.find(
      (each) => each.cost_category_id === entered.cost_category_id,
    );
    expect(row?.cells[Y2015]).toBeNull();
    expect(result.current.outcome).toBeUndefined();
  });
});

/** A node answered: the row written with its version moved on and the values of its line. */
function nodeAnswered(
  from: EstimateNode,
  line: Partial<NonNullable<EstimateNode["estimate_line"]>>,
  totals: NodeTotals | undefined,
  order: number,
): RowsWritten<EstimateNode, NodeTotals> {
  const { estimate_line: read } = from;
  if (read === null || read === undefined) {
    throw new Error("the node written is a line");
  }
  const row: EstimateNode = {
    ...from,
    lock_version: from.lock_version + 1,
    estimate_line: { ...read, ...line },
  };
  return { rows: [row], changed: [], parts: [], totals, order };
}

describe("the nodes written while the page is read anew", () => {
  const first = { address: ADDRESS, rows: nodes.items, totals: nodes.totals };

  /** The rows of the estimate read anew, the line of labour as given. */
  function nodesAnew(labour?: EstimateNode): EstimateNode[] {
    const rows = structuredClone(nodes.items) as EstimateNode[];
    if (labour !== undefined) {
      rows[LABOUR] = labour;
    }
    return rows;
  }

  it("takes the answer of a second cell of a row when a reading anew carries the first, by the version of the node", async () => {
    const { result, rerender } = writes(NODES, first);
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    await enter(result.current, LABOUR, "hours", entry);
    await answer(0, (from) => nodeAnswered(from, { hours: "14" }, undefined, 1));
    const hours = result.current.rows[LABOUR];
    await enter(result.current, LABOUR, "quantity", entry);
    // A reading anew between the two answers: it carries the hours, not the quantity.
    rerender({ address: ADDRESS, rows: nodesAnew(hours), totals: nodes.totals });
    await answer(1, (from) => nodeAnswered(from, { quantity: "3" }, undefined, 2));
    const labour = result.current.rows[LABOUR];
    expect(labour?.estimate_line?.hours).toBe("14");
    expect(labour?.estimate_line?.quantity).toBe("3");
    expect(labour?.lock_version).toBe((nodes.items[LABOUR]?.lock_version ?? 0) + 2);
  });

  it("keeps whole the answer newer than a reading anew: the summary it recalculated and its totals with the row written", async () => {
    const { result, rerender } = writes(NODES, first);
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    const task = nodes.items[TASK];
    if (task?.task === null || task?.task === undefined) {
      throw new Error("the estimate holds the cabling");
    }
    const { task: facet } = task;
    const summed = (amount: string): EstimateNode => ({
      ...task,
      task: { ...facet, base_amount: amount },
    });
    const totalled = (hours: string) => ({ ...nodes.totals, hours });
    await enter(result.current, LABOUR, "hours", entry);
    await answer(0, (from) => ({
      ...nodeAnswered(from, { hours: "14" }, totalled("14"), 1),
      changed: [summed("3000.00")],
    }));
    const firstAnswered = result.current.rows[LABOUR];
    await enter(result.current, LABOUR, "quantity", entry);
    await answer(1, (from) => ({
      ...nodeAnswered(from, { quantity: "3" }, totalled("15"), 2),
      changed: [summed("3500.00")],
    }));
    // A reading anew rendered between the two answers: the state of the first.
    const rows = nodesAnew(firstAnswered);
    rows[TASK] = summed("3000.00");
    rerender({ address: ADDRESS, rows, totals: totalled("14") });
    expect(result.current.rows[TASK]?.task?.base_amount).toBe("3500.00");
    expect(result.current.totals?.hours).toBe("15");
    expect(result.current.rows[LABOUR]?.estimate_line?.quantity).toBe("3");
  });

  it("writes the next cell of a node from the version a reading anew brought", async () => {
    const { result, rerender } = writes(NODES, first);
    const { entry, from } = held<EstimateNode, NodeTotals>();
    const labour = nodes.items[LABOUR];
    const version = (labour?.lock_version ?? 0) + 4;
    rerender({
      address: ADDRESS,
      rows: nodesAnew(labour === undefined ? undefined : { ...labour, lock_version: version }),
      totals: nodes.totals,
    });
    await enter(result.current, LABOUR, "hours", entry);
    expect(from(0)?.lock_version).toBe(version);
  });

  it("shows a node read anew at a later version before the answer of an earlier one", async () => {
    const { result, rerender } = writes(NODES, first);
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    await enter(result.current, LABOUR, "hours", entry);
    const labour = nodes.items[LABOUR];
    if (labour?.estimate_line === null || labour?.estimate_line === undefined) {
      throw new Error("the estimate holds the line of labour");
    }
    const theirs: EstimateNode = {
      ...labour,
      lock_version: labour.lock_version + 4,
      estimate_line: { ...labour.estimate_line, hours: "40" },
    };
    rerender({ address: ADDRESS, rows: nodesAnew(theirs), totals: nodes.totals });
    await answer(0, (from) => nodeAnswered(from, { hours: "14" }, undefined, 1));
    expect(result.current.rows[LABOUR]?.estimate_line?.hours).toBe("40");
  });

  it("keeps the totals answered, where the version of the node says nothing, while the totals read anew are those read before, and lets them go otherwise", async () => {
    const { result, rerender } = writes(NODES, first);
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    const answered = { ...nodes.totals, hours: "14" };
    await enter(result.current, LABOUR, "hours", entry);
    await answer(0, (from) => nodeAnswered(from, { hours: "14" }, answered, 1));
    expect(result.current.totals).toEqual(answered);
    // The line read anew at the version answered: its counter says nothing of the answer.
    const caughtUp = result.current.rows[LABOUR];
    rerender({
      address: ADDRESS,
      rows: nodesAnew(caughtUp),
      totals: structuredClone(nodes.totals),
    });
    expect(result.current.totals).toEqual(answered);
    rerender({
      address: ADDRESS,
      rows: nodesAnew(caughtUp),
      totals: { ...nodes.totals, hours: "15" },
    });
    expect(result.current.totals).toBeUndefined();
  });
});

describe("the outcome of a cell written, in any grid", () => {
  const first = { address: ADDRESS, rows: nodes.items, totals: nodes.totals };
  const refusedDate = example("task_date_computed_refused") as Problem;
  const keyOf = (at: number) => nodeKey(nodes.items[at] as EstimateNode);

  it("tells a refusal by field by the reason of its field, and marks the cell (#817.1)", async () => {
    const { result } = writes(NODES, first);
    const { entry, refuse } = held<EstimateNode, NodeTotals>();
    await enter(result.current, TASK, "finish", entry);
    await refuse(0, { kind: "refused", problem: refusedDate, conflictingObjectId: null });
    expect(result.current.outcome).toMatchObject({
      problem: { code: "COMPUTED_VALUE", fields: [{ pointer: "/finish" }] },
    });
    expect(result.current.refused(keyOf(TASK), "finish")).toBe(true);
  });

  it.each([
    {
      failure: "a version gone stale",
      outcome: {
        kind: "stale",
        problem: { code: "STALE_LOCK_VERSION", status: 412 },
        conflictingObjectId: null,
      },
    },
    {
      failure: "a state that forbids the write",
      outcome: {
        kind: "conflict",
        problem: { code: "STATE_FORBIDS_OPERATION", status: 409 },
        conflictingObjectId: null,
      },
    },
    { failure: "the API out of reach", outcome: { kind: "unreachable" } },
  ] as const)(
    "tells $failure without marking the cell, which says nothing of the value (#819.2)",
    async ({ outcome }) => {
      const { result } = writes(NODES, first);
      const { entry, refuse } = held<EstimateNode, NodeTotals>();
      await enter(result.current, LABOUR, "hours", entry);
      await refuse(0, outcome);
      expect(result.current.outcome).toEqual(outcome);
      expect(result.current.refused(keyOf(LABOUR), "hours")).toBe(false);
    },
  );

  it("writes nothing of a value the row answered already holds, which would carry its version alone (#819.8)", async () => {
    const { result } = writes(NODES, first);
    const { entry, answer, from } = held<EstimateNode, NodeTotals>();
    const hours: CellEntry<EstimateNode, NodeTotals> = {
      ...entry,
      value: (row) => row.estimate_line?.hours,
    };
    // The same value validated twice before the first answered: the second, written from the row
    // answered, finds it there.
    await enter(result.current, LABOUR, "hours", hours, "14");
    await enter(result.current, LABOUR, "hours", hours, "14");
    await answer(0, (row) => nodeAnswered(row, { hours: "14" }, undefined, 1));
    expect(from(1)).toBeUndefined();
    expect(result.current.pending(keyOf(LABOUR), "hours")).toBeUndefined();
    expect(result.current.rows[LABOUR]?.estimate_line?.hours).toBe("14");
  });

  it("tells the screen each write, under way until it answered (#1224)", async () => {
    const told: Promise<unknown>[] = [];
    const { result } = writes(NODES, first, (write) => {
      told.push(write);
    });
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    await enter(result.current, LABOUR, "hours", entry);
    let over = false;
    void told[0]?.then(() => {
      over = true;
    });
    await act(async () => {
      await settled();
    });
    expect(told).toHaveLength(1);
    expect(over).toBe(false);
    await answer(0, (row) => nodeAnswered(row, { hours: "1" }, undefined, 1));
    expect(over).toBe(true);
  });

  it("lifts the refusal of a cell typed anew as the row holds it, writing nothing (#819.8)", async () => {
    const { result } = writes(NODES, first);
    const { entry, refuse, from } = held<EstimateNode, NodeTotals>();
    const hours: CellEntry<EstimateNode, NodeTotals> = {
      ...entry,
      value: (row) => row.estimate_line?.hours,
    };
    await enter(result.current, LABOUR, "hours", hours, "13");
    await refuse(0, { kind: "refused", problem: refusedDate, conflictingObjectId: null });
    expect(result.current.refused(keyOf(LABOUR), "hours")).toBe(true);
    // « 12,50 » typed for the 12.5 the row holds: the entry validates the decimal the row writes.
    await enter(result.current, LABOUR, "hours", hours, "12.5");
    expect(from(1)).toBeUndefined();
    expect(result.current.refused(keyOf(LABOUR), "hours")).toBe(false);
    expect(result.current.outcome).toBeUndefined();
  });
});

describe("the rows written together while a cell of theirs is under way", () => {
  // Rows written together — a choice of the menu of a cell, a paste — taking the place of the line
  // of labour while a cell of it, written before them, has not answered yet: the gestures and the
  // confirmation of a paste wait for a cell under way (#1224), but a cell may leave while a gesture
  // is under way, and answer after it.
  const first = { address: ADDRESS, rows: nodes.items, totals: nodes.totals };
  const keyOf = (at: number) => nodeKey(nodes.items[at] as EstimateNode);

  /** The cabling, the summary of the line of labour, as an answer recalculated it. */
  function summed(amount: string): EstimateNode {
    const task = nodes.items[TASK];
    if (task?.task === null || task?.task === undefined) {
      throw new Error("the estimate holds the cabling");
    }
    return { ...task, task: { ...task.task, base_amount: amount } };
  }

  /**
   * The line of labour written together with others, at a later place among the writes: its
   * summary and the totals recalculated with it.
   */
  function together(): RowsWritten<EstimateNode, NodeTotals> {
    const labour = nodes.items[LABOUR] as EstimateNode;
    return {
      ...nodeAnswered(
        { ...labour, lock_version: labour.lock_version + 1 },
        { hours: "40" },
        { ...nodes.totals, hours: "38.5" },
        4,
      ),
      changed: [summed("4000.00")],
    };
  }

  it("keeps what the rows written together answered when the cell written before them answers after them, earlier: their rows, the summary above them, the totals (#421)", async () => {
    const { result } = writes(NODES, first);
    const { entry, answer } = held<EstimateNode, NodeTotals>();
    await enter(result.current, LABOUR, "hours", entry, "14");
    act(() => {
      result.current.applied(together());
    });
    // The cell answers after them, earlier in the structure, with its own summary and totals: it
    // takes back none of theirs.
    await answer(0, (from) => ({
      ...nodeAnswered(from, { hours: "14" }, { ...nodes.totals, hours: "12.5" }, 3),
      changed: [summed("3000.00")],
    }));
    expect(result.current.rows[LABOUR]?.estimate_line?.hours).toBe("40");
    expect(result.current.rows[TASK]?.task?.base_amount).toBe("4000.00");
    expect(result.current.totals?.hours).toBe("38.5");
    expect(result.current.pending(keyOf(LABOUR), "hours")).toBeUndefined();
  });

  it("keeps quiet the refusal of a cell written before rows written together took its row (#202)", async () => {
    const { result } = writes(NODES, first);
    const { entry, refuse } = held<EstimateNode, NodeTotals>();
    await enter(result.current, LABOUR, "hours", entry, "14");
    act(() => {
      result.current.applied(together());
    });
    await refuse(0, {
      kind: "stale",
      problem: { code: "STALE_LOCK_VERSION", status: 412 },
      conflictingObjectId: null,
    });
    expect(result.current.outcome).toBeUndefined();
    expect(result.current.refused(keyOf(LABOUR), "hours")).toBe(false);
    expect(result.current.rows[LABOUR]?.estimate_line?.hours).toBe("40");
  });

  it("tells the refusal of a row they did not write, whatever the quiet refusal answered after it (#202)", async () => {
    const { result } = writes(NODES, first);
    const { entry, refuse } = held<EstimateNode, NodeTotals>();
    const marked: Outcome<never> = {
      kind: "conflict",
      problem: { code: "REVISION_MARKED", status: 409 },
      conflictingObjectId: null,
    };
    await enter(result.current, TASK, "label", entry);
    await enter(result.current, LABOUR, "hours", entry, "14");
    act(() => {
      result.current.applied(together());
    });
    await refuse(0, marked);
    await refuse(1, {
      kind: "stale",
      problem: { code: "STALE_LOCK_VERSION", status: 412 },
      conflictingObjectId: null,
    });
    expect(result.current.outcome).toEqual(marked);
  });

  it("keeps the refusal of a cell written before them on a row they did not write", async () => {
    const { result } = writes(NODES, first);
    const { entry, refuse } = held<EstimateNode, NodeTotals>();
    const stale: Outcome<never> = {
      kind: "stale",
      problem: { code: "STALE_LOCK_VERSION", status: 412 },
      conflictingObjectId: null,
    };
    await enter(result.current, TASK, "label", entry);
    act(() => {
      result.current.applied(together());
    });
    await refuse(0, stale);
    expect(result.current.outcome).toEqual(stale);
    expect(result.current.rows[LABOUR]?.estimate_line?.hours).toBe("40");
  });
});
