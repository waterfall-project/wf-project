// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it } from "vitest";

import { gestureBegun, heldClick, holdNavigation } from "./held-writes";

/** A write under way, and the way to answer it. */
function underWay(): { write: Promise<boolean>; answer: (applied: boolean) => void } {
  let answer: (applied: boolean) => void = () => undefined;
  const write = new Promise<boolean>((resolve) => {
    answer = resolve;
  });
  return { write, answer };
}

/** Every promise under way settled. */
function settled(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(() => {
  gestureBegun();
});

describe("the writes a navigation waits for (#688)", () => {
  it("are none at first: a click goes at once", () => {
    expect(heldClick()).toBeUndefined();
  });

  it("are all waited for, those started meanwhile included, one refused enough to hold the navigation", async () => {
    const first = underWay();
    holdNavigation(first.write);
    const waited = heldClick();
    const second = underWay();
    holdNavigation(second.write);
    first.answer(true);
    await settled();
    second.answer(false);
    expect(await waited).toBe(false);
    gestureBegun();
    expect(heldClick()).toBeUndefined();
  });

  it("take a write that failed without an outcome for one not applied", async () => {
    holdNavigation(Promise.reject(new Error("the server of Next out of reach")));
    expect(await heldClick()).toBe(false);
  });

  it("hold the click of the gesture a write left in, though refused before the click arrives — not the click of a gesture begun after the refusal was told", async () => {
    const write = underWay();
    holdNavigation(write.write);
    write.answer(false);
    await settled();
    expect(await heldClick()).toBe(false);
    // The same gesture, its click made again, waits for nothing more.
    expect(heldClick()).toBeUndefined();
    holdNavigation(Promise.resolve(false));
    await settled();
    gestureBegun();
    expect(heldClick()).toBeUndefined();
  });

  it("let a click go at once when the writes of its gesture were all applied", async () => {
    holdNavigation(Promise.resolve(true));
    await settled();
    expect(heldClick()).toBeUndefined();
  });

  it("hold nothing once released by the screen that made them, under way or refused", async () => {
    const write = underWay();
    const release = holdNavigation(write.write);
    const waited = heldClick();
    release();
    expect(await waited).toBe(true);
    const refused = holdNavigation(Promise.resolve(false));
    await settled();
    refused();
    expect(heldClick()).toBeUndefined();
  });
});
