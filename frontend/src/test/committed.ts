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

/** The text of what describes `element`, by the identifiers its `aria-describedby` names. */
function description(element: Element): string {
  return (element.getAttribute("aria-describedby") ?? "")
    .split(/\s+/)
    .filter((id) => id !== "")
    .map((id) => element.ownerDocument.getElementById(id)?.textContent ?? "")
    .join(" ")
    .trim();
}

/**
 * What describes `field` each time it takes the focus, `stop` giving them (#1484). A field refused
 * takes the focus once the commit that says its refusal is made: taken before, a reader of the screen
 * announces it without its refusal. It only sees the focuses that arrive after it is called: a field
 * already focused when it is called is not read.
 */
export function atFocus(field: Element): { readonly stop: () => readonly string[] } {
  const seen: string[] = [];
  const focused = () => {
    seen.push(description(field));
  };
  field.addEventListener("focus", focused);
  return {
    stop: () => {
      field.removeEventListener("focus", focused);
      return seen;
    },
  };
}
