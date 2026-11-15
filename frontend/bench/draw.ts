// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The draw of the load of fifty users (US-2300, `load.ts`): when each virtual user makes its next
 * gesture, and which. Pure, so that k6 runs it in the load and Vitest tries it (`draw.test.ts`);
 * nothing of k6 here, which Node does not have.
 *
 * A user pauses between five and fifteen seconds before each gesture, ten on average — the
 * fifty users active of §4.6.2, never fifty requests at once (decision of the author, 2026-11-14) —,
 * and makes nine readings for one entry: each run of ten gestures holds one entry, at a place of
 * the run drawn anew, so that the proportion is exact over every ten gestures and the entries of
 * the users do not fall together. The draw is reproducible: the same seed and the same user give
 * the same gestures, run after run; two users, different ones.
 */

/** The shortest and the longest pause before a gesture, in seconds. */
export const PAUSE = { least: 5, most: 15 } as const;

/** How many readings for one entry. */
export const READS_PER_WRITE = 9;

/** A gesture of a user: the pause before it, in seconds, then a reading or an entry, and which. */
export interface Gesture {
  readonly pause: number;
  readonly kind: "read" | "write";
  /** Which of the readings or of the entries, from 0. */
  readonly choice: number;
}

/** How many readings and entries a user chooses among. */
export interface Choices {
  readonly reads: number;
  readonly writes: number;
}

/**
 * A generator of numbers in [0, 1) from a seed of 32 bits: Mulberry32, enough for a draw of
 * pauses, and the same on every engine — `Math.random` of k6 is not seeded per user.
 */
export function generator(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let mixed = Math.imul(state ^ (state >>> 15), state | 1);
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4_294_967_296;
  };
}

/** The seed of a user: the seed of the load and its number mixed, so that users differ. */
function userSeed(seed: number, user: number): number {
  return Math.imul(seed ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(user, 0xc2b2ae35);
}

/** A whole number in [0, count), from a draw in [0, 1). */
function among(draw: number, count: number): number {
  return Math.min(count - 1, Math.floor(draw * count));
}

/**
 * The gestures of a user, one at each call: the seed of the load and the number of the user, from
 * 1, fix them all. `choices` says among how many readings and entries each is drawn.
 */
export function gestures(seed: number, user: number, choices: Choices): () => Gesture {
  if (choices.reads < 1 || choices.writes < 1) {
    throw new Error("a user chooses among one reading and one entry at least");
  }
  const random = generator(userSeed(seed, user));
  const run = READS_PER_WRITE + 1;
  let made = 0;
  let entryAt = 0;
  return () => {
    const place = made % run;
    if (place === 0) {
      entryAt = among(random(), run);
    }
    made += 1;
    const pause = PAUSE.least + random() * (PAUSE.most - PAUSE.least);
    const kind = place === entryAt ? "write" : "read";
    const choice = among(random(), kind === "write" ? choices.writes : choices.reads);
    return { pause, kind, choice };
  };
}
