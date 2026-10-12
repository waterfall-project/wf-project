// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The writes a navigation waits for (#688, « ne perd rien en silence »): a cell left for a link of
 * the side bar is validated as the pointer goes down on the link, and its write leaves before the
 * click arrives — a command pressed, a paste applied, just before. The navigation waits until every
 * such write has answered; one refused — whatever the refusal, a session lost among them —, the
 * navigation does not take place: the screen says the refusal where the write was made, and the
 * person decides, the way to sign in again included. Each write says here whether it was applied.
 *
 * A click is judged by its gesture, which begins as the pointer goes down or a key is pressed
 * (`gestureBegun`): it waits for the writes still under way, and for every write that left since
 * its gesture began, answered or not. A session lost answers in a few milliseconds, before the
 * click of the gesture that validated the cell: the refusal already arrived holds that click all
 * the same. A write answered before the gesture began holds nothing: its refusal was told, and the
 * person, who saw it, decides.
 *
 * A write is released when the screen that made it goes (`release`): what it answers is told
 * nowhere, and holds no click of the next screen.
 *
 * A store of the browser, outside React: the writes of a screen are held by the screen, the
 * navigation by the shell, and neither renders on the other's account.
 */

/** A write a navigation waits for: whether it was applied, once answered. */
interface Held {
  readonly answer: Promise<boolean>;
  applied?: boolean;
}

/** The writes not answered yet. */
const underWay = new Set<Held>();
/** The writes that left since the gesture under way began, answered or not. */
let ofGesture = new Set<Held>();
/** The writes the clicks held meanwhile wait for, each set given those that leave meanwhile. */
const waits = new Set<Set<Held>>();

/**
 * Hold the navigations of the page until a write has answered: whether it was applied. Gives back
 * its release, for the screen that made it to call when it goes.
 */
export function holdNavigation(write: Promise<boolean>): () => void {
  let release: () => void = () => undefined;
  const released = new Promise<boolean>((resolve) => {
    release = () => {
      resolve(true);
    };
  });
  // A write that fails without an outcome was not applied; one released holds nothing.
  const held: Held = { answer: Promise.race([write.catch(() => false), released]) };
  underWay.add(held);
  ofGesture.add(held);
  for (const wait of waits) {
    wait.add(held);
  }
  void held.answer.then((applied) => {
    held.applied = applied;
    underWay.delete(held);
  });
  return () => {
    release();
    underWay.delete(held);
    ofGesture.delete(held);
  };
}

/** A gesture begins — a pointer goes down, a key is pressed —: its click waits for what it leaves. */
export function gestureBegun(): void {
  ofGesture = new Set();
}

/**
 * What a click of the gesture under way waits for before it navigates: whether every write it
 * waits for was applied — those that leave meanwhile included —, or nothing when it waits for none.
 * The gesture is judged once: a click made again in its name waits only for what is under way.
 */
export function heldClick(): Promise<boolean> | undefined {
  const waited = new Set([...ofGesture, ...underWay]);
  ofGesture = new Set();
  if ([...waited].every((held) => held.applied === true)) {
    return undefined;
  }
  return allApplied(waited);
}

/** Whether every write waited for was applied, once all answered, those added meanwhile included. */
async function allApplied(waited: Set<Held>): Promise<boolean> {
  waits.add(waited);
  try {
    const answered = new Set<Held>();
    let applied = true;
    while (answered.size < waited.size) {
      const waiting = [...waited].filter((held) => !answered.has(held));
      const answers = await Promise.all(waiting.map((held) => held.answer));
      for (const held of waiting) {
        answered.add(held);
      }
      applied &&= answers.every(Boolean);
    }
    return applied;
  } finally {
    waits.delete(waited);
  }
}
