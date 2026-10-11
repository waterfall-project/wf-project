// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The writes under way in the page, which a navigation waits for (#688, « ne perd rien en
 * silence »): a cell left for a link of the side bar is validated as the focus leaves it, and its
 * write is under way when the click arrives. The navigation waits until every write has answered;
 * one refused — whatever the refusal, a session lost among them —, the navigation does not take
 * place: the screen says the refusal where the write was made, and the person decides, the way to
 * sign in again included. Each write says here whether it was applied.
 *
 * A store of the browser, outside React: the writes of a screen are held by the screen, the
 * navigation by the shell, and neither renders on the other's account.
 */

/** The writes under way, each to say whether it was applied. */
const underWay = new Set<Promise<boolean>>();

/** Hold the navigations of the page until a write has answered: whether it was applied. */
export function holdNavigation(write: Promise<boolean>): void {
  // A write that fails without an outcome was not applied.
  const applied = write.catch(() => false);
  underWay.add(applied);
  void applied.finally(() => underWay.delete(applied));
}

/** Whether a write is under way: a navigation then waits for it. */
export function writesUnderWay(): boolean {
  return underWay.size > 0;
}

/**
 * Wait until every write under way has answered — those started meanwhile included —: whether all
 * of them were applied, which a navigation needs to take place.
 */
export async function writesApplied(): Promise<boolean> {
  let applied = true;
  while (underWay.size > 0) {
    const waiting = [...underWay];
    const answers = await Promise.all(waiting);
    for (const write of waiting) {
      underWay.delete(write);
    }
    applied &&= answers.every(Boolean);
  }
  return applied;
}
