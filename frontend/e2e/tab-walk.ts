// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A page walked by the keyboard alone (WF-IHM-0100): Tab, pressed from where the focus is, until
 * the focus comes back to the first element it reached. What the walk says of a page, the page
 * measuring each element as the focus reaches it (`focus-probe.ts`):
 *
 * - each element the focus reaches is seen: it is shown, not transparent, and the middle of what is
 *   left of it once the window and the padding box of every box that clips it have cut it is the
 *   element itself — nothing that paints is drawn over it, a layer the pointer passes through
 *   included; and nothing takes the pointer there instead of it, a transparent layer that catches
 *   the clicks included;
 * - each wears an indicator of its focus: an outline or a shadow it did not wear before the walk —
 *   when nothing had the focus —, or wears no more once the focus left it, which is not
 *   transparent, not cut by a box that clips it, nor, inside it, under what paints over it — what it
 *   holds, for an inset shadow, a positioned element, for an outline; an element born during the
 *   walk and gone once left cannot be judged, and is said so;
 * - no element is reached twice before the first again: that would be a loop the focus cannot
 *   leave, a trap; a field made of fields — the day, the month and the year of a date — keeps the
 *   focus from one to the next, which is no trap unless it keeps it longer than any could;
 * - every element the page lets Tab reach — shown, enabled, in the order of the keyboard — is
 *   reached itself, a widget that moves the focus among its items — a group of radios — when the
 *   focus lands in it; every such widget is entered; none lies wholly beyond the edge of a box that
 *   hides what overflows it, which the browser scrolls to the focus but a pointer never reaches — a
 *   box the user scrolls is no such edge for what it scrolls to;
 * - no link nor button is taken out of the order of the keyboard, but in such a widget.
 *
 * What it reached is said by role and name, in order: the same page walked in a narrower window
 * must reach all of it again (`lost`). Leaving the last element, the focus leaves the document a
 * moment for the browser, then comes back to the first. The tools of the development server of
 * Next (`nextjs-portal`), which the built front does not have, are passed by without a look.
 */
import type { Page } from "@playwright/test";

import { finishWalk, type Focus, focusNow, startWalk } from "./focus-probe";

/** What a walk saw, each element said by its role and its name. */
export interface Walk {
  /** The elements the focus reached, in order, before it came back to the first. */
  readonly reached: readonly string[];
  /** The elements reached that the window did not show, and why. */
  readonly unseen: readonly string[];
  /** The elements reached where something else takes the pointer, and what. */
  readonly covered: readonly string[];
  /** The elements reached that wore no indicator of the focus that shows. */
  readonly unmarked: readonly string[];
  /** The elements born during the walk and gone once left, whose focus could not be judged. */
  readonly unjudged: readonly string[];
  /** The element reached a second time before the first again, if any: a trap. */
  readonly trapped: string | undefined;
  /** The elements Tab may reach that it never reached. */
  readonly missed: readonly string[];
  /** The widgets that move the focus among their items, which the walk never entered. */
  readonly stopless: readonly string[];
  /** The elements Tab may reach wholly beyond the edge of a box that hides what overflows it. */
  readonly clipped: readonly string[];
  /** The links and buttons out of the order of the keyboard, in no widget that moves the focus. */
  readonly untabbable: readonly string[];
}

/**
 * More presses than any screen has elements to reach: a walk that has not come back by then
 * never will.
 */
const PRESSES = 600;

/** More presses than a field of the browser holds fields — a date and its time, six at most. */
const FIELDS = 8;

/** What a walk has seen so far, and where it stands. */
interface Tally {
  readonly reached: string[];
  readonly unseen: string[];
  readonly covered: string[];
  readonly unmarked: string[];
  readonly unjudged: string[];
  readonly visited: Set<number>;
  first: number | undefined;
  previous: number | undefined;
  held: number;
  trapped: string | undefined;
  /** Whether the focus came back to the first element. */
  back: boolean;
}

/** Note what the page says of the focus of an element once it was left. */
function settle(tally: Tally, focus: Focus): void {
  if (focus.settled === undefined) {
    return;
  }
  if (focus.settled.marked === undefined) {
    tally.unjudged.push(focus.settled.said);
  } else if (!focus.settled.marked) {
    tally.unmarked.push(focus.settled.said);
  }
}

/** Note what one press of Tab brought: an element reached, the first again, a trap, or nothing. */
function take(tally: Tally, focus: Focus): void {
  settle(tally, focus);
  if (focus.kind !== "element") {
    tally.previous = undefined;
    return;
  }
  if (focus.id === tally.previous) {
    tally.held += 1;
    tally.trapped = tally.held < FIELDS ? undefined : `${focus.said}, holding the focus`;
    return;
  }
  tally.held = 0;
  tally.previous = focus.id;
  if (focus.id === tally.first) {
    tally.back = true;
    return;
  }
  if (tally.visited.has(focus.id)) {
    tally.trapped = focus.said;
    return;
  }
  tally.first ??= focus.id;
  tally.visited.add(focus.id);
  tally.reached.push(focus.said);
  const notes = [
    [tally.unseen, focus.unseen],
    [tally.covered, focus.covered],
  ] as const;
  for (const [list, why] of notes) {
    if (why !== undefined) {
      list.push(`${focus.said}, ${why}`);
    }
  }
  if (focus.marked === false) {
    tally.unmarked.push(focus.said);
  }
}

/**
 * Walk the page by Tab from where the focus is, until it comes back to the first element it
 * reached, and say what the walk saw.
 */
export async function walkByTab(page: Page): Promise<Walk> {
  const { clipped, untabbable } = await startWalk(page);
  const tally: Tally = {
    reached: [],
    unseen: [],
    covered: [],
    unmarked: [],
    unjudged: [],
    visited: new Set(),
    first: undefined,
    previous: undefined,
    held: 0,
    trapped: undefined,
    back: false,
  };
  for (let press = 0; press < PRESSES && !tally.back && tally.trapped === undefined; press += 1) {
    await page.keyboard.press("Tab");
    take(tally, await focusNow(page));
  }
  if (!tally.back) {
    tally.trapped ??= `no way back to the first element after ${String(PRESSES)} presses`;
  }
  const { missed, stopless } = await finishWalk(page);
  const { reached, unseen, covered, unmarked, unjudged, trapped } = tally;
  return {
    reached,
    unseen,
    covered,
    unmarked,
    unjudged,
    trapped,
    missed,
    stopless,
    clipped,
    untabbable,
  };
}

/**
 * What a walk reached that another no longer reaches, element by element, an element reached
 * twice counting twice: what a narrower window took out of the reach of the keyboard.
 */
export function lost(before: readonly string[], after: readonly string[]): string[] {
  const left = [...after];
  return before.filter((said) => {
    const index = left.indexOf(said);
    if (index === -1) {
      return true;
    }
    left.splice(index, 1);
    return false;
  });
}
