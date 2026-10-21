// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading anew that follows a write, held as Next holds it: `router.refresh()` starts a
 * transition that stays pending until the server answers. A test wraps the grid in `Reading`, makes
 * the next `refresh` of its router double a reading held (`holdReading`), and lets it go
 * (`releaseReading`). Given the grid read anew, it commits it in the very commit that ends the
 * transition, the rows and the end of the reading together, as Next does; given none, it ends the
 * transition alone, the rows the test rendered by `rerender` having come before it — an urgent
 * update, which does not wait for the transition.
 * A module of the browser: tests of the project `dom` alone import it, each file its own reading.
 */
"use client";

import { type ReactNode, use, useEffect, useState } from "react";
import type { Mock } from "vitest";

/** The grid read anew, shown over the grid the wrapper was given when the reading was let go. */
interface Arrival {
  readonly shown: ReactNode;
  readonly over: ReactNode;
}

/** How the reading of the grid rendered is suspended, and how the reading held is let go. */
const reading: {
  suspend?: (wait: Promise<void>) => void;
  resume?: () => void;
  /** What the wrapper last rendered. */
  latest?: ReactNode;
  arrival?: Arrival | undefined;
} = {};

/** Wrap a grid so that a reading held keeps its transition pending until `releaseReading()`. */
export function Reading({ children }: { readonly children: ReactNode }) {
  const [wait, suspend] = useState<Promise<void>>();
  useEffect(() => {
    reading.suspend = suspend;
  }, [suspend]);
  useEffect(() => {
    reading.latest = children;
  });
  if (wait !== undefined) {
    use(wait);
  }
  // The grid read anew stands while the test renders no other: a later `rerender` takes over.
  const { arrival } = reading;
  return arrival !== undefined && arrival.over === children ? arrival.shown : children;
}

/** Make the next calls of a router double's `refresh` readings that last until `releaseReading()`. */
export function holdReading(refresh: Mock): void {
  refresh.mockImplementation(() => {
    reading.suspend?.(
      new Promise<void>((resolve) => {
        reading.resume = resolve;
      }),
    );
  });
}

/**
 * Let the reading held go, if one is, with the grid read anew if one is given: the transition ends
 * in the commit that shows it.
 */
export function releaseReading(read?: ReactNode): void {
  if (read !== undefined) {
    reading.arrival = { shown: read, over: reading.latest };
  }
  reading.resume?.();
  delete reading.resume;
}
