// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { holdNavigation, writesApplied, writesUnderWay } from "./held-writes";

/** A write under way, and the way to answer it. */
function underWay(): { write: Promise<boolean>; answer: (applied: boolean) => void } {
  let answer: (applied: boolean) => void = () => undefined;
  const write = new Promise<boolean>((resolve) => {
    answer = resolve;
  });
  return { write, answer };
}

describe("the writes a navigation waits for (#688)", () => {
  it("are none at first, and all applied", async () => {
    expect(writesUnderWay()).toBe(false);
    expect(await writesApplied()).toBe(true);
  });

  it("are all waited for, those started meanwhile included, one refused enough to hold the navigation", async () => {
    const first = underWay();
    holdNavigation(first.write);
    expect(writesUnderWay()).toBe(true);
    const waited = writesApplied();
    const second = underWay();
    holdNavigation(second.write);
    first.answer(true);
    await Promise.resolve();
    second.answer(false);
    expect(await waited).toBe(false);
    expect(writesUnderWay()).toBe(false);
  });

  it("take a write that failed without an outcome for one not applied", async () => {
    holdNavigation(Promise.reject(new Error("the server of Next out of reach")));
    expect(await writesApplied()).toBe(false);
    expect(writesUnderWay()).toBe(false);
  });
});
