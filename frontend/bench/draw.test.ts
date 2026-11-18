// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { type Gesture, generator, gestures, PAUSE, READS_PER_WRITE } from "./draw";

const CHOICES = { reads: 7, writes: 2 };

/** The first gestures of a user. */
function first(seed: number, user: number, count: number): Gesture[] {
  const next = gestures(seed, user, CHOICES);
  return Array.from({ length: count }, () => next());
}

describe("generator", () => {
  it("draws in [0, 1), the same numbers from the same seed", () => {
    const one = generator(42);
    const again = generator(42);
    const drawn = Array.from({ length: 1000 }, () => one());
    expect(drawn.every((value) => value >= 0 && value < 1)).toBe(true);
    expect(Array.from({ length: 1000 }, () => again())).toEqual(drawn);
    expect(new Set(drawn).size).toBeGreaterThan(990);
  });
});

describe("gestures", () => {
  it("makes nine readings for one entry in every run of ten gestures [WF-QUA-0060-A]", () => {
    const made = first(2300, 1, 1000);
    for (let run = 0; run < made.length; run += READS_PER_WRITE + 1) {
      const kinds = made.slice(run, run + READS_PER_WRITE + 1).map(({ kind }) => kind);
      expect(kinds.filter((kind) => kind === "write")).toHaveLength(1);
      expect(kinds.filter((kind) => kind === "read")).toHaveLength(READS_PER_WRITE);
    }
  });

  it("pauses between five and fifteen seconds, ten on average [WF-QUA-0060-A]", () => {
    const pauses = Array.from({ length: 50 }, (_, user) => first(2300, user + 1, 200))
      .flat()
      .map(({ pause }) => pause);
    expect(Math.min(...pauses)).toBeGreaterThanOrEqual(PAUSE.least);
    expect(Math.max(...pauses)).toBeLessThan(PAUSE.most);
    const mean = pauses.reduce((sum, pause) => sum + pause, 0) / pauses.length;
    expect(mean).toBeGreaterThan(9.8);
    expect(mean).toBeLessThan(10.2);
  });

  it("draws the same gestures again from the same seed and user, others for another user", () => {
    expect(first(2300, 7, 100)).toEqual(first(2300, 7, 100));
    expect(first(2300, 8, 100)).not.toEqual(first(2300, 7, 100));
    expect(first(2301, 7, 100)).not.toEqual(first(2300, 7, 100));
  });

  it("chooses among every reading and every entry", () => {
    const made = first(2300, 3, 2000);
    const chosen = (kind: Gesture["kind"]) =>
      new Set(made.filter((one) => one.kind === kind).map(({ choice }) => choice));
    expect([...chosen("read")].toSorted()).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect([...chosen("write")].toSorted()).toEqual([0, 1]);
  });

  it("does not put the entries of the users at the same place of their runs", () => {
    const places = Array.from({ length: 50 }, (_, user) =>
      first(2300, user + 1, 10).findIndex(({ kind }) => kind === "write"),
    );
    expect(new Set(places).size).toBeGreaterThan(5);
  });

  it("refuses a user with nothing to choose", () => {
    expect(() => gestures(1, 1, { reads: 0, writes: 1 })).toThrow(/one reading and one entry/);
  });
});
