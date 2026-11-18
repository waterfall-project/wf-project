// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A part of a screen the server reads apart from the rest — the indicators above a grid —, shown
 * without ever holding back a navigation of the screen (US-2290, #3630).
 *
 * A filter navigates in a transition. A `Suspense` boundary already revealed does not show its
 * fallback again in a transition: React keeps what it shows and retains the whole transition — the
 * address, the grid — until what suspended is ready. So a part streamed in a boundary of its own,
 * read at each navigation, held the address of a filter that does not change it exactly as if it
 * had been awaited by the page. `Streamed` reads its content when it first appears, in the
 * boundary of the caller, which shows its fallback; once it has shown it, a content that arrives
 * with a later navigation is not read in the render but when it is ready, and the content shown
 * stays until then. A caller whose content depends on what a navigation changes puts a `key` on the
 * boundary: that boundary is a new one, and shows its fallback rather than the figures of another
 * reading.
 */
"use client";

import { type ReactNode, use, useEffect, useState } from "react";

/** What a content read came to: the content, or the failure to throw where it is shown. */
type Settled = { readonly node: ReactNode } | { readonly failure: Error };

/** The first reading of the content, the one that suspends the boundary of the caller. */
function First({ content }: { readonly content: Promise<ReactNode> }): ReactNode {
  return use(content);
}

/**
 * The content, a promise of what the server renders — an element, or null — shown as soon as it is
 * read the first time, and, from the second, once it is ready, the previous one kept in the
 * meantime. A failure to read it is thrown to the error boundary of the screen, as the first one:
 * the screen of failure, which says the session required or the correlation identifier by the
 * digest of the error.
 */
export function Streamed({ content }: { readonly content: Promise<ReactNode> }): ReactNode {
  const [settled, setSettled] = useState<Settled | undefined>(undefined);
  useEffect(() => {
    // The content of a navigation that a later one has replaced says nothing more (defect n° 1).
    let current = true;
    content.then(
      (node) => {
        if (current) {
          setSettled({ node });
        }
      },
      (failure: unknown) => {
        if (current) {
          setSettled({ failure: failure instanceof Error ? failure : new Error(String(failure)) });
        }
      },
    );
    return () => {
      current = false;
    };
  }, [content]);
  // A second navigation that comes before the effect of the first has run finds `settled` still
  // undefined: `First` then reads the content and suspends that transition until it is ready. A
  // window of a few milliseconds after the first appearance, accepted.
  if (settled === undefined) {
    return <First content={content} />;
  }
  if ("failure" in settled) {
    throw settled.failure;
  }
  return settled.node;
}
