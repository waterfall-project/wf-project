// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cards of figures of a screen, folded into a summary that unfolds (US-0710, #1209): a window
 * narrower than the large breakpoint — what a zoom of 150 % leaves of a laptop's — has no room for
 * two rows of cards above a grid whose totals must stay in view. Open from the large breakpoint
 * up, folded below; what the reader chose stays until the width crosses the breakpoint again.
 */
"use client";

import { type ReactNode, useLayoutEffect, useRef, useSyncExternalStore } from "react";

/** The width from which the cards stay unfolded, in CSS pixels (Tailwind's `lg`). */
const LARGE = "(min-width: 1024px)";

function subscribe(notify: () => void): () => void {
  const query = window.matchMedia(LARGE);
  query.addEventListener("change", notify);
  return () => {
    query.removeEventListener("change", notify);
  };
}

/** Whether the window is large; open on the server, where no width is known. */
function useLarge(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(LARGE).matches,
    () => true,
  );
}

/** The cards in `children`, under a summary named `title`. */
export function FoldingFigures({
  title,
  children,
}: {
  readonly title: string;
  readonly children: ReactNode;
}) {
  const large = useLarge();
  const details = useRef<HTMLDetailsElement>(null);
  // Set on the element, not through a prop or a key: crossing the breakpoint sets the summary
  // anew without remounting the cards (nothing they hold is lost), and the reader's own
  // toggling stays in the element until then.
  useLayoutEffect(() => {
    if (details.current !== null) {
      details.current.open = large;
    }
  }, [large]);
  return (
    <details ref={details} className="text-sm">
      <summary className="cursor-pointer text-muted-foreground">{title}</summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}
