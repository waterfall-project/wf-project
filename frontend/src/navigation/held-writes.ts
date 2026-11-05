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
 * A write is released when what would tell its refusal is no longer shown (`release`): its screen
 * gone — left by « Précédent », by the router, or by a link while the write had not left yet —, or
 * the list it was asked from read otherwise, which tells a refusal on the reading it was asked from
 * alone. It holds no click then. One still under way, and refused after, is told by the bar of the
 * shell (`LeftRefusals`), which outlives every screen (#863): nothing is lost unsaid — save when
 * what asked it tells it still (`told`), a dialog left open telling the refusal at its fields, which
 * the bar does not say twice. One refused before its release was told where it was made, and is not
 * told again — save when its screen is `away` as the refusal arrives: left by « Précédent » or
 * « Suivant » for another path, and shown until the write answers, the router of Next waiting for it
 * when the write is awaited in a transition (`useHeldWrites`), it goes with what tells the refusal.
 * Brought back to its path after the refusal and before the router showed the entry traversed to —
 * « Suivant » pressed while the next page is read —, the screen never went and tells the refusal
 * itself: the bar, which told it meanwhile, takes it back (`broughtBack`, #1476), the history of
 * the messages noting it once, by the identity of its outcome. It is told twice in turn, the bar
 * first, the screen after; never twice at once.
 *
 * Each refusal the bar tells is kept with what the write answered — its outcome, when it gave one —
 * and the screen it was made on, for the bar to note it in the history of the messages
 * (`message-history.ts`, #1043), with its sentence: the outcome of a command is noted, its screen
 * gone or not.
 *
 * A store of the browser, outside React: the writes of a screen are held by the screen, the
 * navigation by the shell, and neither renders on the other's account.
 */

import type { Outcome } from "@/api/problem";
import type { MessageScreen } from "@/components/notices/message-history";

/** What a write answered: whether it was applied, or its outcome — applied when done. */
export type WriteAnswer = boolean | Outcome<unknown>;

/** A write refused once released: its refusal, when it answered one, and the screen it was made on. */
export interface LeftRefusal {
  readonly refusal: Exclude<Outcome<unknown>, { kind: "done" }> | undefined;
  readonly screen: MessageScreen | undefined;
}

/** Whether a write was applied, by what it answered. */
export function wasApplied(answer: WriteAnswer): boolean {
  return typeof answer === "boolean" ? answer : answer.kind === "done";
}

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

/** The writes refused once released, told nowhere else: the bar of the shell tells them. */
let leftRefused: readonly LeftRefusal[] = [];
/**
 * The refusals the bar tells only because their screen was away as they arrived: the `away` of
 * their screen, and whether that screen, brought back, tells the refusal itself.
 */
const keptAway = new WeakMap<LeftRefusal, { away: () => boolean; tells: () => boolean }>();
/** Those the count of the writes refused once released is told to. */
const listeners = new Set<() => void>();

/** Tell the count of the writes refused once released anew. */
function tellLeftRefusals(): void {
  for (const listener of listeners) {
    listener();
  }
}

/** The writes refused once released, not yet dismissed: the same list as long as none is added. */
export function refusedLeft(): readonly LeftRefusal[] {
  return leftRefused;
}

/** Listen to the count of the writes refused once released; gives back the end of it. */
export function onLeftRefusals(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Forget the writes refused once released: their notice has been read. */
export function dismissLeftRefusals(): void {
  if (leftRefused.length !== 0) {
    leftRefused = [];
    tellLeftRefusals();
  }
}

/**
 * The screen whose `away` is given is back on its path, never gone: the refusals the bar tells only
 * because it was away as they arrived, and which it tells itself — the write held still, or what
 * asked it telling it (`told`) —, are taken back from the bar (#1476).
 */
export function broughtBack(away: () => boolean): void {
  const kept = leftRefused.filter((each) => {
    const back = keptAway.get(each);
    return back?.away !== away || !back.tells();
  });
  if (kept.length !== leftRefused.length) {
    leftRefused = kept;
    tellLeftRefusals();
  }
}

/**
 * Hold the navigations of the page until a write has answered: whether it was applied, or its
 * outcome. Gives back its release, for the screen that made it to call when what tells its refusal
 * is no longer shown; refused after it, the write is kept among those the bar of the shell tells,
 * with the screen it was made on — unless `told` says, as the refusal arrives, that what asked the
 * write tells it itself. Refused while `away` says, as the refusal arrives, that its screen is left
 * and about to go with what tells it, the write is kept among them whatever `told` says, released
 * or not — and taken back from them if its screen is brought back before it went (`broughtBack`).
 * `told` is read only in the callbacks of `answered`, a promise derived from the write that settles a
 * turn after it, so that what asked the write may set what `told` reads in its own `then`: a reading
 * made at the resolution itself would come too early.
 */
export function holdNavigation(
  write: Promise<WriteAnswer>,
  told?: () => boolean,
  screen?: MessageScreen,
  away?: () => boolean,
): () => void {
  let release: () => void = () => undefined;
  const released = new Promise<boolean>((resolve) => {
    release = () => {
      resolve(true);
    };
  });
  // A write that fails without an outcome was not applied; one released holds nothing.
  const held: Held = { answer: Promise.race([write.then(wasApplied, () => false), released]) };
  underWay.add(held);
  ofGesture.add(held);
  for (const wait of waits) {
    wait.add(held);
  }
  void held.answer.then((applied) => {
    held.applied = applied;
    underWay.delete(held);
  });
  const answered = write.catch((): WriteAnswer => false);
  let isReleased = false;
  // Whether the screen tells the refusal itself: the write held still, or what asked it telling it.
  const tells = () => !isReleased || told?.() === true;
  // Kept once among the refusals the bar tells, whichever way it is found to be; kept while its
  // screen is away, it is taken back if the screen is brought back telling it.
  let kept = false;
  const keep = (answer: WriteAnswer, whileAway: boolean) => {
    if (kept || wasApplied(answer)) {
      return;
    }
    kept = true;
    const refusal = typeof answer === "boolean" || answer.kind === "done" ? undefined : answer;
    const each: LeftRefusal = { refusal, screen };
    if (whileAway && away !== undefined) {
      keptAway.set(each, { away, tells });
    }
    leftRefused = [...leftRefused, each];
    tellLeftRefusals();
  };
  void answered.then((answer) => {
    if (!isReleased && away?.() === true) {
      keep(answer, true);
    }
  });
  return () => {
    if (underWay.has(held)) {
      // Under way as it is released: refused after, it is told by the bar of the shell, unless what
      // asked it tells it still on a screen not left.
      void answered.then((answer) => {
        const gone = away?.() === true;
        if (gone || told?.() !== true) {
          keep(answer, gone);
        }
      });
    }
    isReleased = true;
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
