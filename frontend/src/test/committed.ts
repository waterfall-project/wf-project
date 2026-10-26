// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the page said of itself in the commit that first showed an answer (#1484). An update made
 * after an await, in `startTransition(async …)`, does not belong to the transition: it is painted
 * in a commit of its own, and the end of the transition in a later one. Between the two, the
 * answer is shown while what `pending` holds — a press, Escape, a control made inactive — is still
 * held. The observer reads the page in the microtask that follows each commit, before the next
 * task of React's scheduler: it sees the commit that shows the answer, never only the last.
 */

/** Read `read` once, in the first commit under `root` where `shown` holds; `stop` gives it. */
export function atCommit(
  root: Node,
  shown: () => boolean,
  read: () => string | null,
): { readonly stop: () => readonly (string | null)[] } {
  const seen: (string | null)[] = [];
  const observer = new MutationObserver(() => {
    if (seen.length === 0 && shown()) {
      seen.push(read());
    }
  });
  observer.observe(root, { subtree: true, childList: true, attributes: true, characterData: true });
  return {
    stop: () => {
      observer.disconnect();
      return seen;
    },
  };
}
