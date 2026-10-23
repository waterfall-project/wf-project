// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { KEPT_LANES, keptLanes, type LaneSpan, movedBy, movedTo, stackLanes } from "./lanes";

/** A rectangle from a day to another, its finish excluded. */
function span(id: string, from: number, to: number): LaneSpan {
  return { id, from, to };
}

// In the order of the plan: A and B overlap, C overlaps neither, D overlaps B alone.
const SPANS = [span("A", 0, 10), span("B", 5, 15), span("C", 20, 30), span("D", 12, 18)];

/** The lanes as a plain object, to compare. */
function plain(lanes: ReadonlyMap<string, number>): Record<string, number> {
  return Object.fromEntries(lanes);
}

describe("the automatic stacking of the lanes", () => {
  it("puts each rectangle, in the order of the plan, in the first lane where it overlaps none", () => {
    expect(plain(stackLanes(SPANS, undefined))).toEqual({ A: 0, B: 1, C: 0, D: 0 });
  });

  it("takes two rectangles that only touch for neighbours in a lane", () => {
    expect(plain(stackLanes([span("A", 0, 10), span("B", 10, 20)], undefined))).toEqual({
      A: 0,
      B: 0,
    });
  });

  it("keeps a placed rectangle in its lane, and stacks the others around it", () => {
    // C placed in the second lane; A, B and D stacked automatically, B in the first free lane.
    expect(plain(stackLanes(SPANS, { C: 1 }))).toEqual({ A: 0, B: 1, C: 1, D: 0 });
    expect(plain(stackLanes(SPANS, { A: 1 }))).toEqual({ A: 1, B: 0, C: 0, D: 1 });
  });

  it("closes up the lanes left empty, and ignores a task no longer inscribed", () => {
    expect(plain(stackLanes(SPANS, { C: 7, gone: 3 }))).toEqual({ A: 0, B: 1, C: 2, D: 0 });
  });

  it("stacks again a placed rectangle that its dates make overlap another of its lane", () => {
    // A and B both placed in the first lane: B, later in the plan, no longer fits there.
    expect(plain(stackLanes(SPANS, { A: 0, B: 0 }))).toEqual({ A: 0, B: 1, C: 0, D: 0 });
  });
});

describe("a move to a lane, as the pointer drops it", () => {
  const lanes = stackLanes(SPANS, undefined);

  it("moves a rectangle into a lane where it fits, and nothing else", () => {
    expect(movedTo(SPANS, lanes, "C", 1)).toEqual({
      kind: "moved",
      lane: 1,
      lanes: new Map([
        ["A", 0],
        ["B", 1],
        ["C", 1],
        ["D", 0],
      ]),
    });
  });

  it("refuses a lane where the rectangle would overlap another, naming it", () => {
    expect(movedTo(SPANS, lanes, "D", 1)).toEqual({ kind: "overlap", lane: 1, with: "B" });
  });

  it("opens the empty lane below the last, and never one above the first", () => {
    const moved = movedTo(SPANS, lanes, "C", 9);
    expect(moved).toMatchObject({ kind: "moved", lane: 2 });
    expect(movedTo(SPANS, lanes, "B", -3)).toEqual({ kind: "overlap", lane: 0, with: "A" });
  });

  it("stays where it is dropped on its own lane, or alone below the last", () => {
    expect(movedTo(SPANS, lanes, "C", 0)).toEqual({ kind: "stayed" });
    expect(movedTo(SPANS, lanes, "B", 2)).toEqual({ kind: "stayed" });
  });
});

describe("a move up or down, as the keyboard makes it", () => {
  const lanes = stackLanes(SPANS, undefined);

  it("moves a rectangle to the nearest lane that way where it fits", () => {
    expect(movedBy(SPANS, lanes, "C", 1)).toMatchObject({ kind: "moved", lane: 1 });
    // A placed below B's lane: up, it passes the lane of B, which it overlaps, to the first.
    const below = stackLanes(SPANS, { B: 1, A: 2 });
    expect(plain(below)).toEqual({ A: 2, B: 1, C: 0, D: 0 });
    expect(movedBy(SPANS, below, "A", -1)).toMatchObject({ kind: "moved", lane: 0 });
  });

  it("refuses a move up where every lane above overlaps, naming the rectangle just above", () => {
    expect(movedBy(SPANS, lanes, "B", -1)).toEqual({ kind: "overlap", lane: 0, with: "A" });
  });

  it("refuses the top lane upward, and the last lane downward to a rectangle alone in it", () => {
    expect(movedBy(SPANS, lanes, "A", -1)).toEqual({ kind: "edge", edge: "top" });
    expect(movedBy(SPANS, lanes, "B", 1)).toEqual({ kind: "edge", edge: "bottom" });
  });

  it("opens a lane below the last to a rectangle that shares its lane", () => {
    // A and D overlap B in the second lane: each passes it, to the empty lane below.
    expect(movedBy(SPANS, lanes, "A", 1)).toMatchObject({ kind: "moved", lane: 2 });
    expect(movedBy(SPANS, lanes, "D", 1)).toMatchObject({ kind: "moved", lane: 2 });
  });
});

describe("the lanes a timeline keeps", () => {
  it("keeps the lane of every rectangle shown, so that a move moves nothing else", () => {
    const lanes = stackLanes(SPANS, { C: 1 });
    expect(keptLanes(SPANS, lanes, "C", undefined)).toEqual({ A: 0, B: 1, C: 1, D: 0 });
  });

  it("keeps the moved rectangle first, then those placed, within the bound of the contract", () => {
    const many = Array.from({ length: KEPT_LANES + 2 }, (_, at) =>
      span(`T${String(at)}`, at * 10, at * 10 + 5),
    );
    const lanes = stackLanes(many, { T65: 0 });
    const kept = keptLanes(many, lanes, "T64", { T65: 0 });
    expect(Object.keys(kept)).toHaveLength(KEPT_LANES);
    expect(Object.keys(kept).slice(0, 3)).toEqual(["T64", "T65", "T0"]);
  });
});
